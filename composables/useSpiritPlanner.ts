/**
 * 灵魂经济最优路径求解器（纯函数，可在前端运行）。
 *
 * 所有常数均从 凯瑞甘生存2 最新版.SC2Map 的 Galaxy 脚本/GameData 核实（2026-06-16）：
 *  - 银行：每 3.5s 利息 = floor(余额/100)（>1万）或 round(余额/100)（≤1万），复利。
 *  - 股市：投资后 60s 锁定，每 9.9s 复利一次共 6 次，乘数 = 1.0925 + 运气/5，需水晶供电。
 *  - 股市投资手续费（气）：按档位，最省为 Deposit2000=13气/2000矿 ≈ 0.65%；取款免费。
 *  - 建筑造价：股市 25矿、证券交易所 250矿+1气、水晶球 25矿+2气、水晶 10矿、银行 25矿、赌场 50矿。
 *  - 运气：占卜设定，仅持续 120s，到期/水晶塔被毁清零归 0。
 *  - 占卜（水晶球 35矿+35气）→ 均值 +0.215 运气。
 *  - 赌场轮盘：75矿+1气，净期望 +53.25 矿（最优固定变现）。
 *
 * 关键修正：气体是股市投资的硬约束——每 60s 投资周期需付约 0.65% 本金的气体手续费。
 * 气耗尽则矿无法继续投股市，只能进银行（增长率约为股市 1/4）。本模型按 60s 周期推进。
 */

export interface SpiritPlanInput {
  minerals: number
  gas: number
  timeSec: number
  hasPylon?: boolean
}

export interface SpiritPlanStep {
  tStart: number
  tEnd: number
  action: string
  detail: string
  kind: 'bank' | 'market' | 'divine' | 'cashout' | 'setup'
}

export interface SpiritPlanResult {
  steps: SpiritPlanStep[]
  finalWealth: number
  startWealth: number
  growthX: number
  notes: string[]
}

// —— 核实常数 ——
const BANK_PERIOD = 3.5
const MARKET_BASE = 1.0925
const MARKET_LOCK = 60
const MARKET_TICKS = 6
const DEPOSIT_GAS_RATE = 0.0065 // 最省档 Deposit2000：13气/2000矿
const LUCK_DURATION = 120
const DIVINE_COST_MIN = 35
const DIVINE_COST_GAS = 35
const DIVINE_LUCK = 0.215
const ROULETTE_COST_MIN = 75
const ROULETTE_GAS = 1
const ROULETTE_NET = 53.25

// 银行 60s 复利倍数（按 3.5s 每期 1% 近似连续复利）
function bankCycleMult(): number {
  const ticks = MARKET_LOCK / BANK_PERIOD
  return Math.pow(1.01, ticks)
}
// 股市单个 60s 周期倍数
function marketCycleMult(luck: number): number {
  return Math.pow(MARKET_BASE + luck / 5, MARKET_TICKS)
}

export function solveSpiritPlan(input: SpiritPlanInput): SpiritPlanResult {
  const T = Math.max(0, Math.floor(input.timeSec))
  let M = Math.max(0, input.minerals)
  let G = Math.max(0, input.gas)
  const hasPylon = input.hasPylon !== false
  const notes: string[] = []
  const steps: SpiritPlanStep[] = []
  const startWealth = M + G

  let luck = 0
  let luckCyclesLeft = 0 // 运气剩余可用的 60s 周期数（120s = 2 周期）

  let divineCount = 0
  let rouletteTotal = 0
  let marketCycles = 0
  let bankCycles = 0
  let gasOutAt = -1

  const nCycles = Math.floor(T / MARKET_LOCK)
  // 终局阈值：最后 1 个周期把剩余气变现（剩余复利时间太短，抬运气不划算）
  const CASHOUT_CYCLE = nCycles - 1

  for (let c = 0; c < nCycles; c++) {
    const cycleStart = c * MARKET_LOCK
    const cyclesRemaining = nCycles - c

    // 运气过期
    if (luckCyclesLeft <= 0) luck = 0

    // 决策1：是否占卜抬运气（前期、运气低、够矿够气、剩余周期足够回本）
    if (
      hasPylon &&
      cyclesRemaining > 1 &&
      luckCyclesLeft <= 0 &&
      G >= DIVINE_COST_GAS + 50 && // 占卜后还要留气投股市
      M >= DIVINE_COST_MIN &&
      c <= CASHOUT_CYCLE
    ) {
      M -= DIVINE_COST_MIN
      G -= DIVINE_COST_GAS
      luck = DIVINE_LUCK
      luckCyclesLeft = Math.floor(LUCK_DURATION / MARKET_LOCK) // = 2
      divineCount++
      steps.push({
        tStart: cycleStart, tEnd: cycleStart,
        action: '🔮 水晶球占卜',
        detail: `花 ${DIVINE_COST_MIN}矿+${DIVINE_COST_GAS}气，运气→+${DIVINE_LUCK}（持续2个周期），股市增长率 ${Math.round((marketCycleMult(DIVINE_LUCK) - 1) * 100)}%/周期`,
        kind: 'divine',
      })
    }

    // 决策2：终局变现（最后一个周期，把剩余气投轮盘）
    if (c >= CASHOUT_CYCLE && G >= ROULETTE_GAS && M >= ROULETTE_COST_MIN) {
      // 一个周期 60s，每 10s 一次轮盘 → 最多 6 次，受气/矿限制
      const maxByGas = Math.floor(G / ROULETTE_GAS)
      const plays = Math.min(6, maxByGas)
      if (plays > 0) {
        G -= plays * ROULETTE_GAS
        M += plays * ROULETTE_NET
        rouletteTotal += plays
        steps.push({
          tStart: cycleStart, tEnd: Math.min(T, cycleStart + MARKET_LOCK),
          action: '🎰 终局变现（轮盘）',
          detail: `剩余气投轮盘 ${plays} 次，预期 +${Math.round(plays * ROULETTE_NET).toLocaleString()} 矿`,
          kind: 'cashout',
        })
      }
    }

    // 决策3：矿复利。有电+有气→股市；否则银行
    const gasFee = M * DEPOSIT_GAS_RATE
    if (hasPylon && G >= gasFee) {
      G -= gasFee
      const before = M
      M *= marketCycleMult(luck)
      marketCycles++
      if (luckCyclesLeft > 0) luckCyclesLeft--
      steps.push({
        tStart: cycleStart, tEnd: Math.min(T, cycleStart + MARKET_LOCK),
        action: luck > 0 ? '📈 满仓股市（高运气）' : '📈 满仓股市',
        detail: `投入 ${Math.round(before).toLocaleString()} 矿，付 ${Math.ceil(gasFee)} 气手续费，60s 后 → ${Math.round(M).toLocaleString()} 矿（+${Math.round(M - before).toLocaleString()}）`,
        kind: 'market',
      })
    } else {
      if (hasPylon && gasOutAt < 0) { gasOutAt = c; notes.push(`第 ${Math.round(cycleStart / 60)} 分钟气体耗尽，之后矿物转入银行（增长率约为股市 1/4）`) }
      const before = M
      M *= bankCycleMult()
      bankCycles++
      steps.push({
        tStart: cycleStart, tEnd: Math.min(T, cycleStart + MARKET_LOCK),
        action: '🏦 银行储蓄',
        detail: `${hasPylon ? '气体不足，' : '无供电，'}矿物存银行，60s 后 → ${Math.round(M).toLocaleString()} 矿（+${Math.round(M - before).toLocaleString()}）`,
        kind: 'bank',
      })
    }
  }

  // 不足一个完整周期的尾巴：进银行
  const tail = T - nCycles * MARKET_LOCK
  if (tail > 0 && M > 0) {
    const before = M
    M *= Math.pow(1.01, tail / BANK_PERIOD)
    if (M - before >= 1) {
      steps.push({
        tStart: nCycles * MARKET_LOCK, tEnd: T,
        action: '🏦 收尾（银行）',
        detail: `剩余 ${tail}s 存银行 → +${Math.round(M - before).toLocaleString()} 矿`,
        kind: 'bank',
      })
    }
  }

  if (!hasPylon) notes.unshift('未供电：股市不可用，仅靠银行（增长率约为股市的 1/4）。强烈建议先建水晶通电。')
  if (divineCount > 0) notes.push(`共占卜 ${divineCount} 次维持运气（每次 35矿+35气，覆盖 2 个周期）`)
  if (marketCycles > 0) notes.push(`股市复利 ${marketCycles} 个周期，是增长主力`)
  if (rouletteTotal > 0) notes.push(`终局把剩余气投轮盘变现 ${rouletteTotal} 次（每次净 +${ROULETTE_NET} 矿）`)
  notes.push('⚠️ 运气仅持续120秒、水晶塔被毁会清零，务必保护水晶塔')
  notes.push('注：结果为理论上界，实战受手动操作、分批投资、运气波动影响会偏低')

  return {
    steps,
    finalWealth: Math.round(M),
    startWealth: Math.round(startWealth),
    growthX: startWealth > 0 ? M / startWealth : 0,
    notes,
  }
}
