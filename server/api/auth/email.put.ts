import { requireUser } from '~/server/utils/auth'
import { getDb } from '~/server/utils/db'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default defineEventHandler(async (event) => {
  const user = requireUser(event)
  const body = await readBody(event)
  const email = (body.email || '').trim()

  if (!email) {
    throw createError({ statusCode: 400, message: '请输入邮箱地址' })
  }
  if (!EMAIL_RE.test(email)) {
    throw createError({ statusCode: 400, message: '邮箱格式不正确' })
  }

  const db = getDb()

  // 唯一性检查（排除自己）
  const existing = db.prepare(
    `SELECT id FROM users WHERE email = ? AND id != ?`
  ).get(email, user.id)
  if (existing) {
    throw createError({ statusCode: 409, message: '该邮箱已被其他账号使用' })
  }

  db.prepare('UPDATE users SET email = ? WHERE id = ?').run(email, user.id)
  return { success: true, email }
})