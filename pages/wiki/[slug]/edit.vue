<template>
  <ClientOnly>
    <div v-if="!canEdit" class="text-center py-20">
      <p class="text-gray-400 text-lg">需要编辑者权限</p>
      <NuxtLink to="/login" class="text-survivor-600 hover:underline mt-2 inline-block">登录</NuxtLink>
    </div>
    <div v-else>
    <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">
      {{ isNew ? '新建页面' : `编辑：${title}` }}
    </h1>
    <div class="space-y-4 mb-4">
      <input v-model="title" placeholder="页面标题"
        class="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-300" />
      <div class="flex gap-2">
        <input v-model="slugInput" placeholder="URL标识 (英文)" :disabled="!isNew"
          class="flex-1 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-300 disabled:opacity-50" />
        <input v-model="category" placeholder="分类 (可选)"
          class="w-40 border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-2 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-300" />
      </div>
    </div>
<!-- PLACEHOLDER_EDITOR_BODY -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div>
        <label class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">Markdown</label>
        <textarea v-model="content" rows="20"
          class="w-full border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-3 text-sm font-mono bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-300 resize-y" />
      </div>
      <div>
        <label class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1 block">预览</label>
        <div class="border border-gray-200 dark:border-gray-600 rounded-lg px-4 py-3 min-h-[20rem] overflow-auto bg-white dark:bg-gray-800">
          <div class="wk-preview" v-html="preview" />
        </div>
      </div>
    </div>
    <div class="flex items-center gap-3 mt-4">
      <button @click="save" :disabled="saving"
        class="px-5 py-2 text-sm font-medium text-white bg-survivor-600 rounded-lg hover:bg-survivor-700 disabled:opacity-50 transition">
        {{ saving ? '保存中...' : '保存' }}
      </button>
      <span v-if="error" class="text-sm text-red-500">{{ error }}</span>
      <span v-if="saved" class="text-sm text-green-600">已保存</span>
    </div>
  </div>
  </ClientOnly>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

const route = useRoute()
const router = useRouter()
const paramSlug = route.params.slug as string
const isNew = paramSlug === 'new'
const { canEdit, authHeaders } = useAuth()

const title = ref('')
const slugInput = ref(isNew ? '' : paramSlug)
const category = ref('')
const content = ref('')
const saving = ref(false)
const error = ref('')
const saved = ref(false)

if (!isNew) {
  const { data } = await useFetch(`/api/wiki/${paramSlug}`)
  if (data.value) {
    title.value = data.value.title || ''
    content.value = data.value.content || ''
    category.value = data.value.category || ''
  }
}

const preview = computed(() => content.value ? DOMPurify.sanitize(marked.parse(content.value) as string) : '<span class="text-gray-400">输入Markdown内容...</span>')

async function save() {
  const slug = slugInput.value.trim()
  if (!slug || !title.value.trim()) {
    error.value = '标题和URL标识不能为空'
    return
  }
  saving.value = true
  error.value = ''
  saved.value = false
  try {
    await $fetch(`/api/wiki/${slug}`, {
      method: 'PUT',
      headers: authHeaders.value,
      body: { title: title.value, content: content.value, category: category.value || undefined },
    })
    saved.value = true
    if (isNew) {
      router.push(`/wiki/${slug}`)
    }
  } catch (e: any) {
    error.value = e.data?.message || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>
