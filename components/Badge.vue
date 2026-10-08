<template>
  <span class="inline-block shrink-0 rounded px-1.5 py-px text-[0.6rem] leading-4" :class="toneClass">
    <slot />
  </span>
</template>

<script setup lang="ts">
/** 兵种/属性用的小徽章。tone 决定配色；attribute 徽章由 useUnitsData 提供现成 class 串。 */
const props = withDefaults(defineProps<{ tone?: 'neutral' | 'danger' | 'warn' | 'info' | 'accent' }>(), { tone: 'neutral' })

const TONES: Record<string, string> = {
  neutral: 'bg-surface-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  danger: 'bg-kerrigan-50 text-kerrigan-700 dark:bg-kerrigan-800/40 dark:text-kerrigan-200',
  warn: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  info: 'bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300',
  accent: 'bg-survivor-50 text-survivor-700 dark:bg-survivor-800/40 dark:text-survivor-200',
}
const toneClass = computed(() => TONES[props.tone])
</script>
