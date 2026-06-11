<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">职业列表</h1>
    <ClassFilter v-model:team="team" v-model:category="category" v-model:search="search" />
    <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      <ClassCard v-for="(cls, i) in filtered" :key="cls.id" :data="cls" class="stagger-item" />
    </div>
    <p v-if="filtered.length === 0" class="mt-8 text-center text-gray-500 dark:text-gray-400">
      没有匹配的职业
    </p>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { classes } = useClassData()

const team = ref((route.query.team as string) || 'All')
const category = ref((route.query.category as string) || 'All')
const search = ref('')

const filtered = computed(() => {
  return classes.filter(c => {
    if (team.value !== 'All' && c.team !== team.value) return false
    if (category.value !== 'All' && c.category !== category.value) return false
    if (search.value) {
      const q = search.value.toLowerCase()
      return c.nameEn.toLowerCase().includes(q) ||
        (c.nameZh && c.nameZh.toLowerCase().includes(q))
    }
    return true
  })
})
</script>
