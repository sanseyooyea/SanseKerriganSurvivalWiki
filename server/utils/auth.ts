import jwt from 'jsonwebtoken'
import type { H3Event } from 'h3'
import { getDb } from '~/server/utils/db'

const JWT_SECRET = process.env.JWT_SECRET
// 生产环境必须显式配置密钥；缺失则直接拒绝启动，避免用可预测的默认值签发 token。
if (!JWT_SECRET && process.env.NODE_ENV === 'production') {
  throw new Error('JWT_SECRET 环境变量未配置，拒绝以默认密钥启动')
}
const SECRET = JWT_SECRET || 'ks2-wiki-dev-secret-change-in-prod'

export interface TokenPayload {
  userId: number
  username: string
  role: string
}

export interface AuthUser {
  id: number
  username: string
  role: 'admin' | 'editor' | 'user'
  handle: string
}

export function signToken(payload: TokenPayload): string {
  return jwt.sign(payload, SECRET, { expiresIn: '7d' })
}

export function verifyToken(token: string): TokenPayload | null {
  try {
    return jwt.verify(token, SECRET) as TokenPayload
  } catch {
    return null
  }
}

/**
 * 校验请求携带的有效 token，并从数据库取出最新的用户记录。
 * token 里的 role 只是签发时的快照，权限判断必须以库里当前 role 为准，
 * 否则降权后 7 天内旧 token 仍能越权操作。
 */
export function requireUser(event: H3Event): AuthUser {
  const auth = getHeader(event, 'authorization')
  if (!auth?.startsWith('Bearer ')) {
    throw createError({ statusCode: 401, message: '未登录' })
  }
  const payload = verifyToken(auth.slice(7))
  if (!payload) {
    throw createError({ statusCode: 401, message: '登录已过期' })
  }
  const db = getDb()
  const user = db
    .prepare('SELECT id, username, role, handle FROM users WHERE id = ?')
    .get(payload.userId) as AuthUser | undefined
  if (!user) {
    throw createError({ statusCode: 401, message: '用户不存在' })
  }
  return { ...user, handle: user.handle || '' }
}

/** 在 requireUser 基础上，要求用户角色在 roles 白名单内。 */
export function requireRole(event: H3Event, roles: AuthUser['role'][]): AuthUser {
  const user = requireUser(event)
  if (!roles.includes(user.role)) {
    throw createError({ statusCode: 403, message: '权限不足' })
  }
  return user
}
