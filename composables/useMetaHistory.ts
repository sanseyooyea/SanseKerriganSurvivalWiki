import metaData from '~/data/meta-history.json'

// Per-role win-rate time series precomputed offline from the prod DB dump's
// `historical_balance` table (scripts/build_meta.py), downsampled to one
// snapshot per ISO week. Static snapshot — see `dumpThrough`.

export interface RoleStat {
  winrate: number // 0..1
  sample: number
  k: number | null
  p: number | null
}

export interface MetaSnapshot {
  ds: string // full timestamp
  date: string // YYYY-MM-DD
  roles: Record<string, RoleStat> // English role_name -> stat
}

export interface MetaRole {
  role: string // English role_name
  team: number // 0 = Survivor, 1 = Kerrigan
}

export function useMetaHistory() {
  const data = metaData as {
    generated_at: string
    dump_through: string | null
    roles: MetaRole[]
    snapshots: MetaSnapshot[]
  }

  return {
    roles: data.roles,
    snapshots: data.snapshots,
    dumpThrough: data.dump_through,
  }
}
