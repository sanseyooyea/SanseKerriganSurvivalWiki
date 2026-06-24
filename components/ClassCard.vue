<template>
  <NuxtLink :to="`/classes/${data.id}`" class="group">
    <div class="wiki-card p-3.5 group-hover:-translate-y-0.5 group-hover:shadow-elevated transition-all duration-200"
      :class="data.team === 'Kerrigan' ? 'group-hover:border-kerrigan-200 dark:group-hover:border-kerrigan-700' : 'group-hover:border-survivor-200 dark:group-hover:border-survivor-700'">
      <div class="flex items-center gap-3">
        <div class="relative">
          <img :src="`/icons/${String(data.id).padStart(2, '0')}.png`"
            :alt="data.nameZh || data.nameEn"
            class="w-11 h-11 rounded-lg shadow-sm transition-transform duration-200 group-hover:scale-110" />
          <div :class="teamDotClass"
            class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white dark:border-gray-800"></div>
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-medium text-sm text-gray-900 dark:text-gray-100 truncate transition-colors duration-200"
            :class="data.team === 'Kerrigan' ? 'group-hover:text-kerrigan-600 dark:group-hover:text-kerrigan-400' : 'group-hover:text-survivor-600 dark:group-hover:text-survivor-400'">
            {{ data.nameZh || data.nameEn }}
          </div>
          <div class="text-xs text-gray-400 dark:text-gray-500">{{ data.nameEn }}</div>
        </div>
        <div class="flex flex-col items-end gap-0.5">
          <span v-if="winRate != null" class="text-xs font-mono font-semibold"
            :class="winRate >= 0.5 ? 'text-green-600 dark:text-green-500' : 'text-red-500 dark:text-red-400'">
            {{ (winRate * 100).toFixed(0) }}%
          </span>
          <span class="text-xs text-gray-400 dark:text-gray-500 font-medium">{{ categoryLabel }}</span>
        </div>
      </div>
    </div>
  </NuxtLink>
</template>

<script setup lang="ts">
import type { ClassInfo } from '~/composables/useClassData'

const props = defineProps<{ data: ClassInfo }>()

const { getByRoleId } = useBalanceData()
// 样本不足的不显示，避免误导
const winRate = computed(() => {
  const b = getByRoleId(props.data.id)
  return b && !b.low_sample ? b.win_rate : null
})

const teamDotClass = computed(() =>
  props.data.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'
)

const categoryMap: Record<string, string> = {
  Hunter: '猎手', Builder: '建造者', Support: '辅助',
  Defender: '防御者', Random: '随机'
}
const categoryLabel = computed(() => categoryMap[props.data.category] || props.data.category)
</script>
