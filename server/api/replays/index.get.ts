import { getDb } from '~/server/utils/db'
import { verifyToken } from '~/server/utils/auth'
import { publicRow, kickQueue, type ReplayRow } from '~/server/utils/replays'

/**
 * 录像列表（只含解析完成的），按上传时间倒序分页。
 * ?mine=1 且已登录时，额外返回当前用户自己未完成（排队/解析中/失败）的记录。
 */
export default defineEventHandler((event) => {
  // 服务重启后首个请求顺带恢复队列
  kickQueue()

  const q = getQuery(event)
  const page = Math.min(10_000, Math.max(1, Math.floor(Number(q.page)) || 1))
  const size = 24
  const auth = getHeader(event, 'authorization')
  const meId = auth?.startsWith('Bearer ') ? (verifyToken(auth.slice(7))?.userId || 0) : 0

  const db = getDb()
  const total = (db.prepare(`SELECT COUNT(*) AS n FROM replays WHERE status = 'done'`).get() as { n: number }).n
  const rows = db.prepare(`
    SELECT r.*, u.username AS uploader_name FROM replays r
    LEFT JOIN users u ON u.id = r.uploader_id
    WHERE r.status = 'done'
    ORDER BY r.created_at DESC, r.rowid DESC
    LIMIT ? OFFSET ?
  `).all(size, (page - 1) * size) as ReplayRow[]

  let mine: ReturnType<typeof publicRow>[] = []
  if (meId && q.mine) {
    mine = (db.prepare(`
      SELECT * FROM replays WHERE uploader_id = ? AND status != 'done'
      ORDER BY created_at DESC LIMIT 20
    `).all(meId) as ReplayRow[]).map(r => publicRow(r, meId))
  }

  return { total, page, pageSize: size, replays: rows.map(r => publicRow(r, meId)), mine }
})
