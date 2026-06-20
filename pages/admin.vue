<template>
  <div v-if="!isAdmin" class="text-center py-20">
    <p class="text-gray-400 text-lg">需要管理员权限</p>
  </div>
  <div v-else>
    <div class="flex items-center gap-2 mb-6 border-b border-surface-200 dark:border-gray-700">
      <button v-for="t in tabs" :key="t.key" @click="tab = t.key"
        class="px-4 py-2.5 text-sm font-medium -mb-px border-b-2 transition-colors"
        :class="tab === t.key
          ? 'border-survivor-500 text-survivor-600 dark:text-survivor-400'
          : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'">
        {{ t.label }}
      </button>
    </div>

    <!-- 用户管理 -->
    <div v-show="tab === 'users'" class="wiki-card overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-50 dark:bg-gray-800 text-left text-xs text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3 font-medium">用户名</th>
            <th class="px-4 py-3 font-medium">句柄</th>
            <th class="px-4 py-3 font-medium">角色</th>
            <th class="px-4 py-3 font-medium">注册时间</th>
            <th class="px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-for="u in users" :key="u.id">
            <td class="px-4 py-3 text-gray-900 dark:text-gray-100 font-medium">{{ u.username }}</td>
            <td class="px-4 py-3 text-xs text-gray-500">
              <NuxtLink v-if="u.handle" :to="`/player/${u.handle}`" class="text-survivor-600 hover:underline">{{ u.handle }}</NuxtLink>
              <span v-else class="text-gray-300">-</span>
            </td>
            <td class="px-4 py-3">
              <select :value="u.role" @change="changeRole(u.id, ($event.target as HTMLSelectElement).value)"
                class="text-xs border border-gray-200 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200">
                <option value="user">user</option>
                <option value="editor">editor</option>
                <option value="admin">admin</option>
              </select>
            </td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ formatDate(u.created_at) }}</td>
            <td class="px-4 py-3 text-xs text-gray-400">ID: {{ u.id }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 流量统计 -->
    <div v-show="tab === 'stats'">
      <div class="flex items-center justify-between mb-4">
        <div class="flex gap-2">
          <button v-for="d in [7, 30, 90]" :key="d" @click="loadStats(d)"
            class="px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors"
            :class="range === d
              ? 'border-survivor-500 text-survivor-600 dark:text-survivor-400 bg-survivor-50 dark:bg-survivor-900/30'
              : 'border-surface-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-surface-100 dark:hover:bg-gray-800'">
            近 {{ d }} 天
          </button>
        </div>
      </div>

      <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div v-for="c in summaryCards" :key="c.label" class="wiki-card p-4">
          <div class="text-xs text-gray-500 dark:text-gray-400">{{ c.label }}</div>
          <div class="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{{ c.value.toLocaleString() }}</div>
        </div>
      </div>

      <!-- 每日趋势柱状图 -->
      <div v-if="stats" class="wiki-card p-5 mb-6">
        <div class="flex items-center gap-4 mb-4 text-xs">
          <span class="font-medium text-gray-700 dark:text-gray-300">每日趋势</span>
          <span class="flex items-center gap-1.5 text-gray-500"><span class="w-3 h-3 rounded-sm bg-survivor-500"></span>PV</span>
          <span class="flex items-center gap-1.5 text-gray-500"><span class="w-3 h-3 rounded-sm bg-kerrigan-500"></span>UV</span>
        </div>
        <div v-if="stats.trend.length" class="flex items-end gap-1 h-44">
          <div v-for="r in stats.trend" :key="r.day" class="flex-1 flex flex-col items-center justify-end group relative h-full">
            <div class="absolute -top-1 left-1/2 -translate-x-1/2 -translate-y-full hidden group-hover:block whitespace-nowrap text-[0.65rem] bg-gray-900 text-white px-2 py-1 rounded shadow-lg z-10">
              {{ r.day.slice(5) }} · PV {{ r.pv }} · UV {{ r.uv }}
            </div>
            <div class="w-full flex items-end justify-center gap-px h-full">
              <div class="w-1/2 bg-survivor-500/80 rounded-t-sm transition-all" :style="{ height: barH(r.pv) }"></div>
              <div class="w-1/2 bg-kerrigan-500/80 rounded-t-sm transition-all" :style="{ height: barH(r.uv) }"></div>
            </div>
          </div>
        </div>
        <p v-else class="text-sm text-gray-400 py-8 text-center">暂无数据</p>
      </div>

      <!-- 热门页面 -->
      <div v-if="stats" class="wiki-card overflow-hidden">
        <div class="px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 border-b border-surface-200 dark:border-gray-700">
          热门页面 · 近 {{ range }} 天
        </div>
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 dark:bg-gray-800 text-left text-xs text-gray-500 dark:text-gray-400">
              <th class="px-4 py-2.5 font-medium">路径</th>
              <th class="px-4 py-2.5 font-medium text-right">PV</th>
              <th class="px-4 py-2.5 font-medium text-right">UV</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="p in stats.topPages" :key="p.path">
              <td class="px-4 py-2.5">
                <NuxtLink :to="p.path" class="text-survivor-600 dark:text-survivor-400 hover:underline font-mono text-xs">{{ p.path }}</NuxtLink>
              </td>
              <td class="px-4 py-2.5 text-right text-gray-900 dark:text-gray-100 font-medium">{{ p.pv.toLocaleString() }}</td>
              <td class="px-4 py-2.5 text-right text-gray-500 dark:text-gray-400">{{ p.uv.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!stats.topPages.length" class="text-sm text-gray-400 py-8 text-center">暂无数据</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { isAdmin, authHeaders } = useAuth()
const users = ref<any[]>([])

const tabs = [
  { key: 'users', label: '用户管理' },
  { key: 'stats', label: '流量统计' },
]
const tab = ref<'users' | 'stats'>('users')

async function loadUsers() {
  try {
    const res = await $fetch<any>('/api/admin/users', { headers: authHeaders.value })
    users.value = res.users || res
  } catch {}
}

async function changeRole(userId: number, role: string) {
  try {
    await $fetch('/api/admin/users', {
      method: 'PATCH',
      headers: authHeaders.value,
      body: { userId, role },
    })
    await loadUsers()
  } catch {}
}

// 流量统计
interface Stats {
  days: number
  today: { pv: number; uv: number }
  totalPv: number
  rangePv: number
  rangeUv: number
  trend: { day: string; pv: number; uv: number }[]
  topPages: { path: string; pv: number; uv: number }[]
}
const stats = ref<Stats | null>(null)
const range = ref(30)

const summaryCards = computed(() => stats.value ? [
  { label: '今日 PV', value: stats.value.today.pv },
  { label: '今日 UV', value: stats.value.today.uv },
  { label: `近 ${range.value} 天 PV`, value: stats.value.rangePv },
  { label: '累计 PV', value: stats.value.totalPv },
] : [])

const maxBar = computed(() =>
  Math.max(1, ...(stats.value?.trend.map(r => r.pv) ?? [1]))
)
function barH(v: number) {
  return `${Math.max(2, (v / maxBar.value) * 100)}%`
}

async function loadStats(days: number) {
  range.value = days
  try {
    stats.value = await $fetch<Stats>('/api/admin/stats', {
      headers: authHeaders.value,
      query: { days },
    })
  } catch {}
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('zh-CN')
}

watch(tab, (t) => {
  if (t === 'stats' && !stats.value) loadStats(range.value)
})

onMounted(loadUsers)
</script>
