import { createHash } from 'node:crypto'
import { getDb } from '~/server/utils/db'

// 客户端在每次路由切换后调用，记录一次页面浏览。
// 无需登录；做轻量校验和机器人过滤，避免污染统计。
const BOT_RE = /bot|crawl|spider|slurp|bing|baidu|yandex|duckduck|facebookexternalhit|headless|curl|wget|python-requests|axios/i

// 只统计真实页面路径，挡掉 API/静态资源/异常长路径。
function isTrackablePath(p: string): boolean {
  if (typeof p !== 'string' || !p.startsWith('/') || p.length > 200) return false
  if (p.startsWith('/api/') || p.startsWith('/_')) return false
  if (/\.[a-z0-9]{1,5}$/i.test(p)) return false // .js/.png/.ico 等
  return true
}

// 本地日（服务器时区）YYYY-MM-DD
function today(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

// 取来源站点 host（去掉协议、路径、参数）。同站来源记为空（直接/站内跳转）。
function refHost(ref: unknown, selfHost: string): string {
  if (typeof ref !== 'string' || !ref) return ''
  try {
    const h = new URL(ref).hostname.toLowerCase()
    if (!h || h === selfHost) return ''
    return h.slice(0, 100)
  } catch {
    return ''
  }
}

export default defineEventHandler(async (event) => {
  const body = await readBody(event).catch(() => null)
  const path = body?.path
  if (!isTrackablePath(path)) {
    throw createError({ statusCode: 400, message: '参数错误' })
  }

  const ua = getHeader(event, 'user-agent') || ''
  if (BOT_RE.test(ua)) return { ok: true } // 机器人静默丢弃

  // 真实 IP：宿主机 Nginx 反代会带 x-forwarded-for，取第一段。
  const xff = getHeader(event, 'x-forwarded-for') || ''
  const ip = xff.split(',')[0].trim() || getRequestIP(event) || ''

  const day = today()
  // 访客指纹：IP+UA+day 哈希。含 day 盐，跨天不可关联 → 按日去重 UV。
  const visitor = createHash('sha256').update(`${ip}|${ua}|${day}`).digest('hex').slice(0, 16)

  const selfHost = (getRequestHost(event) || '').toLowerCase().split(':')[0]
  const ref = refHost(body?.ref, selfHost)

  const db = getDb()
  db.prepare('INSERT INTO page_views (day, path, visitor, ref) VALUES (?, ?, ?, ?)')
    .run(day, String(path).slice(0, 200), visitor, ref)

  return { ok: true }
})
