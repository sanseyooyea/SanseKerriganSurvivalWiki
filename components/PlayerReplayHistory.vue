<template>
  <div v-if="res && res.summary && res.summary.games > 0" class="wiki-card p-5 mb-6">
    <div class="flex flex-wrap items-baseline justify-between gap-2 mb-1">
      <div class="section-title !mb-0">录像对局记录</div>
      <NuxtLink to="/replays" class="text-xs text-survivor-600 dark:text-survivor-400 hover:underline">全部录像 →</NuxtLink>
    </div>
    <p class="text-[11px] text-gray-400 dark:text-gray-500 mb-4">
      统计范围仅限玩家上传到本站的录像（未经官方验证，仅供参考），不是该玩家的全部对局。
      录像主人中途离开的对局没有胜负记录，不计入胜率。
      <template v-if="res.names.length > 1">录像中用过的名字：{{ res.names.join('、') }}</template>
    </p>

    <!-- 汇总 -->
    <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 text-sm mb-4">
      <div v-for="s in tiles" :key="s.label">
        <div class="text-gray-500 dark:text-gray-400 text-xs mb-0.5">{{ s.label }}</div>
        <div class="text-lg font-bold font-mono tabular-nums text-gray-900 dark:text-gray-100">{{ s.value }}</div>
      </div>
    </div>

    <!-- 按角色 -->
    <div v-if="res.byRole.length" class="mb-4">
      <div class="text-xs font-medium text-gray-600 dark:text-gray-300 mb-1.5">按角色</div>
      <div class="flex flex-wrap gap-1.5">
        <span v-for="r in res.byRole" :key="(r.roleEn || '') + r.team"
          class="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs"
          :class="r.team === 1
            ? 'bg-kerrigan-50 text-kerrigan-800 dark:bg-kerrigan-800/20 dark:text-kerrigan-200'
            : 'bg-surface-100 text-gray-700 dark:bg-gray-700/60 dark:text-gray-200'">
          <UnitIcon :icon="roleIcon(r.roleEn)" size="xs" :alt="r.role || ''" />
          {{ r.role || '未知' }}
          <span class="font-mono tabular-nums text-gray-500 dark:text-gray-400">
            {{ r.games }}局 {{ rate(r.wins, r.losses) }}
          </span>
        </span>
      </div>
    </div>

    <!-- 对局列表 -->
    <div class="overflow-x-auto -mx-1">
      <table class="w-full text-xs min-w-[36rem]">
        <thead>
          <tr class="text-left text-gray-400 dark:text-gray-500">
            <th class="px-1 py-1 font-normal">日期</th>
            <th class="px-1 py-1 font-normal">角色</th>
            <th class="px-1 py-1 font-normal">地图</th>
            <th class="px-1 py-1 font-normal">时长</th>
            <th class="px-1 py-1 font-normal">结果</th>
            <th class="px-1 py-1 font-normal text-right">击杀</th>
            <th class="px-1 py-1 font-normal text-right">对虫族伤害</th>
            <th class="px-1 py-1 font-normal text-right">科技</th>
            <th class="px-1 py-1 font-normal text-right">MMR</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-surface-100 dark:divide-gray-700/60">
          <tr v-for="g in res.games" :key="g.hash" class="hover:bg-surface-50 dark:hover:bg-gray-700/30">
            <td class="px-1 py-1.5 whitespace-nowrap">
              <NuxtLink :to="`/replays/${g.hash}`" class="text-survivor-600 dark:text-survivor-400 hover:underline">
                {{ fmtDate(g.playedAt) }}
              </NuxtLink>
            </td>
            <td class="px-1 py-1.5 whitespace-nowrap">
              <span class="inline-flex items-center gap-1">
                <UnitIcon :icon="roleIcon(g.roleEn)" size="xs" :alt="g.role || ''" />{{ g.role || '?' }}
              </span>
            </td>
            <td class="px-1 py-1.5 whitespace-nowrap text-gray-600 dark:text-gray-300">{{ mapName(g.mapKey) }}</td>
            <td class="px-1 py-1.5 font-mono tabular-nums text-gray-500">{{ g.loops ? fmtLoop(g.loops) : '—' }}</td>
            <td class="px-1 py-1.5 whitespace-nowrap">
              <span v-if="g.won === 1" class="text-emerald-600 dark:text-emerald-400">胜</span>
              <span v-else-if="g.won === 0" class="text-kerrigan-600 dark:text-kerrigan-400">负</span>
              <span v-else class="text-gray-400" title="录像在对局结束前就停止了（录像主人中途离开），没有记录胜负；不计入胜率">无结果</span>
              <span v-if="g.team === 0 && g.heroDeathLoop != null" class="ml-1 text-gray-400"
                :title="`英雄在 ${fmtLoop(g.heroDeathLoop)} 阵亡`">✕{{ fmtLoop(g.heroDeathLoop) }}</span>
            </td>
            <td class="px-1 py-1.5 text-right font-mono tabular-nums">{{ num(g.kills) }}</td>
            <td class="px-1 py-1.5 text-right font-mono tabular-nums">{{ g.team === 1 ? '—' : num(g.heroDamage) }}</td>
            <td class="px-1 py-1.5 text-right font-mono tabular-nums">{{ num(g.upgrades) }}</td>
            <td class="px-1 py-1.5 text-right font-mono tabular-nums whitespace-nowrap">
              <template v-if="g.mmrBefore != null">
                {{ g.mmrBefore }}<span v-if="g.mmrAfter != null && g.mmrAfter !== g.mmrBefore"
                  :class="g.mmrAfter > g.mmrBefore ? 'text-emerald-600 dark:text-emerald-400' : 'text-kerrigan-600 dark:text-kerrigan-400'">
                  {{ g.mmrAfter > g.mmrBefore ? '+' : '' }}{{ g.mmrAfter - g.mmrBefore }}</span>
              </template>
              <template v-else>—</template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="res.summary.games > res.pageSize" class="mt-3 flex items-center justify-center gap-2 text-xs">
      <button type="button" class="rh-page" :disabled="page <= 1" @click="page--">上一页</button>
      <span class="text-gray-500 tabular-nums">{{ page }} / {{ pages }}</span>
      <button type="button" class="rh-page" :disabled="page >= pages" @click="page++">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fmtLoop } from '~/utils/replay'
import roleIconMap from '~/data/role-icon-map.json'

const props = defineProps<{ handle: string }>()

interface Game {
  hash: string; role: string | null; roleEn: string | null; team: number | null; won: number | null
  mmrBefore: number | null; mmrAfter: number | null; heroDeathLoop: number | null
  kills: number | null; heroDamage: number | null; upgrades: number | null
  loops: number | null; mapKey: string | null; playedAt: string | null
}
interface Resp {
  handle: string
  names: string[]
  page: number
  pageSize: number
  summary: { games: number; wins: number | null; losses: number | null; avgKills: number | null
    avgHeroDamage: number | null; avgApm: number | null; heroDeaths: number | null; lastPlayed: string | null }
  byRole: { role: string | null; roleEn: string | null; team: number | null; games: number; wins: number | null; losses: number | null }[]
  games: Game[]
}

const page = ref(1)
const res = ref<Resp | null>(null)
const pages = computed(() => (res.value ? Math.max(1, Math.ceil(res.value.summary.games / res.value.pageSize)) : 1))

async function load() {
  try {
    res.value = await $fetch<Resp>(`/api/replays/player/${encodeURIComponent(props.handle)}`, { query: { page: page.value } })
  } catch {
    res.value = null // 句柄格式不对 / 无数据：整块不显示
  }
}
onMounted(load)
watch(page, load)

const { maps } = useTerrainData()
const mapName = (k: string | null) => maps.find(m => m.key === k)?.nameZh || k || '—'
const fmtDate = (s: string | null) => (s ? new Date(s).toLocaleDateString('zh-CN') : '—')
const num = (v: number | null | undefined) => (v == null ? '—' : Math.round(v).toLocaleString('zh-CN'))
function rate(w: number | null, l: number | null) {
  const n = (w || 0) + (l || 0)
  return n ? `${Math.round(((w || 0) / n) * 100)}%` : '—'
}
function roleIcon(en: string | null) {
  const code = en ? (roleIconMap as Record<string, string>)[en] : null
  return code ? `/icons/${code}.png` : null
}

const tiles = computed(() => {
  const s = res.value!.summary
  return [
    { label: '录像场次', value: s.games },
    { label: '胜 / 负 / 无结果', value: `${s.wins || 0} / ${s.losses || 0} / ${s.games - (s.wins || 0) - (s.losses || 0)}` },
    // 有结果的场次太少时胜率没有意义，不显示百分比
    { label: '胜率', value: (s.wins || 0) + (s.losses || 0) >= 5 ? rate(s.wins, s.losses) : '样本不足' },
    { label: '场均击杀', value: num(s.avgKills) },
    { label: '场均 APM', value: num(s.avgApm) },
  ]
})
</script>

<style scoped>
.rh-page {
  @apply px-2.5 py-1 rounded-lg border border-surface-200 dark:border-gray-600 bg-surface-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-600 transition disabled:opacity-40 disabled:cursor-not-allowed;
}
</style>
