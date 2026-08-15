import DatabaseCtor from 'better-sqlite3'
import type { Database } from 'better-sqlite3'
import { join } from 'path'
import { existsSync } from 'fs'
import { inflateSync } from 'zlib'

// 官方网关 (194823.xyz/api/player) 是当前 MMR 的第一数据源；它不定期整体故障
// （对全部 handle 返回 404 "Player not found"）。故加离线兜底：上游 404/5xx/超时时，
// 从 data/stats.db 的 player_mmr_current 读取由生产库 dump 重建的当前 MMR 快照
// （见 scripts/build_stats_db.py），拼成同样的载荷返回，附 _snapshot/_through 标记。
let sdb: Database | null = null
function statsDb(): Database | null {
  if (sdb) return sdb
  const p = join(process.cwd(), 'data', 'stats.db')
  if (!existsSync(p)) return null
  sdb = new DatabaseCtor(p, { readonly: true, fileMustExist: true })
  return sdb
}

function snapshotFor(handle: string): any | null {
  const db = statsDb()
  if (!db) return null

  // identity 多为 battle_tag，少数为 toon。先 handle->battle_tag，再回退 handle 本身。
  const bt = (db.prepare('SELECT battle_tag FROM handles WHERE player_handle = ?').get(handle) as
    | { battle_tag: string | null }
    | undefined)?.battle_tag

  const get = db.prepare('SELECT data FROM player_mmr_current WHERE identity = ?')
  const row =
    ((bt && get.get(bt)) as { data: Buffer } | undefined) ||
    (get.get(handle) as { data: Buffer } | undefined) ||
    (get.get(handle.toUpperCase()) as { data: Buffer } | undefined)
  if (!row) return null

  const through = (db.prepare("SELECT value FROM meta WHERE key='player_mmr_current_through'").get() as
    | { value: string }
    | undefined)?.value || null

  try {
    const payload = JSON.parse(inflateSync(row.data).toString('utf-8'))
    return { ...payload, _snapshot: true, _through: through }
  } catch {
    return null
  }
}

export default defineCachedEventHandler(async (event) => {
  const handle = getQuery(event).handle as string
  if (!handle) {
    throw createError({ statusCode: 400, message: '缺少handle参数' })
  }

  try {
    const data = await $fetch(`https://194823.xyz/api/player?player_handle=${encodeURIComponent(handle)}`, {
      headers: { Accept: 'application/json' },
      timeout: 8000,
    })
    // 上游偶发返回空体/空对象；这类也回退到快照，避免整页空白。
    if (data && typeof data === 'object' && Object.keys(data as object).length) {
      return data
    }
    return snapshotFor(handle)
  } catch (e: any) {
    // 上游 404（含整体故障时的 "Player not found"）或 5xx/超时：优先用离线快照兜底。
    const snap = snapshotFor(handle)
    if (snap) return snap
    if (e.status === 404 || e.statusCode === 404) return null
    throw createError({ statusCode: 502, message: '无法获取MMR数据' })
  }
}, {
  maxAge: 30,
  name: 'mmr',
  getKey: (event) => (getQuery(event).handle as string) || 'none',
})
