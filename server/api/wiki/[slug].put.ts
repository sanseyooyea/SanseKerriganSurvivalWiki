import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  // 任何登录用户都可发起编辑：admin 直写发布，editor/user 进待审队列。
  const user = requireUser(event)

  const slug = getRouterParam(event, 'slug')
  const body = await readBody(event)
  const { title, content, category } = body

  if (!slug || !title) {
    throw createError({ statusCode: 400, message: '缺少必要字段' })
  }

  const db = getDb()
  const existing = db.prepare('SELECT * FROM wiki_pages WHERE slug = ?').get(slug) as any

  // 非管理员：不碰 wiki_pages/wiki_revisions，只插一条待审记录。
  if (user.role !== 'admin') {
    db.prepare(`
      INSERT INTO wiki_edit_reviews
        (slug, page_id, is_new, title, content, category, submitted_by, base_updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      slug,
      existing ? existing.id : null,
      existing ? 0 : 1,
      title,
      content || '',
      category || 'general',
      user.id,
      existing ? existing.updated_at : null,
    )
    return { pending: true, slug }
  }

  // 管理员：直接发布（保留原有行为，编辑前把旧版快照进修订表）。
  if (existing) {
    db.prepare('INSERT INTO wiki_revisions (page_id, title, content, edited_by) VALUES (?, ?, ?, ?)')
      .run(existing.id, existing.title, existing.content, user.id)

    db.prepare('UPDATE wiki_pages SET title = ?, content = ?, category = ?, updated_by = ?, updated_at = datetime(\'now\') WHERE slug = ?')
      .run(title, content || '', category || 'general', user.id, slug)
  } else {
    db.prepare('INSERT INTO wiki_pages (slug, title, content, category, updated_by) VALUES (?, ?, ?, ?, ?)')
      .run(slug, title, content || '', category || 'general', user.id)
  }

  return { published: true, slug }
})
