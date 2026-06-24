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

export function useBalanceData() {
  const data = balanceData as {
    generated_at: string
    dump_through: string
    low_sample_threshold: number
    global: GlobalBalance
    heroes: HeroBalance[]
  }

  const byId = new Map<number, HeroBalance>(data.heroes.map(h => [h.role_id, h]))

  const getByRoleId = (id: number | string): HeroBalance | undefined =>
    byId.get(typeof id === 'string' ? parseInt(id, 10) : id)

  return {
    global: data.global,
    heroes: data.heroes,
    dumpThrough: data.dump_through,
    lowSampleThreshold: data.low_sample_threshold,
    getByRoleId,
  }
}
