import type { RockCandidate } from './useTerrainData'

/**
 * 石头（可破坏障碍）生成算法的 JS 复刻，逐段对齐 Scripts/game/rocks.galaxy
 * (`gt_Game_Rocks_PlaceRocks_Func` / `IsRockPositionBad`)。
 *
 * 关键：KS2 里石头是**实时阻挡寻路的单位**——放一批 → 更新寻路 → 逐个复查、
 * 移除会导致周边采样点不连通或绕行超限的坏石头 → 循环补放。真实游戏**只有这一层
 * ±3 局部检测**（IsRockPositionBad），**没有任何全局连通兜底**；正是这个「带活体阻挡
 * 的放置-复查-移除」循环保证不会出现被石头封死、单位无法进入的区域。
 *
 * 本模拟器忠实复刻该机制：
 *  1. 洗牌候选斜坡，目标数 n = floor(rockProb × 候选数)。
 *  2. 按顺序放置：每颗石头以 ~4×4 足迹阻挡通行网格；放置前用 isRockPositionBad
 *     在**含已放石头**的网格上校验（±3 邻点 ≥2 可通行、彼此连通、绕行 ≤ maxElongation）。
 *  3. 全部就位后逐个复查、移除此时变坏的石头（对齐地图移除循环）。**无全局兜底**——
 *     曾加过一版全局洪水兜底，但它按 **cell** 判死区，会把石头/墙边缘 1–2 格、单位
 *     （半径 0.75，需 2×2 净空）根本站不进去的碎屑误判为死区，从而拆掉大量合法石头
 *     （ruins_of_imladoon@0.5 曾 71→30）。按**格点**（单位 2×2 落位）度量时真实死区为 0，
 *     故与真实游戏一致地删除该兜底。
 *
 * 关键不变量：连通判定（reachAll）一律在**格点**（单位 2×2 落位）上洪泛，且**禁止对角
 * 贴角穿越**——斜向移动需两侧正交落位也合法。真实单位有半径，挤不过两颗石头对角相邻
 * 留下的 1 格缝；若在 cell 上洪泛或允许贴角穿越，被石头对角围死的区域会被误判为连通，
 * 坏石头逃过校验，页面便重现「被石头完全包围、破坏前无法进入」的死区。
 *
 * 石头**每局随机**，同种子可复现、可重掷。寻路 = 静态可走地面 (t3CellFlags bit0x02)
 * ∩ ¬**永久阻挡** (doodad/瞭望塔) ∩ **悬崖高度层 (t3SyncCliffLevel)** 跨格可行。
 * 悬崖跨格判定：相邻两 cell 高差 > cliffStep 即悬崖面，不可跨越——只有斜坡能连通台地。
 * 缺了这层，bit0x02 几乎全图可走，斜坡就不成咽喉，石头封不住任何东西，也就复现/防不住
 * 死路。永久阻挡层 (grid.isBlocked，来自 CellAttribute_Pnp + Objects 里的瞭望塔) 同样关键：
 * t3CellFlags 不含 doodad/单位足迹，缺它则树/塔占的格被当空地，石头模拟会保留真实游戏会
 * 拒绝的石头 → 多层悬崖上重现死区。加入悬崖跨格 + 永久阻挡后，封住斜坡/贴阻挡的坏石头会
 * 被 isRockPositionBad 判坏并移除，从而保证不会出现单位无法进入的区域。
 */

export interface SimResult {
  placed: RockCandidate[]
  rejected: RockCandidate[]
  n: number          // 目标放置数
  count: number      // 候选总数
  maxElongation: number
}

interface Grid {
  isPassable: (cx: number, cy: number) => boolean
  cliffAt: (cx: number, cy: number) => number
  cliffStep: number
  size: number
  isBlocked?: (cx: number, cy: number) => boolean // 永久阻挡（doodad/瞭望塔），可选
}

const ROCK_RADIUS = 2.0 // 方形 4×4 足迹的半边长（对齐 CommonTerrainDebris4x4 / ±3 邻点采样）
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

  // 静态可通行（越界视为不可通行）= t3CellFlags 可走 ∩ ¬永久阻挡（doodad/瞭望塔）。
  // 永久阻挡在此一并扣除，故 passable/nodeOK/reachAll/isRockPositionBad 全链路自动感知，
  // 石头放置校验与死区基准都会把塔/树当作真实障碍——无需改动下游算法。
  const isBlocked = grid.isBlocked
  const staticPass = (cx: number, cy: number) =>
    cx >= 0 && cy >= 0 && cx < W && cy < H && grid.isPassable(cx, cy) &&
    !(isBlocked !== undefined && isBlocked(cx, cy))

  // 悬崖高度层（预解一次）：相邻两 cell 高差 > cliffStep 即不可跨越的悬崖面
  // uint16：高台地图（Maze/DeathValley）层级可达 576，单字节会溢出
  const cliffLevel = new Uint16Array(W * H)
  for (let cy = 0; cy < H; cy++) {
    for (let cx = 0; cx < W; cx++) cliffLevel[cy * W + cx] = grid.cliffAt(cx, cy)
  }
  const step = grid.cliffStep
  // 悬崖跨越判定已并入格点合法性（nodeOK：2×2 足迹内高差 ≤step），无需单独的跨格 edge 判定。

  // 石头占用的 cell（活体阻挡）
  const blocked = new Uint8Array(W * H)
  const passable = (cx: number, cy: number) =>
    staticPass(cx, cy) && blocked[cy * W + cx] === 0

  // —— 单位半径（clearance）：在**格点(vertex)**上洪泛 —— //
  // 真实判定用的是 CommonPathingUnit（Radius=0.75，直径 1.5 世界单位）。1 cell = 1 世界单位，
  // 它的寻路足迹约 **2×2**：**1 格宽的走廊挤不过去，需要约 2 格净空**。若把导航体当成一个「点」
  // （逐 cell 移动），会从 1 格缝里钻过去——把走廊收窄到单位直径以下的封路石被误判「仍连通」而
  // 保留，页面便出现被石头围死、破坏前无法进入的死区。
  //
  // 正确模型：单位落位用**格点**表示——格点 (x,y) 代表单位 2×2 足迹覆盖 cell (x..x+1, y..y+1)。
  // 在**格点**上洪泛（而非在 cell 上），才能正确判定「单位能否真的从 A 走到 B」：夹点处若用逐
  // cell 洪泛，会出现「A 靠左 2×2 站立、B 靠右 2×2 站立」却其实过不去的假连通，漏掉封路石；格点
  // 洪泛要求相邻落位的 2×2 足迹连续可行，才算能走。cell 可达 ⇔ 存在覆盖它的合法格点被访问到。
  //
  // 格点合法：四格全可通行且高度一致（单位不骑悬崖面）。相邻格点重叠两格 → 天然强制高度连续，
  // 斜坡（每格 ≤cliffStep 渐变）仍连通，悬崖面（>cliffStep）自动阻断，无需再单独判 edge。
  function nodeOK(free: (x: number, y: number) => boolean, x: number, y: number): boolean {
    if (x < 0 || y < 0 || x + 1 >= W || y + 1 >= H) return false
    if (!free(x, y) || !free(x + 1, y) || !free(x, y + 1) || !free(x + 1, y + 1)) return false
    const l0 = cliffLevel[y * W + x]
    const l1 = cliffLevel[y * W + x + 1]
    const l2 = cliffLevel[(y + 1) * W + x]
    const l3 = cliffLevel[(y + 1) * W + x + 1]
    return Math.max(l0, l1, l2, l3) - Math.min(l0, l1, l2, l3) <= step
  }
  // 覆盖 cell (cx,cy) 的四个候选格点锚点（锚点 a → 2×2 足迹 a,(a+1,y),(a,y+1),(a+1,y+1)）
  const COVER: [number, number][] = [[0, 0], [-1, 0], [0, -1], [-1, -1]]
  // 覆盖 (cx,cy) 的一个合法格点锚点索引；-1 表示单位在此 cell「站不下」（无 2 格净空）
  function nodeForCell(free: (x: number, y: number) => boolean, cx: number, cy: number): number {
    for (const [ox, oy] of COVER) {
      const ax = cx + ox
      const ay = cy + oy
      if (nodeOK(free, ax, ay)) return ay * W + ax
    }
    return -1
  }

  // 一颗石头以 center 为心的**方形 4×4 足迹**（对齐地图实际放置的 CommonTerrainDebris4x4）。
  // 关键：必须是**实心方块**，不能用圆盘——圆盘会漏掉四角/边缘，在窄走廊里石头碰不到两侧墙、
  // 留下 1 格缝，逐格洪水便从缝里钻过去，导致「石头堵死走廊」被误判为仍连通、封口石头逃过
  // isRockPositionBad 校验而保留，页面上就出现被石头围死的死区。方块顶满走廊即可复现真实封堵，
  // 让 ±3 采样点在被堵侧断开、判坏移除（伊姆拉顿废墟高石头率下曾稳定复现）。
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
        // 方形：cell 中心在两轴上都落在 ±ROCK_RADIUS 内（4×4 实心），而非圆盘 ex²+ey²≤r²
        if (Math.abs(ex) <= ROCK_RADIUS && Math.abs(ey) <= ROCK_RADIUS && staticPass(cx, cy)) {
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
   * 在**格点**上从 srcNode 出发 BFS，判定所有 targetNodes 是否都在 maxDist 步内可达。
   * 参数均为格点锚点索引（ay*W+ax）。cap 限制探索节点数：超出仍未达标 → 视为被封/绕行过远。
   * 含石头（passable）判据：石头 4×4 足迹使相关格点非法，单位便无法经过 → 封路石被判坏。
   */
  function reachAll(srcNode: number, targetNodes: number[], maxDist: number, cap: number): boolean {
    gen++
    let head = 0
    let tail = 0
    stamp[srcNode] = gen
    dist[srcNode] = 0
    queue[tail++] = srcNode
    const need = new Set(targetNodes)
    need.delete(srcNode)
    if (need.size === 0) return true
    let visited = 0
    while (head < tail) {
      const cur = queue[head++]
      const cd = dist[cur]
      if (cd >= maxDist) continue // 超出绕行上限，不再扩展
      if (++visited > cap) return false
      const nxn = cur % W
      const nyn = (cur / W) | 0
      for (let d = 0; d < 16; d += 2) {
        const ddx = DIRS[d]
        const ddy = DIRS[d + 1]
        const ax = nxn + ddx
        const ay = nyn + ddy
        if (!nodeOK(passable, ax, ay)) continue // 相邻落位的 2×2 足迹须连续可行
        // 禁止对角贴角穿越：斜向移动两侧正交落位也须合法，否则单位挤不过障碍夹角的缝。
        if (ddx !== 0 && ddy !== 0 && (!nodeOK(passable, nxn + ddx, nyn) || !nodeOK(passable, nxn, nyn + ddy))) continue
        const ni = ay * W + ax
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
      const nd = nodeForCell(passable, cx, cy) // 采样点须单位站得下（clearance），取其覆盖格点
      if (nd >= 0) pts.push(nd)
    }
    if (pts.length < 2) return true
    // 连通性 + 绕行上限：其余采样格点都要在 maxElongation 步内从 pts[0] 可达
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

  return {
    placed: placed.map(r => r.c),
    rejected,
    n,
    count,
    maxElongation: Math.round(elongationMean),
  }
}
