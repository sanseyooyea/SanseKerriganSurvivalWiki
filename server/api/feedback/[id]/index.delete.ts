import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'

// 删除建议：管理员可删任意，普通用户仅能删自己的
export default defineEventHandler(async (event) => {
  const user = requireUser(event)
  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isInteger(id) || id <= 0) {
    throw createError({ statusCode: 400, message: '参数错误' })
  }

  const db = getDb()
  const row = db.prepare('SELECT user_id FROM feedback WHERE id = ?').get(id) as { user_id: number } | undefined
  if (!row) throw createError({ statusCode: 404, message: '建议不存在' })

  if (user.role !== 'admin' && row.user_id !== user.id) {
    throw createError({ statusCode: 403, message: '只能删除自己的建议' })
  }

  db.prepare('DELETE FROM feedback_votes WHERE feedback_id = ?').run(id)
  db.prepare('DELETE FROM feedback WHERE id = ?').run(id)

  return { success: true }
})
