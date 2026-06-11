<template>
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
    <div v-if="stats.hp" class="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
      <span class="text-red-500 text-sm font-medium">HP</span>
      <span class="text-sm text-gray-700">{{ stats.hp }}</span>
    </div>
    <div v-if="stats.speed" class="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
      <span class="text-green-600 text-sm font-medium">速度</span>
      <span class="text-sm text-gray-700">{{ stats.speed }}</span>
    </div>
    <div v-if="stats.armor" class="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
      <span class="text-yellow-600 text-sm font-medium">护甲</span>
      <span class="text-sm text-gray-700">{{ stats.armor }}</span>
    </div>
    <div v-if="stats.energy" class="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
      <span class="text-blue-500 text-sm font-medium">能量</span>
      <span class="text-sm text-gray-700">{{ stats.energy }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ClassStats } from '~/composables/useClassData'
defineProps<{ stats: ClassStats }>()
</script>
