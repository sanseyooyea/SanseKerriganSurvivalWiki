<template>
  <div class="wl-root">
    <div class="wl-grid" aria-hidden="true"></div>

    <div class="relative max-w-4xl mx-auto py-10 px-4">
      <!-- 头部 -->
      <header class="wl-head">
        <div class="wl-kicker">// KNOWLEDGE&nbsp;BASE</div>
        <div class="wl-head-row">
          <h1 class="wl-title">WIKI<span class="wl-title-accent">.</span></h1>
          <NuxtLink v-if="isLoggedIn" to="/wiki/new/edit" class="wl-new">{{ isAdmin ? '+ 新建页面' : '+ 提议新建' }}</NuxtLink>
        </div>
        <p class="wl-sub">凯瑞甘生存2 社区知识库 · 共 {{ pages?.length || 0 }} 篇</p>
      </header>

      <!-- 文章列表 -->
      <div v-if="pages?.length" class="wl-list">
        <NuxtLink
          v-for="(page, i) in pages" :key="page.slug" :to="`/wiki/${page.slug}`"
          class="wl-item stagger-item" :style="{ animationDelay: Math.min(i, 12) * 40 + 'ms' }">
          <div class="wl-item-rail"></div>
          <div class="wl-item-body">
            <div class="wl-item-top">
              <span v-if="page.category" class="wl-cat">{{ page.category }}</span>
              <h2 class="wl-item-title">{{ page.title }}</h2>
            </div>
            <div class="wl-item-meta">
              <span class="wl-slug">/{{ page.slug }}</span>
              <span class="wl-dot">·</span>
              <span>{{ page.updated_by }}</span>
              <span class="wl-dot">·</span>
              <span>{{ formatDate(page.updated_at) }}</span>
            </div>
          </div>
          <span class="wl-arrow">→</span>
        </NuxtLink>
      </div>

      <div v-else class="wl-empty">
        <div class="wl-kicker">// EMPTY</div>
        <p>暂无 Wiki 页面</p>
        <NuxtLink v-if="isLoggedIn" to="/wiki/new/edit" class="wl-new">{{ isAdmin ? '创建第一篇' : '提议新建' }}</NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { isLoggedIn, isAdmin } = useAuth()
const { data: pages } = await useFetch('/api/wiki')

function formatDate(d: string) {
  return new Date(d.replace(' ', 'T') + 'Z').toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.wl-root { position: relative; min-height: 100%; overflow: hidden; }
.wl-grid {
  position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(to right, rgba(37,99,235,0.045) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(37,99,235,0.045) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: radial-gradient(ellipse 80% 50% at 50% 0%, #000 25%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse 80% 50% at 50% 0%, #000 25%, transparent 80%);
}
.dark .wl-grid {
  background-image:
    linear-gradient(to right, rgba(96,165,250,0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(96,165,250,0.06) 1px, transparent 1px);
}

.wl-head { margin-bottom: 2rem; }
.wl-kicker {
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: #2563eb; margin-bottom: 0.6rem;
}
.dark .wl-kicker { color: #60a5fa; }
.wl-head-row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
.wl-title {
  font-family: 'JetBrains Mono', monospace; font-weight: 500;
  font-size: clamp(2.2rem, 6vw, 3.2rem); line-height: 1; letter-spacing: -0.02em; color: #111827;
}
.dark .wl-title { color: #f3f4f6; }
.wl-title-accent { color: #2563eb; }
.dark .wl-title-accent { color: #60a5fa; }
.wl-sub { margin-top: 0.8rem; font-size: 0.82rem; color: #6b7280; font-family: 'JetBrains Mono', monospace; }

.wl-new {
  font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; padding: 0.5rem 1rem;
  background: #2563eb; color: #fff; transition: background 0.15s; flex-shrink: 0;
  clip-path: polygon(7px 0, 100% 0, 100% calc(100% - 7px), calc(100% - 7px) 100%, 0 100%, 0 7px);
}
.wl-new:hover { background: #1d4ed8; }
.dark .wl-new { background: #3b82f6; }
.dark .wl-new:hover { background: #60a5fa; }

.wl-list { display: flex; flex-direction: column; gap: 0.7rem; }
.wl-item {
  display: flex; align-items: stretch; gap: 0; background: #fff; border: 1px solid #e5e7eb;
  clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
  transition: border-color 0.2s, transform 0.2s;
}
.wl-item:hover { transform: translateX(3px); border-color: #93c5fd; }
.dark .wl-item { background: #1f2937; border-color: #374151; }
.dark .wl-item:hover { border-color: #3b82f6; }
.wl-item-rail { width: 3px; flex-shrink: 0; background: linear-gradient(#2563eb, #dc2626); opacity: 0.7; }
.wl-item-body { flex: 1; min-width: 0; padding: 0.95rem 1.1rem; }
.wl-item-top { display: flex; align-items: baseline; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 0.35rem; }
.wl-cat {
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.05em;
  padding: 2px 7px; background: rgba(37,99,235,0.1); color: #2563eb; flex-shrink: 0;
}
.dark .wl-cat { background: rgba(96,165,250,0.15); color: #60a5fa; }
.wl-item-title { font-weight: 600; font-size: 1.02rem; color: #111827; }
.dark .wl-item-title { color: #f3f4f6; }
.wl-item-meta {
  display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap;
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #9ca3af;
}
.wl-slug { color: #2563eb; }
.dark .wl-slug { color: #60a5fa; }
.wl-dot { opacity: 0.5; }
.wl-arrow {
  display: flex; align-items: center; padding: 0 1.1rem; color: #cbd5e1;
  font-size: 1.1rem; transition: color 0.2s, transform 0.2s;
}
.wl-item:hover .wl-arrow { color: #2563eb; transform: translateX(3px); }
.dark .wl-arrow { color: #4b5563; }
.dark .wl-item:hover .wl-arrow { color: #60a5fa; }

.wl-empty {
  text-align: center; padding: 4rem 0; color: #9ca3af;
  display: flex; flex-direction: column; align-items: center; gap: 0.8rem;
}
</style>
