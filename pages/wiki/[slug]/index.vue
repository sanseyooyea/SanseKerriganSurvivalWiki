<template>
  <div v-if="page">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ page.title }}</h1>
      <NuxtLink v-if="canEdit" :to="`/wiki/${slug}/edit`"
        class="px-3 py-1.5 text-sm font-medium text-survivor-700 dark:text-survivor-300 border border-survivor-300 dark:border-survivor-700 rounded-lg hover:bg-survivor-50 dark:hover:bg-survivor-900/30 transition">
        编辑
      </NuxtLink>
    </div>
    <div class="wiki-card p-6 mb-6">
      <div class="prose prose-sm dark:prose-invert max-w-none" v-html="rendered" />
    </div>
    <div class="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-2">
      <span>最后编辑：{{ page.updated_by }}</span>
      <span>·</span>
      <span>{{ formatDate(page.updated_at) }}</span>
    </div>
  </div>
  <div v-else class="text-center py-20">
    <p class="text-gray-400 text-lg mb-3">页面不存在</p>
    <NuxtLink v-if="canEdit" :to="`/wiki/${slug}/edit`"
      class="text-survivor-600 hover:underline">创建此页面</NuxtLink>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

const route = useRoute()
const slug = route.params.slug as string
const { canEdit } = useAuth()

const { data: page } = await useFetch(`/api/wiki/${slug}`)

const rendered = computed(() => {
  if (!page.value?.content) return ''
  return DOMPurify.sanitize(marked.parse(page.value.content) as string)
})

function formatDate(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}
</script>
