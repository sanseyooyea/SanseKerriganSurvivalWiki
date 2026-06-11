<template>
  <div class="cl-root">
    <!-- 背景纹理层 -->
    <div class="cl-grid" aria-hidden="true"></div>
    <div class="cl-scan" aria-hidden="true"></div>

    <div class="relative max-w-3xl mx-auto py-10 px-4">
      <!-- 头部 -->
      <header class="mb-10">
        <div class="cl-kicker">// PATCH&nbsp;LOG &nbsp;·&nbsp; 版本更新记录</div>
        <h1 class="cl-title">更新<span class="cl-title-accent">日志</span></h1>
        <div class="cl-meta">
          <span class="cl-meta-dot"></span>
          数据中继 ·
          <a href="https://194823.xyz" target="_blank" rel="noopener" class="cl-link">194823.xyz</a>
          <template v-if="total"> &nbsp;·&nbsp; 共 <span class="cl-num">{{ total }}</span> 个版本</template>
        </div>
      </header>

      <div v-if="loading" class="cl-status">
        <span class="cl-blink">▮</span> 正在拉取版本数据...
      </div>
      <div v-else-if="error" class="cl-status cl-status-err">! {{ error }}</div>

      <!-- 版本时间线 -->
      <div v-else class="cl-timeline">
        <div
          v-for="(item, i) in items"
          :key="item.version + item.date"
          class="cl-entry stagger-item"
          :style="{ animationDelay: i * 45 + 'ms' }"
        >
          <!-- 时间线节点 -->
          <div class="cl-node-col">
            <div class="cl-node" :class="{ 'cl-node-latest': page === 1 && i === 0 }"></div>
            <div class="cl-line" v-if="i < items.length - 1"></div>
          </div>

          <!-- 内容卡片 -->
          <div class="cl-card">
            <div class="cl-card-head">
              <div class="cl-ver">
                <span class="cl-ver-tag">VER</span>
                <span class="cl-ver-num">{{ item.version }}</span>
                <span v-if="page === 1 && i === 0" class="cl-latest">LATEST</span>
              </div>
              <time class="cl-date">{{ item.date }}</time>
            </div>
            <div class="cl-notes">{{ joinNotes(item.notes) }}</div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <nav v-if="!loading && !error && totalPages > 1" class="cl-pager">
        <button @click="go(page - 1)" :disabled="page <= 1" class="cl-pg-btn">‹ 上一页</button>
        <span class="cl-pg-ind"><span class="cl-num">{{ page }}</span> / {{ totalPages }}</span>
        <button @click="go(page + 1)" :disabled="page >= totalPages" class="cl-pg-btn">下一页 ›</button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
const PAGE_SIZE = 20
const items = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const error = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function joinNotes(notes: string[]) {
  return (notes || []).join('').trim()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await $fetch<any>(`/api/patchnotes?page=${page.value}&page_size=${PAGE_SIZE}`)
    items.value = res.items || []
    total.value = res.total || 0
  } catch {
    error.value = '无法获取更新日志，请稍后再试'
    items.value = []
  } finally {
    loading.value = false
  }
}

function go(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
  load()
}

onMounted(load)
</script>

<style scoped>
.cl-root {
  position: relative;
  min-height: 100%;
  overflow: hidden;
}
/* 网格底纹 */
.cl-grid {
  position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(to right, rgba(37,99,235,0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(37,99,235,0.05) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 80%);
}
.cl-scan {
  position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background: linear-gradient(180deg, rgba(37,99,235,0.06), transparent 220px);
}
.dark .cl-grid {
  background-image:
    linear-gradient(to right, rgba(96,165,250,0.07) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(96,165,250,0.07) 1px, transparent 1px);
}
.dark .cl-scan {
  background: linear-gradient(180deg, rgba(59,130,246,0.1), transparent 220px);
}

/* 头部 */
.cl-kicker {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem; letter-spacing: 0.18em; text-transform: uppercase;
  color: #2563eb; margin-bottom: 0.6rem;
}
.dark .cl-kicker { color: #60a5fa; }
.cl-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: clamp(2.2rem, 6vw, 3.4rem); font-weight: 500; line-height: 0.95;
  letter-spacing: -0.02em; color: #111827;
}
.dark .cl-title { color: #f3f4f6; }
.cl-title-accent { color: #2563eb; }
.dark .cl-title-accent { color: #60a5fa; }
.cl-meta {
  margin-top: 0.9rem; font-size: 0.82rem; color: #6b7280;
  display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap;
}
.cl-meta-dot {
  width: 7px; height: 7px; border-radius: 999px; background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34,197,94,0.18); animation: clPulse 2s ease-in-out infinite;
}
@keyframes clPulse { 0%,100% { opacity: 1 } 50% { opacity: 0.4 } }
.cl-link { color: #2563eb; font-family: 'JetBrains Mono', monospace; }
.cl-link:hover { text-decoration: underline; }
.dark .cl-link { color: #60a5fa; }
.cl-num { font-family: 'JetBrains Mono', monospace; font-weight: 500; color: #111827; }
.dark .cl-num { color: #f3f4f6; }

.cl-status {
  font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
  color: #6b7280; padding: 3rem 0; text-align: center;
}
.cl-status-err { color: #dc2626; }
.dark .cl-status-err { color: #f87171; }
.cl-blink { animation: clBlink 1s steps(1) infinite; color: #2563eb; }
@keyframes clBlink { 50% { opacity: 0 } }

/* 时间线 */
.cl-timeline { position: relative; }
.cl-entry { display: flex; gap: 1.1rem; }
.cl-node-col {
  display: flex; flex-direction: column; align-items: center;
  flex-shrink: 0; width: 14px; padding-top: 0.4rem;
}
.cl-node {
  width: 12px; height: 12px; flex-shrink: 0;
  background: #2563eb; transform: rotate(45deg);
  box-shadow: 0 0 0 4px rgba(37,99,235,0.12);
}
.dark .cl-node { background: #60a5fa; box-shadow: 0 0 0 4px rgba(96,165,250,0.15); }
.cl-node-latest {
  background: #dc2626; box-shadow: 0 0 0 4px rgba(220,38,38,0.18);
  animation: clPulse 1.6s ease-in-out infinite;
}
.dark .cl-node-latest { background: #f87171; box-shadow: 0 0 0 4px rgba(248,113,113,0.2); }
.cl-line {
  width: 2px; flex: 1; min-height: 1.4rem; margin-top: 4px;
  background: linear-gradient(to bottom, rgba(37,99,235,0.4), rgba(37,99,235,0.08));
}
.dark .cl-line { background: linear-gradient(to bottom, rgba(96,165,250,0.4), rgba(96,165,250,0.06)); }

/* 卡片（切角） */
.cl-card {
  flex: 1; margin-bottom: 1.1rem; padding: 1.1rem 1.25rem;
  background: #fff; border: 1px solid #e5e7eb;
  clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
  transition: border-color 0.2s, transform 0.2s;
}
.cl-card:hover { border-color: #93c5fd; transform: translateX(2px); }
.dark .cl-card { background: #1f2937; border-color: #374151; }
.dark .cl-card:hover { border-color: #3b82f6; }
.cl-card-head {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.7rem;
  padding-bottom: 0.6rem; border-bottom: 1px dashed #e5e7eb;
}
.dark .cl-card-head { border-color: #374151; }
.cl-ver { display: flex; align-items: baseline; gap: 0.5rem; }
.cl-ver-tag {
  font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
  letter-spacing: 0.1em; color: #9ca3af; align-self: center;
  border: 1px solid currentColor; padding: 1px 4px; border-radius: 2px;
}
.cl-ver-num {
  font-family: 'JetBrains Mono', monospace; font-size: 1.45rem; font-weight: 500;
  color: #2563eb; line-height: 1; letter-spacing: -0.01em;
}
.dark .cl-ver-num { color: #60a5fa; }
.cl-latest {
  font-family: 'JetBrains Mono', monospace; font-size: 0.58rem; letter-spacing: 0.12em;
  background: #dc2626; color: #fff; padding: 2px 6px; align-self: center;
}
.dark .cl-latest { background: #f87171; color: #111827; }
.cl-date {
  font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #9ca3af;
}
.cl-notes {
  font-size: 0.875rem; line-height: 1.7; color: #374151;
  white-space: pre-wrap; word-break: break-word;
}
.dark .cl-notes { color: #d1d5db; }

/* 分页 */
.cl-pager {
  display: flex; align-items: center; justify-content: center;
  gap: 1.25rem; margin-top: 2rem;
}
.cl-pg-btn {
  font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
  padding: 0.5rem 1rem; border: 1px solid #d1d5db; background: #fff; color: #374151;
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  transition: all 0.18s;
}
.cl-pg-btn:hover:not(:disabled) { border-color: #2563eb; color: #2563eb; }
.cl-pg-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.dark .cl-pg-btn { background: #1f2937; border-color: #374151; color: #d1d5db; }
.dark .cl-pg-btn:hover:not(:disabled) { border-color: #60a5fa; color: #60a5fa; }
.cl-pg-ind {
  font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #6b7280;
}

@media (max-width: 640px) {
  .cl-card { padding: 0.9rem 1rem; }
  .cl-ver-num { font-size: 1.2rem; }
}
</style>



