import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

// 流量统计汇总，仅管理员可见。
// PV = 浏览记录数；UV = 按日去重的访客数（visitor 含 day 盐，跨天不可累加去重，
// 故「总 UV」按各日 UV 求和的口径，即「人次/日」，不是绝对独立人数）。
export default defineEventHandler((event) => {
  requireRole(event, ['admin'])
  const db = getDb()

  const days = Math.min(Math.max(Number(getQuery(event).days) || 30, 7), 90)

  // 每日 PV / UV 趋势
  const trend = db.prepare(`
    SELECT day,
           COUNT(*) AS pv,
           COUNT(DISTINCT visitor) AS uv
    FROM page_views
    WHERE day >= date('now', 'localtime', ?)
    GROUP BY day
    ORDER BY day
  `).all(`-${days - 1} days`) as { day: string; pv: number; uv: number }[]

  // 今日 / 总计
  const todayRow = db.prepare(`
    SELECT COUNT(*) AS pv, COUNT(DISTINCT visitor) AS uv
    FROM page_views WHERE day = date('now', 'localtime')
  `).get() as { pv: number; uv: number }

  const totalRow = db.prepare(
    'SELECT COUNT(*) AS pv FROM page_views'
  ).get() as { pv: number }

  // 热门页面（区间内 PV Top 20）
  const topPages = db.prepare(`
    SELECT path,
           COUNT(*) AS pv,
           COUNT(DISTINCT visitor) AS uv
    FROM page_views
    WHERE day >= date('now', 'localtime', ?)
    GROUP BY path
    ORDER BY pv DESC
    LIMIT 20
  `).all(`-${days - 1} days`) as { path: string; pv: number; uv: number }[]

  return {
    days,
    today: { pv: todayRow.pv, uv: todayRow.uv },
    totalPv: totalRow.pv,
    rangePv: trend.reduce((s, r) => s + r.pv, 0),
    rangeUv: trend.reduce((s, r) => s + r.uv, 0),
    trend,
    topPages,
  }
})
