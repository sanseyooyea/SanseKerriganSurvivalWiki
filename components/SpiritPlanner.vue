<template>
  <div class="sp-planner">
    <div class="spp-head">
      <h3 class="spp-title">⚡ 灵魂经济路径规划器</h3>
      <p class="spp-sub">输入当前资源与剩余时间，按已核实的游戏数值推演最优发展路线（理论上界，实战受操作/锁定影响会略低）。</p>
    </div>

    <!-- 输入区 -->
    <div class="spp-inputs">
      <label class="spp-field">
        <span>当前矿物</span>
        <input v-model.number="minerals" type="number" min="0" />
      </label>
      <label class="spp-field">
        <span>当前气体</span>
        <input v-model.number="gas" type="number" min="0" />
      </label>
      <label class="spp-field">
        <span>剩余时间（秒）</span>
        <input v-model.number="timeSec" type="number" min="0" />
      </label>
      <label class="spp-check">
        <input v-model="hasPylon" type="checkbox" />
        <span>已有水晶供电（股市可用）</span>
      </label>
    </div>

    <!-- 结果摘要 -->
    <div v-if="result" class="spp-summary">
      <div class="spp-stat">
        <div class="spp-stat-v">{{ result.finalWealth.toLocaleString() }}</div>
        <div class="spp-stat-l">预期终局矿物</div>
      </div>
      <div class="spp-stat">
        <div class="spp-stat-v">×{{ result.growthX.toFixed(1) }}</div>
        <div class="spp-stat-l">财富增长倍数</div>
      </div>
      <div class="spp-stat">
        <div class="spp-stat-v">{{ Math.round(timeSec / 60) }}分</div>
        <div class="spp-stat-l">规划时长</div>
      </div>
    </div>

    <!-- 时间线 -->
    <div v-if="result" class="spp-timeline">
      <div v-for="(s, i) in result.steps" :key="i" class="spp-step" :class="`k-${s.kind}`">
        <div class="spp-step-time">{{ fmtTime(s.tStart) }}<template v-if="s.tEnd > s.tStart"> – {{ fmtTime(s.tEnd) }}</template></div>
        <div class="spp-step-body">
          <div class="spp-step-action">{{ s.action }}</div>
          <div class="spp-step-detail">{{ s.detail }}</div>
        </div>
      </div>
    </div>

    <!-- 提示 -->
    <ul v-if="result && result.notes.length" class="spp-notes">
      <li v-for="(n, i) in result.notes" :key="i">{{ n }}</li>
    </ul>

    <p class="spp-disclaimer">
      模型基于已核实常数：银行每3.5s复利1%、股市每9.9s×6复利（乘数1.0925+运气/5，需供电）、
      运气120s时效、轮盘净期望+53矿。结果为理论上界，实战因手动操作、60s锁定、运气波动会有出入。
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { solveSpiritPlan } from '~/composables/useSpiritPlanner'

const minerals = ref(1000)
const gas = ref(100)
const timeSec = ref(600)
const hasPylon = ref(true)

const result = computed(() => {
  if (timeSec.value <= 0) return null
  return solveSpiritPlan({
    minerals: minerals.value || 0,
    gas: gas.value || 0,
    timeSec: timeSec.value || 0,
    hasPylon: hasPylon.value,
  })
})

function fmtTime(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`
}
</script>

<style scoped>
.sp-planner {
  margin-top: 1.5rem; padding: 1.25rem; border-radius: 0.9rem;
  border: 1px solid rgba(139,92,246,0.25);
  background: linear-gradient(135deg, rgba(139,92,246,0.06), rgba(217,70,239,0.04));
}
.dark .sp-planner { border-color: rgba(139,92,246,0.3); background: linear-gradient(135deg, rgba(139,92,246,0.12), rgba(217,70,239,0.08)); }
.spp-title { font-size: 1rem; font-weight: 800; color: rgb(124,58,237); }
.dark .spp-title { color: rgb(196,181,253); }
.spp-sub { font-size: 0.72rem; line-height: 1.55; color: rgb(107,114,128); margin-top: 0.3rem; }
.dark .spp-sub { color: rgb(156,163,175); }

.spp-inputs { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1rem 0; align-items: end; }
.spp-field { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.7rem; color: rgb(107,114,128); }
.spp-field input {
  width: 110px; padding: 0.4rem 0.55rem; border-radius: 0.5rem; font-size: 0.85rem;
  border: 1px solid rgb(209,213,219); background: rgba(255,255,255,0.8); color: rgb(31,41,55);
}
.dark .spp-field input { border-color: rgb(75,85,99); background: rgba(17,24,39,0.6); color: rgb(229,231,235); }
.spp-check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.72rem; color: rgb(75,85,99); }
.dark .spp-check { color: rgb(156,163,175); }

.spp-summary { display: flex; gap: 0.6rem; margin: 1rem 0; flex-wrap: wrap; }
.spp-stat { flex: 1; min-width: 100px; text-align: center; padding: 0.7rem; border-radius: 0.7rem; background: rgba(139,92,246,0.08); }
.dark .spp-stat { background: rgba(139,92,246,0.14); }
.spp-stat-v { font-size: 1.3rem; font-weight: 800; color: rgb(124,58,237); }
.dark .spp-stat-v { color: rgb(196,181,253); }
.spp-stat-l { font-size: 0.62rem; color: rgb(156,163,175); margin-top: 0.2rem; }

.spp-timeline { display: flex; flex-direction: column; gap: 0.4rem; margin: 1rem 0; }
.spp-step { display: flex; gap: 0.75rem; padding: 0.55rem 0.7rem; border-radius: 0.6rem; background: rgba(255,255,255,0.5); border-left: 3px solid rgb(156,163,175); }
.dark .spp-step { background: rgba(31,41,55,0.4); }
.spp-step.k-market { border-left-color: rgb(16,185,129); }
.spp-step.k-bank { border-left-color: rgb(59,130,246); }
.spp-step.k-divine { border-left-color: rgb(139,92,246); }
.spp-step.k-cashout { border-left-color: rgb(234,179,8); }
.spp-step-time { font-family: monospace; font-size: 0.72rem; font-weight: 600; color: rgb(107,114,128); min-width: 90px; }
.spp-step-action { font-size: 0.8rem; font-weight: 700; color: rgb(31,41,55); }
.dark .spp-step-action { color: rgb(229,231,235); }
.spp-step-detail { font-size: 0.68rem; color: rgb(107,114,128); margin-top: 0.1rem; }
.dark .spp-step-detail { color: rgb(156,163,175); }

.spp-notes { margin: 0.75rem 0; padding-left: 1.1rem; display: flex; flex-direction: column; gap: 0.25rem; }
.spp-notes li { font-size: 0.7rem; color: rgb(107,114,128); list-style: disc; }
.dark .spp-notes li { color: rgb(156,163,175); }
.spp-disclaimer { font-size: 0.62rem; line-height: 1.5; color: rgb(156,163,175); margin-top: 0.75rem; padding-top: 0.6rem; border-top: 1px dashed rgba(156,163,175,0.3); }
</style>
