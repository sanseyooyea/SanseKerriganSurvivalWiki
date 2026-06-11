import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const user = requireRole(event, ['admin', 'editor'])

  const slug = getRouterParam(event, 'slug')
  const body = await readBody(event)
  const { title, content, category } = body

  if (!slug || !title) {
    throw createError({ statusCode: 400, message: '缺少必要字段' })
  }

  const db = getDb()
  const existing = db.prepare('SELECT * FROM wiki_pages WHERE slug = ?').get(slug) as any

  if (existing) {
    db.prepare('INSERT INTO wiki_revisions (page_id, title, content, edited_by) VALUES (?, ?, ?, ?)')
      .run(existing.id, existing.title, existing.content, user.id)

    db.prepare('UPDATE wiki_pages SET title = ?, content = ?, category = ?, updated_by = ?, updated_at = datetime(\'now\') WHERE slug = ?')
      .run(title, content || '', category || 'general', user.id, slug)
  } else {
    db.prepare('INSERT INTO wiki_pages (slug, title, content, category, updated_by) VALUES (?, ?, ?, ?, ?)')
      .run(slug, title, content || '', category || 'general', user.id)
  }

  return { success: true, slug }
})
