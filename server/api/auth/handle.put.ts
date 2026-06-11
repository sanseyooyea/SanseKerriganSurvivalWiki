import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  const user = requireUser(event)

  const body = await readBody(event)
  const { handle } = body

  if (!handle || typeof handle !== 'string') {
    throw createError({ statusCode: 400, message: '句柄不能为空' })
  }

  const trimmed = handle.trim()
  if (!/^\d+-S2-\d+-\d+$/.test(trimmed)) {
    throw createError({ statusCode: 400, message: '句柄格式不正确，应为类似 5-S2-1-1194668 的格式' })
  }

  // Verify handle exists by querying MMR API
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

  const db = getDb()
  db.prepare('UPDATE users SET handle = ? WHERE id = ?').run(trimmed, user.id)

  return { success: true, handle: trimmed }
})
