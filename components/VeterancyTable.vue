<template>
  <div v-if="vet" class="bg-gray-50 rounded-lg p-4">
    <h3 class="text-sm font-medium text-gray-700 mb-3">属性成长 (每级)</h3>
    <div class="grid grid-cols-3 gap-4 text-center">
      <div>
        <div class="text-lg font-bold text-red-600">+{{ vet.str }}</div>
        <div class="text-xs text-gray-500">力量 STR</div>
      </div>
      <div>
        <div class="text-lg font-bold text-green-600">+{{ vet.agi }}</div>
        <div class="text-xs text-gray-500">敏捷 AGI</div>
      </div>
      <div>
        <div class="text-lg font-bold text-blue-600">+{{ vet.int }}</div>
        <div class="text-xs text-gray-500">智力 INT</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ heroName: string }>()
const { getForHero } = useVeterancyData()
const vet = computed(() => getForHero(props.heroName))
</script>
