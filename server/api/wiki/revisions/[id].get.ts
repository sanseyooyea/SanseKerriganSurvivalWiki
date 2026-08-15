import { getDb } from '~/server/utils/db'

// 查看单条历史修订的完整内容（公开）。列表端点省略了大字段 content，这里按需取。
// revisions 为静态段，先于 [slug] 解析，无路由冲突。
export default defineEventHandler((event) => {
  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isInteger(id) || id <= 0) {
    throw createError({ statusCode: 400, message: '参数错误' })
  }

  const db = getDb()
  const revision = db.prepare(`
    SELECT r.id, r.page_id, r.title, r.content, r.created_at,
           u.username AS edited_by, p.slug
    FROM wiki_revisions r
    LEFT JOIN users u ON r.edited_by = u.id
    LEFT JOIN wiki_pages p ON r.page_id = p.id
    WHERE r.id = ?
  `).get(id) as any
  if (!revision) throw createError({ statusCode: 404, message: '修订不存在' })

  return { revision }
})
