<template>
  <div class="wk-root">
    <div class="wk-grid" aria-hidden="true"></div>

    <div class="relative max-w-4xl mx-auto py-10 px-4">
      <NuxtLink :to="`/wiki/${slug}`" class="wk-back">‹ 返回文章</NuxtLink>
      <header class="wk-head">
        <div class="wk-kicker">// EDIT&nbsp;HISTORY</div>
        <h1 class="wk-title">{{ page?.title || slug }}</h1>
        <p v-if="page" class="wk-sub">共 {{ revisions.length }} 条历史修订 · 当前由 {{ page.updated_by }} 编辑</p>
      </header>

      <div v-if="!page" class="text-center py-16 text-gray-400 text-sm">页面不存在</div>

      <div v-else class="wk-timeline">
        <!-- 当前版本 -->
        <div class="wk-rev wk-rev-current">
          <div class="wk-rev-row">
            <span class="wk-rev-tag">当前</span>
            <span class="wk-rev-who">{{ page.updated_by }}</span>
            <span class="wk-rev-time">{{ formatDate(page.updated_at) }}</span>
          </div>
        </div>

        <!-- 历史修订（每条 = 一次编辑前的旧内容快照） -->
        <div v-for="rev in revisions" :key="rev.id" class="wk-rev">
          <div class="wk-rev-row" @click="toggle(rev.id)" role="button">
            <svg class="wk-rev-caret" :class="{ open: openId === rev.id }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
            <span class="wk-rev-who">{{ rev.edited_by || '未知' }}</span>
            <span class="wk-rev-title">{{ rev.title }}</span>
            <span class="wk-rev-time">{{ formatDate(rev.created_at) }}</span>
          </div>

          <!-- 展开：并排对比（左=此历史版本 / 右=当前）+ 回滚 -->
          <div v-if="openId === rev.id" class="wk-rev-detail">
            <div v-if="!detail[rev.id]" class="text-xs text-gray-400 py-6 text-center">加载中…</div>
            <template v-else>
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <div class="wk-col-label">此历史版本</div>
                  <div class="wk-col-box">
                    <div class="wk-preview" v-html="renderMd(detail[rev.id].content)" />
                  </div>
                </div>
                <div>
                  <div class="wk-col-label wk-col-label-cur">当前版本</div>
                  <div class="wk-col-box">
                    <div class="wk-preview" v-html="renderMd(page.content)" />
                  </div>
                </div>
              </div>

              <div v-if="isAdmin" class="flex items-center gap-2 mt-3">
                <button @click="restore(rev.id)" :disabled="busy === rev.id"
                  class="text-xs px-4 py-1.5 rounded bg-survivor-500 text-white hover:bg-survivor-600 disabled:opacity-50">
                  {{ busy === rev.id ? '回滚中…' : '回滚到此版本' }}
                </button>
                <span v-if="msg && msgFor === rev.id" class="text-xs" :class="msgOk ? 'text-green-600 dark:text-green-400' : 'text-red-500'">{{ msg }}</span>
              </div>
            </template>
          </div>
        </div>

        <div v-if="!revisions.length" class="text-center py-12 text-gray-400 text-sm">暂无历史修订</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

const route = useRoute()
const slug = route.params.slug as string
const { isAdmin, authHeaders } = useAuth()

const { data: page, refresh: refreshPage } = await useFetch<any>(`/api/wiki/${slug}`)
const { data: hist, refresh: refreshHist } = await useFetch<any>(`/api/wiki/${slug}.history`)
const revisions = computed(() => hist.value?.revisions || [])

const openId = ref<number | null>(null)
const detail = reactive<Record<number, any>>({})
const busy = ref<number | null>(null)
const msg = ref('')
const msgOk = ref(false)
const msgFor = ref<number | null>(null)

function renderMd(src: string) {
  return DOMPurify.sanitize(marked.parse(src || '') as string, { ADD_ATTR: ['id'] })
}

async function toggle(id: number) {
  if (openId.value === id) { openId.value = null; return }
  openId.value = id
  if (!detail[id]) {
    try {
      const res = await $fetch<any>(`/api/wiki/revisions/${id}`)
      detail[id] = res.revision
    } catch {
      openId.value = null
    }
  }
}

async function restore(id: number) {
  const rev = detail[id]
  if (!rev || !page.value) return
  busy.value = id
  msg.value = ''
  msgFor.value = id
  try {
    await $fetch(`/api/wiki/${slug}`, {
      method: 'PUT',
      headers: authHeaders.value,
      body: { title: rev.title, content: rev.content, category: page.value.category },
    })
    msgOk.value = true
    msg.value = '已回滚，页面已更新'
    await Promise.all([refreshPage(), refreshHist()])
    openId.value = null
  } catch (e: any) {
    msgOk.value = false
    msg.value = e?.data?.message || '回滚失败'
  } finally {
    busy.value = null
  }
}

function formatDate(d: string) {
  return new Date(d.replace(' ', 'T') + 'Z').toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
}
</script>

<style scoped>
.wk-root { position: relative; min-height: 100%; overflow: hidden; }
.wk-grid {
  position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(to right, rgba(37,99,235,0.045) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(37,99,235,0.045) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: radial-gradient(ellipse 75% 50% at 50% 0%, #000 25%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse 75% 50% at 50% 0%, #000 25%, transparent 80%);
}
.dark .wk-grid {
  background-image:
    linear-gradient(to right, rgba(96,165,250,0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(96,165,250,0.06) 1px, transparent 1px);
}

.wk-back {
  display: inline-block; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
  letter-spacing: 0.1em; color: #6b7280; margin-bottom: 1.2rem; transition: color 0.15s;
}
.wk-back:hover { color: #2563eb; }
.dark .wk-back:hover { color: #60a5fa; }

.wk-head { margin-bottom: 1.6rem; padding-bottom: 1.1rem; border-bottom: 1px solid #e5e7eb; }
.dark .wk-head { border-color: #374151; }
.wk-kicker {
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: #2563eb; margin-bottom: 0.6rem;
}
.dark .wk-kicker { color: #60a5fa; }
.wk-title {
  font-family: 'JetBrains Mono', monospace; font-weight: 500;
  font-size: clamp(1.6rem, 4vw, 2.4rem); line-height: 1.1; letter-spacing: -0.02em; color: #111827;
}
.dark .wk-title { color: #f3f4f6; }
.wk-sub { margin-top: 0.7rem; font-size: 0.78rem; color: #9ca3af; font-family: 'JetBrains Mono', monospace; }

.wk-timeline { display: flex; flex-direction: column; gap: 0.5rem; }
.wk-rev {
  background: #fff; border: 1px solid #e5e7eb;
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%);
}
.dark .wk-rev { background: #1f2937; border-color: #374151; }
.wk-rev-current { border-color: #93c5fd; }
.dark .wk-rev-current { border-color: #3b82f6; }

.wk-rev-row {
  display: flex; align-items: center; gap: 0.6rem; padding: 0.7rem 0.95rem;
  font-size: 0.82rem; cursor: pointer; flex-wrap: wrap;
}
.wk-rev-current .wk-rev-row { cursor: default; }
.wk-rev-caret {
  width: 0.9rem; height: 0.9rem; color: #9ca3af; flex-shrink: 0; transition: transform 0.15s;
}
.wk-rev-caret.open { transform: rotate(90deg); }
.wk-rev-tag {
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.05em;
  padding: 1px 7px; background: rgba(37,99,235,0.1); color: #2563eb; margin-left: 1.5rem;
}
.dark .wk-rev-tag { background: rgba(96,165,250,0.15); color: #60a5fa; }
.wk-rev-who { font-weight: 600; color: #111827; }
.dark .wk-rev-who { color: #f3f4f6; }
.wk-rev-title { color: #6b7280; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wk-rev-time {
  margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #9ca3af; flex-shrink: 0;
}

.wk-rev-detail { border-top: 1px solid #e5e7eb; padding: 1rem 0.95rem; }
.dark .wk-rev-detail { border-color: #374151; }
.wk-col-label {
  font-size: 0.72rem; font-weight: 500; color: #6b7280; margin-bottom: 0.4rem;
}
.wk-col-label-cur { color: #2563eb; }
.dark .wk-col-label-cur { color: #60a5fa; }
.wk-col-box {
  border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 0.75rem 1rem;
  max-height: 26rem; overflow: auto; background: #fff;
}
.dark .wk-col-box { border-color: #374151; background: #111827; }
</style>
