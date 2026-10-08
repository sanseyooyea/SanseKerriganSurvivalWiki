<template>
  <div v-if="groups.length" class="space-y-2">
    <div class="flex flex-wrap items-center gap-1.5">
      <span class="text-[0.65rem] text-gray-400">科技</span>
      <button v-for="p in PRESETS" :key="p.key" type="button"
        class="rounded border border-surface-200 px-1.5 py-px text-[0.65rem] text-gray-500 transition-colors hover:border-surface-300 hover:text-gray-700
               dark:border-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        @click="apply(p.key)">{{ p.label }}</button>
      <span class="ml-auto font-mono text-[0.65rem] tabular-nums text-gray-400">已投入 {{ costText }}</span>
    </div>

    <div v-for="g in groups" :key="g.family" class="flex flex-wrap items-center gap-x-2 gap-y-1">
      <span class="min-w-0 flex-1 truncate text-xs text-gray-600 dark:text-gray-300" :title="g.nameZh">
        {{ g.nameZh }}
        <span class="ml-0.5 text-[0.6rem]" :class="g.kind === 'combat' ? 'text-orange-500' : 'text-sky-500'">
          {{ g.kind === 'combat' ? '攻防' : '额外' }}
        </span>
      </span>
      <div class="flex shrink-0 overflow-hidden rounded border border-surface-200 dark:border-gray-700">
        <button
          v-for="n in g.levels.length + 1"
          :key="n"
          type="button"
          class="min-w-[1.6rem] px-1 py-px font-mono text-[0.65rem] tabular-nums transition-colors"
          :class="(modelValue[g.family] || 0) === n - 1
            ? 'bg-survivor-600 text-white dark:bg-survivor-500'
            : 'text-gray-500 hover:bg-surface-50 dark:text-gray-400 dark:hover:bg-gray-700/50'"
          :title="n - 1 === 0 ? '未研究' : levelTitle(g, n - 1)"
          @click="set(g.family, n - 1)"
        >{{ g.levels.length === 1 ? (n - 1 ? '✓' : '—') : n - 1 }}</button>
      </div>
    </div>
  </div>
  <p v-else class="text-[0.7rem] text-gray-400">这个单位没有可研究的科技</p>
</template>

<script setup lang="ts">
import type { UnitEntry, UpgradeGroup } from '~/composables/useUnitsData'
import { researchable, maxLevels, type Levels } from '~/utils/unitEngine'

const props = defineProps<{ unit: UnitEntry; modelValue: Levels }>()
const emit = defineEmits<{ 'update:modelValue': [v: Levels] }>()

const groups = computed(() => researchable(props.unit))

const PRESETS = [
  { key: 'none', label: '清零' },
  { key: 'combat', label: '攻防满级' },
  { key: 'all', label: '全部满级' },
]

function apply(key: string) {
  if (key === 'none') emit('update:modelValue', {})
  else if (key === 'combat') emit('update:modelValue', maxLevels(props.unit, 'combat'))
  else emit('update:modelValue', maxLevels(props.unit))
}
function set(family: string, n: number) {
  emit('update:modelValue', { ...props.modelValue, [family]: n })
}
function levelTitle(g: UpgradeGroup, n: number) {
  const lv = g.levels.slice(0, n)
  const m = lv.reduce((s, l) => s + (l.minerals || 0), 0)
  const gas = lv.reduce((s, l) => s + (l.gas || 0), 0)
  return `研究到第 ${n} 级 · 累计 ${m} 矿 / ${gas} 气`
}
const costText = computed(() => {
  let m = 0, g = 0
  for (const grp of groups.value) {
    for (const l of grp.levels.slice(0, props.modelValue[grp.family] || 0)) { m += l.minerals || 0; g += l.gas || 0 }
  }
  return `${m} 矿 / ${g} 气`
})
</script>
