import rolesData from '~/data/roles.json'

export interface ClassStats {
  hp: number | null
  speed: number | null
  armor: number | null
  energy: number | null
  energyRegen: number | null
  damage: number | null
  attackSpeed: number | null
  attackCount: number | null
  range: number | null
}

export interface ClassInfo {
  id: number
  nameEn: string
  nameZh: string
  heroUnits: string[]
  category: string
  team: string
  unitIcon: string
  portrait: string
  description: string
  stats: ClassStats
  abilities: string[]
}

export function useClassData() {
  const classes = rolesData as ClassInfo[]

  const getById = (id: number) => classes.find(c => c.id === id)

  const filterByTeam = (team: string) =>
    team === 'All' ? classes : classes.filter(c => c.team === team)

  const filterByCategory = (category: string) =>
    category === 'All' ? classes : classes.filter(c => c.category === category)

  const getAll = () => classes

  return { classes, getAll, getById, filterByTeam, filterByCategory }
}
