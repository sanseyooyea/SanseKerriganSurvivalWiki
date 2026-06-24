import DatabaseCtor from 'better-sqlite3'
import type { Database } from 'better-sqlite3'
import { join } from 'path'
import { existsSync } from 'fs'

// 只读引用库 data/stats.db（scripts/build_stats_db.py 从生产库转储生成）。
// 公开网关不暴露 played_like，故离线静态快照供「最近对局等效MMR」查询。
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
  if (!db) return { games: [], through: null, identity: null }

  // 句柄 -> identity(battle_tag)，无绑定则回退句柄本身（大写）
  const row = db.prepare('SELECT battle_tag FROM handles WHERE player_handle = ?').get(handle) as
    | { battle_tag: string | null }
    | undefined
  const identity = row?.battle_tag || handle.toUpperCase()

  const games = db
    .prepare(
      `SELECT datetime_of_game AS date, functional_role AS role, team_int AS team,
              estimated_mmr AS estimated, played_like
       FROM played_like WHERE identity = ?
       ORDER BY datetime_of_game DESC LIMIT 50`,
    )
    .all(identity) as Array<{
      date: string
      role: string
      team: number
      estimated: number | null
      played_like: number | null
    }>

  const through = (db.prepare("SELECT value FROM meta WHERE key='played_like_through'").get() as
    | { value: string }
    | undefined)?.value || null

  return { identity, through, games }
}, {
  maxAge: 300,
  name: 'played_like',
  getKey: (event) => (getQuery(event).handle as string) || 'none',
})
