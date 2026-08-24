<template>
  <div class="rounded-lg border overflow-hidden transition-all"
    :class="[
      expanded
        ? 'bg-gray-50 dark:bg-gray-900 border-gray-300 dark:border-gray-600'
        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
    ]">
    <div class="flex items-center justify-between px-4 py-2.5 cursor-pointer select-none"
      @click="expanded = !expanded">
      <div class="flex items-center gap-2">
        <img v-if="ability?.icon && !iconFailed"
          :src="`/ability-icons/${ability.icon}`"
          :alt="ability?.nameZh || abilityId"
          class="w-6 h-6 rounded shadow-sm flex-shrink-0"
          @error="iconFailed = true" />
        <div v-else class="w-1.5 h-1.5 rounded-full bg-survivor-500 opacity-60"></div>
        <span class="text-sm font-medium text-gray-800 dark:text-gray-200">
          {{ ability?.nameZh || abilityId }}
        </span>
        <span v-if="ability?.nameEn && ability.nameEn !== ability.nameZh"
          class="text-xs text-gray-500 dark:text-gray-400">
          {{ ability.nameEn }}
        </span>
        <span v-if="badge"
          class="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 whitespace-nowrap">
          {{ badge }}
        </span>
      </div>
      <svg class="w-4 h-4 text-gray-400 transition-transform duration-200"
        :class="expanded ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>
    </div>
    <div v-if="expanded" class="px-4 pb-3 animate-slide-up">
      <div v-if="ability?.tooltip"
        class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed pl-3.5 border-l-2 border-gray-300 dark:border-gray-600"
        v-html="parsedTooltip" />
      <div v-else class="text-sm text-gray-400 italic pl-3.5">暂无描述</div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ abilityId: string; badge?: string }>()
const { getAbility } = useAbilityData()
const ability = computed(() => getAbility(props.abilityId))
const expanded = ref(false)
const iconFailed = ref(false)
const parsedTooltip = computed(() =>
  ability.value?.tooltip ? parseDescription(ability.value.tooltip) : ''
)
</script>
