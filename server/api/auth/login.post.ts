import bcrypt from 'bcryptjs'
import { getDb } from '~/server/utils/db'
import { signToken } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { username, password } = body

  if (!username || !password) {
    throw createError({ statusCode: 400, message: '请输入用户名和密码' })
  }

  const db = getDb()
  const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username) as any
  if (!user || !bcrypt.compareSync(password, user.password_hash)) {
    throw createError({ statusCode: 401, message: '用户名或密码错误' })
  }

  const token = signToken({ userId: user.id, username: user.username, role: user.role })
  return { token, user: { id: user.id, username: user.username, role: user.role } }
})
