import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const slug = query.slug as string
  if (!slug) throw createError({ statusCode: 400, message: '缺少页面标识' })

  const db = getDb()

  if (event.method === 'GET') {
    const comments = db.prepare(`
      SELECT c.id, c.content, c.created_at, u.username
      FROM comments c
      JOIN users u ON c.user_id = u.id
      WHERE c.page_slug = ?
      ORDER BY c.created_at DESC
      LIMIT 100
    `).all(slug)
    return { comments }
  }

  if (event.method === 'POST') {
    const user = requireUser(event)

    const body = await readBody(event)
    if (!body.content?.trim()) {
      throw createError({ statusCode: 400, message: '评论内容不能为空' })
    }

    db.prepare('INSERT INTO comments (page_slug, user_id, content) VALUES (?, ?, ?)')
      .run(slug, user.id, body.content.trim())

    return { success: true }
  }
})
