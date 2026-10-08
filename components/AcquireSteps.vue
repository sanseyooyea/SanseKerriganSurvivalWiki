<template>
  <div v-if="steps.length" class="space-y-1.5">
    <div class="flex flex-wrap items-baseline gap-2">
      <span class="text-xs font-medium text-gray-700 dark:text-gray-200">获取总成本</span>
      <span class="font-mono text-sm font-semibold tabular-nums text-gray-900 dark:text-gray-100">{{ fmtCost(acquire) }}</span>
      <span v-if="listed" class="text-[0.65rem] text-gray-400">（单位标价 {{ fmtCost(listed) }}，仅用于击杀 / 回收计价）</span>
    </div>
    <ol class="space-y-0.5 border-l-2 border-surface-200 pl-3 dark:border-gray-700">
      <li v-for="(s, i) in steps" :key="i" class="flex flex-wrap items-baseline gap-x-2 text-xs">
        <span class="w-9 shrink-0 text-gray-400">{{ KIND[s.kind] || s.kind }}</span>
        <span class="text-gray-600 dark:text-gray-300">
          <template v-if="s.from && s.kind !== 'start'">
            <NuxtLink :to="`/units/${s.from}`" class="hover:text-survivor-600 dark:hover:text-survivor-400">{{ name(s.from) }}</NuxtLink>
            <span class="mx-1 text-gray-300 dark:text-gray-600">→</span>
          </template>
          <NuxtLink :to="`/units/${s.to}`" class="hover:text-survivor-600 dark:hover:text-survivor-400">{{ name(s.to) }}</NuxtLink>
          <span v-if="s.kind === 'merge'" class="text-gray-400">（消耗上面两台）</span>
        </span>
        <span class="ml-auto font-mono tabular-nums" :class="s.minerals || s.gas ? 'text-gray-700 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">
          {{ s.kind === 'start' ? '开局自带' : fmtCost(s) }}
        </span>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
/** 变形 / 合体链的获取成本明细（重锤军士芬里尔：两台坦克各自升满 + 合体费）。 */
const props = defineProps<{
  acquire?: { minerals: number; gas: number; steps: any[] } | null
  listed?: { minerals: number; gas: number } | null
}>()
const { unitMap } = useUnitsData()

const steps = computed(() => props.acquire?.steps || [])
const KIND: Record<string, string> = {
  start: '开局', train: '训练', build: '建造', warp: '折跃', morph: '变形', merge: '合体', summon: '召唤',
}
function name(id: string) { return unitMap[id]?.nameZh || id }
function fmtCost(c?: { minerals?: number; gas?: number } | null) {
  if (!c) return '—'
  const m = Math.round((c.minerals || 0) * 100) / 100
  const g = Math.round((c.gas || 0) * 100) / 100
  return [`${m.toLocaleString()} 矿`, g ? `${g.toLocaleString()} 气` : ''].filter(Boolean).join(' / ')
}
</script>
