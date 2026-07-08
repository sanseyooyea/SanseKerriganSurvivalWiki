import bcrypt from 'bcryptjs'
import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

const HANDLE_RE = /^\d+-S2-\d+-\d+$/

export default defineEventHandler(async (event) => {
  const user = requireRole(event, ['admin'])

  const db = getDb()

  if (event.method === 'GET') {
    const users = db.prepare('SELECT id, username, role, handle, created_at FROM users ORDER BY id').all()
    return { users }
  }

  if (event.method === 'PATCH') {
    const body = await readBody(event)
    // 兼容旧调用：无 action 字段时按「改角色」处理
    const action = body.action || 'setRole'
    const userId = body.userId

    if (!userId || typeof userId !== 'number') {
      throw createError({ statusCode: 400, message: '缺少目标用户' })
    }
    const target = db.prepare('SELECT id FROM users WHERE id = ?').get(userId)
    if (!target) {
      throw createError({ statusCode: 404, message: '用户不存在' })
    }
    return handleAction(event, db, user, action, userId, body)
  }
})

async function handleAction(event: any, db: any, admin: any, action: string, userId: number, body: any) {
  if (action === 'setRole') {
    const { role } = body
    if (!['admin', 'editor', 'user'].includes(role)) {
      throw createError({ statusCode: 400, message: '角色不合法' })
    }
    // 防止管理员把自己降级后系统再无管理员入口
    if (userId === admin.id && role !== 'admin') {
      throw createError({ statusCode: 400, message: '不能修改自己的管理员角色' })
    }
    db.prepare('UPDATE users SET role = ? WHERE id = ?').run(role, userId)
    return { success: true }
  }

  if (action === 'resetPassword') {
    const { password } = body
    if (!password || typeof password !== 'string' || password.length < 6) {
      throw createError({ statusCode: 400, message: '密码至少6位' })
    }
    const hash = bcrypt.hashSync(password, 10)
    db.prepare('UPDATE users SET password_hash = ? WHERE id = ?').run(hash, userId)
    // JWT 无状态、有效期 7 天且无 token 版本列，重置不会立即失效该用户已登录的旧 token。
    return { success: true, note: '密码已重置；该用户已登录的旧会话最长 7 天后失效' }
  }

  if (action === 'setHandle') {
    const raw = body.handle
    const trimmed = typeof raw === 'string' ? raw.trim() : ''
    // 空串 = 清空句柄，跳过外部校验
    if (!trimmed) {
      db.prepare('UPDATE users SET handle = ? WHERE id = ?').run('', userId)
      return { success: true, handle: '' }
    }
    if (!HANDLE_RE.test(trimmed)) {
      throw createError({ statusCode: 400, message: '句柄格式不正确，应为类似 5-S2-1-1194668 的格式' })
    }
    try {
      const data = await $fetch<any>(`https://194823.xyz/api/player?player_handle=${encodeURIComponent(trimmed)}`, {
        headers: { Accept: 'application/json' },
        timeout: 8000,
      })
      if (!data || !data.player_handle) {
        throw createError({ statusCode: 400, message: '未找到该句柄对应的玩家数据' })
      }
    } catch (e: any) {
      if (e.statusCode === 400) throw e
      throw createError({ statusCode: 400, message: '无法验证句柄，请检查格式是否正确' })
    }
    db.prepare('UPDATE users SET handle = ? WHERE id = ?').run(trimmed, userId)
    return { success: true, handle: trimmed }
  }

  throw createError({ statusCode: 400, message: '未知操作' })
}
