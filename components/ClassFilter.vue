<template>
  <div class="flex flex-col sm:flex-row flex-wrap gap-2 items-stretch sm:items-center p-3 bg-white dark:bg-gray-800 rounded-xl border border-surface-200 dark:border-gray-700">
    <select v-model="team"
      class="border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-surface-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800 transition">
      <option value="All">全部阵营</option>
      <option value="Survivor">生存者</option>
      <option value="Kerrigan">凯瑞甘</option>
    </select>
    <select v-model="category"
      class="border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-surface-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800 transition">
      <option value="All">全部类型</option>
      <option v-for="cat in availableCategories" :key="cat.value" :value="cat.value">{{ cat.label }}</option>
    </select>
    <div class="relative flex-1 min-w-[180px]">
      <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
      </svg>
      <input v-model="search" type="text" placeholder="搜索职业名..."
        class="w-full border border-surface-200 dark:border-gray-600 rounded-lg pl-8 pr-3 py-1.5 text-sm bg-surface-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800 transition" />
    </div>
  </div>
</template>

<script setup lang="ts">
const team = defineModel<string>('team', { default: 'All' })
const category = defineModel<string>('category', { default: 'All' })
const search = defineModel<string>('search', { default: '' })

const categoryMap: Record<string, { value: string; label: string }[]> = {
  All: [
    { value: 'Hunter', label: '猎手' },
    { value: 'Builder', label: '建造者' },
    { value: 'Support', label: '辅助' },
    { value: 'Defender', label: '防御者' },
    { value: 'Random', label: '随机' },
  ],
  Kerrigan: [
    { value: 'Hunter', label: '猎手' },
    { value: 'Defender', label: '防御者' },
  ],
  Survivor: [
    { value: 'Builder', label: '建造者' },
    { value: 'Support', label: '辅助' },
    { value: 'Random', label: '随机' },
  ],
}

const availableCategories = computed(() => categoryMap[team.value] || categoryMap.All)

watch(team, () => {
  const valid = availableCategories.value.some(c => c.value === category.value)
  if (!valid) category.value = 'All'
})
</script>
