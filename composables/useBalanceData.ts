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

// Region group of the daily buckets. cn = 国服(China), intl = 外服(EU+NA+KR).
export type RegionGroup = 'cn' | 'intl'
export type RegionFilter = 'all' | RegionGroup

interface Daily {
  days: string[] // contiguous "YYYY-MM-DD", chronological
  regions: RegionGroup[]
  // flat per-day arrays aligned to days[]
  global: Record<RegionGroup, { s: number[]; k: number[] }> // survivor/kerrigan wins
  heroes: Record<string, Record<RegionGroup, { p: number[]; w: number[] }>> // plays/wins
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
    daily: Daily
  }

  const threshold = data.low_sample_threshold
  const byId = new Map<number, HeroBalance>(data.heroes.map(h => [h.role_id, h]))
  const teamById = new Map<number, number>(data.heroes.map(h => [h.role_id, h.team]))

  const getByRoleId = (id: number | string): HeroBalance | undefined =>
    byId.get(typeof id === 'string' ? parseInt(id, 10) : id)

  const daily = data.daily
  const dayCount = daily.days.length

  // Inclusive sum of a flat per-day array over [start, end].
  function sumRange(series: number[], start: number, end: number): number {
    let acc = 0
    for (let i = start; i <= end; i++) acc += series[i] || 0
    return acc
  }

  // Map a "YYYY-MM-DD" date to a day index, clamped into range. Since days are
  // contiguous we can offset from days[0] instead of scanning.
  function dayToIndex(date: string): number {
    if (!dayCount) return 0
    const base = Date.parse(daily.days[0] + 'T00:00:00')
    const t = Date.parse(date + 'T00:00:00')
    if (isNaN(t)) return 0
    const idx = Math.round((t - base) / 86_400_000)
    return Math.max(0, Math.min(idx, dayCount - 1))
  }

  /**
   * Aggregate the daily buckets over the inclusive day range [start, end] and
   * the given region filter, returning the same shape as the all-time
   * `global` + `heroes` so the page can render either interchangeably.
   */
  function aggregate(start: number, end: number, region: RegionFilter) {
    const s = Math.max(0, Math.min(start, dayCount - 1))
    const e = Math.max(s, Math.min(end, dayCount - 1))
    const grps = regionsFor(region)

    let survWins = 0
    let kerrWins = 0
    for (const g of grps) {
      survWins += sumRange(daily.global[g].s, s, e)
      kerrWins += sumRange(daily.global[g].k, s, e)
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
      const hw = daily.heroes[String(h.role_id)]
      let plays = 0
      let wins = 0
      if (hw) {
        for (const g of grps) {
          plays += sumRange(hw[g].p, s, e)
          wins += sumRange(hw[g].w, s, e)
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
    days: daily.days,
    dayCount,
    dayToIndex,
    aggregate,
  }
}
