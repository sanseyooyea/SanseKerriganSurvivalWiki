import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

// 管理员审批待审编辑：通过则应用到 wiki_pages（署名归投稿人），驳回则记备注。
export default defineEventHandler(async (event) => {
  const admin = requireRole(event, ['admin'])

  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isInteger(id) || id <= 0) {
    throw createError({ statusCode: 400, message: '参数错误' })
  }

  const db = getDb()
  const review = db.prepare('SELECT * FROM wiki_edit_reviews WHERE id = ?').get(id) as any
  if (!review) throw createError({ statusCode: 404, message: '记录不存在' })
  if (review.status !== 'pending') {
    throw createError({ statusCode: 409, message: '该编辑已处理' })
  }

  const body = await readBody(event)
  const status = body.status
  if (status !== 'approved' && status !== 'rejected') {
    throw createError({ statusCode: 400, message: '无效的状态' })
  }
  const note = body.admin_note !== undefined ? String(body.admin_note).slice(0, 1000) : null

  if (status === 'rejected') {
    db.prepare(`
      UPDATE wiki_edit_reviews
      SET status = 'rejected', admin_note = COALESCE(?, admin_note),
          reviewed_by = ?, updated_at = datetime('now')
      WHERE id = ?
    `).run(note, admin.id, id)
    return { success: true }
  }

  // 通过：按 slug 重新定位页面（page_id 仅提示），整个应用过程放进事务。
  const apply = db.transaction(() => {
    const existing = db.prepare('SELECT * FROM wiki_pages WHERE slug = ?').get(review.slug) as any
    if (existing) {
      // 应用前把当前状态快照进修订表；edited_by 记为投稿人（与直写路径一致，记录动作发起者）。
      db.prepare('INSERT INTO wiki_revisions (page_id, title, content, edited_by) VALUES (?, ?, ?, ?)')
        .run(existing.id, existing.title, existing.content, review.submitted_by)
      db.prepare(`
        UPDATE wiki_pages
        SET title = ?, content = ?, category = ?, updated_by = ?, updated_at = datetime('now')
        WHERE slug = ?
      `).run(review.title, review.content, review.category, review.submitted_by, review.slug)
    } else {
      db.prepare('INSERT INTO wiki_pages (slug, title, content, category, updated_by) VALUES (?, ?, ?, ?, ?)')
        .run(review.slug, review.title, review.content, review.category, review.submitted_by)
    }
    db.prepare(`
      UPDATE wiki_edit_reviews
      SET status = 'approved', admin_note = COALESCE(?, admin_note),
          reviewed_by = ?, updated_at = datetime('now')
      WHERE id = ?
    `).run(note, admin.id, id)
  })
  apply()

  return { success: true, published: true, slug: review.slug }
})
