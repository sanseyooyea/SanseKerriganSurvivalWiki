<template>
  <div>
    <header class="mb-6">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">版本 Meta · 角色强度走势</h1>
        <NuxtLink to="/balance" class="text-xs text-survivor-600 dark:text-survivor-400 hover:underline">→ 当前胜率总览</NuxtLink>
      </div>
      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        基于官方历史平衡报告，按周采样。展示各角色胜率随时间（跨版本）的演化。
      </p>
      <p v-if="dumpThrough" class="mt-1 text-xs font-mono text-gray-400 dark:text-gray-500">
        数据截至 {{ dumpThrough }} · 共 {{ snapshots.length }} 个周快照
      </p>
    </header>

    <!-- 趋势图 -->
    <section class="wiki-card p-5 mb-6">
      <div class="section-title">胜率走势</div>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-1 mb-3">点选角色叠加曲线；虚线为 50% 基准。</p>
      <LineChart v-if="trendSeries.length" :series="trendSeries" :height="300"
        :ref-y="0.5" :x-format="fmtMonth" :y-format="fmtPct" />
      <p v-else class="text-sm text-gray-400 py-8 text-center">请在下方选择至少一个角色</p>

      <!-- 队伍切换 + 角色选择 -->
      <div class="flex items-center gap-2 mt-4 mb-2">
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
        <button @click="selected = []" class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">清空</button>
      </div>
      <div class="flex flex-wrap gap-1.5">
        <button v-for="r in teamRoles" :key="r.role" @click="toggle(r.role)"
          class="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs border transition"
          :class="selected.includes(r.role)
            ? 'border-transparent text-white'
            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
          :style="selected.includes(r.role) ? `background:${colorOf(r.role)}` : ''">
          <img :src="`/icons/${roleIcon(r.role)}.png`" class="w-4 h-4 rounded" :alt="r.role" />
          {{ roleName(r.role) }}
        </button>
      </div>
    </section>

    <!-- 历史快照表 -->
    <section class="wiki-card p-5 mb-6">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <div class="section-title !mb-0">历史快照</div>
        <span class="text-sm font-mono font-semibold text-gray-700 dark:text-gray-200">{{ activeSnapshot?.date }}</span>
      </div>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-1 mb-3">拖动时间轴查看任一时点的全角色胜率排行。</p>
      <input type="range" min="0" :max="snapshots.length - 1" v-model.number="snapIdx"
        class="w-full accent-survivor-500 mb-1" />
      <div class="flex justify-between text-[0.65rem] font-mono text-gray-400 mb-4">
        <span>{{ snapshots[0]?.date }}</span>
        <span>{{ snapshots[snapshots.length - 1]?.date }}</span>
      </div>

      <div class="space-y-1.5">
        <div v-for="(r, i) in snapshotRows" :key="r.role"
          class="flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
          :class="{ 'opacity-50': r.sample < 30 }">
          <span class="w-5 text-right text-xs font-mono text-gray-300 dark:text-gray-600">{{ i + 1 }}</span>
          <img :src="`/icons/${roleIcon(r.role)}.png`" class="w-7 h-7 rounded shrink-0" :alt="r.role" />
          <span class="text-sm font-medium text-gray-800 dark:text-gray-200 w-28 truncate">{{ roleName(r.role) }}</span>
          <span class="text-xs px-1.5 py-0.5 rounded shrink-0"
            :class="r.team === 1
              ? 'bg-kerrigan-50 text-kerrigan-600 dark:bg-kerrigan-900/30 dark:text-kerrigan-400'
              : 'bg-survivor-50 text-survivor-600 dark:bg-survivor-900/30 dark:text-survivor-400'">
            {{ r.team === 1 ? '凯' : '人' }}
          </span>
          <div class="hidden sm:block flex-1 mx-2 max-w-[12rem]">
            <div class="h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
              <div class="h-full rounded-full bar-fill" :class="r.team === 1 ? 'bar-kerrigan' : 'bar-survivor'"
                :style="`width: ${Math.min(r.winrate * 100, 100)}%`" />
            </div>
          </div>
          <span class="text-sm font-mono font-bold w-12 text-right"
            :class="r.winrate >= 0.5 ? 'text-green-600' : 'text-red-500'">{{ fmtPct(r.winrate) }}</span>
          <span class="text-xs text-gray-400 w-16 text-right">{{ r.sample.toLocaleString() }}场</span>
        </div>
      </div>
    </section>

    <p class="text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
      说明：数据取自官方历史平衡报告（historical_balance），每个时点的胜率为该角色所在阵营取胜的占比；按 ISO 周采样（每周末次快照）。
      游戏内补丁无独立版本号，故时间轴以日期表示。样本不足 30 场的角色已置灰。
    </p>
  </div>
</template>

<script setup lang="ts">
import iconMap from '~/data/role-icon-map.json'
import nameMap from '~/data/role-name-map.json'

const { roles, snapshots, dumpThrough } = useMetaHistory()

const PALETTE = ['#16a34a', '#dc2626', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#14b8a6', '#a855f7']

type TeamFilter = 'all' | 'survivor' | 'kerrigan'
const TEAM_TABS: { value: TeamFilter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'survivor', label: '幸存者' },
  { value: 'kerrigan', label: '凯瑞甘' },
]
const team = ref<TeamFilter>('all')

const teamOf = new Map(roles.map(r => [r.role, r.team]))

const teamRoles = computed(() => {
  if (team.value === 'survivor') return roles.filter(r => r.team === 0)
  if (team.value === 'kerrigan') return roles.filter(r => r.team === 1)
  return roles
})

// 默认选中最新快照里样本最多的 3 个角色，避免初始空图
const latest = snapshots[snapshots.length - 1]
const defaultSel = latest
  ? Object.entries(latest.roles).sort((a, b) => b[1].sample - a[1].sample).slice(0, 3).map(e => e[0])
  : []
const selected = ref<string[]>(defaultSel)

function toggle(role: string) {
  const i = selected.value.indexOf(role)
  if (i >= 0) selected.value.splice(i, 1)
  else selected.value.push(role)
}
function colorOf(role: string): string {
  const i = selected.value.indexOf(role)
  return PALETTE[(i < 0 ? 0 : i) % PALETTE.length]
}

function ts(date: string): number {
  return new Date(date + 'T00:00:00').getTime()
}
const trendSeries = computed(() =>
  selected.value.map(role => ({
    label: roleName(role),
    color: colorOf(role),
    points: snapshots
      .filter(s => s.roles[role])
      .map(s => [ts(s.date), s.roles[role].winrate] as [number, number]),
  })).filter(s => s.points.length),
)

// 快照表
const snapIdx = ref(snapshots.length - 1)
const activeSnapshot = computed(() => snapshots[snapIdx.value])
const snapshotRows = computed(() => {
  const snap = activeSnapshot.value
  if (!snap) return []
  return Object.entries(snap.roles)
    .map(([role, st]) => ({ role, team: teamOf.get(role) ?? 0, winrate: st.winrate, sample: st.sample }))
    .sort((a, b) => b.winrate - a.winrate)
})

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`
}
function fmtMonth(t: number): string {
  const d = new Date(t)
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString('zh-CN', { year: '2-digit', month: 'numeric' })
}
function roleIcon(name: string): string {
  const map = iconMap as Record<string, string>
  return map[name] || map[name.replace(/ /g, '_')] || '00'
}
function roleName(name: string): string {
  const map = nameMap as Record<string, string>
  return map[name] || map[name.replace(/ /g, '_')] || name
}

useHead({ title: '版本Meta · 角色强度走势 - 凯瑞甘生存2 Wiki' })
</script>

<style scoped>
.bar-fill { box-shadow: 0 0 6px rgba(0, 0, 0, 0.06); }
.bar-survivor { background: linear-gradient(90deg, #3b82f6, #2563eb); }
.bar-kerrigan { background: linear-gradient(90deg, #ef4444, #dc2626); }
:global(.dark) .bar-survivor { background: linear-gradient(90deg, #60a5fa, #3b82f6); }
:global(.dark) .bar-kerrigan { background: linear-gradient(90deg, #f87171, #ef4444); }
</style>
