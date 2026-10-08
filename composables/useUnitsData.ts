import unitsData from '~/data/units-v2.json'

// 属性徽章：(标签, Tailwind class 串)。class 用静态完整字符串（防 purge）。
export const ATTRIBUTE_LABELS: Record<string, [string, string]> = {
  Light: ['轻甲', 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'],
  Armored: ['重甲', 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300'],
  Biological: ['生物', 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'],
  Mechanical: ['机械', 'bg-slate-100 text-slate-600 dark:bg-slate-700/60 dark:text-slate-300'],
  Massive: ['巨型', 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'],
  Structure: ['建筑', 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'],
  Psionic: ['灵能', 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'],
  Heroic: ['英雄', 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'],
  MapBoss: ['首领', 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300'],
}
export const ATTRIBUTE_FALLBACK = ['bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300']

export const CATEGORY_LABELS: Record<string, string> = {
  hero: '英雄',
  troop: '兵种',
  building: '建筑',
  economy: '经济建筑',
  morph: '形态',
  summon: '召唤物',
}

// 武器 notes → 中文提示（未解析的部分单独标红，绝不猜数值）
export const WEAPON_NOTE_LABELS: Record<string, string> = {
  baseGameParent: '数值继承自基础游戏数据',
  periodInherited: '攻击间隔继承自基础游戏数据',
  amountInherited: '伤害值继承自基础游戏数据',
  zeroAmountDropped: '已忽略通用自杀/占位伤害效果',
  persistUntilDestroyed: '持续时间由脚本/目标决定，按单次结算',
  sweep: '扫射型攻击：同一目标只吃其中一段伤害',
  randomSet: '随机分支效果，取等分估计',
  switch: '条件分支效果，取默认/首分支',
  displayEffect: '由 DisplayEffect 回退解析（Effect 链无可静态解析伤害）',
}

export interface UnitComponent {
  effect: string
  amount: number
  bonus?: Record<string, number>
  armorReduction?: number
  hits?: number
  kind?: string
  secondary?: boolean
  vital?: boolean
  dot?: { behavior: string; duration: number | null; period: number | null }
  splash?: { radius: number; rings: { radius: number; fraction: number }[]; maxCount?: number }
}
export interface UnitWeapon {
  id: string
  nameZh: string | null
  period: number | null
  range: number | null
  minRange: number | null
  melee: boolean
  suicide: boolean
  targets: { ground: boolean; air: boolean; exclude: string[] }
  vitalDamage?: number | null
  components: UnitComponent[]
  unresolved: string[]
  notes: string[]
}
export interface UnitUpgradeLevel {
  level: number
  upgrade: string
  minerals: number
  gas: number
  time: number
  researchedBy?: string | null
  effects: { ref: string; op: string; value: number }[]
}
export interface UnitUpgrade {
  family: string
  nameZh: string
  researchable: boolean
  levels: UnitUpgradeLevel[]
}
export interface CurvePoint {
  level: number
  cost: { minerals: number; gas: number }
  hp: number
  shield: number
  armor: number
  weapons: { id: string; range: number | null; period: number | null } &
    Record<string, { perAttack: number; dps: number | null }>
}
export interface UnitEntry {
  id: string
  nameZh: string
  team: string
  owners: string[]
  category: string
  stats: {
    hp: number; shield: number; armor: number; shieldArmor: number
    hpRegen: number; shieldRegen: number; energy: number; speed: number
    creepSpeedMul: number | null; sight: number; armorName?: string
    armorLevel?: number; shieldArmorLevel?: number; radius?: number | null
  }
  cost: { minerals: number; gas: number; food: number; supplyProvided: number }
  attributes: string[]
  planes: string[]
  flags: string[]
  icon: string | null
  weapons: UnitWeapon[]
  upgrades: UnitUpgrade[]
  curve: CurvePoint[]
  derived: Record<string, any>
  produces?: string[]
  producedBy?: { from: string; abil: string; index?: string; kind: string; time?: number; count?: number }[]
}
export interface HeroEdge {
  from: string
  abil: string
  index?: string
  kind: string
  time?: number
  cooldown?: number
  requirements?: string
  button?: string
  count?: number
  units: string[]
}
export interface HeroUnitsEntry {
  team: string
  category: string | null
  roleId: number
  heroUnits: string[]
  unitIds: string[]
  edges: HeroEdge[]
}

const DATA = unitsData as unknown as {
  targets: Record<string, { attributes: string[]; armor: number }>
  heroes: Record<string, HeroUnitsEntry>
  units: Record<string, UnitEntry>
}

/**
 * 兵种数据集中层（对称 useTechData / useEconomyData）。
 * units-v2.json 由 scripts/build_units_v2.py 从地图提取：
 * 生产树、造价/人口、完整武器（对轻甲/重甲/凯瑞甘的 DPS）、升级曲线、性价比。
 */
export function useUnitsData() {
  const { classes } = useClassData()

  const targets = DATA.targets
  const heroMap = DATA.heroes
  const unitMap = DATA.units

  const roleOf = (nameEn: string) => classes.find(c => c.nameEn === nameEn)

  /** 某英雄的生产树条目（含 roleId/nameZh 关联）。 */
  function getHero(nameEn: string) {
    const h = heroMap[nameEn]
    if (!h) return undefined
    const role = roleOf(nameEn)
    return { ...h, nameEn, nameZh: role?.nameZh || nameEn, roleId: role?.id ?? -1 }
  }
  function hasUnits(nameEn: string) {
    return !!heroMap[nameEn]
  }
  function getUnit(id: string): UnitEntry | undefined {
    return unitMap[id]
  }

  /** 某英雄可达的单位条目，按发现顺序。 */
  function heroUnitEntries(nameEn: string): UnitEntry[] {
    const h = heroMap[nameEn]
    if (!h) return []
    return h.unitIds.map(id => unitMap[id]).filter(Boolean)
  }

  /** 按类别分组（兵种/建筑/经济建筑/形态/召唤物）。 */
  const CATEGORY_ORDER = ['troop', 'building', 'economy', 'morph', 'summon', 'hero']
  function groupByCategory(units: UnitEntry[]) {
    return CATEGORY_ORDER
      .map(cat => ({ category: cat, label: CATEGORY_LABELS[cat] || cat, units: units.filter(u => u.category === cat) }))
      .filter(g => g.units.length)
  }

  /** 谁生产了这个单位（跨英雄合并，取第一条边）。 */
  function producersOf(uid: string) {
    const out: { hero: string; edge: HeroEdge }[] = []
    for (const [hero, h] of Object.entries(heroMap)) {
      for (const e of h.edges) {
        if (e.units.includes(uid)) out.push({ hero, edge: e })
      }
    }
    return out
  }

  const allUnits = computed(() => Object.values(unitMap))

  return {
    targets, heroMap, unitMap, allUnits,
    hasUnits, getHero, getUnit, heroUnitEntries, groupByCategory, producersOf,
    roleOf,
  }
}
