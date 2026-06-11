import { getDb } from '~/server/utils/db'

export default defineEventHandler(async (event) => {
  const slug = getRouterParam(event, 'slug')
  if (!slug) throw createError({ statusCode: 400, message: '缺少页面标识' })

  const db = getDb()
  const page = db.prepare('SELECT id FROM wiki_pages WHERE slug = ?').get(slug) as any
  if (!page) return { revisions: [] }

  const revisions = db.prepare(`
    SELECT r.id, r.title, r.created_at, u.username as edited_by
    FROM wiki_revisions r
    LEFT JOIN users u ON r.edited_by = u.id
    WHERE r.page_id = ?
    ORDER BY r.created_at DESC
    LIMIT 50
  `).all(page.id)

  return { revisions }
})
