import { getDb } from '~/server/utils/db'
import { requireUser } from '~/server/utils/auth'
import { isValidHash, deleteReplay } from '~/server/utils/replays'

/** 删除录像：上传者本人或管理员；正在解析中的不能删（子进程正在写文件） */
export default defineEventHandler((event) => {
  const user = requireUser(event)
  const hash = String(getRouterParam(event, 'hash') || '').toLowerCase()
  if (!isValidHash(hash)) throw createError({ statusCode: 400, message: '无效的录像编号' })
  const row = getDb().prepare(`SELECT uploader_id, status FROM replays WHERE hash = ?`).get(hash) as
    | { uploader_id: number | null; status: string } | undefined
  if (!row) throw createError({ statusCode: 404, message: '录像不存在' })
  if (user.role !== 'admin' && row.uploader_id !== user.id) {
    throw createError({ statusCode: 403, message: '只能删除自己上传的录像' })
  }
  if (row.status === 'processing') {
    throw createError({ statusCode: 409, message: '正在解析中，请稍后再删除' })
  }
  deleteReplay(hash)
  return { ok: true }
})
