import { getDb } from '~/server/utils/db'

export default defineEventHandler(async (event) => {
  const slug = getRouterParam(event, 'slug')
  if (!slug) throw createError({ statusCode: 400, message: '缺少页面标识' })

  const db = getDb()
  const page = db.prepare('SELECT * FROM wiki_pages WHERE slug = ?').get(slug) as any
  if (!page) throw createError({ statusCode: 404, message: '页面不存在' })

  return page
})
