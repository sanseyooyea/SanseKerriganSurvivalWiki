import DatabaseCtor from 'better-sqlite3'
import type { Database } from 'better-sqlite3'
import { join } from 'path'
import { existsSync } from 'fs'
import { inflateSync } from 'zlib'

// 只读引用库 data/stats.db 的 mmr_history 表（scripts/build_stats_db.py 从生产库
// 转储的 player_mmrs.history pickle 解码而来）。官方网关只给当前 MMR 快照，不给历史
// 时间序列，故离线静态快照供「MMR 走势」查询。
let sdb: Database | null = null
function statsDb(): Database | null {
  if (sdb) return sdb
  const p = join(process.cwd(), 'data', 'stats.db')
  if (!existsSync(p)) return null
  sdb = new DatabaseCtor(p, { readonly: true, fileMustExist: true })
  return sdb
}

export default defineCachedEventHandler((event) => {
  const handle = ((getQuery(event).handle as string) || '').trim()
  if (!handle) {
    throw createError({ statusCode: 400, message: '缺少handle参数' })
  }

  const db = statsDb()
  if (!db) return { identity: null, through: null, core: [], roles: {} }

  // identity 多为 battle_tag，少数为 toon。先 handle->battle_tag，再回退 handle 本身。
  const bt = (db.prepare('SELECT battle_tag FROM handles WHERE player_handle = ?').get(handle) as
    | { battle_tag: string | null }
    | undefined)?.battle_tag

  const get = db.prepare('SELECT identity, core, roles FROM mmr_history WHERE identity = ?')
  const row =
    (bt && (get.get(bt) as MmrRow | undefined)) ||
    (get.get(handle) as MmrRow | undefined) ||
    (get.get(handle.toUpperCase()) as MmrRow | undefined)

  const through = (db.prepare("SELECT value FROM meta WHERE key='mmr_history_through'").get() as
    | { value: string }
    | undefined)?.value || null

  if (!row) return { identity: bt || handle, through, core: [], roles: {} }

  // core/roles are zlib-compressed JSON blobs (see scripts/build_stats_db.py)
  const unzip = (buf: Buffer | null, fallback: string): any => {
    if (!buf) return JSON.parse(fallback)
    try {
      return JSON.parse(inflateSync(buf).toString('utf-8'))
    } catch {
      return JSON.parse(fallback)
    }
  }

  return {
    identity: row.identity,
    through,
    core: unzip(row.core, '[]') as [number, number, number][],
    roles: unzip(row.roles, '{}') as Record<string, [number, number][]>,
  }
}, {
  maxAge: 300,
  name: 'mmr_history',
  getKey: (event) => (getQuery(event).handle as string) || 'none',
})

interface MmrRow {
  identity: string
  core: Buffer | null
  roles: Buffer | null
}
