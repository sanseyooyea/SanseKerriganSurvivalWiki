import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'

// 切换点赞：已赞则取消，未赞则点赞。返回最新票数与我的状态。
export default defineEventHandler(async (event) => {
  const user = requireUser(event)
  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isInteger(id) || id <= 0) {
    throw createError({ statusCode: 400, message: '参数错误' })
  }

  const db = getDb()
  const exists = db.prepare('SELECT 1 FROM feedback WHERE id = ?').get(id)
  if (!exists) throw createError({ statusCode: 404, message: '建议不存在' })

  const voted = db.prepare(
    'SELECT 1 FROM feedback_votes WHERE feedback_id = ? AND user_id = ?'
  ).get(id, user.id)

  if (voted) {
    db.prepare('DELETE FROM feedback_votes WHERE feedback_id = ? AND user_id = ?').run(id, user.id)
  } else {
    db.prepare('INSERT INTO feedback_votes (feedback_id, user_id) VALUES (?, ?)').run(id, user.id)
  }

  const votes = (db.prepare(
    'SELECT COUNT(*) AS c FROM feedback_votes WHERE feedback_id = ?'
  ).get(id) as { c: number }).c

  return { success: true, votes, voted: !voted }
})
