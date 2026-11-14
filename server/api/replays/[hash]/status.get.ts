import { getDb } from '~/server/utils/db'
import { isValidHash, publicRow, kickQueue, type ReplayRow } from '~/server/utils/replays'

/** 单个录像的解析状态（前端上传后轮询）；排队中时附带前面还有几个 */
export default defineEventHandler((event) => {
  const hash = String(getRouterParam(event, 'hash') || '').toLowerCase()
  if (!isValidHash(hash)) throw createError({ statusCode: 400, message: '无效的录像编号' })
  kickQueue()
  const db = getDb()
  const row = db.prepare(`
    SELECT r.*, u.username AS uploader_name FROM replays r
    LEFT JOIN users u ON u.id = r.uploader_id WHERE r.hash = ?`).get(hash) as ReplayRow | undefined
  if (!row) throw createError({ statusCode: 404, message: '录像不存在' })
  let ahead = 0
  if (row.status === 'queued') {
    ahead = (db.prepare(`
      SELECT COUNT(*) AS n FROM replays
      WHERE status IN ('queued', 'processing') AND hash != ?
        AND (status = 'processing' OR created_at < ? OR (created_at = ? AND rowid < (SELECT rowid FROM replays WHERE hash = ?)))`,
    ).get(hash, row.created_at, row.created_at, hash) as { n: number }).n
  }
  return { replay: publicRow(row), ahead }
})
