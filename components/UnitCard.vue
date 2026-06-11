<template>
  <div class="rounded-lg border overflow-hidden transition-all"
    :class="[
      expanded
        ? 'bg-gray-50 dark:bg-gray-900 border-gray-300 dark:border-gray-600'
        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
    ]">
    <div class="flex items-center justify-between px-3 py-2 cursor-pointer select-none"
      @click="expanded = !expanded">
      <div class="flex items-center gap-2">
        <div class="w-1.5 h-1.5 rounded-full" :class="isBuilding ? 'bg-amber-500' : 'bg-green-500'" />
        <span class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ unit.nameZh || unit.id }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="unit.hp" class="text-xs font-mono text-gray-400">{{ unit.hp }}</span>
        <svg class="w-3.5 h-3.5 text-gray-400 transition-transform duration-200"
          :class="expanded ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </div>
    </div>
    <div v-if="expanded" class="px-3 pb-3 animate-slide-up">
      <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs pl-3.5 border-l-2 border-gray-300 dark:border-gray-600">
        <div v-if="unit.hp" class="flex justify-between">
          <span class="text-gray-500">生命值</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.hp }}</span>
        </div>
        <div v-if="unit.shield" class="flex justify-between">
          <span class="text-gray-500">护盾</span>
          <span class="font-mono text-blue-600 dark:text-blue-400">{{ unit.shield }}</span>
        </div>
        <div v-if="unit.armor" class="flex justify-between">
          <span class="text-gray-500">护甲</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.armor }}</span>
        </div>
        <div v-if="unit.speed" class="flex justify-between">
          <span class="text-gray-500">移速</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.speed }}</span>
        </div>
        <div v-if="unit.damage" class="flex justify-between">
          <span class="text-gray-500">伤害</span>
          <span class="font-mono text-red-600 dark:text-red-400">{{ unit.damage }}</span>
        </div>
        <div v-if="unit.attackSpeed" class="flex justify-between">
          <span class="text-gray-500">攻击间隔</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.attackSpeed }}s</span>
        </div>
        <div v-if="unit.range" class="flex justify-between">
          <span class="text-gray-500">射程</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.range }}</span>
        </div>
      </div>
      <NuxtLink :to="`/units/${unit.id}`"
        class="inline-flex items-center gap-1 mt-2 ml-3.5 text-xs text-survivor-600 dark:text-survivor-400 hover:underline">
        查看详情
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
        </svg>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  unit: { id: string; nameZh: string; hp?: number; shield?: number; armor?: number; speed?: number; damage?: number; attackSpeed?: number; range?: number }
  isBuilding?: boolean
}>()
const expanded = ref(false)
</script>
