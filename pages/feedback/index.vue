<template>
  <div class="fb-root">
    <div class="fb-grid" aria-hidden="true"></div>
    <div class="fb-glow" aria-hidden="true"></div>

    <div class="relative max-w-4xl mx-auto py-10 px-4">
      <!-- 头部 -->
      <header class="mb-8">
        <div class="fb-kicker">// SIGNAL&nbsp;RELAY &nbsp;·&nbsp; 建议与反馈</div>
        <h1 class="fb-title">信号<span class="fb-title-accent">中继</span></h1>
        <p class="fb-sub">
          提交功能建议、Bug 报告或数据纠错，管理员会在此跟进处理进度。
        </p>
      </header>

      <!-- 提交表单 -->
      <section class="fb-compose">
        <div v-if="!isLoggedIn" class="fb-login-hint">
          <span class="fb-blink">▮</span>
          需先
          <NuxtLink to="/login" class="fb-link">登录</NuxtLink>
          后发送信号
        </div>
        <form v-else @submit.prevent="submit" class="fb-form">
          <div class="fb-form-row">
            <select v-model="form.category" class="fb-select">
              <option v-for="c in CATEGORIES" :key="c.key" :value="c.key">{{ c.label }}</option>
            </select>
            <input v-model="form.title" type="text" required maxlength="100"
              placeholder="一句话概括你的建议" class="fb-input" />
          </div>
          <textarea v-model="form.content" rows="3" maxlength="2000"
            placeholder="详细描述（可选）" class="fb-textarea"></textarea>
          <div class="fb-form-foot">
            <span v-if="formError" class="fb-err">! {{ formError }}</span>
            <span v-else class="fb-hint">SIGNAL READY</span>
            <button type="submit" :disabled="submitting" class="fb-send">
              {{ submitting ? '发送中...' : '▸ 发送信号' }}
            </button>
          </div>
        </form>
      </section>

      <!-- 筛选 -->
      <div class="fb-filters">
        <div class="fb-filter-group">
          <span class="fb-filter-lbl">CAT</span>
          <button @click="filterCat = ''" class="fb-chip" :class="{ 'fb-chip-on': filterCat === '' }">全部</button>
          <button v-for="c in CATEGORIES" :key="c.key" @click="filterCat = c.key"
            class="fb-chip" :class="{ 'fb-chip-on': filterCat === c.key }">{{ c.label }}</button>
        </div>
        <div class="fb-filter-group">
          <span class="fb-filter-lbl">STATUS</span>
          <button @click="filterStatus = ''" class="fb-chip" :class="{ 'fb-chip-on': filterStatus === '' }">全部</button>
          <button v-for="s in STATUSES" :key="s.key" @click="filterStatus = s.key"
            class="fb-chip" :class="{ 'fb-chip-on': filterStatus === s.key }">{{ s.label }}</button>
        </div>
      </div>

      <!-- 列表 -->
      <div v-if="loading" class="fb-status"><span class="fb-blink">▮</span> 正在接收信号...</div>
      <div v-else-if="!list.length" class="fb-status">暂无信号，发送第一条吧</div>
      <div v-else class="fb-list">
        <article
          v-for="(item, i) in list" :key="item.id"
          class="fb-item stagger-item" :style="{ animationDelay: Math.min(i, 12) * 40 + 'ms' }"
          :data-cat="item.category"
        >
          <!-- 点赞 -->
          <button @click="toggleVote(item)" :disabled="!isLoggedIn"
            class="fb-vote" :class="{ 'fb-voted': item.voted, 'fb-vote-off': !isLoggedIn }"
            :title="isLoggedIn ? '点赞' : '登录后可点赞'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7"/>
            </svg>
            <span class="fb-vote-n">{{ item.votes }}</span>
          </button>

          <div class="fb-body">
            <div class="fb-head">
              <span class="fb-cat" :class="'fb-cat-' + item.category">{{ catLabel(item.category) }}</span>
              <span class="fb-badge" :class="'fb-badge-' + item.status">{{ statusLabel(item.status) }}</span>
              <h3 class="fb-pt">{{ item.title }}</h3>
            </div>
            <p v-if="item.content" class="fb-content">{{ item.content }}</p>

            <footer class="fb-foot">
              <span class="fb-user">{{ item.username }}</span>
              <span class="fb-time">{{ formatDate(item.created_at) }}</span>
              <button v-if="canDelete(item)" @click="remove(item)" class="fb-del">删除</button>
            </footer>

            <!-- 管理员回复（进度说明，全员可见） -->
            <div v-if="item.admin_note" class="fb-reply">
              <span class="fb-reply-tag">▸ 管理员回复</span>
              <span class="fb-reply-txt">{{ item.admin_note }}</span>
            </div>

            <!-- 管理员控制台 -->
            <div v-if="isAdmin" class="fb-admin">
              <select :value="item.status" @change="changeStatus(item, ($event.target as HTMLSelectElement).value)" class="fb-admin-sel">
                <option v-for="s in STATUSES" :key="s.key" :value="s.key">{{ s.label }}</option>
              </select>
              <input v-model="item._noteDraft" type="text" maxlength="1000" placeholder="填写处理说明" class="fb-admin-in" />
              <button @click="saveNote(item)" class="fb-admin-save">保存</button>
            </div>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const { isLoggedIn, isAdmin, authHeaders } = useAuth()

const CATEGORIES = [
  { key: 'feature', label: '功能建议' },
  { key: 'bug', label: 'Bug报错' },
  { key: 'data', label: '数据纠错' },
  { key: 'other', label: '其他' },
]
const STATUSES = [
  { key: 'pending', label: '待处理' },
  { key: 'accepted', label: '已采纳' },
  { key: 'done', label: '已完成' },
  { key: 'rejected', label: '不采纳' },
]

const list = ref<any[]>([])
const loading = ref(true)
const filterCat = ref('')
const filterStatus = ref('')

const form = reactive({ category: 'feature', title: '', content: '' })
const formError = ref('')
const submitting = ref(false)

function catLabel(k: string) { return CATEGORIES.find(c => c.key === k)?.label || k }
function statusLabel(k: string) { return STATUSES.find(s => s.key === k)?.label || k }
function formatDate(d: string) {
  return new Date(d.replace(' ', 'T') + 'Z').toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
}
function canDelete(_item: any) {
  return isAdmin.value
}

async function load() {
  loading.value = true
  try {
    const q = new URLSearchParams()
    if (filterCat.value) q.set('category', filterCat.value)
    if (filterStatus.value) q.set('status', filterStatus.value)
    const res = await $fetch<any>(`/api/feedback?${q.toString()}`, { headers: authHeaders.value })
    list.value = (res.feedback || []).map((f: any) => ({
      ...f,
      voted: !!f.voted,
      _noteDraft: f.admin_note || '',
    }))
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function submit() {
  formError.value = ''
  if (!form.title.trim()) { formError.value = '请填写标题'; return }
  submitting.value = true
  try {
    await $fetch('/api/feedback', { method: 'POST', headers: authHeaders.value, body: { ...form } })
    form.title = ''
    form.content = ''
    form.category = 'feature'
    await load()
  } catch (e: any) {
    formError.value = e?.data?.message || '提交失败'
  } finally {
    submitting.value = false
  }
}

async function toggleVote(item: any) {
  if (!isLoggedIn.value) return
  try {
    const res = await $fetch<any>(`/api/feedback/${item.id}/vote`, { method: 'POST', headers: authHeaders.value })
    item.votes = res.votes
    item.voted = res.voted
  } catch {}
}

async function changeStatus(item: any, status: string) {
  try {
    await $fetch(`/api/feedback/${item.id}`, { method: 'PATCH', headers: authHeaders.value, body: { status } })
    item.status = status
  } catch {}
}

async function saveNote(item: any) {
  try {
    await $fetch(`/api/feedback/${item.id}`, { method: 'PATCH', headers: authHeaders.value, body: { admin_note: item._noteDraft } })
    item.admin_note = item._noteDraft
  } catch {}
}

async function remove(item: any) {
  if (!confirm('确定删除这条建议？')) return
  try {
    await $fetch(`/api/feedback/${item.id}`, { method: 'DELETE', headers: authHeaders.value })
    list.value = list.value.filter(f => f.id !== item.id)
  } catch {}
}

watch([filterCat, filterStatus], load)
onMounted(load)
</script>

<style scoped>
.fb-root { position: relative; min-height: 100%; overflow: hidden; }
.fb-grid {
  position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(to right, rgba(37,99,235,0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(37,99,235,0.05) 1px, transparent 1px);
  background-size: 30px 30px;
  mask-image: radial-gradient(ellipse 85% 55% at 50% 0%, #000 25%, transparent 78%);
  -webkit-mask-image: radial-gradient(ellipse 85% 55% at 50% 0%, #000 25%, transparent 78%);
}
.fb-glow {
  position: absolute; top: -100px; left: 50%; transform: translateX(-50%);
  width: 600px; height: 320px; pointer-events: none; z-index: 0;
  background: radial-gradient(circle, rgba(37,99,235,0.12), transparent 60%);
}
.dark .fb-grid {
  background-image:
    linear-gradient(to right, rgba(96,165,250,0.07) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(96,165,250,0.07) 1px, transparent 1px);
}
.dark .fb-glow { background: radial-gradient(circle, rgba(59,130,246,0.16), transparent 60%); }

.fb-kicker {
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
  letter-spacing: 0.18em; text-transform: uppercase; color: #2563eb; margin-bottom: 0.6rem;
}
.dark .fb-kicker { color: #60a5fa; }
.fb-title {
  font-family: 'JetBrains Mono', monospace; font-weight: 500;
  font-size: clamp(2.2rem, 6vw, 3.4rem); line-height: 0.95; letter-spacing: -0.02em; color: #111827;
}
.dark .fb-title { color: #f3f4f6; }
.fb-title-accent { color: #2563eb; }
.dark .fb-title-accent { color: #60a5fa; }
.fb-sub { margin-top: 0.9rem; font-size: 0.85rem; color: #6b7280; max-width: 40rem; }
.fb-link { color: #2563eb; font-family: 'JetBrains Mono', monospace; }
.fb-link:hover { text-decoration: underline; }
.dark .fb-link { color: #60a5fa; }
.fb-blink { animation: fbBlink 1s steps(1) infinite; color: #2563eb; }
@keyframes fbBlink { 50% { opacity: 0 } }
.dark .fb-blink { color: #60a5fa; }

/* 提交表单 — 控制台输入面板 */
.fb-compose {
  position: relative; margin-bottom: 1.8rem; padding: 1.25rem;
  background: #fff; border: 1px solid #e5e7eb; border-left: 3px solid #2563eb;
  clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
}
.dark .fb-compose { background: #1f2937; border-color: #374151; border-left-color: #60a5fa; }
.fb-login-hint {
  font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #6b7280; text-align: center; padding: 0.6rem;
}
.fb-form { display: flex; flex-direction: column; gap: 0.7rem; }
.fb-form-row { display: flex; gap: 0.7rem; }
.fb-select, .fb-input, .fb-textarea {
  font-family: inherit; font-size: 0.875rem; padding: 0.55rem 0.75rem;
  background: #f9fafb; border: 1px solid #e5e7eb; color: #111827; transition: border-color 0.18s;
}
.fb-select:focus, .fb-input:focus, .fb-textarea:focus { outline: none; border-color: #2563eb; }
.fb-input { flex: 1; }
.fb-textarea { width: 100%; resize: vertical; }
.dark .fb-select, .dark .fb-input, .dark .fb-textarea {
  background: #111827; border-color: #374151; color: #f3f4f6;
}
.fb-form-foot { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.fb-hint { font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; letter-spacing: 0.12em; color: #9ca3af; }
.fb-err { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #dc2626; }
.dark .fb-err { color: #f87171; }
.fb-send {
  font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; padding: 0.55rem 1.2rem;
  background: #2563eb; color: #fff; border: none; transition: all 0.18s;
  clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
}
.fb-send:hover:not(:disabled) { background: #1d4ed8; }
.fb-send:disabled { opacity: 0.5; cursor: not-allowed; }
.dark .fb-send { background: #3b82f6; }
.dark .fb-send:hover:not(:disabled) { background: #60a5fa; }

/* 筛选 */
.fb-filters { display: flex; flex-direction: column; gap: 0.55rem; margin-bottom: 1.4rem; }
.fb-filter-group { display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem; }
.fb-filter-lbl {
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.1em;
  color: #9ca3af; width: 3.4rem; flex-shrink: 0;
}
.fb-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; padding: 0.32rem 0.7rem;
  border: 1px solid #d1d5db; background: transparent; color: #6b7280;
  clip-path: polygon(5px 0, 100% 0, 100% calc(100% - 5px), calc(100% - 5px) 100%, 0 100%, 0 5px);
  transition: all 0.16s;
}
.fb-chip:hover { border-color: #93c5fd; color: #2563eb; }
.fb-chip-on { border-color: #2563eb; color: #2563eb; background: rgba(37,99,235,0.08); font-weight: 500; }
.dark .fb-chip { border-color: #374151; color: #9ca3af; }
.dark .fb-chip:hover { border-color: #3b82f6; color: #60a5fa; }
.dark .fb-chip-on { border-color: #60a5fa; color: #60a5fa; background: rgba(96,165,250,0.12); }

.fb-status {
  font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
  color: #6b7280; padding: 3rem 0; text-align: center;
}

/* 信号卡片 */
.fb-list { display: flex; flex-direction: column; gap: 0.85rem; }
.fb-item {
  display: flex; gap: 0.9rem; padding: 1rem 1.15rem;
  background: #fff; border: 1px solid #e5e7eb;
  clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
  transition: border-color 0.2s, transform 0.2s;
}
.fb-item:hover { transform: translateX(2px); border-color: #cbd5e1; }
.dark .fb-item { background: #1f2937; border-color: #374151; }
.dark .fb-item:hover { border-color: #4b5563; }

/* 点赞 */
.fb-vote {
  flex-shrink: 0; width: 3rem; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; padding: 0.45rem 0; border: 1px solid #d1d5db; background: #f9fafb; color: #6b7280; transition: all 0.18s;
  clip-path: polygon(0 0, 100% 0, 100% 100%, 6px 100%, 0 calc(100% - 6px));
}
.fb-vote svg { width: 1rem; height: 1rem; }
.fb-vote-n { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 600; }
.fb-vote:hover:not(.fb-vote-off) { border-color: #2563eb; color: #2563eb; }
.fb-voted { border-color: #2563eb; background: rgba(37,99,235,0.1); color: #2563eb; }
.fb-vote-off { opacity: 0.55; cursor: not-allowed; }
.dark .fb-vote { background: #111827; border-color: #374151; color: #9ca3af; }
.dark .fb-vote:hover:not(.fb-vote-off) { border-color: #60a5fa; color: #60a5fa; }
.dark .fb-voted { border-color: #60a5fa; background: rgba(96,165,250,0.15); color: #60a5fa; }

.fb-body { flex: 1; min-width: 0; }
.fb-head { display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.4rem; }
.fb-cat, .fb-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.03em;
  padding: 2px 6px; flex-shrink: 0;
}
.fb-cat-feature { background: rgba(37,99,235,0.12); color: #2563eb; }
.fb-cat-bug { background: rgba(220,38,38,0.12); color: #dc2626; }
.fb-cat-data { background: rgba(217,119,6,0.14); color: #b45309; }
.fb-cat-other { background: rgba(100,116,139,0.15); color: #64748b; }
.dark .fb-cat-feature { color: #60a5fa; background: rgba(96,165,250,0.15); }
.dark .fb-cat-bug { color: #f87171; background: rgba(248,113,113,0.15); }
.dark .fb-cat-data { color: #fbbf24; background: rgba(251,191,36,0.14); }
.dark .fb-cat-other { color: #94a3b8; background: rgba(148,163,184,0.15); }
.fb-badge { border: 1px solid currentColor; }
.fb-badge-pending { color: #6b7280; }
.fb-badge-accepted { color: #2563eb; }
.fb-badge-done { color: #16a34a; }
.fb-badge-rejected { color: #9ca3af; text-decoration: line-through; }
.dark .fb-badge-pending { color: #9ca3af; }
.dark .fb-badge-accepted { color: #60a5fa; }
.dark .fb-badge-done { color: #4ade80; }
.fb-pt { font-weight: 600; font-size: 0.98rem; color: #111827; flex: 1; min-width: 0; word-break: break-word; }
.dark .fb-pt { color: #f3f4f6; }
.fb-content {
  font-size: 0.84rem; line-height: 1.6; color: #4b5563;
  white-space: pre-wrap; word-break: break-word; margin-bottom: 0.6rem;
}
.dark .fb-content { color: #cbd5e1; }
.fb-foot {
  display: flex; align-items: center; gap: 0.85rem; flex-wrap: wrap;
  font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #9ca3af;
}
.fb-del { color: #dc2626; opacity: 0.7; transition: opacity 0.15s; }
.fb-del:hover { opacity: 1; text-decoration: underline; }

/* 管理员回复 */
.fb-reply {
  margin-top: 0.7rem; padding: 0.6rem 0.8rem; font-size: 0.8rem; line-height: 1.55;
  background: rgba(37,99,235,0.06); border-left: 2px solid #2563eb; color: #374151;
}
.fb-reply-tag {
  font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; color: #2563eb; margin-right: 0.4rem; font-weight: 500;
}
.fb-reply-txt { white-space: pre-wrap; word-break: break-word; }
.dark .fb-reply { background: rgba(96,165,250,0.1); border-left-color: #60a5fa; color: #cbd5e1; }
.dark .fb-reply-tag { color: #60a5fa; }

/* 管理员控制台 */
.fb-admin {
  margin-top: 0.7rem; padding-top: 0.7rem; border-top: 1px dashed #e5e7eb;
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem;
}
.dark .fb-admin { border-color: #374151; }
.fb-admin-sel, .fb-admin-in {
  font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; padding: 0.3rem 0.5rem;
  background: #f9fafb; border: 1px solid #e5e7eb; color: #374151;
}
.fb-admin-in { flex: 1; min-width: 150px; }
.fb-admin-sel:focus, .fb-admin-in:focus { outline: none; border-color: #2563eb; }
.dark .fb-admin-sel, .dark .fb-admin-in { background: #111827; border-color: #374151; color: #d1d5db; }
.fb-admin-save {
  font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; padding: 0.3rem 0.85rem;
  background: #2563eb; color: #fff; transition: background 0.15s;
}
.fb-admin-save:hover { background: #1d4ed8; }
.dark .fb-admin-save { background: #3b82f6; }

@media (max-width: 640px) {
  .fb-form-row { flex-direction: column; }
  .fb-item { padding: 0.85rem 0.95rem; }
}
</style>


