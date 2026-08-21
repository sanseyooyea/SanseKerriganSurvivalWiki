import techData from '~/data/tech.json'

// 升级分类(UpgradeType:*) → 中文标签。未知分类回退到「其他强化」。
export const TECH_CATEGORY_LABELS: Record<string, string> = {
  AttackBonus: '攻击强化',
  ArmorBonus: '防御强化',
  SpellResearch: '技能研究',
  Talents: '天赋',
}
export const TECH_CATEGORY_FALLBACK = '其他强化'

export function techCategoryLabel(cat: string | null | undefined): string {
  if (!cat) return TECH_CATEGORY_FALLBACK
  return TECH_CATEGORY_LABELS[cat] || TECH_CATEGORY_FALLBACK
}

export interface TechLevel {
  level: number
  cost: number
  gasCost: number
  time: number
  descZh: string
}
export interface TechUpgrade {
  id: string
  nameZh: string
  category: string | null
  icon: string | null
  levels: TechLevel[]
}
// 秋伊专属：galaxy 驱动的「小进化」次要强化（升级时可选，英文说明，与研究科技树独立）
export interface ChewolutionUpgrade {
  index: number
  link: string
  descEn: string
  maxCount: number
  category: string
}
export interface TechHero {
  hero: string           // 英文名（tech.json 的 hero）
  nameZh: string
  roleId: number
  researchAbility: string | null
  researchAbilities?: string[]
  upgrades: TechUpgrade[]
  chewolution?: ChewolutionUpgrade[]
}

// 按分类聚合升级组（保持组内既有顺序），供组件分区渲染。
export interface TechCategoryGroup {
  category: string | null
  label: string
  upgrades: TechUpgrade[]
}
function groupByCategory(upgrades: TechUpgrade[]): TechCategoryGroup[] {
  const order: (string | null)[] = []
  const map = new Map<string | null, TechUpgrade[]>()
  for (const u of upgrades) {
    const key = u.category ?? null
    if (!map.has(key)) { map.set(key, []); order.push(key) }
    map.get(key)!.push(u)
  }
  return order.map(key => ({
    category: key,
    label: techCategoryLabel(key),
    upgrades: map.get(key)!,
  }))
}

/**
 * 科技数据集中层：供 /classes/[id] 的「科技研究」板块复用（试点：Swann + Chew）。
 * - techHeroes：tech.json 的英雄（关联 roleId/nameZh）
 * - hasTech / getTech：按英文名查（角色页据此决定是否显示科技板块）
 * - getTechGroups：取某英雄按分类分区后的升级组
 * 对称 useEconomyData()。
 */
export function useTechData() {
  const { classes } = useClassData()

  const techHeroes = computed<TechHero[]>(() => {
    return (techData as any[]).map((hero: any) => {
      const role = classes.find(c => c.nameEn === hero.hero || c.nameZh === hero.hero)
      return {
        ...hero,
        roleId: role?.id ?? -1,
        nameZh: role?.nameZh || hero.hero,
      } as TechHero
    })
  })

  const techNames = computed(() => new Set(techHeroes.value.map(h => h.hero)))
  const allTechHeroes = computed(() => techHeroes.value)

  function hasTech(nameEn: string) {
    return techNames.value.has(nameEn)
  }
  function getTech(nameEn: string): TechHero | undefined {
    return techHeroes.value.find(h => h.hero === nameEn)
  }
  function getTechGroups(nameEn: string): TechCategoryGroup[] {
    const h = getTech(nameEn)
    return h ? groupByCategory(h.upgrades) : []
  }

  return { techHeroes, allTechHeroes, hasTech, getTech, getTechGroups }
}
