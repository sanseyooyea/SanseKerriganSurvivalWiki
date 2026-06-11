import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

const STATUSES = ['pending', 'accepted', 'rejected', 'done']

// 管理员更新建议进度：status 和/或 admin_note
export default defineEventHandler(async (event) => {
  requireRole(event, ['admin'])
  const id = Number(getRouterParam(event, 'id'))
  if (!Number.isInteger(id) || id <= 0) {
    throw createError({ statusCode: 400, message: '参数错误' })
  }

  const db = getDb()
  const exists = db.prepare('SELECT 1 FROM feedback WHERE id = ?').get(id)
  if (!exists) throw createError({ statusCode: 404, message: '建议不存在' })

  const body = await readBody(event)
  const fields: string[] = []
  const params: any[] = []

  if (body.status !== undefined) {
    if (!STATUSES.includes(body.status)) {
      throw createError({ statusCode: 400, message: '无效的状态' })
    }
    fields.push('status = ?'); params.push(body.status)
  }
  if (body.admin_note !== undefined) {
    const note = String(body.admin_note).slice(0, 1000)
    fields.push('admin_note = ?'); params.push(note)
  }
  if (!fields.length) {
    throw createError({ statusCode: 400, message: '无可更新字段' })
  }

  fields.push("updated_at = datetime('now')")
  params.push(id)
  db.prepare(`UPDATE feedback SET ${fields.join(', ')} WHERE id = ?`).run(...params)

  return { success: true }
})
