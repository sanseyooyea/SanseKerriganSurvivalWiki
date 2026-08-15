import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'

// 投稿人查看自己提交的编辑及其审核状态。静态段 mine 先于动态 [id] 解析，无冲突。
export default defineEventHandler((event) => {
  const user = requireUser(event)
  const db = getDb()

  const reviews = db.prepare(`
    SELECT id, slug, is_new, title, category, status, admin_note, created_at, updated_at
    FROM wiki_edit_reviews
    WHERE submitted_by = ?
    ORDER BY created_at DESC
    LIMIT 100
  `).all(user.id)

  return { reviews }
})
