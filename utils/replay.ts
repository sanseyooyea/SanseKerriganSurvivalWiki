/**
 * 录像回放数据模型 + 解码。数据由 scripts/replay/parse_replay.py 生成（format 1）。
 *
 * 时间单位一律为 game loop；游戏内计时器 = loop / 22.4（"更快"速度）。
 * 扁平数组约定（省体积）：
 *   unit.p      [loop, x, y, loop, x, y, ...]  已知坐标关键帧（真实采样 + 英雄走位估算）
 *   unit.f      [loop, typeIdx, ...]           变形
 *   unit.ow     [loop, ownerPid, ...]          易主
 *   deaths      [loop, x, y, ownerPid, ...]    全部带坐标的死亡（按 loop 升序）
 *   cameras[p]  [loop, x, y, ...]
 *   perf[key]   [loop, value, ...]
 */

export const LOOPS_PER_SEC = 22.4

export interface ReplayPlayer {
  pid: number
  name: string
  handle: string
  color: string
  isHuman: boolean
  role: number | null
  roleNameEn?: string
  roleNameZh?: string | null
  team: 0 | 1 | null          // 0 = 幸存者，1 = 凯瑞甘方
  outcome: 0 | 1 | null
  mmrBefore: number | null
  mmrAfter: number | null
  gamesPlayed: number | null
  deathSec: number | null
  leaveLoop: number | null
  heroType: string | null
  heroId?: number
  perf: Record<string, number[]>
}

export interface ReplayUnitType {
  id: string
  nameZh: string | null
  icon: string | null
  category: string | null
}

export interface ReplayUnitRow {
  i: number
  t: number
  o: number
  b: number
  d: number | null
  p: number[]
  h?: 1
  f?: number[]
  ow?: number[]
}

export type ReplayEvent =
  | { t: number; kind: 'game_start' }
  | { t: number; kind: 'game_end'; winningTeam: 0 | 1 }
  | { t: number; kind: 'kerrigan'; pid: number; x: number; y: number }
  | { t: number; kind: 'hero_death'; pid: number; killer: number | null; unit: string; x: number; y: number }
  | { t: number; kind: 'ghost'; pid: number; x: number; y: number }
  | { t: number; kind: 'boss_kill'; pid: number; unit: string; x: number; y: number }
  | { t: number; kind: 'upgrade'; pid: number; upgrade: string; team?: 1 }
  | { t: number; kind: 'leave'; pid: number }
  | { t: number; kind: 'chat'; pid: number; text: string; toAll: boolean }
  | { t: number; kind: 'ping'; pid: number; x: number; y: number }

export interface ReplayVerify {
  mapHash: string | null
  /** 地图文件哈希在已知官方版本清单（data/ks2-map-hashes.json）里 */
  mapKnown: boolean
  dependencyCount: number
  dependenciesOk: boolean
  /** 录像是否带可验证签名。SC2 录像没有签名机制，目前恒为 false */
  signed: boolean
}

export interface ReplayData {
  format: number
  hash: string
  meta: {
    mapTitle: string
    mapKey: string | null
    mapEnum: string | null
    date: string
    build: number
    region: string
    loops: number
    startLoop: number
    mapId?: number
    gameMode?: number
    replayVersion?: number
    winningTeam?: 0 | 1
    rockPercentage?: number
  }
  /** 头部校验信息（parse_replay.precheck）。老数据可能没有 */
  verify?: ReplayVerify
  players: ReplayPlayer[]
  types: ReplayUnitType[]
  upgrades: Record<string, { nameZh: string | null; icon: string | null }>
  units: ReplayUnitRow[]
  deaths: number[]
  cameras: Record<string, number[]>
  events: ReplayEvent[]
}

export interface ReplayIndexEntry {
  file: string
  hash: string
  date: string
  mapKey: string | null
  loops: number
  winningTeam: 0 | 1 | null
  players: { name: string; role: string | null; team: 0 | 1 | null }[]
}

/** 播放用的已解码单位：坐标拆成 typed array，便于逐帧二分插值 */
export interface DecodedUnit {
  id: number
  type: number
  owner: number
  hero: boolean
  /** 可见区间：首个可信坐标 ~ 死亡 */
  from: number
  to: number
  loops: Int32Array
  xs: Float32Array
  ys: Float32Array
}

export function decodeUnits(data: ReplayData): DecodedUnit[] {
  const out: DecodedUnit[] = []
  for (const u of data.units) {
    const n = u.p.length / 3
    if (n === 0) continue
    const loops = new Int32Array(n)
    const xs = new Float32Array(n)
    const ys = new Float32Array(n)
    for (let k = 0; k < n; k++) {
      loops[k] = u.p[k * 3]
      xs[k] = u.p[k * 3 + 1]
      ys[k] = u.p[k * 3 + 2]
    }
    out.push({
      id: u.i,
      type: u.t,
      owner: u.o,
      hero: !!u.h,
      from: Math.max(u.b, loops[0]),
      to: u.d ?? Number.POSITIVE_INFINITY,
      loops, xs, ys,
    })
  }
  // 英雄最后画（压在最上层）
  out.sort((a, b) => Number(a.hero) - Number(b.hero))
  return out
}

/** 最后一个 ≤ t 的下标；全部 > t 时返回 -1 */
export function lowerIndex(arr: ArrayLike<number>, t: number, stride = 1): number {
  let lo = 0
  let hi = arr.length / stride - 1
  let ans = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (arr[mid * stride] <= t) { ans = mid; lo = mid + 1 } else hi = mid - 1
  }
  return ans
}

/** 相邻关键帧间隔超过此值（loop）就不插值：中间走了什么路线未知，直线会穿墙 */
export const MAX_INTERP_GAP = 20 * 22.4

/**
 * 单位在 t 时刻的位置。关键帧间隔 ≤ MAX_INTERP_GAP 时线性插值；
 * 否则停在上一个已知点并标记 stale（前端画成空心，表示"位置不确定"）。
 */
export function unitPosAt(u: DecodedUnit, t: number): [number, number, boolean] {
  const i = lowerIndex(u.loops, t)
  if (i < 0) return [u.xs[0], u.ys[0], true]
  const t0 = u.loops[i]
  if (i >= u.loops.length - 1) return [u.xs[i], u.ys[i], t - t0 > MAX_INTERP_GAP]
  const t1 = u.loops[i + 1]
  if (t1 - t0 > MAX_INTERP_GAP) return [u.xs[i], u.ys[i], t - t0 > MAX_INTERP_GAP / 2]
  const k = t1 > t0 ? (t - t0) / (t1 - t0) : 0
  return [u.xs[i] + (u.xs[i + 1] - u.xs[i]) * k, u.ys[i] + (u.ys[i + 1] - u.ys[i]) * k, false]
}

/** 扁平 [loop, a, b, ...] 序列在 t 时刻的值（stride 内第 col 列，阶梯取值） */
export function stepAt(flat: number[] | undefined, t: number, stride: number, col = 1): number | null {
  if (!flat || !flat.length) return null
  const i = lowerIndex(flat, t, stride)
  return i < 0 ? null : flat[i * stride + col]
}

export function fmtLoop(loop: number): string {
  const s = Math.max(0, Math.floor(loop / LOOPS_PER_SEC))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`
}

export function playerLabel(p: ReplayPlayer | undefined): string {
  if (!p) return '未知'
  return p.name
}

export function roleLabel(p: ReplayPlayer | undefined): string {
  if (!p) return ''
  return p.roleNameZh || p.roleNameEn || ''
}

/**
 * 录像对应的地形版本：同一张图有多次历史烘焙（key / key_YYYYMMDD），
 * 取「日期 ≤ 录像日期」里最新的一版；都晚于录像时退回最早一版。
 */
export function pickTerrainKey(
  mapKey: string | null,
  replayDate: string,
  maps: { key: string; date: string | null }[],
): string | null {
  if (!mapKey) return null
  const cands = maps.filter(m => m.key === mapKey || m.key.startsWith(mapKey + '_'))
  if (!cands.length) return null
  const day = replayDate.slice(0, 10)
  const dated = cands
    .map(m => ({ key: m.key, date: m.date ?? '9999-99-99' }))
    .sort((a, b) => a.date.localeCompare(b.date))
  const ok = dated.filter(m => m.date <= day)
  return (ok.length ? ok[ok.length - 1] : dated[0]).key
}
