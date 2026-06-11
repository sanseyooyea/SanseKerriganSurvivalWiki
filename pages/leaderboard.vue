<template>
  <div class="lb-root" :class="`board-${board}`">
    <!-- 氛围背景层 -->
    <div class="lb-bg" aria-hidden="true">
      <div class="lb-orb lb-orb-1"></div>
      <div class="lb-orb lb-orb-2"></div>
      <div class="lb-grid"></div>
    </div>

    <div class="relative">
      <!-- 页头 -->
      <header class="lb-header">
        <div class="lb-eyebrow">
          <span class="lb-live-dot"></span>
          RANKED LADDER · 天梯
        </div>
        <h1 class="lb-title">王座之争</h1>
        <p class="lb-sub">各阵营核心分前 50 名 · 点击查看玩家档案</p>
        <span v-if="generatedAt" class="lb-stamp">同步于 {{ generatedAt }}</span>
      </header>

      <!-- 阵营切换 -->
      <div class="lb-switch" role="tablist">
        <div class="lb-switch-glider" :class="board"></div>
        <button role="tab" :aria-selected="board === 'kerrigan'"
          @click="board = 'kerrigan'"
          class="lb-switch-btn" :class="{ active: board === 'kerrigan' }">
          <span class="lb-switch-mark mark-k"></span>凯瑞甘
        </button>
        <button role="tab" :aria-selected="board === 'survivor'"
          @click="board = 'survivor'"
          class="lb-switch-btn" :class="{ active: board === 'survivor' }">
          <span class="lb-switch-mark mark-s"></span>生存者
        </button>
      </div>

      <!-- 加载 -->
      <div v-if="pending" class="lb-skel-wrap">
        <div class="grid grid-cols-3 gap-3 items-end">
          <div class="lb-skel" style="height:9rem"></div>
          <div class="lb-skel" style="height:12rem"></div>
          <div class="lb-skel" style="height:7.5rem"></div>
        </div>
        <div v-for="i in 7" :key="i" class="lb-skel" style="height:3.5rem"></div>
      </div>

      <div v-else-if="error" class="lb-error">
        排行榜加载失败，请稍后重试
      </div>

      <template v-else>
        <!-- 领奖台 -->
        <section v-if="podium.length" class="lb-podium" :key="board">
          <article v-for="p in podium" :key="p.rank"
            class="lb-pod" :class="[`tier-${p.rank}`, podiumOrder(p.rank)]"
            :style="{ animationDelay: `${podiumDelay(p.rank)}ms` }"
            @click="openDetail(p)">
            <div class="lb-pod-aura"></div>
            <div class="lb-pod-medal">
              <svg v-if="p.rank === 1" class="lb-crown" viewBox="0 0 24 24" fill="currentColor">
                <path d="M5 16L3 7l5.5 4L12 5l3.5 6L21 7l-2 9H5z"/>
              </svg>
              <span class="lb-pod-rank">{{ p.rank }}</span>
            </div>
            <div class="lb-pod-name">{{ p.display_name || '未知玩家' }}</div>
            <div v-if="p.identity" class="lb-pod-id">{{ p.identity }}</div>
            <div class="lb-pod-mmr">
              {{ p.mmr }}<span class="lb-pod-unit">MMR</span>
            </div>
            <span v-if="p.team_name" class="lb-pod-team">{{ p.team_name }}</span>
            <div class="lb-pod-base">{{ rankLabel(p.rank) }}</div>
          </article>
        </section>

        <!-- 名次列表 -->
        <section class="lb-list">
          <div class="lb-list-head">
            <span>排名</span>
            <span>玩家</span>
            <span class="lb-list-head-mmr">核心分</span>
          </div>
          <button v-for="(row, i) in rest" :key="row.rank"
            @click="openDetail(row)"
            class="lb-row"
            :class="{ 'is-clickable': row.handles?.length }"
            :style="{ animationDelay: `${Math.min(i * 28, 600)}ms` }">
            <span class="lb-row-bar"></span>
            <span class="lb-row-rank">{{ row.rank }}</span>
            <div class="lb-row-main">
              <div class="lb-row-name">{{ row.display_name || '未知玩家' }}</div>
              <div class="lb-row-meta">
                <span v-if="row.identity" class="lb-row-id">{{ row.identity }}</span>
                <span v-if="row.team_name" class="lb-row-team">{{ row.team_name }}</span>
              </div>
            </div>
            <div class="lb-row-score">
              <div class="lb-row-track">
                <div class="lb-row-fill" :style="{ width: mmrPct(row.mmr) }"></div>
              </div>
              <span class="lb-row-mmr">{{ row.mmr }}</span>
            </div>
            <svg class="lb-row-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
        </section>
      </template>
    </div>

    <PlayerDetailModal v-if="selected" :player="selected" @close="selected = null" />
  </div>
</template>

<script setup lang="ts">
const board = ref<'kerrigan' | 'survivor'>('kerrigan')
const selected = ref<any>(null)

const { data, pending, error } = await useFetch<any>('/api/leaderboard')

const rows = computed(() => data.value?.boards?.[board.value] ?? [])
const podium = computed(() => rows.value.slice(0, 3))
const rest = computed(() => rows.value.slice(3))
const topMmr = computed(() => rows.value[0]?.mmr || 1)

function mmrPct(mmr: number) {
  const lo = rest.value[rest.value.length - 1]?.mmr ?? 0
  const top = topMmr.value
  const span = Math.max(top - lo, 1)
  const pct = 30 + ((mmr - lo) / span) * 70
  return `${Math.max(12, Math.min(100, pct)).toFixed(1)}%`
}

const generatedAt = computed(() => {
  const at = data.value?.generated_at
  if (!at) return ''
  const d = new Date(at)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
})

// 领奖台视觉顺序：2 - 1 - 3
function podiumOrder(rank: number) {
  return rank === 1 ? 'order-2' : rank === 2 ? 'order-1' : 'order-3'
}
function podiumDelay(rank: number) {
  return rank === 1 ? 120 : rank === 2 ? 260 : 400
}
function rankLabel(rank: number) {
  return rank === 1 ? 'CHAMPION' : rank === 2 ? 'RUNNER-UP' : 'THIRD'
}

function openDetail(player: any) {
  if (!player?.handles?.length) return
  selected.value = player
}

useHead({ title: '天梯排行榜 - 凯瑞甘生存2 Wiki' })
</script>

<style scoped>
.lb-root {
  --accent: #dc2626;
  --accent-soft: #ef4444;
  --accent-glow: rgba(220, 38, 38, 0.45);
  position: relative;
  max-width: 56rem;
  margin: 0 auto;
  padding: 0.5rem 0 4rem;
}
.board-survivor {
  --accent: #2563eb;
  --accent-soft: #3b82f6;
  --accent-glow: rgba(37, 99, 235, 0.45);
}

/* ---- 氛围背景 ---- */
.lb-bg {
  position: absolute;
  inset: -2rem -2rem 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}
.lb-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  transition: background 0.6s ease;
  will-change: transform;
}
.lb-orb-1 {
  width: 28rem; height: 28rem;
  top: -10rem; left: -6rem;
  background: radial-gradient(circle, var(--accent-glow), transparent 70%);
  animation: orbFloat 18s ease-in-out infinite;
}
.lb-orb-2 {
  width: 22rem; height: 22rem;
  top: 4rem; right: -8rem;
  background: radial-gradient(circle, var(--accent-glow), transparent 70%);
  opacity: 0.32;
  animation: orbFloat 22s ease-in-out infinite reverse;
}
@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(2rem, 1.5rem) scale(1.08); }
}
.lb-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, currentColor 1px, transparent 1px),
    linear-gradient(to bottom, currentColor 1px, transparent 1px);
  background-size: 44px 44px;
  color: rgba(100, 116, 139, 0.06);
  mask-image: radial-gradient(ellipse 80% 50% at 50% 0%, black, transparent 75%);
  -webkit-mask-image: radial-gradient(ellipse 80% 50% at 50% 0%, black, transparent 75%);
}
.dark .lb-grid { color: rgba(148, 163, 184, 0.07); }

/* ---- 页头 ---- */
.lb-header {
  position: relative;
  text-align: center;
  padding: 1.5rem 0 2rem;
}
.lb-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  color: var(--accent);
  text-transform: uppercase;
}
.lb-live-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--accent-soft);
  box-shadow: 0 0 0 0 var(--accent-glow);
  animation: livePulse 2s infinite;
}
@keyframes livePulse {
  0% { box-shadow: 0 0 0 0 var(--accent-glow); }
  70% { box-shadow: 0 0 0 8px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}
.lb-title {
  font-size: clamp(2.2rem, 6vw, 3.4rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.02;
  margin: 0.5rem 0 0.4rem;
  background: linear-gradient(120deg,
    rgb(17, 24, 39) 20%, var(--accent) 50%, rgb(17, 24, 39) 80%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: titleShine 6s linear infinite;
}
.dark .lb-title {
  background: linear-gradient(120deg,
    rgb(243, 244, 246) 20%, var(--accent-soft) 50%, rgb(243, 244, 246) 80%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
@keyframes titleShine {
  to { background-position: 200% center; }
}
.lb-sub {
  font-size: 0.875rem;
  color: rgb(107, 114, 128);
}
.dark .lb-sub { color: rgb(156, 163, 175); }
.lb-stamp {
  display: block;
  margin-top: 0.6rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: rgb(156, 163, 175);
}
.dark .lb-stamp { color: rgb(107, 114, 128); }

/* ---- 阵营切换 ---- */
.lb-switch {
  position: relative;
  display: flex;
  width: max-content;
  margin: 0 auto 2.5rem;
  padding: 0.3rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgb(229, 231, 235);
  box-shadow: 0 4px 16px rgba(0,0,0,0.05);
  backdrop-filter: blur(8px);
}
.dark .lb-switch {
  background: rgba(31, 41, 55, 0.6);
  border-color: rgb(55, 65, 81);
}
.lb-switch-glider {
  position: absolute;
  top: 0.3rem; bottom: 0.3rem;
  width: calc(50% - 0.3rem);
  border-radius: 999px;
  background: linear-gradient(135deg, var(--accent), var(--accent-soft));
  box-shadow: 0 4px 14px var(--accent-glow);
  transition: transform 0.42s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.3s;
  transform: translateX(0);
}
.lb-switch-glider.survivor { transform: translateX(100%); }
.lb-switch-btn {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.6rem 1.8rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: rgb(107, 114, 128);
  border-radius: 999px;
  transition: color 0.3s;
}
.dark .lb-switch-btn { color: rgb(156, 163, 175); }
.lb-switch-btn.active { color: #fff; }
.lb-switch-mark {
  width: 9px; height: 9px;
  border-radius: 2px;
  transform: rotate(45deg);
}
.mark-k { background: #ef4444; }
.mark-s { background: #3b82f6; }
.lb-switch-btn.active .lb-switch-mark { background: rgba(255,255,255,0.9); }

/* ---- 领奖台 ---- */
.lb-podium {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  align-items: end;
  margin-bottom: 2.5rem;
}
.lb-pod {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 2rem 0.75rem 1rem;
  border-radius: 1.25rem 1.25rem 0.5rem 0.5rem;
  cursor: pointer;
  overflow: hidden;
  background: rgba(255,255,255,0.85);
  border: 1px solid rgb(229, 231, 235);
  box-shadow: 0 10px 30px rgba(0,0,0,0.07);
  backdrop-filter: blur(6px);
  opacity: 0;
  animation: podRise 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.dark .lb-pod {
  background: rgba(31, 41, 55, 0.7);
  border-color: rgb(55, 65, 81);
}
.lb-pod:hover {
  transform: translateY(-6px);
  box-shadow: 0 18px 44px rgba(0,0,0,0.12);
}
@keyframes podRise {
  from { opacity: 0; transform: translateY(28px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.lb-pod.tier-1 {
  padding-top: 2.75rem;
  padding-bottom: 1.75rem;
  border-color: rgba(234, 179, 8, 0.5);
}
.lb-pod-aura {
  position: absolute;
  top: -40%; left: 50%;
  width: 120%; height: 80%;
  transform: translateX(-50%);
  opacity: 0;
  transition: opacity 0.4s;
  pointer-events: none;
}
.tier-1 .lb-pod-aura {
  opacity: 1;
  background: radial-gradient(ellipse at center, rgba(234,179,8,0.22), transparent 65%);
}
.tier-2 .lb-pod-aura {
  opacity: 1;
  background: radial-gradient(ellipse at center, rgba(148,163,184,0.18), transparent 65%);
}
.tier-3 .lb-pod-aura {
  opacity: 1;
  background: radial-gradient(ellipse at center, rgba(217,119,6,0.16), transparent 65%);
}
.lb-pod-medal {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem; height: 2.5rem;
  margin-bottom: 0.75rem;
  border-radius: 50%;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 1.05rem;
}
.tier-1 .lb-pod-medal {
  width: 3rem; height: 3rem;
  background: linear-gradient(135deg, #fde047, #ca8a04);
  color: #422006;
  box-shadow: 0 6px 18px rgba(202,138,4,0.5);
}
.tier-2 .lb-pod-medal {
  background: linear-gradient(135deg, #f1f5f9, #94a3b8);
  color: #1e293b;
  box-shadow: 0 6px 16px rgba(148,163,184,0.45);
}
.tier-3 .lb-pod-medal {
  background: linear-gradient(135deg, #fbbf24, #b45309);
  color: #fff;
  box-shadow: 0 6px 16px rgba(180,83,9,0.4);
}
.lb-crown {
  position: absolute;
  top: -1.35rem; left: 50%;
  transform: translateX(-50%);
  width: 1.6rem; height: 1.6rem;
  color: #facc15;
  filter: drop-shadow(0 2px 4px rgba(202,138,4,0.5));
  animation: crownBob 3s ease-in-out infinite;
}
@keyframes crownBob {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(-3px); }
}
.lb-pod-rank { line-height: 1; }
.lb-pod-name {
  font-weight: 600;
  font-size: 0.95rem;
  color: rgb(17, 24, 39);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tier-1 .lb-pod-name { font-size: 1.05rem; }
.dark .lb-pod-name { color: rgb(243, 244, 246); }
.lb-pod-id {
  font-size: 0.7rem;
  color: rgb(156, 163, 175);
  margin-top: 0.15rem;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lb-pod-mmr {
  margin-top: 0.6rem;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--accent);
}
.tier-1 .lb-pod-mmr { font-size: 1.85rem; }
.dark .lb-pod-mmr { color: var(--accent-soft); }
.lb-pod-unit {
  font-size: 0.6rem;
  font-weight: 500;
  letter-spacing: 0.1em;
  color: rgb(156, 163, 175);
  margin-left: 0.3rem;
}
.lb-pod-team {
  margin-top: 0.5rem;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, transparent);
}
.lb-pod-base {
  margin-top: 0.75rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.18em;
  color: rgb(203, 213, 225);
}
.dark .lb-pod-base { color: rgb(75, 85, 99); }

/* ---- 名次列表 ---- */
.lb-list {
  position: relative;
  border-radius: 1rem;
  overflow: hidden;
  background: rgba(255,255,255,0.7);
  border: 1px solid rgb(229, 231, 235);
  box-shadow: 0 8px 28px rgba(0,0,0,0.05);
  backdrop-filter: blur(6px);
}
.dark .lb-list {
  background: rgba(31, 41, 55, 0.55);
  border-color: rgb(55, 65, 81);
}
.lb-list-head {
  display: grid;
  grid-template-columns: 3rem 1fr auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.7rem 1.1rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgb(156, 163, 175);
  border-bottom: 1px solid rgb(229, 231, 235);
}
.dark .lb-list-head { border-color: rgb(55, 65, 81); }
.lb-list-head-mmr { text-align: right; padding-right: 1.85rem; }

.lb-row {
  position: relative;
  display: grid;
  grid-template-columns: 3rem 1fr auto auto;
  gap: 0.75rem;
  align-items: center;
  width: 100%;
  padding: 0.7rem 1.1rem;
  text-align: left;
  border-bottom: 1px solid rgb(243, 244, 246);
  opacity: 0;
  animation: rowIn 0.45s ease-out both;
  transition: background 0.2s ease;
}
.dark .lb-row { border-color: rgba(55, 65, 81, 0.6); }
.lb-row:last-child { border-bottom: none; }
.lb-row.is-clickable { cursor: pointer; }
.lb-row:hover { background: color-mix(in srgb, var(--accent) 6%, transparent); }
@keyframes rowIn {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}
.lb-row-bar {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--accent);
  transform: scaleY(0);
  transform-origin: center;
  transition: transform 0.25s ease;
}
.lb-row:hover .lb-row-bar { transform: scaleY(1); }
.lb-row-rank {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  font-size: 0.9rem;
  color: rgb(156, 163, 175);
  text-align: center;
  font-variant-numeric: tabular-nums;
}
.lb-row:hover .lb-row-rank { color: var(--accent); }
.lb-row-main { min-width: 0; }
.lb-row-name {
  font-weight: 500;
  font-size: 0.9rem;
  color: rgb(17, 24, 39);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dark .lb-row-name { color: rgb(243, 244, 246); }
.lb-row-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.15rem;
}
.lb-row-id {
  font-size: 0.72rem;
  color: rgb(156, 163, 175);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lb-row-team {
  flex-shrink: 0;
  padding: 0.05rem 0.45rem;
  border-radius: 4px;
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 11%, transparent);
}
.lb-row-score {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.lb-row-track {
  display: none;
  width: 5rem; height: 5px;
  border-radius: 999px;
  background: rgb(229, 231, 235);
  overflow: hidden;
}
.dark .lb-row-track { background: rgb(55, 65, 81); }
.lb-row-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 40%, transparent), var(--accent));
}
.lb-row-mmr {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 1rem;
  color: var(--accent);
  min-width: 3ch;
  text-align: right;
}
.dark .lb-row-mmr { color: var(--accent-soft); }
.lb-row-arrow {
  width: 1rem; height: 1rem;
  color: rgb(209, 213, 219);
  transition: transform 0.2s, color 0.2s;
}
.dark .lb-row-arrow { color: rgb(75, 85, 99); }
.lb-row:hover .lb-row-arrow {
  color: var(--accent);
  transform: translateX(3px);
}

/* ---- 骨架 / 错误 ---- */
.lb-skel-wrap { display: flex; flex-direction: column; gap: 0.75rem; }
.lb-skel {
  border-radius: 0.9rem;
  background: linear-gradient(100deg,
    rgba(0,0,0,0.04) 30%, rgba(0,0,0,0.07) 50%, rgba(0,0,0,0.04) 70%);
  background-size: 200% 100%;
  animation: skelShimmer 1.4s ease-in-out infinite;
}
.dark .lb-skel {
  background: linear-gradient(100deg,
    rgba(255,255,255,0.04) 30%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 70%);
  background-size: 200% 100%;
}
@keyframes skelShimmer {
  to { background-position: -200% 0; }
}
.lb-error {
  padding: 2.5rem;
  text-align: center;
  border-radius: 1rem;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

/* ---- 响应式 ---- */
@media (min-width: 640px) {
  .lb-podium { gap: 1.25rem; }
  .lb-row { grid-template-columns: 3.5rem 1fr auto auto; padding: 0.8rem 1.35rem; }
  .lb-row-track { display: block; }
  .lb-list-head { grid-template-columns: 3.5rem 1fr auto; padding-left: 1.35rem; }
}

@media (prefers-reduced-motion: reduce) {
  .lb-orb-1, .lb-orb-2, .lb-title, .lb-crown, .lb-live-dot,
  .lb-pod, .lb-row, .lb-skel {
    animation: none !important;
  }
  .lb-pod, .lb-row { opacity: 1 !important; }
}
</style>
