import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

const STATUSES = ['pending', 'approved', 'rejected']

// 管理员列出待审编辑。可选 ?status= 过滤；默认按「待审优先、最新在前」排序。
// 列表省略大字段 content（详情端点再取），减小载荷。
export default defineEventHandler((event) => {
  requireRole(event, ['admin'])

  const status = getQuery(event).status as string | undefined
  const db = getDb()

  const where = status && STATUSES.includes(status) ? 'WHERE r.status = ?' : ''
  const params = where ? [status] : []

  const reviews = db.prepare(`
    SELECT r.id, r.slug, r.page_id, r.is_new, r.title, r.category, r.status,
           r.admin_note, r.submitted_by, r.base_updated_at, r.created_at, r.updated_at,
           su.username AS submitter,
           ru.username AS reviewer
    FROM wiki_edit_reviews r
    LEFT JOIN users su ON r.submitted_by = su.id
    LEFT JOIN users ru ON r.reviewed_by = ru.id
    ${where}
    ORDER BY CASE r.status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
             r.created_at DESC
    LIMIT 300
  `).all(...params)

  const pending = (db.prepare(
    "SELECT COUNT(*) AS n FROM wiki_edit_reviews WHERE status = 'pending'"
  ).get() as any).n as number

  return { reviews, pending }
})
