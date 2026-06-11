<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Wiki 页面</h1>
      <NuxtLink v-if="canEdit" to="/wiki/new/edit"
        class="px-4 py-2 text-sm font-medium text-white bg-survivor-600 rounded-lg hover:bg-survivor-700 transition">
        新建页面
      </NuxtLink>
    </div>
    <div v-if="pages?.length" class="space-y-2">
      <NuxtLink v-for="page in pages" :key="page.slug" :to="`/wiki/${page.slug}`"
        class="wiki-card block p-4 hover:shadow-card-hover transition">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">{{ page.title }}</h2>
            <span v-if="page.category" class="text-xs text-gray-500 dark:text-gray-400">{{ page.category }}</span>
          </div>
          <div class="text-xs text-gray-400 dark:text-gray-500 text-right">
            <div>{{ page.updated_by }}</div>
            <div>{{ formatDate(page.updated_at) }}</div>
          </div>
        </div>
      </NuxtLink>
    </div>
    <p v-else class="text-center text-gray-400 dark:text-gray-500 py-12">
      暂无Wiki页面
      <NuxtLink v-if="canEdit" to="/wiki/new/edit" class="text-survivor-600 hover:underline ml-1">创建第一个</NuxtLink>
    </p>
  </div>
</template>

<script setup lang="ts">
const { canEdit } = useAuth()
const { data: pages } = await useFetch('/api/wiki')

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('zh-CN')
}
</script>
