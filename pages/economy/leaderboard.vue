<template>
  <div>
    <div class="flex items-center gap-2 mb-2">
      <NuxtLink to="/economy" class="text-sm text-survivor-600 dark:text-survivor-400 hover:underline">← 经济系统</NuxtLink>
    </div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">经济投资比排行榜</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4 leading-relaxed">
      把全职业所有经济项（建筑 / 采集组合 / 挂件组合 / 装填工人）拍平横向对比。
      <b>投资比 = 总投入（晶矿 + 气体） ÷ 每秒产矿</b>，即买“1 矿/秒”持续收入的总投入，<b>越低越划算</b>。
    </p>

    <!-- 基础 / 加速 榜切换 -->
    <div class="inline-flex rounded-lg border border-surface-200 dark:border-gray-600 bg-surface-50 dark:bg-gray-700 p-0.5 mb-3">
      <button type="button" @click="board = 'base'"
        class="px-3 py-1.5 text-sm rounded-md transition"
        :class="board === 'base' ? 'bg-survivor-600 text-white shadow-sm' : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'">
        基础投资比
      </button>
      <button type="button" @click="board = 'boosted'"
        class="px-3 py-1.5 text-sm rounded-md transition"
        :class="board === 'boosted' ? 'bg-yellow-500 text-white shadow-sm' : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'">
        加速投资比
      </button>
    </div>

    <!-- 工具条：搜索 + 类型筛选 -->
    <div class="flex flex-col sm:flex-row gap-2 sm:items-center mb-3">
      <div class="relative flex-1 min-w-[180px]">
        <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input v-model="search" type="text" placeholder="搜索英雄 / 项目 / 类型…"
          class="w-full border border-surface-200 dark:border-gray-600 rounded-lg pl-8 pr-3 py-1.5 text-sm bg-surface-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800 transition" />
      </div>
    </div>
    <div class="flex flex-wrap gap-1.5 mb-4">
      <button type="button" @click="typeFilter = ''"
        class="text-xs px-2 py-1 rounded-md border transition"
        :class="typeFilter === '' ? 'border-survivor-400 bg-survivor-50 text-survivor-700 dark:border-survivor-500 dark:bg-survivor-900/30 dark:text-survivor-300' : 'border-surface-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-surface-100 dark:hover:bg-gray-700'">
        全部
      </button>
      <button v-for="t in typeOptions" :key="t.type" type="button" @click="typeFilter = t.type"
        class="text-xs px-2 py-1 rounded-md border transition"
        :class="typeFilter === t.type ? 'border-survivor-400 bg-survivor-50 text-survivor-700 dark:border-survivor-500 dark:bg-survivor-900/30 dark:text-survivor-300' : 'border-surface-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-surface-100 dark:hover:bg-gray-700'">
        {{ t.label }} <span class="opacity-60">{{ t.count }}</span>
      </button>
    </div>

    <!-- 排行表 -->
    <div class="overflow-x-auto -mx-4 px-4">
      <table class="w-full text-sm min-w-[620px]">
        <thead>
          <tr class="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700">
            <th class="text-right font-medium pb-2 pr-2 w-10">#</th>
            <th class="text-left font-medium pb-2">英雄</th>
            <th class="text-left font-medium pb-2">项目</th>
            <th class="text-right font-medium pb-2">投入</th>
            <th class="text-right font-medium pb-2">每秒</th>
            <th class="text-right font-medium pb-2 pr-1">{{ board === 'boosted' ? '投资比(加速)' : '投资比' }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50 dark:divide-gray-700/50">
          <tr v-for="(r, i) in filtered" :key="r.hero + r.label"
            class="hover:bg-surface-50 dark:hover:bg-gray-700/30 transition-colors">
            <td class="py-1.5 pr-2 text-right font-mono" :class="rankClass(i)">{{ i + 1 }}</td>
            <td class="py-1.5">
              <NuxtLink v-if="r.roleId >= 0" :to="`/classes/${r.roleId}`" class="inline-flex items-center gap-2 group">
                <img :src="`/icons/${String(r.roleId).padStart(2, '0')}.png`" class="w-6 h-6 rounded shadow-sm shrink-0" />
                <span class="text-gray-800 dark:text-gray-100 group-hover:text-survivor-600 dark:group-hover:text-survivor-400 whitespace-nowrap">{{ r.nameZh }}</span>
              </NuxtLink>
              <span v-else class="text-gray-800 dark:text-gray-100 whitespace-nowrap">{{ r.nameZh }}</span>
            </td>
            <td class="py-1.5">
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center text-[0.6rem] px-1.5 py-0.5 rounded font-medium shrink-0" :class="badgeClass(r.type)">{{ r.typeLabel }}</span>
                <span class="text-gray-600 dark:text-gray-300 text-xs">{{ r.label }}</span>
              </div>
            </td>
            <td class="py-1.5 text-right font-mono text-gray-600 dark:text-gray-300 whitespace-nowrap">
              {{ r.mineral }}<span v-if="r.gas" class="text-green-600 dark:text-green-500">+{{ r.gas }}g</span>
            </td>
            <td class="py-1.5 text-right font-mono text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
              {{ perSecLabel(r) }}<span v-if="board === 'boosted' && r.timeScale > 1" class="text-[0.65rem] text-yellow-600 dark:text-yellow-500"> ×{{ r.timeScale }}</span>
            </td>
            <td class="py-1.5 pr-1 text-right font-mono font-semibold text-purple-600 dark:text-purple-400">
              {{ board === 'boosted' ? r.roiBoosted : r.roi }}矿
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!filtered.length" class="text-center text-gray-500 dark:text-gray-400 py-8">没有匹配的项目</p>
    </div>

    <p class="text-xs text-gray-400 dark:text-gray-500 mt-4 leading-relaxed">
      投资比统一把气体折算进投入（1 气 ≈ 1 矿求和）；<b>加速榜</b>对有超频（chrono）的英雄按其最优倍率提速每秒收入后重排，无超频英雄两榜数值相同。
      挂件行的投资比含挂件气耗，故略高于坦克详情页矩阵（那里只计晶矿）。
      先知萃取 / 技术员转化 / 灵魂金融 / 元素使狩猎的收入来自寄生、击杀或理财，没有固定单位投资比，未纳入本榜。
    </p>
  </div>
</template>

<script setup lang="ts">
import { ECON_TYPE_LABELS } from '~/composables/useEconomyData'

const { rows, rankByBase, rankByBoosted } = useEconomyRanking()

const board = ref<'base' | 'boosted'>('base')
const search = ref('')
const typeFilter = ref('')

// 类型徽章配色（静态 class，避免 Tailwind purge；与 /economy 一致）
const TYPE_BADGE: Record<string, string> = {
  generic: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  harvest: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  addon: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  miner: 'bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300',
}
function badgeClass(type: string) {
  return TYPE_BADGE[type] || TYPE_BADGE.generic
}

// 出现在榜里的类型 + 计数（用于筛选 chips）
const typeOptions = computed(() => {
  const counts: Record<string, number> = {}
  for (const r of rows.value) counts[r.type] = (counts[r.type] || 0) + 1
  return Object.keys(counts).map(type => ({ type, label: ECON_TYPE_LABELS[type] || type, count: counts[type] }))
})

const ranked = computed(() => (board.value === 'boosted' ? rankByBoosted.value : rankByBase.value))

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return ranked.value.filter((r) => {
    if (typeFilter.value && r.type !== typeFilter.value) return false
    if (!q) return true
    return r.nameZh.toLowerCase().includes(q)
      || r.hero.toLowerCase().includes(q)
      || r.label.toLowerCase().includes(q)
      || (r.typeLabel && r.typeLabel.toLowerCase().includes(q))
  })
})

function perSecLabel(r: any) {
  const v = board.value === 'boosted' ? r.perSec * r.timeScale : r.perSec
  return `${v % 1 === 0 ? v : v.toFixed(2)}/s`
}

function rankClass(i: number) {
  if (i === 0) return 'text-yellow-500 font-bold'
  if (i === 1) return 'text-gray-400 font-bold'
  if (i === 2) return 'text-amber-600 font-bold'
  return 'text-gray-400 dark:text-gray-500'
}
</script>
