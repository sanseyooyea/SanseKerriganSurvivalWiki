import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const user = requireRole(event, ['admin'])

  const db = getDb()

  if (event.method === 'GET') {
    const users = db.prepare('SELECT id, username, role, handle, created_at FROM users ORDER BY id').all()
    return { users }
  }

  if (event.method === 'PATCH') {
    const body = await readBody(event)
    const { userId, role } = body
    if (!userId || !['admin', 'editor', 'user'].includes(role)) {
      throw createError({ statusCode: 400, message: '参数错误' })
    }
    // 防止管理员把自己降级后系统再无管理员入口
    if (userId === user.id && role !== 'admin') {
      throw createError({ statusCode: 400, message: '不能修改自己的管理员角色' })
    }
    db.prepare('UPDATE users SET role = ? WHERE id = ?').run(role, userId)
    return { success: true }
  }
})
