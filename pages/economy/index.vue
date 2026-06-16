<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">经济系统</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
      生存者方通过建造经济建筑获取晶矿收入，不同职业拥有不同的经济体系。
    </p>

    <div class="space-y-6">
      <div v-for="hero in econHeroes" :key="hero.hero" class="wiki-card p-5 stagger-item">
        <div class="flex items-center gap-3 mb-3">
          <img v-if="hero.roleId >= 0" :src="`/icons/${String(hero.roleId).padStart(2, '0')}.png`"
            class="w-9 h-9 rounded-lg shadow-sm" />
          <div class="flex-1">
            <NuxtLink v-if="hero.roleId >= 0" :to="`/classes/${hero.roleId}`"
              class="font-semibold text-gray-900 dark:text-gray-100 hover:text-survivor-600 dark:hover:text-survivor-400 transition-colors">
              {{ hero.nameZh }}
            </NuxtLink>
            <span v-else class="font-semibold text-gray-900 dark:text-gray-100">{{ hero.hero }}</span>
            <div class="text-xs text-gray-400 dark:text-gray-500">{{ hero.hero }}</div>
          </div>
          <div v-if="hero.chrono" class="text-right">
            <span class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800">
              {{ hero.chrono.name }} ×{{ hero.chrono.timeScale }}
            </span>
          </div>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3 leading-relaxed">{{ hero.incomeModel }}</p>

        <div v-if="heroChronos(hero).length" class="mb-3 px-3 py-2 rounded-lg bg-yellow-50/50 dark:bg-yellow-900/10 border border-yellow-100 dark:border-yellow-900/30">
          <div v-for="(c, i) in heroChronos(hero)" :key="i" class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-yellow-800 dark:text-yellow-300" :class="i > 0 ? 'mt-1.5 pt-1.5 border-t border-yellow-100 dark:border-yellow-800/50' : ''">
            <span>{{ c.name }}: <b class="font-mono">×{{ c.timeScale }}</b></span>
            <span>消耗: <b class="font-mono">{{ chronoCostLabel(c) }}</b></span>
            <span>持续: <b class="font-mono">{{ c.duration === 'permanent' ? '永久' : c.duration + 's' }}</b></span>
          </div>
        </div>

        <div v-if="!hero.harvestEconomy && !hero.addonEconomy" class="overflow-x-auto -mx-5 px-5">
          <table class="w-full text-sm min-w-[560px]">
            <thead>
              <tr class="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
                <th class="text-left font-medium pb-2 pl-1">建筑</th>
                <th class="text-right font-medium pb-2">收入</th>
                <th class="text-right font-medium pb-2">每秒</th>
                <th class="text-right font-medium pb-2">费用</th>
                <th class="text-right font-medium pb-2" title="购买1矿/秒收入所需的总投入（晶矿+气体），越低性价比越高">投资比</th>
                <th class="text-right font-medium pb-2">回本时间</th>
                <th v-if="heroChronos(hero).length" class="text-right font-medium pb-2 pr-1">加速回本</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-700/50">
              <tr v-for="b in hero.buildings" :key="b.id">
                <td class="py-2 pl-1 text-gray-700 dark:text-gray-300">
                  {{ b.nameZh }}
                  <span v-if="b.upgradeTo" class="text-xs text-gray-400"> →</span>
                </td>
                <td class="py-2 text-right font-mono font-semibold"
                  :class="b.income ? 'text-green-600 dark:text-green-400' : 'text-gray-400'">
                  {{ b.income ? `+${b.income}/${b.incomePeriod || '?'}s` : '-' }}
                </td>
                <td class="py-2 text-right font-mono text-emerald-600 dark:text-emerald-400">
                  {{ incomePerSec(b) || '-' }}
                </td>
                <td class="py-2 text-right font-mono text-gray-600 dark:text-gray-300">
                  <template v-if="b.cost != null">
                    {{ b.cost }}<span v-if="b.gasCost" class="text-green-600 dark:text-green-500">+{{ b.gasCost }}g</span>
                  </template>
                  <template v-else>-</template>
                </td>
                <td class="py-2 text-right font-mono text-purple-600 dark:text-purple-400">
                  {{ roi(b) || '-' }}
                </td>
                <td class="py-2 text-right font-mono text-blue-600 dark:text-blue-400">
                  {{ paybackTime(b) || '-' }}
                </td>
                <td v-if="heroChronos(hero).length" class="py-2 pr-1 text-right font-mono text-yellow-600 dark:text-yellow-400">
                  <span v-for="(c, i) in heroChronos(hero)" :key="i">
                    <span v-if="i > 0"> / </span>{{ paybackTimeBoosted(b, c) || '-' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 采集型经济（塞兰迪斯）：矿区×探机 投资比矩阵 + 探机参数 -->
        <div v-if="hero.harvestEconomy" class="space-y-4">
          <!-- 投资比矩阵 -->
          <div class="overflow-x-auto -mx-5 px-5">
            <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
              投资比矩阵 · 矿区 × 探机（数值越低越划算）
            </div>
            <table class="w-full text-sm min-w-[560px] border-separate border-spacing-1">
              <thead>
                <tr>
                  <th class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 pb-1 pl-1">矿区 \ 探机</th>
                  <th v-for="p in hero.probes" :key="p.id" class="text-center text-xs font-medium text-gray-600 dark:text-gray-300 pb-1">
                    {{ p.nameZh }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in hero.buildings" :key="b.id">
                  <td class="py-1.5 pl-2 pr-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 whitespace-nowrap">
                    <span class="font-mono text-sm font-semibold text-gray-700 dark:text-gray-200">{{ b.nameZh }}</span>
                    <span class="font-mono text-xs text-gray-400 dark:text-gray-500 ml-2">{{ b.cost }}矿 · +{{ b.income }}/趟</span>
                  </td>
                  <td v-for="p in hero.probes" :key="p.id"
                    class="text-center rounded-lg bg-gray-50/60 dark:bg-gray-800/40">
                    <div class="font-mono text-sm" :class="roiCellClass(b, p, hero.probes)">{{ harvestRoi(b, p) }}</div>
                    <div class="font-mono text-[0.65rem] text-gray-400 dark:text-gray-500">{{ harvestPerSec(b, p).toFixed(0) }}/s</div>
                  </td>
                </tr>
              </tbody>
            </table>
            <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 leading-relaxed">
              投资比 =（矿区造价 + 探机造价）÷ 每秒采集量（买“1 矿/秒”持续收入的总投入，越低越划算）；下方小字为该组合每秒采集量。
              假设探机采集运回一趟基准 <b class="font-mono">0.1s</b>，实际每趟 = 0.1 × 探机耗时倍率。矿区最高 +16，无 +32。
              真实速率还受探机往返距离（地图布局）影响，此处为统一基准下的横向对比。
            </p>
          </div>

          <!-- 探机参数 -->
          <div>
            <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
              采集探机 · 造价与参数
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <div v-for="p in hero.probes" :key="p.id"
                class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700/60">
                <div class="flex-1 min-w-0">
                  <div class="flex items-baseline gap-2">
                    <span class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ p.nameZh }}</span>
                    <span class="font-mono text-xs font-bold text-survivor-600 dark:text-survivor-400">{{ p.efficiency }}</span>
                  </div>
                  <div class="font-mono text-[0.7rem] text-gray-400 dark:text-gray-500 mt-0.5">
                    采矿{{ p.mineTime }}s · 单趟量×{{ p.amountMult }}
                  </div>
                </div>
                <div class="font-mono text-xs text-gray-600 dark:text-gray-300 shrink-0 text-right">
                  <span v-if="p.cost">{{ p.cost }}矿</span><span v-if="p.cost && p.gasCost"> </span><span v-if="p.gasCost" class="text-green-600 dark:text-green-400">{{ p.gasCost }}气</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 挂件型经济（坦克）：建筑 × 挂件 回本/投资比矩阵 -->
        <div v-if="hero.addonEconomy" class="overflow-x-auto -mx-5 px-5">
          <div class="text-xs font-semibold uppercase tracking-wider text-survivor-600 dark:text-survivor-400 mb-2">
            挂件矩阵 · 经济建筑 × 挂件（投资比越低越划算）
          </div>
          <table class="w-full text-sm min-w-[560px] border-separate border-spacing-1">
            <thead>
              <tr>
                <th class="text-left text-xs font-medium text-gray-500 dark:text-gray-400 pb-1 pl-1">建筑 \ 挂件</th>
                <th v-for="col in addonCols" :key="col.key" class="text-center text-xs font-medium text-gray-600 dark:text-gray-300 pb-1">
                  {{ col.label }}
                  <span v-if="col.cost" class="block font-mono text-[0.6rem] text-gray-400 dark:text-gray-500 font-normal">+{{ col.cost }}矿<template v-if="col.gasCost">+{{ col.gasCost }}g</template></span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="b in hero.buildings" :key="b.id">
                <td class="py-1.5 pl-2 pr-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 whitespace-nowrap">
                  <span class="font-mono text-sm font-semibold text-gray-700 dark:text-gray-200">{{ b.nameZh }}</span>
                  <span class="font-mono text-xs text-gray-400 dark:text-gray-500 ml-2">{{ b.cost }}矿 · {{ b.income }}/{{ b.incomePeriod }}s</span>
                </td>
                <td v-for="col in addonCols" :key="col.key"
                  class="text-center rounded-lg bg-gray-50/60 dark:bg-gray-800/40">
                  <div class="font-mono text-sm" :class="addonRoiCellClass(b, col)">{{ addonRoi(b, col) }}矿</div>
                  <div class="font-mono text-[0.65rem] text-gray-400 dark:text-gray-500">
                    {{ addonPerSec(b, col).toFixed(2) }}/s · {{ formatTime(addonPayback(b, col)) }}
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <p class="text-xs text-gray-400 dark:text-gray-500 mt-2 leading-relaxed">
            每个经济建筑限挂一个挂件（科技实验室 / 反应堆，二选一）。
            投资比 =（建筑造价 + 挂件造价）÷ 每秒产矿（买"1 矿/秒"持续收入的总投入，越低越划算，仅计晶矿）；
            小字为每秒产矿与回本时间。挂件气体消耗见表头。
          </p>
        </div>
      </div>
    </div>

    <!-- 技术员：独特的转化型经济（独立结构，不套用上方收入表） -->
    <TechnicianEconomy />

    <!-- 灵魂：独特的金融/投资型经济（银行/股市/赌场/水晶球运气） -->
    <SpiritEconomy />
  </div>
</template>

<script setup lang="ts">
import econData from '~/data/economy.json'

const { classes } = useClassData()

const econHeroes = computed(() => {
  return (econData as any[]).map((hero: any) => {
    const role = classes.find(c => c.nameEn === hero.hero || c.nameZh === hero.hero)
    return {
      ...hero,
      roleId: role?.id ?? -1,
      nameZh: role?.nameZh || hero.hero,
    }
  }).sort((a: any, b: any) => a.hero.localeCompare(b.hero))
})

function heroChronos(hero: any): any[] {
  if (!hero.chrono) return []
  return Array.isArray(hero.chrono) ? hero.chrono : [hero.chrono]
}

function chronoCostLabel(chrono: any) {
  if (chrono.gasCost) return `${chrono.gasCost} 气体/次`
  if (chrono.energyCost > 0) return `${chrono.energyCost} 能量`
  return '无'
}

function incomePerSec(b: any) {
  if (!b.income || !b.incomePeriod) return null
  const ips = b.income / b.incomePeriod
  return `${ips % 1 === 0 ? ips : ips.toFixed(2)}/s`
}

function roi(b: any) {
  if (!b.income || !b.incomePeriod || b.cost == null) return null
  const ips = b.income / b.incomePeriod
  const totalCost = b.cost + (b.gasCost || 0)
  const costPer1ps = Math.round(totalCost / ips)
  return `${costPer1ps}矿`
}

function paybackTime(b: any) {
  if (!b.income || !b.cost || !b.incomePeriod) return null
  const incomePerSec = b.income / b.incomePeriod
  const seconds = Math.round(b.cost / incomePerSec)
  return formatTime(seconds)
}

function paybackTimeBoosted(b: any, chrono: any) {
  if (!b.income || !b.cost || !b.incomePeriod || !chrono) return null
  const incomePerSec = (b.income / b.incomePeriod) * chrono.timeScale
  const seconds = Math.round(b.cost / incomePerSec)
  return formatTime(seconds)
}

function formatTime(seconds: number) {
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return s > 0 ? `${m}m${s}s` : `${m}m`
  }
  return `${seconds}s`
}

// —— 塞兰迪斯采集经济 ——
// 一趟 = 采矿 + 运输往返。
//   采矿耗时 = 探机各自的固定采矿时间（游戏实测：普通2.5s / 高级·专家·普罗比斯1.5s）
//   运输往返 = 0.1s（完成采矿到运回基地）
//   每秒采集 = 矿区单趟量 × 单趟量倍率 ÷ 一趟总时长
const TRIP_TRANSPORT = 0.1  // 运输往返(s)

function tripTime(probe: any) {
  return (probe.mineTime || 0) + TRIP_TRANSPORT
}
function harvestPerSec(field: any, probe: any) {
  return (field.income * probe.amountMult) / tripTime(probe)
}
// 投资比 = (矿区造价 + 探机造价 + 探机气耗) ÷ 每秒采集量
// 含探机成本：要达到该采集速率，矿区和探机都得买（气矿按现有页面惯例直接相加）
function harvestRoi(field: any, probe: any) {
  const ips = harvestPerSec(field, probe)
  if (!ips) return null
  const totalCost = field.cost + (probe.cost || 0) + (probe.gasCost || 0)
  return Math.round(totalCost / ips)
}
// 着色：同一矿区行内，投资比越低越“绿”，越高越“暗”
function roiCellClass(field: any, probe: any, probes: any[]) {
  const vals = probes.map(p => harvestRoi(field, p) as number)
  const min = Math.min(...vals), max = Math.max(...vals)
  const v = harvestRoi(field, probe) as number
  if (max === min) return 'text-survivor-600 dark:text-survivor-400'
  const t = (v - min) / (max - min) // 0=最划算
  if (t < 0.34) return 'text-emerald-600 dark:text-emerald-400 font-semibold'
  if (t < 0.67) return 'text-survivor-600 dark:text-survivor-400'
  return 'text-gray-400 dark:text-gray-500'
}

// —— 坦克挂件经济 ——
// 三档：无挂件(×1,0矿) / 科技实验室(×1.5,+20矿+5气) / 反应堆(×2,+200矿+10气)。
// 每秒产矿 = 基础income × 倍率 ÷ 周期(3s)；
// 投资比/回本 = (建筑造价 + 挂件造价) ÷ 每秒产矿（仅计晶矿，与通用表 roi 口径一致）。
const addonCols = [
  { key: 'none', label: '无挂件', multiplier: 1, cost: 0, gasCost: 0 },
  { key: 'tech', label: '科技实验室 ×1.5', multiplier: 1.5, cost: 20, gasCost: 5 },
  { key: 'reactor', label: '反应堆 ×2', multiplier: 2, cost: 200, gasCost: 10 },
]
function addonPerSec(b: any, col: any) {
  if (!b.income || !b.incomePeriod) return 0
  return (b.income * col.multiplier) / b.incomePeriod
}
function addonRoi(b: any, col: any) {
  const ips = addonPerSec(b, col)
  if (!ips) return null
  return Math.round((b.cost + col.cost) / ips)
}
function addonPayback(b: any, col: any) {
  const ips = addonPerSec(b, col)
  if (!ips) return 0
  return Math.round((b.cost + col.cost) / ips)
}
// 着色：同一建筑行内，投资比越低越“绿”
function addonRoiCellClass(b: any, col: any) {
  const vals = addonCols.map(c => addonRoi(b, c) as number)
  const min = Math.min(...vals), max = Math.max(...vals)
  const v = addonRoi(b, col) as number
  if (max === min) return 'text-survivor-600 dark:text-survivor-400'
  const t = (v - min) / (max - min)
  if (t < 0.34) return 'text-emerald-600 dark:text-emerald-400 font-semibold'
  if (t < 0.67) return 'text-survivor-600 dark:text-survivor-400'
  return 'text-gray-400 dark:text-gray-500'
}
</script>