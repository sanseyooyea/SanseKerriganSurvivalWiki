import type { RockCandidate } from './useTerrainData'

/**
 * 石头（可破坏障碍）生成算法的 JS 复刻，逐段对齐 Scripts/game/rocks.galaxy
 * (`gt_Game_Rocks_PlaceRocks_Func` / `IsRockPositionBad`)。
 *
 * 关键：KS2 里石头是**实时阻挡寻路的单位**——放一批 → 更新寻路 → 逐个复查、
 * 移除会导致周边点不连通或绕行超限的坏石头 → 循环补放。正是这个「带活体阻挡的
 * 放置-复查-移除」循环保证**不会出现被石头封死、无法进入的区域**。
 *
 * 本模拟器忠实复刻该机制：
 *  1. 洗牌候选斜坡，目标数 n = floor(rockProb × 候选数)。
 *  2. 按顺序放置：每颗石头以 ~4×4 足迹阻挡通行网格；放置前用 isRockPositionBad
 *     在**含已放石头**的网格上校验（±3 邻点 ≥2 可通行、彼此连通、绕行 ≤ maxElongation）。
 *  3. 全局连通性兜底：洪水填充，若某片本可到达的区域被石头新封死，移除肇事石头，
 *     直至全图连通——硬保证「无法进入的地区」不会出现。
 *
 * 石头**每局随机**，同种子可复现、可重掷。寻路 = 静态可走地面 (t3CellFlags bit0x02)
 * + **悬崖高度层 (t3SyncCliffLevel)** 的**跨格判定**：相邻两 cell 高差 > cliffStep 即
 * 悬崖面，不可跨越——只有斜坡能连通台地。缺了这层，bit0x02 几乎全图可走，斜坡就
 * 不成咽喉，石头封不住任何东西，也就复现/防不住死路。加入悬崖跨格规则后，封住斜坡
 * 的石头会被 isRockPositionBad 判坏并移除，从而**保证不会出现无法进入的区域**。
 */

export interface SimResult {
  placed: RockCandidate[]
  rejected: RockCandidate[]
  n: number          // 目标放置数
  count: number      // 候选总数
  maxElongation: number
  reclaimed: number  // 全局兜底额外移除、避免封死区域的石头数
}

interface Grid {
  isPassable: (cx: number, cy: number) => boolean
  cliffAt: (cx: number, cy: number) => number
  cliffStep: number
  size: number
}

const ROCK_RADIUS = 2.0 // ~4×4 足迹（对齐 CommonTerrainDebris4x4 / ±3 邻点采样）
const OFFSETS: [number, number][] = [
  [-3, 0], [3, 0], [0, -3], [0, 3],
  [-3, 3], [3, 3], [3, -3], [-3, -3],
]

// —— seeded RNG (mulberry32)：同 seed → 同布局，供分享/重现 —— //
function mulberry32(seed: number) {
  let a = seed >>> 0
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// gf_ArrayListIntShuffle：Fisher–Yates
function shuffle<T>(arr: T[], rng: () => number): T[] {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

// gf_GaussianFromDistribution：Box–Muller，返回 mean + z*sqrt(variance)
function gaussian(mean: number, variance: number, rng: () => number): number {
  let u = 0
  let v = 0
  while (u === 0) u = rng()
  while (v === 0) v = rng()
  const z = Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
  return mean + z * Math.sqrt(variance)
}

/**
 * 模拟一局石头布局。
 * @param candidates 候选池（terrain.rockCandidates，顺序即 gv_terrainRockRegions 顺序）
 * @param grid       通行网格（useTerrainData 的 isPassable + cliffAt + cliffStep + size）
 * @param rockProb   放置概率 ∈ [0.3,0.8]（实战随历史胜率动态；此处由 UI 滑条给定）
 * @param seed       随机种子（同 seed → 同布局）
 */
export function simulateRocks(
  candidates: RockCandidate[],
  grid: Grid,
  rockProb: number,
  seed: number,
): SimResult {
  const W = grid.size
  const H = grid.size
  const count = candidates.length

  // 静态可通行（越界视为不可通行）
  const staticPass = (cx: number, cy: number) =>
    cx >= 0 && cy >= 0 && cx < W && cy < H && grid.isPassable(cx, cy)

  // 悬崖高度层（预解一次）：相邻两 cell 高差 > cliffStep 即不可跨越的悬崖面
  const cliffLevel = new Uint8Array(W * H)
  for (let cy = 0; cy < H; cy++) {
    for (let cx = 0; cx < W; cx++) cliffLevel[cy * W + cx] = grid.cliffAt(cx, cy)
  }
  const step = grid.cliffStep
  // 跨格是否连通：两端可走地面且高差在一个斜坡台阶内
  const edge = (a: number, b: number) =>
    Math.abs(cliffLevel[a] - cliffLevel[b]) <= step

  // 石头占用的 cell（活体阻挡）
  const blocked = new Uint8Array(W * H)
  const passable = (cx: number, cy: number) =>
    staticPass(cx, cy) && blocked[cy * W + cx] === 0

  // 一颗石头以 center 为心、半径 ROCK_RADIUS 覆盖的 cell（仅取静态可通行处）
  function footprint(x: number, y: number): number[] {
    const cx0 = Math.floor(x)
    const cy0 = Math.floor(y)
    const cells: number[] = []
    const r = Math.ceil(ROCK_RADIUS)
    for (let dx = -r; dx <= r; dx++) {
      for (let dy = -r; dy <= r; dy++) {
        const cx = cx0 + dx
        const cy = cy0 + dy
        if (cx < 0 || cy < 0 || cx >= W || cy >= H) continue
        const ex = cx + 0.5 - x
        const ey = cy + 0.5 - y
        if (ex * ex + ey * ey <= ROCK_RADIUS * ROCK_RADIUS && staticPass(cx, cy)) {
          cells.push(cy * W + cx)
        }
      }
    }
    return cells
  }
  const setBlocked = (cells: number[], v: number) => { for (const c of cells) blocked[c] = v }

  // —— 带世代戳的 BFS（O(1) 重置，8 向、步数计代价）—— //
  const stamp = new Int32Array(W * H)
  const dist = new Int32Array(W * H)
  const queue = new Int32Array(W * H)
  let gen = 0
  const DIRS = [-1, 0, 1, 0, 0, -1, 0, 1, -1, -1, -1, 1, 1, -1, 1, 1]

  /**
   * 从 src 出发 BFS，判定所有 targets 是否都在 maxDist 步内可达（含 src 自身连通性）。
   * cap 限制探索节点数：超出仍未达标 → 视为被封/绕行过远。
   */
  function reachAll(src: number, targets: number[], maxDist: number, cap: number): boolean {
    gen++
    let head = 0
    let tail = 0
    stamp[src] = gen
    dist[src] = 0
    queue[tail++] = src
    const need = new Set(targets)
    need.delete(src)
    if (need.size === 0) return true
    let visited = 0
    while (head < tail) {
      const cur = queue[head++]
      const cd = dist[cur]
      if (cd >= maxDist) continue // 超出绕行上限，不再扩展
      if (++visited > cap) return false
      const cx = cur % W
      const cy = (cur / W) | 0
      for (let d = 0; d < 16; d += 2) {
        const nx = cx + DIRS[d]
        const ny = cy + DIRS[d + 1]
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue
        if (!passable(nx, ny)) continue
        const ni = ny * W + nx
        if (!edge(cur, ni)) continue // 悬崖面不可跨越
        if (stamp[ni] === gen) continue
        stamp[ni] = gen
        dist[ni] = cd + 1
        if (need.has(ni)) {
          need.delete(ni)
          if (need.size === 0) return true
        }
        queue[tail++] = ni
      }
    }
    return need.size === 0
  }

  const rng = mulberry32(seed)
  const idx = shuffle(candidates.map((_, i) => i), rng)
  const n = Math.floor(rockProb * count)

  // elongationMean/Variance 与地图逻辑一致（rockProb∈[0.3,0.8] → mean∈[90,200]）
  const elongationMean = Math.min(200, Math.max(90, 90 + 220 * (rockProb - 0.3)))
  const elongationVariance = 225

  // IsRockPositionBad：每次抽一次 Gaussian（对齐地图），用含已放石头的网格判定
  function isRockPositionBad(x: number, y: number): boolean {
    const maxElongation = Math.round(
      Math.min(200, Math.max(90, gaussian(elongationMean, elongationVariance, rng))),
    )
    const pts: number[] = []
    for (const [dx, dy] of OFFSETS) {
      const cx = Math.floor(x + dx)
      const cy = Math.floor(y + dy)
      if (passable(cx, cy)) pts.push(cy * W + cx)
    }
    if (pts.length < 2) return true
    // 连通性 + 绕行上限：其余邻点都要在 maxElongation 步内从 pts[0] 可达
    return !reachAll(pts[0], pts, maxElongation, 20000)
  }

  // —— 放置：按洗牌顺序逐个校验并实时阻挡，直到放满 n（坏点跳过，继续往后找）—— //
  const placed: { c: RockCandidate; cells: number[] }[] = []
  const rejected: RockCandidate[] = []
  for (let k = 0; k < count && placed.length < n; k++) {
    const c = candidates[idx[k]]
    if (isRockPositionBad(c.x, c.y)) {
      rejected.push(c)
      continue
    }
    const cells = footprint(c.x, c.y)
    setBlocked(cells, 1)
    placed.push({ c, cells })
  }

  // —— 复查：全部就位后再逐个校验，移除此时变坏的石头（对齐地图的移除循环）—— //
  for (let pass = 0; pass < 3; pass++) {
    let changed = false
    for (let k = placed.length - 1; k >= 0; k--) {
      const r = placed[k]
      if (isRockPositionBad(r.c.x, r.c.y)) {
        setBlocked(r.cells, 0)
        placed.splice(k, 1)
        rejected.push(r.c)
        changed = true
      }
    }
    if (!changed) break
  }

  // —— 全局连通性兜底：确保没有被石头新封死的区域 —— //
  const reclaimed = enforceGlobalConnectivity(placed, rejected)

  return {
    placed: placed.map(r => r.c),
    rejected,
    n,
    count,
    maxElongation: Math.round(elongationMean),
    reclaimed,
  }

  /**
   * 洪水填充比对「无石头基准可达区」与「含石头可达区」：任何本可到达却被石头封死的
   * 静态可通行 cell，说明有石头造成死区 → 移除紧邻该死区的石头，循环至全图连通。
   * 返回额外移除的石头数。
   */
  function enforceGlobalConnectivity(
    kept: { c: RockCandidate; cells: number[] }[],
    rej: RockCandidate[],
  ): number {
    const ref = pickReference()
    if (ref < 0) return 0
    const base = floodMask(ref, false) // 忽略石头的基准可达集
    let removed = 0
    for (let iter = 0; iter < 24; iter++) {
      const now = floodMask(ref, true) // 含石头的实际可达集
      // 死区：基准可达、非石头占用、但现在到不了（石头自身足迹不算死区）
      const dead: number[] = []
      for (let i = 0; i < base.length; i++) {
        if (base[i] === 1 && now[i] === 0 && blocked[i] === 0) dead.push(i)
      }
      if (dead.length === 0) break
      const deadSet = new Set(dead)
      // 移除任何足迹紧邻死区(≤ROCK_RADIUS+1)的石头
      let any = false
      for (let k = kept.length - 1; k >= 0; k--) {
        if (bordersDead(kept[k], deadSet)) {
          setBlocked(kept[k].cells, 0)
          rej.push(kept[k].c)
          kept.splice(k, 1)
          removed++
          any = true
        }
      }
      if (!any) break // 无可移除（死区实为天然地形，非石头造成）
    }
    return removed
  }

  // 洪水填充，返回全新可达掩码（1=可达）。复用共享 queue（无并发）。
  function floodMask(src: number, withRocks: boolean): Uint8Array {
    const mask = new Uint8Array(W * H)
    let head = 0
    let tail = 0
    mask[src] = 1
    queue[tail++] = src
    while (head < tail) {
      const cur = queue[head++]
      const cx = cur % W
      const cy = (cur / W) | 0
      for (let d = 0; d < 16; d += 2) {
        const nx = cx + DIRS[d]
        const ny = cy + DIRS[d + 1]
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue
        const ok = withRocks ? passable(nx, ny) : staticPass(nx, ny)
        if (!ok) continue
        const ni = ny * W + nx
        if (!edge(cur, ni)) continue // 悬崖面不可跨越
        if (mask[ni]) continue
        mask[ni] = 1
        queue[tail++] = ni
      }
    }
    return mask
  }

  function bordersDead(r: { cells: number[] }, deadSet: Set<number>): boolean {
    const reach = Math.ceil(ROCK_RADIUS) + 1
    for (const cell of r.cells) {
      const cx = cell % W
      const cy = (cell / W) | 0
      for (let dx = -reach; dx <= reach; dx++) {
        for (let dy = -reach; dy <= reach; dy++) {
          const nx = cx + dx
          const ny = cy + dy
          if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue
          if (deadSet.has(ny * W + nx)) return true
        }
      }
    }
    return false
  }

  // 参考点：优先地图中心，否则螺旋找最近的静态可通行 cell
  function pickReference(): number {
    const c0 = (H >> 1) * W + (W >> 1)
    if (staticPass(W >> 1, H >> 1)) return c0
    for (let radius = 1; radius < Math.max(W, H); radius++) {
      for (let dx = -radius; dx <= radius; dx++) {
        for (let dy = -radius; dy <= radius; dy++) {
          const nx = (W >> 1) + dx
          const ny = (H >> 1) + dy
          if (staticPass(nx, ny)) return ny * W + nx
        }
      }
    }
    return -1
  }
}
