import { getDb } from '~/server/utils/db'
import { requireUser, verifyToken } from '~/server/utils/auth'

const CATEGORIES = ['feature', 'bug', 'data', 'other']

// 可选地从请求里解析当前用户 id（用于标记“我是否点过赞”），未登录返回 0
function optionalUserId(event: any): number {
  const auth = getHeader(event, 'authorization')
  if (!auth?.startsWith('Bearer ')) return 0
  const payload = verifyToken(auth.slice(7))
  return payload?.userId || 0
}

export default defineEventHandler(async (event) => {
  const db = getDb()

  if (event.method === 'GET') {
    const meId = optionalUserId(event)
    const query = getQuery(event)
    const category = query.category as string | undefined
    const status = query.status as string | undefined

    const where: string[] = []
    const params: any[] = []
    if (category && CATEGORIES.includes(category)) {
      where.push('f.category = ?'); params.push(category)
    }
    if (status && ['pending', 'accepted', 'rejected', 'done'].includes(status)) {
      where.push('f.status = ?'); params.push(status)
    }
    const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : ''

    const list = db.prepare(`
      SELECT f.id, f.category, f.title, f.content, f.status, f.admin_note,
             f.created_at, f.updated_at, f.user_id, u.username,
             (SELECT COUNT(*) FROM feedback_votes v WHERE v.feedback_id = f.id) AS votes,
             EXISTS(SELECT 1 FROM feedback_votes v WHERE v.feedback_id = f.id AND v.user_id = ?) AS voted
      FROM feedback f
      JOIN users u ON f.user_id = u.id
      ${whereSql}
      ORDER BY
        CASE f.status WHEN 'pending' THEN 0 WHEN 'accepted' THEN 1 WHEN 'done' THEN 2 ELSE 3 END,
        votes DESC, f.created_at DESC
      LIMIT 300
    `).all(meId, ...params)

    return { feedback: list }
  }

  if (event.method === 'POST') {
    const user = requireUser(event)
    const body = await readBody(event)
    const title = (body.title || '').trim()
    const content = (body.content || '').trim()
    let category = (body.category || 'feature').trim()
    if (!CATEGORIES.includes(category)) category = 'feature'
    if (!title) throw createError({ statusCode: 400, message: '标题不能为空' })
    if (title.length > 100) throw createError({ statusCode: 400, message: '标题过长（最多100字）' })
    if (content.length > 2000) throw createError({ statusCode: 400, message: '内容过长（最多2000字）' })

    const info = db.prepare(
      'INSERT INTO feedback (user_id, category, title, content) VALUES (?, ?, ?, ?)'
    ).run(user.id, category, title, content)

    return { success: true, id: info.lastInsertRowid }
  }
})
