<template>
  <div>
    <NuxtLink to="/replays" class="text-sm text-gray-500 hover:text-survivor-600 dark:text-gray-400">← 录像列表</NuxtLink>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1 mb-3">录像回放</h1>

    <div v-if="state === 'loading'" class="text-sm text-gray-400">加载录像数据…</div>
    <div v-else-if="state === 'waiting'" class="text-sm text-gray-500 dark:text-gray-400 inline-flex items-center gap-2">
      <span class="inline-block w-4 h-4 border-2 border-survivor-500 border-t-transparent rounded-full animate-spin" />
      {{ waitText }}
    </div>
    <div v-else-if="state === 'error'" class="text-sm text-kerrigan-600 dark:text-kerrigan-400">{{ errorText }}</div>
    <ReplayViewer v-else-if="data" :data="data" />
  </div>
</template>

<script setup lang="ts">
import type { ReplayData } from '~/utils/replay'

const route = useRoute()
const hash = computed(() => String(route.params.hash).toLowerCase().replace(/[^a-f0-9]/g, ''))
useHead({ title: '录像回放 · 凯瑞甘生存2 Wiki' })

const data = shallowRef<ReplayData | null>(null)
const state = ref<'loading' | 'waiting' | 'ready' | 'error'>('loading')
const errorText = ref('')
const waitText = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

// 录像 JSON 体积较大（gzip 后 ~300KB），只在客户端拉取，不进 SSR payload
async function load() {
  if (timer) clearTimeout(timer)
  state.value = 'loading'
  try {
    const st = await $fetch<{ replay: { status: string; error: string }; ahead: number }>(
      `/api/replays/${hash.value}/status`)
    const s = st.replay.status
    if (s === 'failed') {
      state.value = 'error'
      errorText.value = st.replay.error || '该录像解析失败'
      return
    }
    if (s === 'queued' || s === 'processing') {
      state.value = 'waiting'
      waitText.value = s === 'processing' ? '正在解析录像…' : `排队等待解析${st.ahead ? `（前面还有 ${st.ahead} 个）` : ''}…`
      timer = setTimeout(load, 2000)
      return
    }
    data.value = await $fetch<ReplayData>(`/api/replays/${hash.value}/data`)
    state.value = 'ready'
  } catch (e: any) {
    state.value = 'error'
    errorText.value = e?.statusCode === 404 || e?.data?.statusCode === 404 ? '找不到该录像。' : '加载失败，请刷新重试。'
  }
}
onMounted(load)
watch(hash, load)
onBeforeUnmount(() => { if (timer) clearTimeout(timer) })
</script>
