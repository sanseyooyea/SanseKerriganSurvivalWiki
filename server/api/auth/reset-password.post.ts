import crypto from 'crypto'
import bcrypt from 'bcryptjs'
import { getDb } from '~/server/utils/db'
import { signToken } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { token, password } = body

  if (!token || typeof token !== 'string' || !/^[0-9a-f]{64}$/.test(token)) {
    throw createError({ statusCode: 400, message: '重置链接无效' })
  }
  if (!password || typeof password !== 'string' || password.length < 6) {
    throw createError({ statusCode: 400, message: '密码至少6位' })
  }

  const tokenHash = crypto.createHash('sha256').update(token).digest('hex')
  const db = getDb()

  const row = db.prepare(
    'SELECT id, user_id, expires_at FROM password_reset_tokens WHERE token_hash = ?'
  ).get(tokenHash) as { id: number; user_id: number; expires_at: string } | undefined

  if (!row) {
    throw createError({ statusCode: 400, message: '重置链接无效或已过期' })
  }

  if (new Date(row.expires_at) < new Date()) {
    db.prepare('DELETE FROM password_reset_tokens WHERE id = ?').run(row.id)
    throw createError({ statusCode: 400, message: '重置链接已过期，请重新申请' })
  }

  // 更新密码 & 递增 token_version（使所有旧 JWT 立即失效）
  const hash = bcrypt.hashSync(password, 10)
  db.prepare(
    'UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE id = ?'
  ).run(hash, row.user_id)

  // 删除该用户所有重置 token
  db.prepare('DELETE FROM password_reset_tokens WHERE user_id = ?').run(row.user_id)

  // 查最新用户信息并签发新 JWT（自动登录）
  const user = db.prepare(
    'SELECT id, username, role, handle, email, token_version FROM users WHERE id = ?'
  ).get(row.user_id) as any

  const jwtToken = signToken({
    userId: user.id,
    username: user.username,
    role: user.role,
    tokenVersion: user.token_version,
  })

  return {
    success: true,
    token: jwtToken,
    user: {
      id: user.id,
      username: user.username,
      role: user.role,
      handle: user.handle || '',
      email: user.email || '',
    },
  }
})