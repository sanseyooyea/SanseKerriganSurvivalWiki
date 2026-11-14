/**
 * 录像上传与解析队列。
 *
 * 服务器是 2C2G 无 swap，容器 mem_limit 768m。内存预算：
 *   Node 常驻 ~150–250MB + 上传缓冲 ≤5MB（流式读取，见 index.post.ts）+ 一个解析子进程 ≤ PARSE_MEM_MB
 * 所以：
 *  - 同一时刻只跑 1 个解析子进程（实测峰值 RSS ~260MB），其余排队；
 *  - 子进程用 --max-mem-mb 自限地址空间（默认 380MB），超限自己退出（exit 4），
 *    总量落在 768m 内，不触发容器 OOM killer；
 *  - 子进程硬超时，超时 SIGKILL；
 *  - 每个任务最多尝试 MAX_ATTEMPTS 次：即便某个录像真把容器搞崩了，重启后也不会无限重试；
 *  - 解析结果直接写 gzip（~300KB/局），读取时原样以 Content-Encoding: gzip 下发，不占 CPU；
 *  - 录像目录总量超配额时按上传时间淘汰最旧的。
 *
 * 状态存在 wiki.db 的 replays 表（随定时备份）；文件在 data/replays/（不进备份，可重新上传）。
 */
import { spawn } from 'child_process'
import { join } from 'path'
import { existsSync, mkdirSync, unlinkSync, statSync, readdirSync } from 'fs'
import { getDb } from '~/server/utils/db'

export const REPLAY_DIR = join(process.cwd(), 'data', 'replays')
const PARSER = join(process.cwd(), 'scripts', 'replay', 'parse_replay.py')
const PYTHON = process.env.REPLAY_PYTHON || (process.platform === 'win32' ? 'python' : 'python3')

/** 单个上传上限。KS2 实际录像 0.15–2MB，留余量 */
export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024
/** 解析子进程地址空间上限（MB）。实测峰值 RSS ~260MB，VSZ 略高，380 留出余量又守住总预算 */
const PARSE_MEM_MB = Number(process.env.REPLAY_PARSE_MEM_MB || 380)
const PARSE_TIMEOUT_MS = Number(process.env.REPLAY_PARSE_TIMEOUT_MS || 90_000)
/** 原始录像 + 解析结果的总量上限 */
const MAX_TOTAL_BYTES = Number(process.env.REPLAY_MAX_TOTAL_MB || 2048) * 1024 * 1024
/** 全站排队上限；再多就直接拒绝 */
export const MAX_QUEUED = 30
/** 单个用户同时在队列里的上限 */
export const MAX_QUEUED_PER_USER = 3
/** 同一任务最多尝试几次（含因进程崩溃/重启而中断的） */
const MAX_ATTEMPTS = 2

export type ReplayStatus = 'queued' | 'processing' | 'done' | 'failed'

export interface ReplayRow {
  hash: string
  status: ReplayStatus
  error: string
  uploader_id: number | null
  file_name: string
  size: number
  json_size: number
  attempts: number
  summary: string | null
  created_at: string
  parsed_at: string | null
}

export const rawPath = (hash: string) => join(REPLAY_DIR, `${hash}.SC2Replay`)
export const jsonPath = (hash: string) => join(REPLAY_DIR, `${hash}.json.gz`)
const partPath = (hash: string) => jsonPath(hash) + '.part'

export function isValidHash(h: string) {
  return /^[a-f0-9]{32}$/.test(h)
}

const EXIT_MESSAGES: Record<number, string> = {
  2: '不是凯瑞甘生存2的录像',
  3: '录像文件损坏或版本不受支持',
  4: '录像过大，解析超出服务器内存上限',
}

function safeUnlink(p: string) {
  try { unlinkSync(p) } catch {}
}

export function prepareStorage() {
  if (!existsSync(REPLAY_DIR)) mkdirSync(REPLAY_DIR, { recursive: true })
}

// ---------------- 队列 ----------------

let running = false
let recovered = false

/**
 * 进程启动后首次调用时：
 *  - 上次没跑完的 processing（进程被杀/崩溃）放回队列；已达尝试上限的直接判失败，
 *    防止「解析这个录像 → 容器崩溃 → 重启 → 再解析」死循环；
 *  - 清掉残留的 .part 临时文件。
 */
function recoverOnce() {
  if (recovered) return
  recovered = true
  rebuildReplayPlayersOnce()
  const db = getDb()
  db.prepare(`
    UPDATE replays SET status = 'failed', error = '解析时服务异常中断', parsed_at = datetime('now')
    WHERE status = 'processing' AND attempts >= ?`).run(MAX_ATTEMPTS)
  db.prepare(`UPDATE replays SET status = 'queued' WHERE status = 'processing'`).run()
  try {
    for (const f of readdirSync(REPLAY_DIR)) {
      if (f.endsWith('.part')) safeUnlink(join(REPLAY_DIR, f))
    }
  } catch {}
}

/** 唤醒队列；已在运行则直接返回（单 worker） */
export function kickQueue() {
  recoverOnce()
  if (running) return
  running = true
  // 放到下一轮事件循环，不阻塞调用方请求的响应
  setImmediate(drain)
}

async function drain() {
  const db = getDb()
  let current: string | null = null
  try {
    for (;;) {
      const job = db.prepare(
        `SELECT hash FROM replays WHERE status = 'queued' ORDER BY created_at, rowid LIMIT 1`,
      ).get() as { hash: string } | undefined
      if (!job) break
      current = job.hash
      // 先记尝试次数再开跑：进程若在解析中途被杀，重启后能看到这次尝试
      db.prepare(`UPDATE replays SET status = 'processing', attempts = attempts + 1 WHERE hash = ?`).run(job.hash)
      const res = await runParser(job.hash)
      if (res.ok) {
        let jsonSize = 0
        try { jsonSize = statSync(jsonPath(job.hash)).size } catch {}
        db.prepare(`
          UPDATE replays SET status = 'done', error = '', summary = ?, json_size = ?, parsed_at = datetime('now')
          WHERE hash = ?`).run(res.summary, jsonSize, job.hash)
        indexReplayPlayers(job.hash, res.summary)
        enforceQuota()
      } else {
        markFailed(job.hash, res.error)
      }
      current = null
    }
  } catch (e) {
    console.error('[replays] 队列异常', e)
    // 别让当前任务永远卡在 processing（recoverOnce 本进程内只跑一次）
    if (current) { try { markFailed(current, '服务内部错误，请重新上传') } catch {} }
  } finally {
    running = false
  }
}

function markFailed(hash: string, error: string) {
  getDb().prepare(`
    UPDATE replays SET status = 'failed', error = ?, size = 0, json_size = 0, summary = NULL,
      parsed_at = datetime('now') WHERE hash = ?`).run(error, hash)
  // 失败的文件没有保留价值；size 清零让配额统计与磁盘一致
  safeUnlink(rawPath(hash))
  safeUnlink(jsonPath(hash))
  safeUnlink(partPath(hash))
}

function runParser(hash: string): Promise<{ ok: true; summary: string } | { ok: false; error: string }> {
  return new Promise((resolve) => {
    const out = jsonPath(hash)
    const child = spawn(PYTHON, [
      '-I', // 隔离模式：不读用户 site-packages / PYTHON* 环境变量 / 当前目录
      PARSER, rawPath(hash),
      '-o', out, '--summary', '--max-mem-mb', String(PARSE_MEM_MB),
    ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })

    let stdout = ''
    let stderr = ''
    let timedOut = false
    child.stdout.on('data', (d) => { if (stdout.length < 64_000) stdout += d })
    child.stderr.on('data', (d) => { if (stderr.length < 8_000) stderr += d })

    const timer = setTimeout(() => { timedOut = true; child.kill('SIGKILL') }, PARSE_TIMEOUT_MS)

    child.on('error', (err) => {
      clearTimeout(timer)
      console.error('[replays] 无法启动解析器', err)
      resolve({ ok: false, error: '服务器解析组件不可用，请联系管理员' })
    })
    child.on('close', (code, signal) => {
      clearTimeout(timer)
      if (code === 0) {
        const line = stdout.trim().split('\n').pop() || ''
        try {
          JSON.parse(line)
          resolve({ ok: true, summary: line })
        } catch {
          resolve({ ok: false, error: '解析器输出异常' })
        }
        return
      }
      if (timedOut) {
        resolve({ ok: false, error: '解析超时' })
        return
      }
      if (signal) {
        // 不是我们杀的：多半是容器 OOM killer
        console.error(`[replays] 解析 ${hash} 被信号 ${signal} 终止`)
        resolve({ ok: false, error: '录像过大，解析超出服务器内存上限' })
        return
      }
      const known = code != null ? EXIT_MESSAGES[code] : undefined
      if (!known) console.error(`[replays] 解析 ${hash} 失败 code=${code}\n${stderr.slice(-2000)}`)
      resolve({ ok: false, error: known || '解析失败' })
    })
  })
}

// ---------------- 存储配额 ----------------

/** 总量超限时，按上传时间从旧到新淘汰已完成的录像（失败的已在 markFailed 删掉文件、size 清零） */
export function enforceQuota() {
  const db = getDb()
  const total = (db.prepare(
    `SELECT COALESCE(SUM(size + json_size), 0) AS t FROM replays WHERE status = 'done'`,
  ).get() as { t: number }).t
  if (total <= MAX_TOTAL_BYTES) return
  let excess = total - MAX_TOTAL_BYTES
  const victims = db.prepare(
    `SELECT hash, size + json_size AS bytes FROM replays WHERE status = 'done' ORDER BY created_at, rowid`,
  ).all() as { hash: string; bytes: number }[]
  for (const v of victims) {
    if (excess <= 0) break
    deleteReplay(v.hash)
    excess -= v.bytes
  }
}

export function deleteReplay(hash: string) {
  safeUnlink(rawPath(hash))
  safeUnlink(jsonPath(hash))
  safeUnlink(partPath(hash))
  const db = getDb()
  db.prepare(`DELETE FROM replay_players WHERE hash = ?`).run(hash)
  db.prepare(`DELETE FROM replays WHERE hash = ?`).run(hash)
}

// ---------------- 玩家战绩索引 ----------------

/** 句柄格式：区服-S2-1-数字，如 5-S2-1-11514035 */
export function isValidHandle(h: string) {
  return /^[1-6]-S2-[12]-\d{1,12}$/i.test(h)
}

/** 把一局 summary 里的玩家战绩写进 replay_players（幂等：先删后插） */
export function indexReplayPlayers(hash: string, summaryJson: string | null) {
  if (!summaryJson) return
  let s: any
  try { s = JSON.parse(summaryJson) } catch { return }
  const players: any[] = Array.isArray(s?.players) ? s.players : []
  const db = getDb()
  const ins = db.prepare(`
    INSERT INTO replay_players (hash, pid, handle, name, role, role_en, team, won, mmr_before, mmr_after,
      hero_death_loop, kills, hero_damage, minerals, gas_fed, apm, upgrades, loops, map_key, played_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
  const num = (v: any) => (typeof v === 'number' && Number.isFinite(v) ? v : null)
  db.transaction(() => {
    db.prepare(`DELETE FROM replay_players WHERE hash = ?`).run(hash)
    for (const p of players) {
      // 只收有效句柄的人类玩家（老格式 summary 没有 handle，跳过）
      if (!p?.handle || !isValidHandle(p.handle)) continue
      ins.run(
        hash, num(p.pid) ?? 0, String(p.handle).toUpperCase(), String(p.name ?? '').slice(0, 64),
        p.role ?? null, p.roleEn ?? null, num(p.team),
        p.won === true ? 1 : p.won === false ? 0 : null,
        num(p.mmrBefore), num(p.mmrAfter), num(p.heroDeathLoop), num(p.kills), num(p.heroDamage),
        num(p.minerals), num(p.gasFed), num(p.apm), num(p.upgrades),
        num(s.loops), s.mapKey ?? null, s.date ?? null,
      )
    }
  })()
}

/** 用现有 summary 重建整张 replay_players（服务启动后首次调用；表结构变更或老数据补录用） */
let rebuilt = false
export function rebuildReplayPlayersOnce() {
  if (rebuilt) return
  rebuilt = true
  const db = getDb()
  const rows = db.prepare(`SELECT hash, summary FROM replays WHERE status = 'done'`).all() as
    { hash: string; summary: string | null }[]
  for (const r of rows) indexReplayPlayers(r.hash, r.summary)
}

/** 对外展示用：summary 字段从 JSON 字符串展开 */
export function publicRow(r: ReplayRow, meId = 0) {
  let summary = null
  if (r.summary) { try { summary = JSON.parse(r.summary) } catch {} }
  return {
    hash: r.hash,
    status: r.status,
    error: r.error || '',
    fileName: r.file_name,
    createdAt: r.created_at,
    parsedAt: r.parsed_at,
    uploader: (r as any).uploader_name ?? null,
    mine: !!meId && r.uploader_id === meId,
    summary,
  }
}
