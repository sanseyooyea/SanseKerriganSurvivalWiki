import { getDb } from '~/server/utils/db'
import { isValidHandle, kickQueue } from '~/server/utils/replays'

/**
 * 某个玩家在已上传录像里的对局记录 + 汇总。
 * GET /api/replays/player/:handle?page=1
 *
 * 数据来自 replay_players（解析录像时从 summary 拆出）。只覆盖「有人上传过的录像」，
 * 不是该玩家的全部对局——全量战绩看 /api/mmr / played_like。录像未经官方验证，仅供参考。
 */
export default defineEventHandler((event) => {
  kickQueue() // 首次请求顺带完成 replay_players 回填
  const handle = String(getRouterParam(event, 'handle') || '').toUpperCase()
  if (!isValidHandle(handle)) throw createError({ statusCode: 400, message: '无效的玩家句柄' })
  const q = getQuery(event)
  const page = Math.min(1000, Math.max(1, Math.floor(Number(q.page)) || 1))
  const size = 20
  const db = getDb()

  const total = db.prepare(`
    SELECT COUNT(*) AS games,
           SUM(won = 1) AS wins, SUM(won = 0) AS losses,
           AVG(kills) AS avgKills, AVG(hero_damage) AS avgHeroDamage, AVG(apm) AS avgApm,
           SUM(hero_death_loop IS NOT NULL AND team = 0) AS heroDeaths,
           MAX(played_at) AS lastPlayed
    FROM replay_players WHERE handle = ?`).get(handle) as Record<string, number | string | null>

  // 按角色分组：场次、胜率、平均击杀/对虫族伤害
  const byRole = db.prepare(`
    SELECT role, role_en AS roleEn, team, COUNT(*) AS games, SUM(won = 1) AS wins, SUM(won = 0) AS losses,
           AVG(kills) AS avgKills, AVG(hero_damage) AS avgHeroDamage
    FROM replay_players WHERE handle = ?
    GROUP BY role_en, team ORDER BY games DESC, wins DESC LIMIT 20`).all(handle)

  const games = db.prepare(`
    SELECT rp.hash, rp.pid, rp.name, rp.role, rp.role_en AS roleEn, rp.team, rp.won,
           rp.mmr_before AS mmrBefore, rp.mmr_after AS mmrAfter, rp.hero_death_loop AS heroDeathLoop,
           rp.kills, rp.hero_damage AS heroDamage, rp.minerals, rp.gas_fed AS gasFed, rp.apm, rp.upgrades,
           rp.loops, rp.map_key AS mapKey, rp.played_at AS playedAt
    FROM replay_players rp JOIN replays r ON r.hash = rp.hash AND r.status = 'done'
    WHERE rp.handle = ?
    ORDER BY rp.played_at DESC, rp.hash
    LIMIT ? OFFSET ?`).all(handle, size, (page - 1) * size)

  // 录像里出现过的名字（同一句柄可能改过名），最近的在前
  const names = (db.prepare(`
    SELECT name FROM replay_players WHERE handle = ? GROUP BY name ORDER BY MAX(played_at) DESC LIMIT 5`)
    .all(handle) as { name: string }[]).map(r => r.name)

  return { handle, names, page, pageSize: size, summary: total, byRole, games }
})
