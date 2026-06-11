import bcrypt from 'bcryptjs'
import { getDb } from '~/server/utils/db'
import { signToken } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { username, password, handle } = body

  if (!username || !password || username.length < 2 || password.length < 6) {
    throw createError({ statusCode: 400, message: '用户名至少2位，密码至少6位' })
  }

  const db = getDb()
  const existing = db.prepare('SELECT id FROM users WHERE username = ?').get(username)
  if (existing) {
    throw createError({ statusCode: 409, message: '用户名已存在' })
  }

  const hash = bcrypt.hashSync(password, 10)
  const isFirst = !db.prepare('SELECT id FROM users LIMIT 1').get()
  const role = isFirst ? 'admin' : 'user'

  let validHandle = ''
  if (handle && typeof handle === 'string' && handle.trim()) {
    const trimmed = handle.trim()
    if (!/^\d+-S2-\d+-\d+$/.test(trimmed)) {
      throw createError({ statusCode: 400, message: '句柄格式不正确，应为类似 5-S2-1-1194668 的格式' })
    }
    try {
      const data = await $fetch<any>(`https://194823.xyz/api/player?player_handle=${encodeURIComponent(trimmed)}`, {
        headers: { Accept: 'application/json' },
        timeout: 8000,
      })
      if (data && data.player_handle) {
        validHandle = trimmed
      }
    } catch {}
  }

  const result = db.prepare('INSERT INTO users (username, password_hash, role, handle) VALUES (?, ?, ?, ?)')
    .run(username, hash, role, validHandle)

  const token = signToken({ userId: result.lastInsertRowid as number, username, role })
  return { token, user: { id: result.lastInsertRowid, username, role, handle: validHandle } }
})
