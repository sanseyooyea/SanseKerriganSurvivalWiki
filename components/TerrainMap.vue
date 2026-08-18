<template>
  <div>
    <!-- 地图选择器：缩略图横条 -->
    <div class="mb-3">
      <div class="flex items-center gap-2 mb-1.5">
        <span class="text-sm font-medium text-gray-600 dark:text-gray-300">地图</span>
        <span class="text-xs text-gray-400 dark:text-gray-500">共 {{ maps.length }} 张地形（缓存历史）</span>
      </div>
      <div class="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
        <button v-for="m in maps" :key="m.key" type="button" @click="selectMap(m.key)"
          class="group shrink-0 w-24 snap-start rounded-lg overflow-hidden border-2 transition text-left"
          :class="m.key === currentKey
            ? 'border-survivor-500 ring-1 ring-survivor-500/40'
            : 'border-surface-200 dark:border-gray-700 hover:border-survivor-300 dark:hover:border-survivor-700'">
          <div class="relative aspect-square bg-gray-900">
            <img :src="m.minimap" :alt="m.nameZh" loading="lazy"
              class="absolute inset-0 w-full h-full object-cover"
              :class="m.key === currentKey ? '' : 'opacity-80 group-hover:opacity-100'" />
            <span v-if="m.key === currentKey"
              class="absolute top-0.5 right-0.5 px-1 py-0.5 rounded bg-survivor-500 text-white text-[0.6rem] leading-none">当前</span>
          </div>
          <div class="px-1.5 py-1 bg-surface-50 dark:bg-gray-800">
            <div class="text-[0.72rem] font-medium text-gray-700 dark:text-gray-200 truncate">{{ m.nameZh }}</div>
            <div class="text-[0.62rem] text-gray-400 dark:text-gray-500 tabular-nums">
              {{ m.candidateCount }} 斜坡<span v-if="m.date"> · {{ m.date.slice(2) }}</span>
            </div>
          </div>
        </button>
      </div>
    </div>

    <!-- 控件条 -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2 mb-3">
      <!-- 模式切换 -->
      <div class="inline-flex rounded-lg border border-surface-200 dark:border-gray-600 overflow-hidden text-sm">
        <button type="button" @click="mode = 'candidates'"
          class="px-3 py-1.5 transition"
          :class="mode === 'candidates'
            ? 'bg-survivor-600 text-white'
            : 'bg-surface-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-600'">
          候选点
        </button>
        <button type="button" @click="mode = 'simulate'"
          class="px-3 py-1.5 transition border-l border-surface-200 dark:border-gray-600"
          :class="mode === 'simulate'
            ? 'bg-survivor-600 text-white'
            : 'bg-surface-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-600'">
          模拟一局
        </button>
      </div>

      <!-- 模拟控件 -->
      <template v-if="mode === 'simulate'">
        <button type="button" @click="reroll" :disabled="!view"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-kerrigan-200 dark:border-kerrigan-800 bg-kerrigan-50 dark:bg-kerrigan-800/20 text-kerrigan-700 dark:text-kerrigan-200 hover:bg-kerrigan-100 dark:hover:bg-kerrigan-800/40 transition disabled:opacity-50">
          <span aria-hidden="true">🎲</span> 重掷一局
        </button>
        <label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
          <span class="whitespace-nowrap">石头率</span>
          <input type="range" min="0.3" max="0.8" step="0.05" v-model.number="rockProb"
            class="accent-survivor-600 w-28" />
          <span class="font-mono w-9 text-right">{{ rockProb.toFixed(2) }}</span>
        </label>
        <span class="text-sm text-gray-500 dark:text-gray-400">
          石头 <span class="font-mono font-semibold text-survivor-600 dark:text-survivor-400">{{ sim.placed.length }}</span>
          / 候选 {{ sim.count }}
          <span class="text-gray-400 dark:text-gray-500">· 种子 {{ seed }}</span>
        </span>
      </template>
      <template v-else>
        <span class="text-sm text-gray-500 dark:text-gray-400">
          候选斜坡 <span class="font-mono font-semibold text-survivor-600 dark:text-survivor-400">{{ candidates.length }}</span> 处
        </span>
      </template>

      <button type="button" @click="resetView"
        class="ml-auto px-2.5 py-1.5 text-xs rounded-lg border border-surface-200 dark:border-gray-600 bg-surface-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-surface-100 dark:hover:bg-gray-600 transition">
        重置视图
      </button>
    </div>

    <!-- 视口 -->
    <div ref="viewport"
      class="relative w-full aspect-square rounded-xl overflow-hidden border border-surface-200 dark:border-gray-700 bg-gray-900 select-none touch-none"
      :class="dragging ? 'cursor-grabbing' : 'cursor-grab'"
      @wheel.prevent="onWheel"
      @pointerdown="onDown" @pointermove="onMove" @pointerup="onUp" @pointerleave="onUp">
      <div v-if="view" class="absolute inset-0 origin-top-left will-change-transform"
        :style="{ transform: `translate(${tx}px, ${ty}px) scale(${scale})` }">
        <img :src="view.data.minimap.path" :alt="`${view.data.nameZh} 小地图`"
          class="absolute inset-0 w-full h-full object-cover pointer-events-none" draggable="false" />
        <svg class="absolute inset-0 w-full h-full overflow-visible"
          viewBox="0 0 1024 1024" preserveAspectRatio="none">
          <g v-for="c in markers" :key="c.n">
            <circle :cx="px(c).px" :cy="px(c).py" :r="markerR"
              :class="c.on
                ? 'fill-survivor-500/85 stroke-white/90'
                : 'fill-white/25 stroke-white/40'"
              :stroke-width="1.2 / scale"
              class="transition-colors"
              @pointerenter="hovered = c" @pointerleave="hovered = null" />
          </g>
        </svg>
      </div>

      <!-- 加载态 -->
      <div v-if="loading || !view"
        class="absolute inset-0 flex items-center justify-center text-gray-400 text-sm bg-gray-900/60 backdrop-blur-sm">
        <span class="animate-pulse">载入地形…</span>
      </div>

      <!-- 悬浮信息 -->
      <div v-if="hovered"
        class="absolute top-2 left-2 px-2.5 py-1.5 rounded-lg bg-black/70 text-white text-xs font-mono pointer-events-none backdrop-blur-sm">
        Ramp{{ hovered.n }} · ({{ hovered.x.toFixed(1) }}, {{ hovered.y.toFixed(1) }})
        <span v-if="mode === 'simulate'" :class="hovered.on ? 'text-survivor-300' : 'text-gray-400'">
          · {{ hovered.on ? '有石头' : '空' }}
        </span>
      </div>

      <!-- 图例 -->
      <div class="absolute bottom-2 left-2 flex items-center gap-3 px-2.5 py-1.5 rounded-lg bg-black/55 text-white text-[0.7rem] backdrop-blur-sm pointer-events-none">
        <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-survivor-500 border border-white/80"></span>{{ mode === 'simulate' ? '本局石头' : '候选斜坡' }}</span>
        <span v-if="mode === 'simulate'" class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-white/25 border border-white/40"></span>空候选</span>
      </div>
    </div>

    <p class="mt-2 text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
      滚轮缩放、拖拽平移。石头由 <code class="font-mono">Scripts/game/rocks.galaxy</code> 每局从候选斜坡随机生成，
      此处「模拟一局」按同款算法（洗牌 + 按石头率取数 + 寻路校验 + 逐个移除坏石头）复刻，重掷得到不同布局。
      <span class="text-gray-400/80 dark:text-gray-500/80">寻路校验含悬崖跨格判定（可走地面 + 高度层差 ≤ {{ view?.cliffStep ?? 48 }}），
      会封住斜坡的石头一律剔除，故<span class="text-survivor-500 dark:text-survivor-400">不会出现被石头封死、无法进入的区域</span>；仍为近似，不含水/单位半径。</span>
    </p>
  </div>
</template>

<script setup lang="ts">
import { simulateRocks, type SimResult } from '~/composables/useRockSimulator'
import type { RockCandidate, TerrainView } from '~/composables/useTerrainData'

const { maps, defaultMap, loadMap } = useTerrainData()

const currentKey = ref(defaultMap)
const view = shallowRef<TerrainView | null>(null)
const loading = ref(false)

const mode = ref<'candidates' | 'simulate'>('candidates')
const rockProb = ref(0.5)
const seed = ref(1)

const emptySim: SimResult = { placed: [], rejected: [], n: 0, count: 0, maxElongation: 0, reclaimed: 0 }
const sim = ref<SimResult>({ ...emptySim })

const candidates = computed<RockCandidate[]>(() => (view.value?.data.rockCandidates ?? []) as RockCandidate[])

async function selectMap(key: string) {
  if (key === currentKey.value && view.value) return
  currentKey.value = key
  loading.value = true
  hovered.value = null
  try {
    const v = await loadMap(key)
    view.value = v
    rockProb.value = v.data.rockProbDefault
    seed.value = 1
    sim.value = { ...emptySim, count: v.data.rockCandidates.length }
    resetView()
    if (mode.value === 'simulate') runSim()
  } finally {
    loading.value = false
  }
}

function runSim() {
  const v = view.value
  if (!v) return
  const grid = { isPassable: v.isPassable, cliffAt: v.cliffAt, cliffStep: v.cliffStep, size: v.data.worldSize }
  sim.value = simulateRocks(v.data.rockCandidates as RockCandidate[], grid, rockProb.value, seed.value)
}
function reroll() {
  seed.value = (seed.value * 1103515245 + 12345) & 0x7fffffff || 1
  runSim()
}
watch(rockProb, () => { if (mode.value === 'simulate') runSim() })
watch(mode, (m) => { if (m === 'simulate' && sim.value.placed.length === 0) runSim() })

onMounted(() => { selectMap(currentKey.value) })

// 标记：候选模式全部显示；模拟模式区分有/无石头
const placedSet = computed(() => new Set(sim.value.placed.map(c => c.n)))
interface Marker extends RockCandidate { on: boolean }
const markers = computed<Marker[]>(() =>
  candidates.value.map(c => ({
    ...c,
    on: mode.value === 'simulate' ? placedSet.value.has(c.n) : true,
  })),
)
const hovered = ref<Marker | null>(null)

function px(c: RockCandidate) { return view.value!.worldToPx(c.x, c.y) }
const markerR = computed(() => 5 / scale.value)

// —— 平移缩放 —— //
const viewport = ref<HTMLElement | null>(null)
const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const dragging = ref(false)
let startX = 0
let startY = 0
let startTx = 0
let startTy = 0

function resetView() { scale.value = 1; tx.value = 0; ty.value = 0 }

function onWheel(e: WheelEvent) {
  const rect = viewport.value?.getBoundingClientRect()
  if (!rect) return
  const cx = e.clientX - rect.left
  const cy = e.clientY - rect.top
  const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15
  const next = Math.min(8, Math.max(1, scale.value * factor))
  const wx = (cx - tx.value) / scale.value
  const wy = (cy - ty.value) / scale.value
  scale.value = next
  tx.value = cx - wx * next
  ty.value = cy - wy * next
  clampPan(rect)
}

function onDown(e: PointerEvent) {
  dragging.value = true
  startX = e.clientX; startY = e.clientY
  startTx = tx.value; startTy = ty.value
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}
function onMove(e: PointerEvent) {
  if (!dragging.value) return
  tx.value = startTx + (e.clientX - startX)
  ty.value = startTy + (e.clientY - startY)
  const rect = viewport.value?.getBoundingClientRect()
  if (rect) clampPan(rect)
}
function onUp() { dragging.value = false }

// 松散夹取：始终保留至少 25% 视口内有图像，避免拖飞
function clampPan(rect: DOMRect) {
  const w = rect.width * scale.value
  const h = rect.height * scale.value
  const mx = rect.width * 0.25
  const my = rect.height * 0.25
  tx.value = Math.min(rect.width - mx, Math.max(mx - w, tx.value))
  ty.value = Math.min(rect.height - my, Math.max(my - h, ty.value))
}
</script>
