<template>
  <div>
    <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
      基于官方对局数据（去重统计），胜负以阵营是否取胜计。可按时间段与服务器筛选。
      <span v-if="dumpThrough" class="font-mono text-xs text-gray-400 dark:text-gray-500">
        · 数据截至 {{ dumpThroughLabel }}
      </span>
    </p>

    <!-- 筛选：服务器 + 时间段 -->
    <section class="wiki-card p-4 mb-6 space-y-3">
      <!-- 服务器 -->
      <div class="flex items-center gap-3 flex-wrap">
        <span class="text-xs font-medium text-gray-500 dark:text-gray-400 w-12 shrink-0">服务器</span>
        <div class="flex rounded-lg bg-surface-100 dark:bg-gray-800 p-0.5 text-sm">
          <button v-for="r in REGION_TABS" :key="r.value" @click="region = r.value"
            class="px-3 py-1 rounded-md font-medium transition-colors"
            :class="region === r.value
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'">
            {{ r.label }}
          </button>
        </div>
      </div>

      <!-- 时间段预设 -->
      <div class="flex items-center gap-3 flex-wrap">
        <span class="text-xs font-medium text-gray-500 dark:text-gray-400 w-12 shrink-0">时间段</span>
        <div class="flex flex-wrap rounded-lg bg-surface-100 dark:bg-gray-800 p-0.5 text-sm gap-0.5">
          <button v-for="p in PRESETS" :key="p.value" @click="applyPreset(p.value)"
            class="px-3 py-1 rounded-md font-medium transition-colors"
            :class="activePreset === p.value
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'">
            {{ p.label }}
          </button>
        </div>
      </div>

      <!-- 自定义起止日期 -->
      <div class="flex items-center gap-3 flex-wrap">
        <span class="text-xs font-medium text-gray-400 dark:text-gray-500 w-12 shrink-0">自定义</span>
        <div class="flex items-center gap-2 text-sm">
          <input type="date" :min="minDate" :max="maxDate" :value="days[startIdx]" @change="onStartDate"
            class="date-input" />
          <span class="text-gray-400">→</span>
          <input type="date" :min="minDate" :max="maxDate" :value="days[endIdx]" @change="onEndDate"
            class="date-input" />
          <span class="text-xs text-gray-400 dark:text-gray-500 ml-1">共 {{ dayCount ? (endIdx - startIdx + 1) : 0 }} 天</span>
        </div>
      </div>
    </section>

    <!-- 全局阵营胜率 -->
    <section class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
      <div class="wiki-card p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-survivor-600 dark:text-survivor-400">幸存者阵营</span>
          <span class="text-lg font-mono font-bold text-survivor-600 dark:text-survivor-400">{{ pct(global.survivor_win_rate) }}</span>
        </div>
        <div class="h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
          <div class="h-full rounded-full bar-survivor" :style="`width: ${(global.survivor_win_rate ?? 0) * 100}%`" />
        </div>
        <div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">{{ global.survivor_wins.toLocaleString() }} 胜 / 共 {{ global.games.toLocaleString() }} 局</div>
      </div>
      <div class="wiki-card p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-kerrigan-600 dark:text-kerrigan-400">凯瑞甘阵营</span>
          <span class="text-lg font-mono font-bold text-kerrigan-600 dark:text-kerrigan-400">{{ pct(global.kerrigan_win_rate) }}</span>
        </div>
        <div class="h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
          <div class="h-full rounded-full bar-kerrigan" :style="`width: ${(global.kerrigan_win_rate ?? 0) * 100}%`" />
        </div>
        <div class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">{{ global.kerrigan_wins.toLocaleString() }} 胜</div>
      </div>
    </section>

    <!-- 控制栏 -->
    <div class="flex flex-wrap items-center gap-2 mb-3">
      <div class="flex rounded-lg bg-surface-100 dark:bg-gray-800 p-0.5 text-sm">
        <button v-for="t in TEAM_TABS" :key="t.value" @click="team = t.value"
          class="px-3 py-1 rounded-md font-medium transition-colors"
          :class="team === t.value
            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'">
          {{ t.label }}
        </button>
      </div>
      <div class="flex-1"></div>
      <div class="flex rounded-lg bg-surface-100 dark:bg-gray-800 p-0.5 text-sm">
        <button v-for="s in SORT_TABS" :key="s.value" @click="sortBy = s.value"
          class="px-3 py-1 rounded-md font-medium transition-colors"
          :class="sortBy === s.value
            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'">
          {{ s.label }}
        </button>
      </div>
    </div>

    <!-- 胜率表 -->
    <div v-if="global.games === 0" class="py-12 text-center text-sm text-gray-400 dark:text-gray-500">
      所选时间段 / 服务器暂无对局数据。
    </div>
    <div v-else class="space-y-1.5">
      <div v-for="(r, i) in rows" :key="r.role_id"
        class="flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
        :class="{ 'opacity-50': r.low_sample }">
        <span class="w-5 text-right text-xs font-mono text-gray-300 dark:text-gray-600">{{ i + 1 }}</span>
        <NuxtLink :to="`/classes/${r.role_id}`" class="flex items-center gap-3 flex-1 min-w-0 group">
          <img :src="icon(r.role_id)" class="w-7 h-7 rounded shrink-0" :alt="r.nameZh" />
          <span class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate group-hover:text-survivor-600 dark:group-hover:text-survivor-400 transition-colors">
            {{ r.nameZh }}
          </span>
          <span class="text-xs px-1.5 py-0.5 rounded shrink-0"
            :class="r.team === 1
              ? 'bg-kerrigan-50 text-kerrigan-600 dark:bg-kerrigan-900/30 dark:text-kerrigan-400'
              : 'bg-survivor-50 text-survivor-600 dark:bg-survivor-900/30 dark:text-survivor-400'">
            {{ r.team === 1 ? '凯' : '人' }}
          </span>
          <span v-if="r.low_sample" class="text-[0.65rem] text-gray-400 shrink-0">样本不足</span>
        </NuxtLink>
        <div class="hidden sm:block flex-1 mx-2 max-w-[12rem]">
          <div class="h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
            <div class="h-full rounded-full bar-fill" :class="r.team === 1 ? 'bar-kerrigan' : 'bar-survivor'"
              :style="`width: ${Math.min((r.win_rate ?? 0) * 100, 100)}%`" />
          </div>
        </div>
        <span class="text-sm font-mono font-bold w-12 text-right"
          :class="(r.win_rate ?? 0) >= 0.5 ? 'text-green-600' : 'text-red-500'">
          {{ pct(r.win_rate) }}
        </span>
        <span class="text-xs text-gray-400 w-16 text-right">{{ r.plays.toLocaleString() }}场</span>
      </div>
    </div>

    <p class="mt-6 text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
      说明：胜率统计自去重后的对局数据，每名玩家在一局中扮演的角色各计一次；某角色胜率 = 该角色所在阵营取胜的场次占比。
      服务器按对局大区归组：国服 = China，外服 = 欧服 / 美服 / 韩服。可按天任选时间段叠加求和。
      场次低于 {{ lowSampleThreshold }} 的角色样本不足、数据噪声较大，已置灰标注。此为数据截至时点的静态快照。
      本页为**原始去重对局**的即时胜率；官方经 k 值平滑的跨版本口径见「跨版本走势」标签。
    </p>
  </div>
</template>

<script setup lang="ts">
import type { RegionFilter } from '~/composables/useBalanceData'

const { dumpThrough, lowSampleThreshold, aggregate, days, dayCount, dayToIndex } = useBalanceData()
const { getById } = useClassData()

type TeamFilter = 'all' | 'survivor' | 'kerrigan'
type SortKey = 'win_rate' | 'plays'
type PresetKey = 'all' | 'd7' | 'd30' | 'd90' | 'year' | 'custom'

const REGION_TABS: { value: RegionFilter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'cn', label: '国服' },
  { value: 'intl', label: '外服' },
]
const TEAM_TABS: { value: TeamFilter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'survivor', label: '幸存者' },
  { value: 'kerrigan', label: '凯瑞甘' },
]
const SORT_TABS: { value: SortKey; label: string }[] = [
  { value: 'win_rate', label: '按胜率' },
  { value: 'plays', label: '按场次' },
]
const PRESETS: { value: PresetKey; label: string; days?: number }[] = [
  { value: 'all', label: '全部' },
  { value: 'd7', label: '近7天', days: 7 },
  { value: 'd30', label: '近30天', days: 30 },
  { value: 'd90', label: '近90天', days: 90 },
  { value: 'year', label: '今年' },
]

const region = ref<RegionFilter>('all')
const team = ref<TeamFilter>('all')
const sortBy = ref<SortKey>('win_rate')

const startIdx = ref(0)
const endIdx = ref(dayCount - 1)
const activePreset = ref<PresetKey>('all')

const minDate = computed(() => days[0])
const maxDate = computed(() => days[dayCount - 1])

// 今年首日下标：第一个年份 == 最新一天年份的日子
function firstDayOfLatestYear(): number {
  const latestYear = (days[dayCount - 1] || '').slice(0, 4)
  const i = days.findIndex(d => d.slice(0, 4) === latestYear)
  return i < 0 ? 0 : i
}

function applyPreset(p: PresetKey) {
  activePreset.value = p
  const last = dayCount - 1
  if (p === 'all') {
    startIdx.value = 0
    endIdx.value = last
  } else if (p === 'year') {
    startIdx.value = firstDayOfLatestYear()
    endIdx.value = last
  } else {
    const preset = PRESETS.find(x => x.value === p)
    const n = preset?.days ?? dayCount
    startIdx.value = Math.max(0, last - n + 1)
    endIdx.value = last
  }
}

function onStartDate(e: Event) {
  const v = (e.target as HTMLInputElement).value
  if (!v) return
  startIdx.value = Math.min(dayToIndex(v), endIdx.value)
  activePreset.value = 'custom'
}
function onEndDate(e: Event) {
  const v = (e.target as HTMLInputElement).value
  if (!v) return
  endIdx.value = Math.max(dayToIndex(v), startIdx.value)
  activePreset.value = 'custom'
}

const agg = computed(() => aggregate(startIdx.value, endIdx.value, region.value))
const global = computed(() => agg.value.global)

const merged = computed(() =>
  agg.value.heroes.map(h => {
    const cls = getById(h.role_id)
    return { ...h, nameZh: cls?.nameZh || cls?.nameEn || h.role }
  })
)

const rows = computed(() => {
  let list = merged.value
  if (team.value === 'survivor') list = list.filter(r => r.team === 0)
  else if (team.value === 'kerrigan') list = list.filter(r => r.team === 1)
  return [...list].sort((a, b) => {
    if (sortBy.value === 'plays') return b.plays - a.plays
    return (b.win_rate ?? -1) - (a.win_rate ?? -1)
  })
})

function pct(v: number | null | undefined): string {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}
function icon(id: number): string {
  return `/icons/${String(id).padStart(2, '0')}.png`
}

const dumpThroughLabel = computed(() => {
  if (!dumpThrough) return ''
  const d = new Date(dumpThrough.replace(' ', 'T'))
  return isNaN(d.getTime()) ? dumpThrough : d.toLocaleDateString('zh-CN')
})
</script>

<style scoped>
.bar-fill { box-shadow: 0 0 6px rgba(0, 0, 0, 0.06); }
.bar-survivor { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.bar-kerrigan { background: linear-gradient(90deg, #ef4444, #dc2626); }
:global(.dark) .bar-survivor { background: linear-gradient(90deg, #60a5fa, #3b82f6); }
:global(.dark) .bar-kerrigan { background: linear-gradient(90deg, #f87171, #ef4444); }
.date-input {
  @apply px-2 py-1 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800
         text-gray-700 dark:text-gray-200 text-sm font-mono;
}
:global(.dark) .date-input { color-scheme: dark; }
</style>
