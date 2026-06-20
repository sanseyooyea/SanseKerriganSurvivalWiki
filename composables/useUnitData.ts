import unitsData from '~/data/units.json'

export interface HeroUnit {
  id: string
  nameZh: string
  hp?: number
  shield?: number
  armor?: number
  speed?: number
  damage?: number
  attackSpeed?: number
  attackCount?: number
  range?: number
}

interface HeroUnits {
  troops: HeroUnit[]
  buildings: HeroUnit[]
  economy: HeroUnit[]
}

export function useUnitData() {
  const data = unitsData as Record<string, HeroUnits>

  function getForHero(nameEn: string): HeroUnits {
    return data[nameEn] || data[nameEn.replace(' ', '_')] || { troops: [], buildings: [], economy: [] }
  }

  return { getForHero }
}
