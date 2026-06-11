import { getDb } from '~/server/utils/db'
import { verifyToken } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  const db = getDb()
  const row = db.prepare('SELECT data FROM class_overrides WHERE class_id = ?').get(id) as any
  return row ? JSON.parse(row.data) : null
})
