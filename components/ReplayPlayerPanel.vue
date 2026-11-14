<template>
  <div class="rounded-xl border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 overflow-hidden">
    <!-- 标题 -->
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 border-b border-surface-100 dark:border-gray-700/60">
      <span class="w-3 h-3 rounded-full shrink-0" :style="{ background: player.color }" />
      <UnitIcon :icon="icon" size="md" :alt="roleLabel(player)" />
      <div class="min-w-0">
        <div class="font-medium text-gray-800 dark:text-gray-100 truncate">{{ player.name }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">
          {{ roleLabel(player) }} · {{ player.team === 1 ? '凯瑞甘方' : '幸存者' }}
          <template v-if="won != null"> · <span :class="won ? 'text-emerald-600 dark:text-emerald-400' : 'text-kerrigan-600 dark:text-kerrigan-400'">{{ won ? '胜' : '负' }}</span></template>
          <template v-if="player.mmrBefore != null"> · MMR {{ player.mmrBefore }}<template v-if="player.mmrAfter != null && player.mmrAfter !== player.mmrBefore">
            → {{ player.mmrAfter }}</template></template>
        </div>
      </div>
      <span class="ml-auto font-mono text-xs text-gray-500 tabular-nums">截至 {{ fmtLoop(t) }}</span>
      <NuxtLink v-if="player.handle" :to="`/player/${player.handle}`"
        class="text-xs text-survivor-600 dark:text-survivor-400 hover:underline">玩家主页 →</NuxtLink>
      <button type="button" class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" @click="$emit('close')">关闭 ✕</button>
    </div>

    <div class="grid gap-4 p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <!-- 当前时刻的数值 -->
      <div class="space-y-3">
        <div>
          <h3 class="rp-h">经济（{{ econAt ? fmtLoop(econAt.loop) + ' 采样' : '无数据' }}）</h3>
          <dl class="grid grid-cols-3 gap-2">
            <div v-for="s in econTiles" :key="s.label" class="rp-tile">
              <dt>{{ s.label }}</dt>
              <dd>{{ s.value }}</dd>
            </div>
          </dl>
        </div>
        <div>
          <h3 class="rp-h">战斗与发展（{{ perfAt ? fmtLoop(perfAt) + ' 采样，每分钟一次' : '无数据' }}）</h3>
          <dl class="grid grid-cols-3 gap-2">
            <div v-for="s in perfTiles" :key="s.label" class="rp-tile">
              <dt>{{ s.label }}</dt>
              <dd>{{ s.value }}</dd>
            </div>
          </dl>
        </div>
        <p class="text-[11px] leading-relaxed text-gray-400 dark:text-gray-500">
          数据来自录像：经济为引擎每 30 秒的快照；战斗与发展为地图每分钟写入的统计，
          地图写入时对部分大数值做了取整（如采集晶矿按百位），与游戏内结算可能略有出入。
        </p>
      </div>

      <!-- 科技时间线 -->
      <div class="min-w-0">
        <h3 class="rp-h">
          已完成科技 <span class="font-normal text-gray-400">{{ doneUpgrades.length }} / 全场 {{ allUpgrades.length }}</span>
        </h3>
        <div v-if="!allUpgrades.length" class="text-xs text-gray-400">本局没有该玩家的科技记录。</div>
        <ol v-else class="max-h-72 overflow-y-auto pr-1 text-xs divide-y divide-surface-100 dark:divide-gray-700/60">
          <li v-for="(u, i) in allUpgrades" :key="i">
            <button type="button" @click="$emit('seek', u.t - 3 * LOOPS_PER_SEC)"
              class="w-full flex items-center gap-2 py-1 text-left hover:bg-surface-50 dark:hover:bg-gray-700/40 rounded"
              :class="u.t <= t ? '' : 'opacity-40'">
              <span class="font-mono w-12 shrink-0 tabular-nums text-gray-500">{{ fmtLoop(u.t) }}</span>
              <UnitIcon :icon="u.icon" size="xs" :alt="u.name" />
              <span class="truncate text-gray-700 dark:text-gray-200">{{ u.name }}</span>
              <span v-if="u.level > 1" class="text-gray-400 shrink-0">Lv{{ u.level }}</span>
            </button>
          </li>
        </ol>
        <p v-if="player.team === 1" class="mt-1 text-[11px] text-gray-400">凯瑞甘方两名玩家共享虫族科技，此处只列本人购买的。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  type ReplayData, type ReplayPlayer, ECON_STRIDE, LOOPS_PER_SEC, fmtLoop, roleLabel, lowerIndex, stepAt,
} from '~/utils/replay'
import roleIconMap from '~/data/role-icon-map.json'

const props = defineProps<{ data: ReplayData; player: ReplayPlayer; t: number }>()
defineEmits<{ close: []; seek: [loop: number] }>()

const icon = computed(() => {
  const code = props.player.roleNameEn ? (roleIconMap as Record<string, string>)[props.player.roleNameEn] : null
  return code ? `/icons/${code}.png` : null
})
const won = computed(() => {
  const w = props.data.meta.winningTeam
  return w === 0 || w === 1 ? props.player.team === w : null
})

function fmt(v: number | null | undefined): string {
  if (v == null) return '—'
  if (Math.abs(v) >= 100000) return `${(v / 10000).toFixed(1)}万`
  return Math.round(v).toLocaleString('zh-CN')
}

// ---------- 经济快照 ----------
const econAt = computed(() => {
  const e = props.player.econ
  if (!e?.length) return null
  const i = lowerIndex(e, props.t, ECON_STRIDE)
  if (i < 0) return null
  const o = i * ECON_STRIDE
  return { loop: e[o], minerals: e[o + 1], gas: e[o + 2], mRate: e[o + 3], gRate: e[o + 4], army: e[o + 5] }
})
const econTiles = computed(() => {
  const e = econAt.value
  return [
    { label: '持有晶矿', value: fmt(e?.minerals) },
    { label: '持有瓦斯', value: fmt(e?.gas) },
    { label: '军队价值', value: fmt(e?.army) },
    { label: '晶矿/分', value: fmt(e?.mRate) },
    { label: '瓦斯/分', value: fmt(e?.gRate) },
    { label: '累计采集晶矿', value: fmt(perf('minerals')) },
  ]
})

// ---------- 地图统计（每分钟） ----------
function perf(key: string): number | null {
  return stepAt(props.player.perf?.[key], props.t, 2)
}
const perfAt = computed(() => {
  const f = props.player.perf?.apm
  if (!f?.length) return null
  const i = lowerIndex(f, props.t, 2)
  return i < 0 ? null : f[i * 2]
})
const perfTiles = computed(() => {
  const isKerrigan = props.player.team === 1
  const tiles = [
    { label: '击杀单位', value: fmt(perf('kills')) },
    { label: isKerrigan ? '造成伤害' : '对虫族伤害', value: fmt(isKerrigan ? perf('damage') : perf('heroDamage')) },
    { label: '摧毁建筑', value: fmt(perf('razed')) },
    { label: '科技花费', value: fmt(perf('upgradeSpend')) },
    { label: '建造建筑', value: fmt(perf('built')) },
    { label: '训练单位', value: fmt(perf('trained')) },
    { label: '损失资源', value: fmt(perf('resLost')) },
    { label: isKerrigan ? '采集瓦斯' : '喂给虫族瓦斯', value: fmt(isKerrigan ? perf('gas') : perf('gasFed')) },
    { label: 'APM', value: fmt(perf('apm')) },
  ]
  return tiles
})

// ---------- 科技 ----------
const allUpgrades = computed(() => {
  const seen: Record<string, number> = {}
  return props.data.events
    .filter((e): e is Extract<ReplayData['events'][number], { kind: 'upgrade' }> =>
      e.kind === 'upgrade' && e.pid === props.player.pid)
    .map((e) => {
      seen[e.upgrade] = (seen[e.upgrade] || 0) + 1
      const info = props.data.upgrades[e.upgrade]
      return { t: e.t, name: info?.nameZh || e.upgrade, icon: info?.icon || null, level: seen[e.upgrade] }
    })
})
const doneUpgrades = computed(() => allUpgrades.value.filter(u => u.t <= props.t))
</script>

<style scoped>
.rp-h { @apply text-xs font-medium text-gray-600 dark:text-gray-300 mb-1.5; }
.rp-tile { @apply rounded-lg bg-surface-50 dark:bg-gray-900/40 px-2 py-1.5; }
.rp-tile dt { @apply text-[11px] text-gray-500 dark:text-gray-400; }
.rp-tile dd { @apply font-mono text-sm font-semibold text-gray-800 dark:text-gray-100 tabular-nums; }
</style>
