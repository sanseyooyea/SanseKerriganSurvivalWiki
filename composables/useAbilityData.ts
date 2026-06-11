import abilitiesData from '~/data/abilities.json'
import veterancyData from '~/data/veterancy.json'

export interface AbilityInfo {
  nameZh: string
  nameEn: string
  tooltip: string
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
