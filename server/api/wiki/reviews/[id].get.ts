import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

// 管理员查看单条待审编辑详情：含完整 content、当前 live 页面（供并排 diff）、以及陈旧标记。
export default defineEventHandler((event) => {
  requireRole(event, ['admin'])

  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isInteger(id) || id <= 0) {
    throw createError({ statusCode: 400, message: '参数错误' })
  }

  const db = getDb()
  const review = db.prepare(`
    SELECT r.*, su.username AS submitter, ru.username AS reviewer
    FROM wiki_edit_reviews r
    LEFT JOIN users su ON r.submitted_by = su.id
    LEFT JOIN users ru ON r.reviewed_by = ru.id
    WHERE r.id = ?
  `).get(id) as any
  if (!review) throw createError({ statusCode: 404, message: '记录不存在' })

  const current = db.prepare('SELECT * FROM wiki_pages WHERE slug = ?').get(review.slug) as any || null

  // 提交后 live 页面被他人更新过 → 通过会覆盖最新内容，前端据此告警。
  const stale = !!(review.base_updated_at && current && current.updated_at !== review.base_updated_at)

  return { review, current, stale }
})
