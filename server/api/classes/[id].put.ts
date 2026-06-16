import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

function str(v: unknown, max = 4000): string | undefined {
  return typeof v === 'string' ? v.slice(0, max) : undefined
}

// 双轨制：在线编辑只允许改文案（职业简介 description / 攻略 notes）。
// 属性数值、技能、兵种/建筑等结构化数据与游戏地图绑定，走 git + seed + CI 校验，
// 不接受在线覆盖——避免线上手滑写错且绕过审计，也避免与地图重建冲突。
// 详见 docs/DATA_MAINTENANCE.md。
function sanitizeOverride(body: any): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  if (str(body?.description) !== undefined) out.description = str(body.description)
  if (str(body?.notes, 20000) !== undefined) out.notes = str(body.notes, 20000)
  return out
}

export default defineEventHandler(async (event) => {
  const user = requireRole(event, ['admin', 'editor'])

  const id = getRouterParam(event, 'id')
  if (!id || !/^\d+$/.test(id)) {
    throw createError({ statusCode: 400, message: '无效的职业ID' })
  }

  const body = await readBody(event)
  const clean = sanitizeOverride(body)
  const data = JSON.stringify(clean)

  const db = getDb()
  const existing = db.prepare('SELECT id FROM class_overrides WHERE class_id = ?').get(id)

  if (existing) {
    db.prepare('UPDATE class_overrides SET data = ?, updated_by = ?, updated_at = datetime(\'now\') WHERE class_id = ?')
      .run(data, user.id, id)
  } else {
    db.prepare('INSERT INTO class_overrides (class_id, data, updated_by) VALUES (?, ?, ?)')
      .run(id, data, user.id)
  }

  return { success: true }
})
