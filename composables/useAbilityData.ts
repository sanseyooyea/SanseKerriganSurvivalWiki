import abilitiesData from '~/data/abilities.json'
import veterancyData from '~/data/veterancy.json'

export interface AbilityInfo {
  nameZh: string
  nameEn: string
  tooltip: string
  icon?: string // ability-icons/ 下的 png 名；少数召唤/研究/被动类技能无图标
  // 同一 ability id 被多个英雄共用、但各自指令卡按钮面不同名时，按英雄(nameEn)覆盖显示。
  perHero?: Record<string, { nameZh?: string; tooltip?: string; icon?: string }>
}

export interface VeterancyInfo {
  str: number
  agi: number
  int: number
  heroes: string[]
}

export function useAbilityData() {
  const abilities = abilitiesData as Record<string, AbilityInfo>

  const getAbility = (id: string): AbilityInfo | undefined => abilities[id]

  return { abilities, getAbility }
}

export function useVeterancyData() {
  const veterancy = veterancyData as Record<string, VeterancyInfo>

  const getForHero = (heroName: string): VeterancyInfo | undefined =>
    Object.values(veterancy).find(v => v.heroes.includes(heroName))

  return { veterancy, getForHero }
}
