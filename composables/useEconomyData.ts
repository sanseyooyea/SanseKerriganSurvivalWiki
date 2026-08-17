import econData from '~/data/economy.json'

// 经济类型 → 中文标签
export const ECON_TYPE_LABELS: Record<string, string> = {
  generic: '建筑收入',
  harvest: '采集',
  addon: '挂件',
  miner: '装填',
  technician: '转化',
  spirit: '金融',
  extraction: '萃取',
  farm: '狩猎',
}

export interface EconomyHero {
  hero: string // 英文名（economy.json 的 hero，或 Technician/Spirit）
  nameZh: string
  roleId: number
  type: 'generic' | 'harvest' | 'addon' | 'miner' | 'technician' | 'spirit' | 'extraction' | 'farm'
  typeLabel: string
  headline: string
  special?: 'technician' | 'spirit'
  [k: string]: any
}

function econType(h: any): EconomyHero['type'] {
  if (h.special) return h.special
  if (h.farmEconomy) return 'farm'
  if (h.extractionEconomy) return 'extraction'
  if (h.harvestEconomy) return 'harvest'
  if (h.addonEconomy) return 'addon'
  if (h.minerEconomy) return 'miner'
  return 'generic'
}

function fmtNum(n: number) {
  return n % 1 === 0 ? String(n) : n.toFixed(2).replace(/\.?0+$/, '')
}

// 建筑/工人里的峰值每秒产矿（income/incomePeriod 的最大值）
function peakPerSec(list: any[]): number {
  let p = 0
  for (const b of list || []) {
    if (b.income && b.incomePeriod) p = Math.max(p, b.income / b.incomePeriod)
  }
  return p
}

// 手风琴/角色页头部右侧的一行速览
function makeHeadline(h: any, type: EconomyHero['type']): string {
  if (type === 'technician') return '击杀转化经济'
  if (type === 'spirit') return '金融 / 投资经济'
  if (type === 'farm') return '击杀 farming / 投资经济'
  if (type === 'harvest') return '探机采集'
  if (type === 'extraction') {
    const e = h.extraction
    if (e) {
      const v = e.verb || '萃取'
      return `寄生${v} ${Math.round(e.efficiencyBase * 100)}→${Math.round(e.efficiencyUpgraded * 100)}% · ${e.rangeLabel || '范围'} ${e.rangeBase}→${e.rangeUpgraded}`
    }
    return '寄生萃取'
  }
  const chrono = h.chrono ? (Array.isArray(h.chrono) ? h.chrono[0] : h.chrono) : null
  const cTag = chrono ? ` ×${chrono.timeScale}` : ''
  if (type === 'miner') {
    const p = peakPerSec(h.miners)
    return p ? `峰值 ${fmtNum(p)} 矿/s·工${cTag}` : `矿区装填${cTag}`
  }
  const p = peakPerSec(h.buildings)
  return p ? `峰值 ${fmtNum(p)} 矿/s${cTag}` : `${ECON_TYPE_LABELS[type]}${cTag}`
}

/**
 * 经济数据集中层：供 /economy 手风琴与 /classes/[id] 经济板块复用。
 * - econHeroes：economy.json 的 18 个英雄（关联 roleId/nameZh + type/headline）
 * - allEconomyHeroes：再拼上技术员 / 灵魂两个自包含特殊英雄
 * - hasEconomy / getEconomy：按英文名查（角色页据此决定是否显示经济板块）
 */
export function useEconomyData() {
  const { classes } = useClassData()

  const econHeroes = computed<EconomyHero[]>(() => {
    return (econData as any[])
      .map((hero: any) => {
        const role = classes.find(c => c.nameEn === hero.hero || c.nameZh === hero.hero)
        const type = econType(hero)
        return {
          ...hero,
          roleId: role?.id ?? -1,
          nameZh: role?.nameZh || hero.hero,
          type,
          typeLabel: ECON_TYPE_LABELS[type],
          headline: makeHeadline(hero, type),
        } as EconomyHero
      })
      .sort((a, b) => a.hero.localeCompare(b.hero))
  })

  const specials = computed<EconomyHero[]>(() => {
    return ([
      { hero: 'Technician', special: 'technician' as const },
      { hero: 'Spirit', special: 'spirit' as const },
    ]).map((s) => {
      const role = classes.find(c => c.nameEn === s.hero)
      const type = s.special
      return {
        ...s,
        roleId: role?.id ?? -1,
        nameZh: role?.nameZh || s.hero,
        type,
        typeLabel: ECON_TYPE_LABELS[type],
        headline: makeHeadline(s, type),
      } as EconomyHero
    })
  })

  const allEconomyHeroes = computed<EconomyHero[]>(() => [...econHeroes.value, ...specials.value])

  const econNames = computed(() => new Set(allEconomyHeroes.value.map(h => h.hero)))
  function hasEconomy(nameEn: string) {
    return econNames.value.has(nameEn)
  }
  function getEconomy(nameEn: string) {
    return allEconomyHeroes.value.find(h => h.hero === nameEn)
  }

  return { econHeroes, allEconomyHeroes, hasEconomy, getEconomy }
}

// —— 经济投资比排行榜 ——
// 把所有「有固定单位造价 ÷ 每秒产矿」的经济项拍平成可横向对比的行，按投资比排名。
// 公式逐字对齐 components/HeroEconomy.vue（roi / harvestRoi / addonRoi / minerPerSec），
// 仅统一气体口径：所有类型都把气体折算进投入（1 气 = 1 矿求和），包括 addon。
// 排除 extraction / technician / spirit / farm —— 收入来自寄生/击杀/理财，无固定单位投资比。

export interface EconomyRankRow {
  hero: string
  nameZh: string
  roleId: number
  type: EconomyHero['type']
  typeLabel: string
  label: string      // 行名：建筑名 / "矿区 × 探机" / "建筑 × 挂件" / 工人名
  mineral: number
  gas: number
  totalCost: number  // mineral + gas
  perSec: number     // 基础每秒产矿
  roi: number        // 基础投资比 = round(totalCost / perSec)
  timeScale: number  // 该英雄最优 chrono 的倍率（无则 1）
  roiBoosted: number // 加速投资比 = round(totalCost / (perSec × timeScale))
}

// 坦克挂件三档（与 HeroEconomy.vue 的 addonCols 一致）
const RANK_ADDON_COLS = [
  { label: '无挂件', multiplier: 1, cost: 0, gasCost: 0 },
  { label: '科技实验室', multiplier: 1.5, cost: 20, gasCost: 5 },
  { label: '反应堆', multiplier: 2, cost: 200, gasCost: 10 },
]
const HARVEST_TRIP_TRANSPORT = 0.1 // 探机运输往返基准(s)，同 HeroEconomy.vue

function bestTimeScale(h: any): number {
  if (!h.chrono) return 1
  const arr = Array.isArray(h.chrono) ? h.chrono : [h.chrono]
  return arr.reduce((m: number, c: any) => Math.max(m, c?.timeScale || 1), 1)
}

export function useEconomyRanking() {
  const { allEconomyHeroes } = useEconomyData()

  const rows = computed<EconomyRankRow[]>(() => {
    const out: EconomyRankRow[] = []
    for (const h of allEconomyHeroes.value) {
      const ts = bestTimeScale(h)
      const base = { hero: h.hero, nameZh: h.nameZh, roleId: h.roleId, type: h.type, typeLabel: h.typeLabel }
      const push = (label: string, mineral: number, gas: number, perSec: number) => {
        if (!perSec || perSec <= 0) return
        const totalCost = mineral + gas
        if (totalCost <= 0) return // 免费单位（如 DJ 粉丝、Artanis 召唤）无投资可言，不入榜
        out.push({
          ...base, label, mineral, gas, totalCost, perSec,
          roi: Math.round(totalCost / perSec),
          timeScale: ts,
          roiBoosted: Math.round(totalCost / (perSec * ts)),
        })
      }

      if (h.type === 'generic') {
        for (const b of h.buildings || []) {
          if (!b.income || !b.incomePeriod || b.cost == null) continue
          push(b.nameZh, b.cost, b.gasCost || 0, b.income / b.incomePeriod)
        }
      } else if (h.type === 'harvest') {
        for (const f of h.buildings || []) {
          if (!f.income || f.cost == null) continue
          for (const p of h.probes || []) {
            const perSec = (f.income * (p.amountMult || 1)) / ((p.mineTime || 0) + HARVEST_TRIP_TRANSPORT)
            push(`${f.nameZh} × ${p.nameZh}`, f.cost + (p.cost || 0), p.gasCost || 0, perSec)
          }
        }
      } else if (h.type === 'addon') {
        for (const b of h.buildings || []) {
          if (!b.income || !b.incomePeriod || b.cost == null) continue
          for (const col of RANK_ADDON_COLS) {
            push(`${b.nameZh} × ${col.label}`, b.cost + col.cost, col.gasCost, (b.income * col.multiplier) / b.incomePeriod)
          }
        }
      } else if (h.type === 'miner') {
        for (const m of h.miners || []) {
          if (!m.income || !m.incomePeriod || m.cost == null) continue
          push(m.nameZh, m.cost, m.gasCost || 0, m.income / m.incomePeriod)
        }
      }
      // extraction / technician / spirit / farm：无固定单位投资比，跳过
    }
    return out
  })

  const rankByBase = computed(() => [...rows.value].sort((a, b) => a.roi - b.roi))
  const rankByBoosted = computed(() => [...rows.value].sort((a, b) => a.roiBoosted - b.roiBoosted))

  return { rows, rankByBase, rankByBoosted }
}
