<template>
  <div class="rounded-xl border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 p-3">
    <div ref="trackEl" class="relative select-none" :style="{ height: totalH + 'px' }"
      @pointerdown="onDown" @pointermove="onMove" @pointerup="onUp" @pointerleave="onLeave">
      <!-- 泳道 -->
      <div v-for="(lane, li) in lanes" :key="lane.key" class="absolute left-0 right-0 flex items-center"
        :style="{ top: (AXIS_H + DENSITY_H + li * LANE_H) + 'px', height: LANE_H + 'px' }">
        <span class="w-10 shrink-0 text-[11px] text-gray-400 dark:text-gray-500">{{ lane.label }}</span>
        <div class="relative flex-1 h-full border-t border-surface-100 dark:border-gray-700/60" />
      </div>

      <!-- 刻度 -->
      <div class="absolute left-10 right-0 top-0" :style="{ height: AXIS_H + 'px' }">
        <span v-for="tk in ticks" :key="tk" class="absolute -translate-x-1/2 text-[10px] font-mono text-gray-400 tabular-nums"
          :style="{ left: pct(tk) }">{{ fmtLoop(tk) }}</span>
      </div>

      <!-- 战斗强度（每段时间的死亡数） -->
      <svg class="absolute left-10 right-0" :style="{ top: AXIS_H + 'px', height: DENSITY_H + 'px', width: 'calc(100% - 2.5rem)' }"
        :viewBox="`0 0 ${BINS} 1`" preserveAspectRatio="none">
        <rect v-for="(v, i) in density" :key="i" :x="i + 0.1" :width="0.8" :y="1 - v" :height="v"
          class="fill-gray-300 dark:fill-gray-600" />
      </svg>

      <!-- 事件点 -->
      <div class="absolute left-10 right-0 top-0 bottom-0 pointer-events-none">
        <template v-for="m in marks" :key="m.k">
          <span class="absolute -translate-x-1/2 -translate-y-1/2 flex items-center justify-center"
            :style="{ left: pct(m.t), top: m.y + 'px' }">
            <span v-if="m.shape === 'diamond'" class="block w-2.5 h-2.5 rotate-45 ring-2 ring-white dark:ring-gray-800"
              :style="{ background: m.color }" />
            <span v-else-if="m.shape === 'x'" class="block text-[13px] leading-none font-bold" :style="{ color: m.color }">✕</span>
            <span v-else class="block w-2 h-2 rounded-full ring-1 ring-white dark:ring-gray-800" :style="{ background: m.color }" />
          </span>
        </template>
        <!-- 播放头 -->
        <div class="absolute top-0 bottom-0 w-0.5 bg-amber-500" :style="{ left: pct(t) }">
          <div class="absolute -top-0.5 -left-[5px] w-3 h-3 rounded-full bg-amber-500" />
        </div>
        <!-- 悬停竖线 -->
        <div v-if="hover" class="absolute top-0 bottom-0 w-px bg-gray-400/60" :style="{ left: hover.x + 'px' }" />
      </div>

      <!-- 悬停提示 -->
      <div v-if="hover" class="rt-tip" :style="tipStyle">
        <div class="font-mono text-[10px] text-slate-400">{{ fmtLoop(hover.t) }}</div>
        <div v-for="(ev, i) in hover.events" :key="i" class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: ev.color }" />
          <span>{{ ev.text }}</span>
        </div>
        <div v-if="hover.more" class="text-[10px] text-slate-400">…另有 {{ hover.more }} 条</div>
      </div>
    </div>

    <!-- 事件列表（可点击跳转，同时充当可访问的文本视图） -->
    <details class="mt-2 group">
      <summary class="cursor-pointer text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
        事件列表（{{ listEvents.length }}）
      </summary>
      <ol class="mt-2 max-h-64 overflow-y-auto text-xs divide-y divide-surface-100 dark:divide-gray-700/60">
        <li v-for="(ev, i) in listEvents" :key="i">
          <button type="button" @click="emit('seek', ev.t - 3 * LOOPS_PER_SEC)"
            class="w-full flex items-center gap-2 px-1 py-1 text-left hover:bg-surface-50 dark:hover:bg-gray-700/40"
            :class="ev.t <= t ? 'text-gray-700 dark:text-gray-200' : 'text-gray-400 dark:text-gray-500'">
            <span class="font-mono w-14 shrink-0 tabular-nums">{{ fmtLoop(ev.t) }}</span>
            <span class="w-2 h-2 rounded-full shrink-0" :style="{ background: ev.color }" />
            <span class="truncate">{{ ev.text }}</span>
          </button>
        </li>
      </ol>
    </details>
  </div>
</template>

<script setup lang="ts">
import { type ReplayData, type ReplayEvent, type ReplayPlayer, fmtLoop, roleLabel, LOOPS_PER_SEC } from '~/utils/replay'

const props = defineProps<{
  data: ReplayData
  t: number
  lanes: { key: string; label: string; kinds: string[] }[]
  playersByPid: Record<number, ReplayPlayer>
}>()
const emit = defineEmits<{ seek: [loop: number] }>()

const AXIS_H = 16
const DENSITY_H = 22
const LANE_H = 22
const BINS = 120
const totalH = computed(() => AXIS_H + DENSITY_H + props.lanes.length * LANE_H)
const end = computed(() => props.data.meta.loops || 1)
const pct = (loop: number) => `${(loop / end.value) * 100}%`

const ticks = computed(() => {
  const totalSec = end.value / LOOPS_PER_SEC
  const step = [60, 120, 300, 600].find(s => totalSec / s <= 8) ?? 900
  const out: number[] = []
  for (let s = 0; s <= totalSec; s += step) out.push(s * LOOPS_PER_SEC)
  return out
})

const density = computed(() => {
  const D = props.data.deaths
  const bins = new Array(BINS).fill(0)
  for (let i = 0; i < D.length; i += 4) {
    const b = Math.min(BINS - 1, Math.floor(D[i] / end.value * BINS))
    bins[b]++
  }
  const mx = Math.max(1, ...bins)
  return bins.map(v => Math.sqrt(v / mx)) // 开方：低强度也看得见
})

const P = computed(() => props.playersByPid)
const name = (pid: number | null | undefined) => {
  if (pid == null) return '环境'
  const p = P.value[pid]
  return p ? `${p.name}（${roleLabel(p)}）` : `玩家${pid}`
}
const unitName = (id: string) => props.data.types.find(x => x.id === id)?.nameZh || id
const upName = (id: string) => props.data.upgrades[id]?.nameZh || id

function describe(e: ReplayEvent): string {
  switch (e.kind) {
    case 'game_start': return '对局开始（虫道出现）'
    case 'kerrigan': return `凯瑞甘出场 · ${name(e.pid)}`
    case 'hero_death': return `${name(e.pid)} 的英雄阵亡${e.killer ? ' ← ' + name(e.killer) : ''}`
    case 'ghost': return `${name(e.pid)} 成为幽灵`
    case 'boss_kill': return `${name(e.pid)} 击杀 ${unitName(e.unit)}`
    case 'upgrade': return `${e.team === 1 ? '凯瑞甘方' : name(e.pid)} 完成科技：${upName(e.upgrade)}`
    case 'leave': return `${name(e.pid)} 离开游戏`
    case 'chat': return `${name(e.pid)}：${e.text}`
    case 'ping': return `${name(e.pid)} 小地图信号`
    case 'game_end': return e.winningTeam === 1 ? '凯瑞甘方胜利' : '幸存者胜利'
  }
}
function colorOf(e: ReplayEvent): string {
  if ('pid' in e && e.pid != null) return P.value[e.pid]?.color ?? '#9ca3af'
  if (e.kind === 'game_end') return e.winningTeam === 1 ? '#dc2626' : '#2563eb'
  return '#6b7280'
}
function shapeOf(e: ReplayEvent): 'dot' | 'diamond' | 'x' {
  if (e.kind === 'hero_death') return 'x'
  if (e.kind === 'game_start' || e.kind === 'game_end' || e.kind === 'kerrigan' || e.kind === 'boss_kill') return 'diamond'
  return 'dot'
}

const laneOf = computed(() => {
  const m: Record<string, number> = {}
  props.lanes.forEach((l, i) => l.kinds.forEach(k => { m[k] = i }))
  return m
})

const marks = computed(() => props.data.events
  .filter(e => laneOf.value[e.kind] != null)
  .map((e, i) => ({
    k: i, t: e.t, color: colorOf(e), shape: shapeOf(e),
    y: AXIS_H + DENSITY_H + laneOf.value[e.kind] * LANE_H + LANE_H / 2,
  })))

const listEvents = computed(() => props.data.events
  .filter(e => laneOf.value[e.kind] != null)
  .map(e => ({ t: e.t, color: colorOf(e), text: describe(e) })))

// ---------- 交互：拖动 = 拖播放头；悬停 = 附近事件提示 ----------
const trackEl = ref<HTMLDivElement>()
let dragging = false
const hover = ref<{ x: number; t: number; lane: number; events: { color: string; text: string }[]; more: number } | null>(null)

function locate(e: PointerEvent) {
  const rect = trackEl.value!.getBoundingClientRect()
  const left = 40 // w-10
  const w = rect.width - left
  const x = Math.min(Math.max(0, e.clientX - rect.left - left), w)
  return { x, w, y: e.clientY - rect.top, loop: (x / w) * end.value }
}
function onDown(e: PointerEvent) {
  dragging = true
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  const { loop } = locate(e)
  // 点击事件点附近时吸附到该事件（前 3 秒）
  const near = nearestEvents(e)
  emit('seek', near.length ? near[0].t - 3 * LOOPS_PER_SEC : loop)
}
function onUp() { dragging = false }
function onLeave() { if (!dragging) hover.value = null }

function nearestEvents(e: PointerEvent) {
  const { x, w, y } = locate(e)
  const lane = Math.floor((y - AXIS_H - DENSITY_H) / LANE_H)
  if (lane < 0 || lane >= props.lanes.length) return []
  const kinds = props.lanes[lane].kinds
  const tol = 6 / w * end.value // 6px 命中半径
  const xLoop = (x / w) * end.value
  return props.data.events
    .filter(ev => kinds.includes(ev.kind) && Math.abs(ev.t - xLoop) <= tol)
    .sort((a, b) => Math.abs(a.t - xLoop) - Math.abs(b.t - xLoop))
}
function onMove(e: PointerEvent) {
  const { x, loop, y } = locate(e)
  if (dragging) { emit('seek', loop); hover.value = null; return }
  const near = nearestEvents(e)
  const lane = Math.floor((y - AXIS_H - DENSITY_H) / LANE_H)
  hover.value = {
    x, t: near.length ? near[0].t : loop, lane,
    events: near.slice(0, 6).map(ev => ({ color: colorOf(ev), text: describe(ev) })),
    more: Math.max(0, near.length - 6),
  }
}
const tipStyle = computed(() => {
  const h = hover.value
  if (!h) return ''
  const w = trackEl.value?.clientWidth ?? 0
  const right = h.x + 40 > w * 0.6
  return `left:${h.x + 40}px; top:${totalH.value + 4}px; ${right ? 'transform:translateX(-100%)' : ''}`
})
</script>

<style scoped>
.rt-tip {
  position: absolute;
  pointer-events: none;
  background: rgba(15, 25, 35, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 11px;
  color: #e2e8f0;
  z-index: 20;
  max-width: 22rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
</style>
