<template>
  <div class="cc-root">
    <div class="cc-grid" aria-hidden="true"></div>
    <div class="cc-glow" aria-hidden="true"></div>

    <div class="relative max-w-4xl mx-auto py-10 px-4">
      <!-- 头部 -->
      <header class="mb-8">
        <div class="cc-kicker">// DIAMOND&nbsp;COUNCIL &nbsp;·&nbsp; 提案与投票</div>
        <h1 class="cc-title">钻石<span class="cc-title-accent">议会</span></h1>
        <p class="cc-sub">
          钻石及以上玩家对游戏改动的提案投票（在游戏内「比赛模式」聊天发送指令投票）。数据中继
          <a href="https://194823.xyz" target="_blank" rel="noopener" class="cc-link">194823.xyz</a>
        </p>
      </header>

      <div v-if="loading" class="cc-status"><span class="cc-blink">▮</span> 正在接入议会数据...</div>
      <div v-else-if="error" class="cc-status cc-status-err">! {{ error }}</div>

      <template v-else>
        <!-- 筛选标签 -->
        <div class="cc-filters">
          <button
            v-for="f in FILTERS" :key="f.key"
            @click="filter = f.key"
            class="cc-chip" :class="{ 'cc-chip-on': filter === f.key }"
          >
            {{ f.label }}<span class="cc-chip-n">{{ counts[f.key] }}</span>
          </button>
        </div>

        <div v-if="!shown.length" class="cc-status">该分类暂无提案</div>

        <div v-else class="cc-list">
          <article
            v-for="(p, i) in shown" :key="p.proposal_id"
            class="cc-item stagger-item" :style="{ animationDelay: Math.min(i, 12) * 40 + 'ms' }"
            :data-status="status(p)"
          >
            <!-- 状态侧条 -->
            <div class="cc-rail"></div>

            <div class="cc-body">
              <div class="cc-head">
                <span class="cc-id">#{{ p.proposal_id }}</span>
                <h3 class="cc-pt">{{ p.title }}</h3>
                <span class="cc-badge" :class="'cc-badge-' + status(p)">
                  {{ statusLabel(status(p)) }}<template v-if="p.implemented_version"> · v{{ p.implemented_version }}</template>
                </span>
              </div>

              <p v-if="p.description" class="cc-desc">{{ p.description }}</p>

              <!-- 红蓝拔河投票条 -->
              <div class="cc-vote">
                <div class="cc-vote-bar">
                  <div class="cc-vote-up" :style="{ width: p._pct + '%' }">
                    <span v-if="p._pct >= 16" class="cc-vote-inlabel">{{ p._up }}</span>
                  </div>
                  <div class="cc-vote-down" :style="{ width: (100 - p._pct) + '%' }">
                    <span v-if="100 - p._pct >= 16" class="cc-vote-inlabel">{{ p._down }}</span>
                  </div>
                </div>
                <div class="cc-vote-legend">
                  <span class="cc-up-txt">▲ 赞成 {{ p._up }}</span>
                  <span class="cc-pct">{{ p._pct }}%</span>
                  <span class="cc-down-txt">{{ p._down }} 反对 ▼</span>
                </div>
              </div>

              <footer class="cc-foot">
                <span class="cc-proposer">{{ p.proposer_name }}</span>
                <span class="cc-time">{{ formatDate(p.created_at) }}</span>
                <span class="cc-total">{{ p._total }} 票</span>
                <span v-if="p.close_reason" class="cc-reason">⊘ {{ p.close_reason }}</span>
              </footer>

              <!-- 投票按钮（仅投票中提案） -->
              <div v-if="status(p) === 'open'" class="cc-actions">
                <button class="cc-act cc-act-up" @click="openVote(p, 1)">▲ 赞同</button>
                <button class="cc-act cc-act-down" @click="openVote(p, -1)">▼ 反对</button>
                <span class="cc-act-hint">游戏内指令投票</span>
              </div>
            </div>
          </article>
        </div>
      </template>
    </div>

    <!-- 投票方法弹窗 -->
    <Teleport to="body">
      <div v-if="voteModal" class="cv-mask" @click.self="voteModal = null">
        <div class="cv-panel" role="dialog" aria-modal="true">
          <div class="cv-bar"></div>
          <button class="cv-close" @click="voteModal = null" aria-label="关闭">✕</button>

          <div class="cv-kicker">// VOTE&nbsp;PROTOCOL</div>
          <h2 class="cv-title">投票方法</h2>
          <p class="cv-lead">
            你选择了
            <strong :class="voteModal.vote === 1 ? 'cv-up' : 'cv-down'">
              {{ voteModal.vote === 1 ? '赞同' : '反对' }}
            </strong>
            提案 <span class="cv-pid">#{{ voteModal.id }}</span>
          </p>

          <ol class="cv-steps">
            <li>
              复制投票指令：
              <div class="cv-cmd-row">
                <code class="cv-cmd">{{ voteCmd }}</code>
                <button class="cv-copy" @click="copyCmd">{{ copied ? '已复制 ✓' : '复制' }}</button>
              </div>
            </li>
            <li>在游戏内「比赛模式」的聊天框中输入该指令并发送。</li>
            <li>发送后投票即被记录，刷新本页可见票数更新（数据每 3 分钟同步一次）。</li>
          </ol>

          <div class="cv-rules">
            <div class="cv-rule">
              <span class="cv-rule-k">投票资格</span>
              <span class="cv-rule-v">钻石 / 大师 / 宗师（双阵营），总有效对局 &gt; 200，近 30 天有效对局 ≥ 10</span>
            </div>
            <div class="cv-rule">
              <span class="cv-rule-k">投票权重</span>
              <span class="cv-rule-v">钻石 = 1，大师 = 2，宗师 = 3</span>
            </div>
            <div class="cv-rule">
              <span class="cv-rule-k">裁决规则</span>
              <span class="cv-rule-v">
                创建后 {{ RULES.decisionAfterDays }} 天且 ≥ {{ RULES.quorumVotes }} 人投票进入裁决，
                赞同率 &gt; {{ Math.round(RULES.passThreshold * 100) }}% 视为通过（待实施）；
                创建满 {{ RULES.quorumDeadlineDays }} 天仍不足 {{ RULES.quorumVotes }} 人投票则过期。
              </span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
const FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'open', label: '投票中' },
  { key: 'implemented', label: '已实装' },
  { key: 'closed', label: '已关闭' },
]

const proposals = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const filter = ref('all')

function status(p: any) {
  if (p.implemented_version) return 'implemented'
  if (p.closed_at) return 'closed'
  return 'open'
}
function statusLabel(s: string) {
  return { open: '投票中', implemented: '已实装', closed: '已关闭' }[s] || s
}
function formatDate(d: string) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN')
}

const counts = computed(() => {
  const c: Record<string, number> = { all: proposals.value.length, open: 0, implemented: 0, closed: 0 }
  for (const p of proposals.value) c[status(p)]++
  return c
})

const shown = computed(() => {
  if (filter.value === 'all') return proposals.value
  return proposals.value.filter(p => status(p) === filter.value)
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await $fetch<any>('/api/council')
    const list = (res.proposals || []).map((p: any) => {
      const votes = p.votes || []
      const up = votes.filter((v: any) => v.vote === 1).length
      const down = votes.filter((v: any) => v.vote === -1).length
      const total = up + down
      return { ...p, _up: up, _down: down, _total: total, _pct: total ? Math.round((up / total) * 100) : 0 }
    })
    // 全部按创建时间倒序（最新在前）
    list.sort((a: any, b: any) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    proposals.value = list
  } catch {
    error.value = '无法获取钻石议会数据，请稍后再试'
    proposals.value = []
  } finally {
    loading.value = false
  }
}

// 裁决规则常量（与源站一致，硬编码在前端 JS 里、不随 API 下发）
const RULES = { decisionAfterDays: 14, quorumDeadlineDays: 30, quorumVotes: 10, passThreshold: 0.75 }

const voteModal = ref<{ id: number; vote: 1 | -1 } | null>(null)
const copied = ref(false)

const voteCmd = computed(() => voteModal.value ? `-vote ${voteModal.value.id}_${voteModal.value.vote}` : '')

function openVote(p: any, vote: 1 | -1) {
  copied.value = false
  voteModal.value = { id: p.proposal_id, vote }
}

async function copyCmd() {
  const ok = await copyText(voteCmd.value)
  if (ok) {
    copied.value = true
    setTimeout(() => (copied.value = false), 1600)
  }
}

// 弹窗开启时锁定背景滚动 + 支持 Esc 关闭
watch(voteModal, (v) => {
  if (import.meta.client) document.body.style.overflow = v ? 'hidden' : ''
})
function onKey(e: KeyboardEvent) { if (e.key === 'Escape') voteModal.value = null }
onMounted(() => { load(); if (import.meta.client) window.addEventListener('keydown', onKey) })
onBeforeUnmount(() => { if (import.meta.client) { window.removeEventListener('keydown', onKey); document.body.style.overflow = '' } })
</script>

<style scoped>
.cc-root { position: relative; min-height: 100%; overflow: hidden; }
.cc-grid {
  position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(to right, rgba(100,116,139,0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(100,116,139,0.06) 1px, transparent 1px);
  background-size: 38px 38px;
  mask-image: radial-gradient(ellipse 90% 50% at 50% 0%, #000 20%, transparent 75%);
  -webkit-mask-image: radial-gradient(ellipse 90% 50% at 50% 0%, #000 20%, transparent 75%);
}
/* 红蓝对峙的氛围光 */
.cc-glow {
  position: absolute; top: -120px; left: 0; right: 0; height: 380px;
  pointer-events: none; z-index: 0;
  background:
    radial-gradient(circle at 18% 20%, rgba(37,99,235,0.12), transparent 45%),
    radial-gradient(circle at 82% 20%, rgba(220,38,38,0.1), transparent 45%);
}
.dark .cc-glow {
  background:
    radial-gradient(circle at 18% 20%, rgba(59,130,246,0.16), transparent 45%),
    radial-gradient(circle at 82% 20%, rgba(248,113,113,0.12), transparent 45%);
}

.cc-kicker {
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
  letter-spacing: 0.18em; text-transform: uppercase; color: #2563eb; margin-bottom: 0.6rem;
}
.dark .cc-kicker { color: #60a5fa; }
.cc-title {
  font-family: 'JetBrains Mono', monospace; font-weight: 500;
  font-size: clamp(2.2rem, 6vw, 3.4rem); line-height: 0.95; letter-spacing: -0.02em; color: #111827;
}
.dark .cc-title { color: #f3f4f6; }
.cc-title-accent {
  background: linear-gradient(95deg, #2563eb, #dc2626);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.cc-sub { margin-top: 0.9rem; font-size: 0.85rem; color: #6b7280; max-width: 42rem; }
.cc-link { color: #2563eb; font-family: 'JetBrains Mono', monospace; }
.cc-link:hover { text-decoration: underline; }
.dark .cc-link { color: #60a5fa; }

.cc-status {
  font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
  color: #6b7280; padding: 3rem 0; text-align: center;
}
.cc-status-err { color: #dc2626; }
.dark .cc-status-err { color: #f87171; }
.cc-blink { animation: ccBlink 1s steps(1) infinite; color: #2563eb; }
@keyframes ccBlink { 50% { opacity: 0 } }

/* 筛选 */
.cc-filters { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.4rem; }
.cc-chip {
  font-family: 'JetBrains Mono', monospace; font-size: 0.74rem;
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.4rem 0.8rem; border: 1px solid #d1d5db; background: transparent; color: #6b7280;
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
  transition: all 0.18s;
}
.cc-chip:hover { border-color: #93c5fd; color: #2563eb; }
.cc-chip-on { border-color: #2563eb; color: #2563eb; background: rgba(37,99,235,0.08); font-weight: 500; }
.dark .cc-chip { border-color: #374151; color: #9ca3af; }
.dark .cc-chip:hover { border-color: #3b82f6; color: #60a5fa; }
.dark .cc-chip-on { border-color: #60a5fa; color: #60a5fa; background: rgba(96,165,250,0.12); }
.cc-chip-n {
  font-size: 0.64rem; padding: 0 5px; border-radius: 2px;
  background: rgba(100,116,139,0.18); color: inherit;
}

/* 提案卡片 */
.cc-list { display: flex; flex-direction: column; gap: 0.85rem; }
.cc-item {
  position: relative; display: flex; background: #fff; border: 1px solid #e5e7eb;
  clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%);
  transition: border-color 0.2s, transform 0.2s;
}
.cc-item:hover { transform: translateX(2px); border-color: #cbd5e1; }
.dark .cc-item { background: #1f2937; border-color: #374151; }
.dark .cc-item:hover { border-color: #4b5563; }
.cc-rail { width: 4px; flex-shrink: 0; background: #94a3b8; }
.cc-item[data-status="open"] .cc-rail { background: #2563eb; }
.cc-item[data-status="implemented"] .cc-rail { background: #16a34a; }
.cc-item[data-status="closed"] .cc-rail { background: #9ca3af; }
.cc-body { flex: 1; padding: 1rem 1.2rem; min-width: 0; }

.cc-head { display: flex; align-items: baseline; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 0.4rem; }
.cc-id {
  font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #9ca3af; flex-shrink: 0;
}
.cc-pt {
  font-weight: 600; font-size: 1rem; color: #111827; flex: 1; min-width: 0; word-break: break-word;
}
.dark .cc-pt { color: #f3f4f6; }
.cc-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; letter-spacing: 0.04em;
  padding: 3px 7px; flex-shrink: 0; border: 1px solid transparent;
}
.cc-badge-open { background: rgba(37,99,235,0.12); color: #2563eb; border-color: rgba(37,99,235,0.3); }
.cc-badge-implemented { background: rgba(22,163,74,0.12); color: #16a34a; border-color: rgba(22,163,74,0.3); }
.cc-badge-closed { background: rgba(156,163,175,0.15); color: #6b7280; }
.dark .cc-badge-open { color: #60a5fa; background: rgba(96,165,250,0.15); }
.dark .cc-badge-implemented { color: #4ade80; background: rgba(74,222,128,0.15); }
.dark .cc-badge-closed { color: #9ca3af; background: rgba(156,163,175,0.12); }
.cc-desc {
  font-size: 0.84rem; line-height: 1.6; color: #4b5563;
  white-space: pre-wrap; word-break: break-word; margin-bottom: 0.8rem;
}
.dark .cc-desc { color: #cbd5e1; }

/* 红蓝拔河投票条 */
.cc-vote { margin-bottom: 0.7rem; }
.cc-vote-bar {
  display: flex; height: 22px; overflow: hidden;
  border: 1px solid #e5e7eb; background: #f3f4f6;
}
.dark .cc-vote-bar { border-color: #374151; background: #111827; }
.cc-vote-up {
  background: linear-gradient(90deg, #1d4ed8, #3b82f6); min-width: 0;
  display: flex; align-items: center; justify-content: flex-start; padding-left: 6px;
  transition: width 0.5s cubic-bezier(0.4,0,0.2,1);
}
.cc-vote-down {
  background: linear-gradient(90deg, #ef4444, #b91c1c); min-width: 0;
  display: flex; align-items: center; justify-content: flex-end; padding-right: 6px;
  transition: width 0.5s cubic-bezier(0.4,0,0.2,1);
}
.cc-vote-inlabel {
  font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; font-weight: 500; color: #fff;
}
.cc-vote-legend {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 0.3rem; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
}
.cc-up-txt { color: #2563eb; }
.cc-down-txt { color: #dc2626; }
.cc-pct { color: #6b7280; font-weight: 500; }
.dark .cc-up-txt { color: #60a5fa; }
.dark .cc-down-txt { color: #f87171; }

.cc-foot {
  display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap;
  font-size: 0.72rem; color: #9ca3af; font-family: 'JetBrains Mono', monospace;
}
.cc-proposer { color: #6b7280; }
.dark .cc-proposer { color: #9ca3af; }
.cc-reason {
  color: #b45309; background: rgba(180,83,9,0.08); padding: 1px 6px;
  font-family: 'DM Sans', sans-serif; word-break: break-word;
}
.dark .cc-reason { color: #fbbf24; background: rgba(251,191,36,0.1); }

/* 投票按钮 */
.cc-actions {
  margin-top: 0.85rem; padding-top: 0.75rem; border-top: 1px dashed #e5e7eb;
  display: flex; align-items: center; gap: 0.6rem;
}
.dark .cc-actions { border-color: #374151; }
.cc-act {
  font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 500;
  padding: 0.35rem 1rem; border: 1px solid transparent; background: transparent; transition: all 0.16s;
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px);
}
.cc-act-up { color: #2563eb; border-color: rgba(37,99,235,0.4); }
.cc-act-up:hover { background: #2563eb; color: #fff; }
.cc-act-down { color: #dc2626; border-color: rgba(220,38,38,0.4); }
.cc-act-down:hover { background: #dc2626; color: #fff; }
.dark .cc-act-up { color: #60a5fa; border-color: rgba(96,165,250,0.45); }
.dark .cc-act-up:hover { background: #3b82f6; color: #fff; }
.dark .cc-act-down { color: #f87171; border-color: rgba(248,113,113,0.45); }
.dark .cc-act-down:hover { background: #ef4444; color: #fff; }
.cc-act-hint {
  font-family: 'JetBrains Mono', monospace; font-size: 0.66rem; color: #9ca3af; margin-left: auto;
}

/* 投票方法弹窗 */
.cv-mask {
  position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center;
  padding: 1rem; background: rgba(15,23,42,0.55); backdrop-filter: blur(3px);
  animation: cvFade 0.18s ease-out;
}
@keyframes cvFade { from { opacity: 0 } to { opacity: 1 } }
.cv-panel {
  position: relative; width: 100%; max-width: 30rem; max-height: 90vh; overflow-y: auto;
  padding: 1.6rem 1.5rem 1.5rem; background: #fff; border: 1px solid #e5e7eb;
  clip-path: polygon(0 0, calc(100% - 22px) 0, 100% 22px, 100% 100%, 0 100%);
  animation: cvPop 0.22s cubic-bezier(0.2,0.8,0.3,1);
}
@keyframes cvPop { from { opacity: 0; transform: translateY(12px) scale(0.98) } to { opacity: 1; transform: none } }
.dark .cv-panel { background: #1f2937; border-color: #374151; }
.cv-bar { position: absolute; top: 0; left: 0; width: 5px; height: 100%; background: linear-gradient(#2563eb, #dc2626); }
.cv-close {
  position: absolute; top: 0.8rem; right: 1rem; font-size: 0.95rem; color: #9ca3af;
  width: 1.6rem; height: 1.6rem; transition: color 0.15s;
}
.cv-close:hover { color: #dc2626; }
.cv-kicker {
  font-family: 'JetBrains Mono', monospace; font-size: 0.64rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: #2563eb; margin-bottom: 0.35rem;
}
.dark .cv-kicker { color: #60a5fa; }
.cv-title {
  font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; font-weight: 500;
  color: #111827; line-height: 1; margin-bottom: 0.8rem;
}
.dark .cv-title { color: #f3f4f6; }
.cv-lead { font-size: 0.9rem; color: #374151; margin-bottom: 1rem; }
.dark .cv-lead { color: #d1d5db; }
.cv-pid { font-family: 'JetBrains Mono', monospace; color: #6b7280; }
.cv-up { color: #2563eb; } .dark .cv-up { color: #60a5fa; }
.cv-down { color: #dc2626; } .dark .cv-down { color: #f87171; }

.cv-steps {
  list-style: decimal; padding-left: 1.3rem; margin-bottom: 1.1rem;
  font-size: 0.85rem; line-height: 1.7; color: #374151;
}
.dark .cv-steps { color: #cbd5e1; }
.cv-steps li { margin-bottom: 0.5rem; }
.cv-cmd-row { display: flex; gap: 0.5rem; margin-top: 0.4rem; align-items: stretch; }
.cv-cmd {
  flex: 1; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
  background: #0f172a; color: #e2e8f0; padding: 0.55rem 0.8rem; word-break: break-all;
  display: flex; align-items: center;
}
.dark .cv-cmd { background: #0b1220; }
.cv-copy {
  font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 500;
  padding: 0 1rem; background: #2563eb; color: #fff; transition: background 0.15s; flex-shrink: 0;
}
.cv-copy:hover { background: #1d4ed8; }

.cv-rules { border-top: 1px dashed #e5e7eb; padding-top: 0.9rem; display: flex; flex-direction: column; gap: 0.6rem; }
.dark .cv-rules { border-color: #374151; }
.cv-rule { font-size: 0.78rem; line-height: 1.55; }
.cv-rule-k {
  display: inline-block; font-family: 'JetBrains Mono', monospace; font-weight: 600;
  color: #111827; margin-right: 0.4rem;
}
.dark .cv-rule-k { color: #f3f4f6; }
.cv-rule-v { color: #6b7280; }
.dark .cv-rule-v { color: #9ca3af; }

@media (max-width: 640px) {
  .cc-body { padding: 0.85rem 0.95rem; }
  .cc-pt { font-size: 0.92rem; }
  .cc-act-hint { display: none; }
}
</style>


