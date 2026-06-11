import { getDb } from '~/server/utils/db'

export default defineEventHandler(async () => {
  const db = getDb()
  const pages = db.prepare(`
    SELECT slug, title, category, updated_at,
      (SELECT username FROM users WHERE id = wiki_pages.updated_by) as updated_by
    FROM wiki_pages ORDER BY updated_at DESC
  `).all()
  return pages
})
