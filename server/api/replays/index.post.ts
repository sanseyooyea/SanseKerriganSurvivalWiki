import { createHash } from 'crypto'
import { writeFileSync } from 'fs'
import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'
import {
  MAX_UPLOAD_BYTES, MAX_QUEUED, MAX_QUEUED_PER_USER, rawPath, kickQueue, prepareStorage, publicRow,
  type ReplayRow,
} from '~/server/utils/replays'

// 每个用户每小时最多 20 次成功入队；另限每小时 60 次请求（含重复文件），防止拿同一文件反复刷带宽。
// 管理员不限。
const HOUR = 60 * 60 * 1000
const QUEUE_MAX = 20
const ATTEMPT_MAX = 60
const queuedAt = new Map<number, number[]>()
const attemptAt = new Map<number, number[]>()

function within(map: Map<number, number[]>, id: number, max: number, commit: boolean): boolean {
  const now = Date.now()
  const ts = (map.get(id) || []).filter(t => now - t < HOUR)
  map.set(id, ts)
  if (ts.length >= max) return false
  if (commit) ts.push(now)
  return true
}

// SC2Replay 是带用户数据头的 MPQ：文件以 "MPQ\x1b" 开头
const MPQ_MAGIC = Buffer.from([0x4d, 0x50, 0x51, 0x1b])

/**
 * 边读边计数的请求体读取：超过 limit 立即中止，内存占用 ≈ 文件本身大小。
 * 不用 readMultipartFormData：h3 的 multipart 解析逐字节压入 JS 数组，
 * 5MB 文件实测让 Node RSS 涨 ~200MB，在 768m 的容器里不可接受。
 * Content-Length 缺失（chunked）时同样受此上限约束。
 */
function readCappedBody(event: Parameters<typeof requireUser>[0], limit: number): Promise<Buffer> {
  const req = event.node.req
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = []
    let total = 0
    let done = false
    const fail = (err: Error) => {
      if (done) return
      done = true
      req.removeAllListeners('data')
      req.resume() // 丢弃剩余数据，让连接能正常返回 413
      reject(err)
    }
    req.on('data', (c: Buffer) => {
      if (done) return
      total += c.length
      if (total > limit) return fail(createError({ statusCode: 413, message: '文件过大（上限 5MB）' }))
      chunks.push(c)
    })
    req.on('end', () => { if (!done) { done = true; resolve(Buffer.concat(chunks, total)) } })
    req.on('error', fail)
    req.on('aborted', () => fail(createError({ statusCode: 400, message: '上传中断' })))
  })
}

/**
 * 上传一个 .SC2Replay：请求体就是文件原始字节（Content-Type: application/octet-stream），
 * 文件名放在 X-File-Name 头（encodeURIComponent 编码）。
 * 立即返回排队状态；解析在后台单 worker 进行，前端轮询 GET /api/replays/:hash/status。
 */
export default defineEventHandler(async (event) => {
  const user = requireUser(event)
  const isAdmin = user.role === 'admin'

  // 读请求体之前先做完所有便宜的拒绝，避免白白接收 5MB
  const len = Number(getHeader(event, 'content-length') || 0)
  if (len > MAX_UPLOAD_BYTES) {
    throw createError({ statusCode: 413, message: '文件过大（上限 5MB）' })
  }
  if (!isAdmin && !within(attemptAt, user.id, ATTEMPT_MAX, true)) {
    throw createError({ statusCode: 429, message: '请求过于频繁，请稍后再试' })
  }
  if (!isAdmin && !within(queuedAt, user.id, QUEUE_MAX, false)) {
    throw createError({ statusCode: 429, message: '上传过于频繁，请稍后再试（每小时 20 个）' })
  }

  const data = await readCappedBody(event, MAX_UPLOAD_BYTES)
  if (!data.length) throw createError({ statusCode: 400, message: '请选择录像文件' })
  if (!data.subarray(0, 4).equals(MPQ_MAGIC)) {
    throw createError({ statusCode: 400, message: '不是有效的星际争霸 II 录像文件（.SC2Replay）' })
  }

  const hash = createHash('md5').update(data).digest('hex')
  const db = getDb()

  // 重复上传：已有记录（排队/解析中/完成）直接复用；失败的允许重试
  const existing = db.prepare(`SELECT * FROM replays WHERE hash = ?`).get(hash) as ReplayRow | undefined
  if (existing && existing.status !== 'failed') {
    return { replay: publicRow(existing, user.id), duplicate: true }
  }

  const queued = (db.prepare(
    `SELECT COUNT(*) AS n FROM replays WHERE status IN ('queued', 'processing')`,
  ).get() as { n: number }).n
  if (queued >= MAX_QUEUED) {
    throw createError({ statusCode: 503, message: '解析队列已满，请稍后再试' })
  }
  if (!isAdmin) {
    // 单个用户最多同时占 3 个排队位，避免两三个账号就把全站队列塞满
    const mine = (db.prepare(
      `SELECT COUNT(*) AS n FROM replays WHERE uploader_id = ? AND status IN ('queued', 'processing')`,
    ).get(user.id) as { n: number }).n
    if (mine >= MAX_QUEUED_PER_USER) {
      throw createError({ statusCode: 429, message: `你已有 ${mine} 个录像在排队，请等它们解析完再上传` })
    }
  }

  prepareStorage()
  writeFileSync(rawPath(hash), data)

  let fileName = 'replay.SC2Replay'
  try { fileName = decodeURIComponent(getHeader(event, 'x-file-name') || '') || fileName } catch {}
  fileName = fileName.replace(/[\u0000-\u001f]/g, '').slice(0, 120)

  db.prepare(`
    INSERT INTO replays (hash, status, error, uploader_id, file_name, size, json_size, summary, created_at, parsed_at)
    VALUES (?, 'queued', '', ?, ?, ?, 0, NULL, datetime('now'), NULL)
    ON CONFLICT(hash) DO UPDATE SET status = 'queued', error = '', uploader_id = excluded.uploader_id,
      file_name = excluded.file_name, size = excluded.size, json_size = 0, summary = NULL, attempts = 0,
      created_at = datetime('now'), parsed_at = NULL
  `).run(hash, user.id, fileName, data.length)

  // 真正入队后才计入每小时配额
  if (!isAdmin) within(queuedAt, user.id, QUEUE_MAX, true)

  kickQueue()

  const row = db.prepare(`SELECT * FROM replays WHERE hash = ?`).get(hash) as ReplayRow
  return { replay: publicRow(row, user.id), duplicate: false }
})
