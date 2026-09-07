import crypto from 'crypto'
import { getDb } from '~/server/utils/db'
import { sendMail } from '~/server/utils/email'

// ---- 简易内存限流：同 IP 15 分钟内最多 5 次 ----
const rateLimitMap = new Map<string, number[]>()
const RATE_WINDOW = 15 * 60 * 1000 // 15 min
const RATE_MAX = 5

function checkRateLimit(ip: string): boolean {
  const now = Date.now()
  const timestamps = (rateLimitMap.get(ip) || []).filter(t => now - t < RATE_WINDOW)
  if (timestamps.length >= RATE_MAX) return false
  timestamps.push(now)
  rateLimitMap.set(ip, timestamps)
  return true
}

export default defineEventHandler(async (event) => {
  const ip = getRequestIP(event, { xForwardedFor: true }) || 'unknown'
  if (!checkRateLimit(ip)) {
    throw createError({ statusCode: 429, message: '请求过于频繁，请稍后再试' })
  }

  const body = await readBody(event)
  const login = (body.login || '').trim()
  if (!login) {
    throw createError({ statusCode: 400, message: '请输入用户名或邮箱' })
  }

  const db = getDb()

  // 清理过期 token（顺带维护表大小）
  db.prepare(`DELETE FROM password_reset_tokens WHERE expires_at < datetime('now')`).run()

  // 查找用户（用户名或邮箱）
  const user = db.prepare(
    `SELECT id, username, email FROM users WHERE username = ? OR (email != '' AND email = ?)`
  ).get(login, login) as { id: number; username: string; email: string } | undefined

  // 无论是否找到用户，都返回相同响应（防止用户枚举）
  if (!user || !user.email) {
    return { success: true, message: '如果该账号已绑定邮箱，重置链接已发送' }
  }

  // 删除该用户的旧 token
  db.prepare('DELETE FROM password_reset_tokens WHERE user_id = ?').run(user.id)

  // 生成安全随机 token
  const rawToken = crypto.randomBytes(32).toString('hex')
  const tokenHash = crypto.createHash('sha256').update(rawToken).digest('hex')
  const expiresAt = new Date(Date.now() + 3600_000).toISOString() // 1 小时

  db.prepare(
    'INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)'
  ).run(user.id, tokenHash, expiresAt)

  // 构造重置链接和邮件
  const appUrl = (process.env.APP_URL || 'http://localhost:3000').replace(/\/+$/, '')
  const resetUrl = `${appUrl}/reset-password?token=${rawToken}`

  const html = `
<div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
  <h2 style="color: #111827; font-size: 18px;">凯瑞甘生存2 Wiki — 密码重置</h2>
  <p style="color: #374151; font-size: 14px; line-height: 1.6;">
    你好，<strong>${user.username}</strong>，<br>
    我们收到了你的密码重置请求。点击下方按钮重置密码：
  </p>
  <a href="${resetUrl}"
     style="display: inline-block; margin: 16px 0; padding: 10px 24px; background: #2563eb; color: #fff; text-decoration: none; border-radius: 8px; font-size: 14px;">
    重置密码
  </a>
  <p style="color: #6b7280; font-size: 12px;">
    如果按钮无法点击，请复制以下链接到浏览器：<br>
    <span style="color: #2563eb; word-break: break-all;">${resetUrl}</span>
  </p>
  <p style="color: #9ca3af; font-size: 12px; margin-top: 24px;">
    链接有效期为 1 小时。如果你没有请求重置密码，请忽略此邮件。
  </p>
</div>`

  try {
    await sendMail(user.email, '密码重置 — 凯瑞甘生存2 Wiki', html)
  } catch (e) {
    console.error('[forgot-password] 邮件发送失败:', e)
    // 不暴露内部错误给用户
  }

  return { success: true, message: '如果该账号已绑定邮箱，重置链接已发送' }
})