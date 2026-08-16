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
}

export interface EconomyHero {
  hero: string // 英文名（economy.json 的 hero，或 Technician/Spirit）
  nameZh: string
  roleId: number
  type: 'generic' | 'harvest' | 'addon' | 'miner' | 'technician' | 'spirit' | 'extraction'
  typeLabel: string
  headline: string
  special?: 'technician' | 'spirit'
  [k: string]: any
}

function econType(h: any): EconomyHero['type'] {
  if (h.special) return h.special
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
  if (type === 'harvest') return '探机采集'
  if (type === 'extraction') {
    const e = h.extraction
    if (e) return `寄生萃取 ${Math.round(e.efficiencyBase * 100)}→${Math.round(e.efficiencyUpgraded * 100)}% · 范围 ${e.rangeBase}→${e.rangeUpgraded}`
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
