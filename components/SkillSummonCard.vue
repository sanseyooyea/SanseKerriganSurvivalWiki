<template>
  <article class="rounded-lg border border-surface-200 p-3 dark:border-gray-700">
    <header class="mb-2 flex flex-wrap items-center gap-2.5">
      <UnitIcon :icon="skill.icon" :alt="skill.nameZh" size="sm" />
      <h4 class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ skill.nameZh }}</h4>
      <Badge tone="accent">技能 · {{ skill.levels.length }} 级</Badge>
      <span v-if="common.duration" class="font-mono text-xs tabular-nums text-gray-400">持续 {{ common.duration }}s</span>
      <span v-if="common.energyCost" class="font-mono text-xs tabular-nums text-gray-400">耗能 {{ common.energyCost }}</span>
      <span v-if="common.cooldown" class="font-mono text-xs tabular-nums text-gray-400">冷却 {{ common.cooldown }}s</span>
      <span v-if="antiAir" class="font-mono text-xs text-gray-400">对地 / 对空</span>
    </header>

    <p v-if="hasAbsorb" class="mb-2 max-w-3xl text-[0.7rem] leading-relaxed text-gray-500 dark:text-gray-400">
      每次拦截消耗与被挡伤害等量的能量。单架可吸收伤害上限 = 初始能量 + 回能 × 持续时间
      （出生即满能量，回能只在消耗后才生效，所以是上限）。
    </p>

    <div class="overflow-x-auto rounded-md border border-surface-200 dark:border-gray-700">
      <table class="w-full font-mono text-xs">
        <thead class="bg-surface-50 text-[0.65rem] uppercase tracking-wider text-gray-400 dark:bg-gray-900/40 dark:text-gray-500">
          <tr>
            <th class="px-2.5 py-1.5 text-left font-medium">技能等级</th>
            <th v-for="c in columns" :key="c.key" class="px-2.5 py-1.5 text-right font-medium">{{ c.label }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-surface-200 dark:divide-gray-700">
          <tr v-for="(l, i) in skill.levels" :key="l.level" class="transition-colors hover:bg-surface-50 dark:hover:bg-gray-700/30">
            <td class="px-2.5 py-1.5 text-gray-500">
              <NuxtLink :to="`/units/${l.unit}`" class="hover:text-survivor-600 dark:hover:text-survivor-400">Lv{{ l.level }}</NuxtLink>
            </td>
            <td v-for="c in columns" :key="c.key" class="px-2.5 py-1.5 text-right tabular-nums"
              :class="[c.class || 'text-gray-700 dark:text-gray-300', changed(c.key, i) ? 'font-semibold' : '']">
              {{ fmt((l as any)[c.key]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { SkillSummon } from '~/composables/useUnitsData'

const props = defineProps<{ skill: SkillSummon }>()

const ALL_COLUMNS = [
  { key: 'damage', label: '单发伤害', class: 'text-gray-800 dark:text-gray-100' },
  { key: 'period', label: '攻击间隔' },
  { key: 'range', label: '射程' },
  { key: 'dpsLight', label: '对轻甲 DPS', class: 'text-orange-600 dark:text-orange-400' },
  { key: 'dpsArmored', label: '对重甲 DPS', class: 'text-orange-600 dark:text-orange-400' },
  { key: 'dpsKerrigan', label: '对凯瑞甘 DPS', class: 'text-kerrigan-600 dark:text-kerrigan-400' },
  { key: 'unitEnergy', label: '总能量', class: 'text-violet-600 dark:text-violet-400' },
  { key: 'absorbMax', label: '可吸收伤害', class: 'text-emerald-600 dark:text-emerald-400' },
  { key: 'hp', label: '生命' },
  { key: 'armor', label: '护甲' },
  { key: 'unitEnergyRegen', label: '回能/秒' },
  { key: 'duration', label: '持续' },
  { key: 'energyCost', label: '耗能' },
  { key: 'cooldown', label: '冷却' },
]

/** 只显示在任一级有值的列；全级相同的放到标题行（common），不进表。 */
const common = computed(() => {
  const out: Record<string, number> = {}
  for (const k of ['duration', 'energyCost', 'cooldown']) {
    const vals = new Set(props.skill.levels.map(l => (l as any)[k]))
    if (vals.size === 1) {
      const v = [...vals][0]
      if (v) out[k] = v as number
    }
  }
  return out
})
const columns = computed(() => ALL_COLUMNS.filter(c =>
  !(c.key in common.value) &&
  props.skill.levels.some(l => (l as any)[c.key])))
const hasAbsorb = computed(() => props.skill.levels.some(l => l.absorbMax))
const antiAir = computed(() => props.skill.levels.some(l => (l as any).antiAir))

function changed(key: string, i: number) {
  if (i === 0) return false
  return (props.skill.levels[i] as any)[key] !== (props.skill.levels[i - 1] as any)[key]
}
function fmt(v: unknown) {
  return v == null || v === 0 ? '—' : String(v)
}
</script>
