import balanceData from '~/data/balance.json'

// Official-spec win rates precomputed offline from the prod DB dump
// (scripts/build_balance.py). Static snapshot — see `dumpThrough`.

export interface HeroBalance {
  role_id: number
  role: string // English enum name
  team: number // 0 = Survivor, 1 = Kerrigan
  plays: number
  wins: number
  win_rate: number | null // 0~1, null if never played
  low_sample: boolean // plays < threshold; win_rate is noisy
}

export interface GlobalBalance {
  survivor_wins: number
  kerrigan_wins: number
  games: number
  survivor_win_rate: number | null
  kerrigan_win_rate: number | null
}

// Region group of the weekly buckets. cn = 国服(China), intl = 外服(EU+NA+KR).
export type RegionGroup = 'cn' | 'intl'
export type RegionFilter = 'all' | RegionGroup

type Pair = [number, number] // [survivor/plays, kerrigan/wins]

interface Weekly {
  weeks: string[] // Monday date "YYYY-MM-DD" per ISO week, chronological
  regions: RegionGroup[]
  global: Record<RegionGroup, Pair[]> // grp -> aligned [surv_wins, kerr_wins]
  heroes: Record<string, Record<RegionGroup, Pair[]>> // role_id -> grp -> [plays, wins]
}

const REGION_GROUPS: RegionGroup[] = ['cn', 'intl']

function regionsFor(filter: RegionFilter): RegionGroup[] {
  return filter === 'all' ? REGION_GROUPS : [filter]
}

export function useBalanceData() {
  const data = balanceData as {
    generated_at: string
    dump_through: string
    low_sample_threshold: number
    global: GlobalBalance
    heroes: HeroBalance[]
    weekly: Weekly
  }

  const threshold = data.low_sample_threshold
  const byId = new Map<number, HeroBalance>(data.heroes.map(h => [h.role_id, h]))
  const teamById = new Map<number, number>(data.heroes.map(h => [h.role_id, h.team]))

  const getByRoleId = (id: number | string): HeroBalance | undefined =>
    byId.get(typeof id === 'string' ? parseInt(id, 10) : id)

  const weekly = data.weekly
  const weekCount = weekly.weeks.length

  // Sum a pair-series over the inclusive week range [start, end].
  function sumRange(series: Pair[], start: number, end: number): Pair {
    let a = 0
    let b = 0
    for (let i = start; i <= end; i++) {
      const c = series[i]
      if (c) {
        a += c[0]
        b += c[1]
      }
    }
    return [a, b]
  }

  /**
   * Aggregate the weekly buckets over the inclusive week range [start, end] and
   * the given region filter, returning the same shape as the all-time
   * `global` + `heroes` so the page can render either interchangeably.
   */
  function aggregate(start: number, end: number, region: RegionFilter) {
    const s = Math.max(0, Math.min(start, weekCount - 1))
    const e = Math.max(s, Math.min(end, weekCount - 1))
    const grps = regionsFor(region)

    let survWins = 0
    let kerrWins = 0
    for (const g of grps) {
      const [sw, kw] = sumRange(weekly.global[g], s, e)
      survWins += sw
      kerrWins += kw
    }
    const games = survWins + kerrWins
    const global: GlobalBalance = {
      survivor_wins: survWins,
      kerrigan_wins: kerrWins,
      games,
      survivor_win_rate: games ? survWins / games : null,
      kerrigan_win_rate: games ? kerrWins / games : null,
    }

    const heroes: HeroBalance[] = data.heroes.map(h => {
      const hw = weekly.heroes[String(h.role_id)]
      let plays = 0
      let wins = 0
      if (hw) {
        for (const g of grps) {
          const [p, w] = sumRange(hw[g], s, e)
          plays += p
          wins += w
        }
      }
      return {
        role_id: h.role_id,
        role: h.role,
        team: teamById.get(h.role_id) ?? h.team,
        plays,
        wins,
        win_rate: plays ? wins / plays : null,
        low_sample: plays < threshold,
      }
    })

    return { global, heroes }
  }

  return {
    global: data.global,
    heroes: data.heroes,
    dumpThrough: data.dump_through,
    lowSampleThreshold: threshold,
    getByRoleId,
    // time × region
    weeks: weekly.weeks,
    weekCount,
    aggregate,
  }
}
