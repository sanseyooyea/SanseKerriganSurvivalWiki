import { getDb } from '~/server/utils/db'
import { requireRole } from '~/server/utils/auth'

// 经济/兵种条目的允许字段与类型
interface UnitEntry {
  id?: string
  nameZh?: string
  hp?: number
  shield?: number
  damage?: number
  attackSpeed?: number
}

function str(v: unknown, max = 4000): string | undefined {
  return typeof v === 'string' ? v.slice(0, max) : undefined
}
function numOrNull(v: unknown): number | null | undefined {
  if (v === null) return null
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined
}

function cleanUnit(u: any): UnitEntry {
  const out: UnitEntry = {}
  if (str(u?.id, 120) !== undefined) out.id = str(u.id, 120)
  if (str(u?.nameZh, 200) !== undefined) out.nameZh = str(u.nameZh, 200)
  for (const k of ['hp', 'shield', 'damage', 'attackSpeed'] as const) {
    const n = numOrNull(u?.[k])
    if (n !== undefined && n !== null) out[k] = n
  }
  return out
}

function cleanUnitList(v: unknown): UnitEntry[] | undefined {
  if (!Array.isArray(v)) return undefined
  return v.slice(0, 100).map(cleanUnit)
}

// 把任意请求体收敛成已知 schema，剔除未知字段，防止存入畸形或注入数据。
function sanitizeOverride(body: any): Record<string, unknown> {
  const out: Record<string, unknown> = {}

  if (str(body?.description) !== undefined) out.description = str(body.description)
  if (str(body?.notes, 20000) !== undefined) out.notes = str(body.notes, 20000)

  if (body?.stats && typeof body.stats === 'object' && !Array.isArray(body.stats)) {
    const allowed = ['hp', 'speed', 'armor', 'energy', 'energyRegen', 'damage', 'attackSpeed', 'attackCount', 'range']
    const stats: Record<string, number | null> = {}
    for (const k of allowed) {
      const n = numOrNull(body.stats[k])
      if (n !== undefined) stats[k] = n
    }
    out.stats = stats
  }

  if (Array.isArray(body?.abilities)) {
    out.abilities = body.abilities.slice(0, 60).map((a: any) => ({
      nameZh: str(a?.nameZh, 200) || '',
      nameEn: str(a?.nameEn, 200) || '',
      tooltip: str(a?.tooltip, 4000) || '',
    }))
  }

  const troops = cleanUnitList(body?.troops)
  if (troops) out.troops = troops
  const buildings = cleanUnitList(body?.buildings)
  if (buildings) out.buildings = buildings
  const economy = cleanUnitList(body?.economy)
  if (economy) out.economy = economy

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
