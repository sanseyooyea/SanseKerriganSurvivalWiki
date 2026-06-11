<template>
  <div class="wk-root">
    <div class="wk-grid" aria-hidden="true"></div>

    <div v-if="page" class="relative max-w-5xl mx-auto py-10 px-4">
      <!-- 返回 + 头部 -->
      <NuxtLink to="/wiki" class="wk-back">‹ 返回 WIKI</NuxtLink>
      <header class="wk-head">
        <div class="wk-kicker">
          // WIKI&nbsp;ENTRY<template v-if="page.category"> &nbsp;·&nbsp; {{ page.category }}</template>
        </div>
        <h1 class="wk-title">{{ page.title }}</h1>
        <div class="wk-meta">
          <span class="wk-meta-dot"></span>
          最后编辑 {{ page.updated_by }} · {{ formatDate(page.updated_at) }}
          <NuxtLink v-if="canEdit" :to="`/wiki/${slug}/edit`" class="wk-edit">编辑本页</NuxtLink>
        </div>
      </header>

      <div class="wk-layout">
        <!-- 目录 -->
        <aside v-if="headings.length" class="wk-toc">
          <div class="wk-toc-title">目录 / TOC</div>
          <nav>
            <a v-for="h in headings" :key="h.id" :href="`#${h.id}`"
              class="wk-toc-link" :class="'wk-toc-l' + h.level"
              @click.prevent="scrollTo(h.id)">{{ h.text }}</a>
          </nav>
        </aside>

        <!-- 正文 -->
        <article class="wk-article" v-html="rendered" />
      </div>
    </div>

    <div v-else class="relative max-w-3xl mx-auto py-24 px-4 text-center">
      <div class="wk-kicker">// 404</div>
      <p class="wk-404">页面不存在</p>
      <NuxtLink v-if="canEdit" :to="`/wiki/${slug}/edit`" class="wk-edit">创建此页面</NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

const route = useRoute()
const slug = route.params.slug as string
const { canEdit } = useAuth()

const { data: page } = await useFetch(`/api/wiki/${slug}`)

// 解析 Markdown，给 h2/h3 注入锚点 id 并提取目录
const parsed = computed(() => {
  if (!page.value?.content) return { html: '', headings: [] as any[] }
  let html = marked.parse(page.value.content) as string
  const headings: any[] = []
  html = html.replace(/<h([234])>([\s\S]*?)<\/h\1>/g, (_m, lvl, inner) => {
    const text = inner.replace(/<[^>]+>/g, '').trim()
    const id = 'h-' + headings.length
    headings.push({ level: Number(lvl), text, id })
    return `<h${lvl} id="${id}">${inner}</h${lvl}>`
  })
  return { html: DOMPurify.sanitize(html, { ADD_ATTR: ['id'] }), headings }
})
const rendered = computed(() => parsed.value.html)
const headings = computed(() => parsed.value.headings)

function scrollTo(id: string) {
  const el = document.getElementById(id)
  if (el) {
    const y = el.getBoundingClientRect().top + window.scrollY - 80
    window.scrollTo({ top: y, behavior: 'smooth' })
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

.wk-head { margin-bottom: 2rem; padding-bottom: 1.3rem; border-bottom: 1px solid #e5e7eb; }
.dark .wk-head { border-color: #374151; }
.wk-kicker {
  font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: #2563eb; margin-bottom: 0.6rem;
}
.dark .wk-kicker { color: #60a5fa; }
.wk-title {
  font-family: 'JetBrains Mono', monospace; font-weight: 500;
  font-size: clamp(1.9rem, 5vw, 2.9rem); line-height: 1.05; letter-spacing: -0.02em; color: #111827;
}
.dark .wk-title { color: #f3f4f6; }
.wk-meta {
  margin-top: 0.9rem; font-size: 0.78rem; color: #9ca3af;
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
}
.wk-meta-dot {
  width: 6px; height: 6px; border-radius: 999px; background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34,197,94,0.18);
}
.wk-edit {
  font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #2563eb;
  border: 1px solid currentColor; padding: 2px 8px; margin-left: 0.3rem; transition: all 0.15s;
}
.wk-edit:hover { background: #2563eb; color: #fff; }
.dark .wk-edit { color: #60a5fa; }
.dark .wk-edit:hover { background: #3b82f6; color: #fff; }
.wk-404 { font-size: 1.1rem; color: #6b7280; margin: 1rem 0 1.5rem; }

/* 布局：目录 + 正文 */
.wk-layout { display: grid; grid-template-columns: 1fr; gap: 2rem; }
@media (min-width: 1024px) {
  .wk-layout { grid-template-columns: 13rem 1fr; align-items: start; }
}
.wk-toc {
  display: none;
}
@media (min-width: 1024px) {
  .wk-toc {
    display: block; position: sticky; top: 5rem; align-self: start;
    border-left: 2px solid #e5e7eb; padding-left: 1rem; min-width: 0;
  }
  .dark .wk-toc { border-color: #374151; }
}
.wk-toc-title {
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.14em;
  text-transform: uppercase; color: #9ca3af; margin-bottom: 0.7rem;
}
.wk-toc-link {
  display: block; font-size: 0.78rem; line-height: 1.5; color: #6b7280;
  padding: 0.2rem 0; transition: color 0.15s; cursor: pointer;
  overflow-wrap: anywhere; word-break: break-word;
}
.wk-toc-link:hover { color: #2563eb; }
.dark .wk-toc-link { color: #9ca3af; }
.dark .wk-toc-link:hover { color: #60a5fa; }
.wk-toc-l3 { padding-left: 0.8rem; font-size: 0.74rem; }
.wk-toc-l4 { padding-left: 1.6rem; font-size: 0.72rem; }

/* ===== 文章正文排版（替代失效的 prose 类，自定义终端手册风格）===== */
.wk-article {
  min-width: 0; font-size: 0.94rem; line-height: 1.75;
  color: #374151; word-wrap: break-word;
}
.dark .wk-article { color: #d1d5db; }

/* 标题 */
.wk-article :deep(h1),
.wk-article :deep(h2),
.wk-article :deep(h3),
.wk-article :deep(h4) {
  font-family: 'JetBrains Mono', monospace; font-weight: 500;
  color: #111827; line-height: 1.25; scroll-margin-top: 5rem;
}
.dark .wk-article :deep(h1),
.dark .wk-article :deep(h2),
.dark .wk-article :deep(h3),
.dark .wk-article :deep(h4) { color: #f3f4f6; }
.wk-article :deep(h1) { font-size: 1.6rem; margin: 2rem 0 1rem; }
.wk-article :deep(h2) {
  font-size: 1.3rem; margin: 2.2rem 0 1rem; padding-bottom: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
  position: relative; padding-left: 1rem;
}
.wk-article :deep(h2)::before {
  content: ''; position: absolute; left: 0; top: 0.15em; bottom: 0.5em; width: 3px;
  background: linear-gradient(#2563eb, #dc2626);
}
.dark .wk-article :deep(h2) { border-color: #374151; }
.wk-article :deep(h3) { font-size: 1.08rem; margin: 1.6rem 0 0.7rem; color: #2563eb; }
.dark .wk-article :deep(h3) { color: #60a5fa; }
.wk-article :deep(h4) { font-size: 0.95rem; margin: 1.2rem 0 0.5rem; }

/* 段落与强调 */
.wk-article :deep(p) { margin: 0.85rem 0; }
.wk-article :deep(strong) { color: #111827; font-weight: 600; }
.dark .wk-article :deep(strong) { color: #f3f4f6; }
.wk-article :deep(em) { color: #2563eb; font-style: normal; }
.dark .wk-article :deep(em) { color: #60a5fa; }

/* 链接 */
.wk-article :deep(a) {
  color: #2563eb; text-decoration: none; border-bottom: 1px solid rgba(37,99,235,0.3);
  transition: border-color 0.15s;
}
.wk-article :deep(a:hover) { border-bottom-color: #2563eb; }
.dark .wk-article :deep(a) { color: #60a5fa; border-bottom-color: rgba(96,165,250,0.3); }

/* 列表 */
.wk-article :deep(ul),
.wk-article :deep(ol) { margin: 0.85rem 0; padding-left: 1.5rem; }
.wk-article :deep(li) { margin: 0.4rem 0; }
.wk-article :deep(ul) { list-style: none; }
.wk-article :deep(ul > li) { position: relative; }
.wk-article :deep(ul > li)::before {
  content: '▸'; position: absolute; left: -1.3rem; color: #2563eb; font-size: 0.85em;
}
.dark .wk-article :deep(ul > li)::before { color: #60a5fa; }
.wk-article :deep(ol) { list-style: decimal; }
.wk-article :deep(ol > li)::marker { color: #2563eb; font-family: 'JetBrains Mono', monospace; }
.dark .wk-article :deep(ol > li)::marker { color: #60a5fa; }

/* 引用块（切角终端面板） */
.wk-article :deep(blockquote) {
  margin: 1.2rem 0; padding: 0.8rem 1.1rem; font-size: 0.88rem;
  background: rgba(37,99,235,0.05); border-left: 3px solid #2563eb; color: #4b5563;
}
.dark .wk-article :deep(blockquote) { background: rgba(96,165,250,0.08); border-left-color: #60a5fa; color: #cbd5e1; }
.wk-article :deep(blockquote p) { margin: 0.3rem 0; }

/* 代码 */
.wk-article :deep(code) {
  font-family: 'JetBrains Mono', monospace; font-size: 0.85em;
  background: #f3f4f6; color: #dc2626; padding: 0.12em 0.4em; border-radius: 3px;
}
.dark .wk-article :deep(code) { background: #1f2937; color: #f87171; }
.wk-article :deep(pre) {
  margin: 1.2rem 0; padding: 1rem 1.2rem; overflow-x: auto;
  background: #0f172a; border: 1px solid #1e293b;
  clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%);
}
.wk-article :deep(pre code) { background: none; color: #e2e8f0; padding: 0; font-size: 0.84rem; }

/* 表格 */
.wk-article :deep(table) {
  width: 100%; margin: 1.3rem 0; border-collapse: collapse; font-size: 0.86rem;
  font-variant-numeric: tabular-nums;
}
.wk-article :deep(th) {
  font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; letter-spacing: 0.04em;
  text-align: left; padding: 0.6rem 0.8rem; background: rgba(37,99,235,0.08);
  color: #1e40af; border-bottom: 2px solid #2563eb;
}
.dark .wk-article :deep(th) { background: rgba(96,165,250,0.12); color: #93c5fd; border-bottom-color: #3b82f6; }
.wk-article :deep(td) {
  padding: 0.55rem 0.8rem; border-bottom: 1px solid #e5e7eb;
}
.dark .wk-article :deep(td) { border-bottom-color: #374151; }
.wk-article :deep(tbody tr:hover) { background: rgba(37,99,235,0.03); }
.dark .wk-article :deep(tbody tr:hover) { background: rgba(96,165,250,0.05); }

/* 分隔线 */
.wk-article :deep(hr) {
  margin: 2rem 0; border: none; height: 1px;
  background: linear-gradient(to right, #2563eb, transparent);
}
.dark .wk-article :deep(hr) { background: linear-gradient(to right, #60a5fa, transparent); }

/* 图片 */
.wk-article :deep(img) { max-width: 100%; border-radius: 6px; margin: 1rem 0; }
</style>


