<template>
  <div ref="wrap" class="lc-wrap" :style="`height:${height}px`">
    <svg v-if="width > 0" :width="width" :height="height" class="lc-svg"
      @mousemove="onMove" @mouseleave="hoverX = null">
      <!-- horizontal grid + y ticks -->
      <g class="lc-grid">
        <template v-for="t in yTicks" :key="'y' + t">
          <line :x1="padL" :x2="width - padR" :y1="yScale(t)" :y2="yScale(t)" />
          <text :x="padL - 6" :y="yScale(t) + 3" text-anchor="end">{{ yFormat(t) }}</text>
        </template>
      </g>
      <!-- x ticks -->
      <g class="lc-xaxis">
        <text v-for="(t, i) in xTicks" :key="'x' + i" :x="xScale(t)" :y="height - 6" text-anchor="middle">
          {{ xFormat(t) }}
        </text>
      </g>
      <!-- optional reference line (e.g. 50%) -->
      <line v-if="refY != null" class="lc-ref" :x1="padL" :x2="width - padR"
        :y1="yScale(refY)" :y2="yScale(refY)" />
      <!-- series paths -->
      <path v-for="s in series" :key="s.label" :d="pathFor(s)" fill="none"
        :stroke="s.color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
      <!-- hover crosshair + dots + tooltip -->
      <template v-if="hover">
        <line class="lc-cross" :x1="hover.x" :x2="hover.x" :y1="padT" :y2="height - padB" />
        <circle v-for="d in hover.dots" :key="d.label" :cx="hover.x" :cy="d.y" r="3.5"
          :fill="d.color" stroke="#fff" stroke-width="1" />
      </template>
    </svg>
    <!-- tooltip (HTML, positioned over svg) -->
    <div v-if="hover" class="lc-tip" :style="tipStyle">
      <div class="lc-tip-x">{{ xFormat(hover.xv) }}</div>
      <div v-for="d in hover.dots" :key="d.label" class="lc-tip-row">
        <span class="lc-tip-dot" :style="`background:${d.color}`"></span>
        <span class="lc-tip-label">{{ d.label }}</span>
        <span class="lc-tip-val">{{ yFormat(d.v) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface Series {
  label: string
  color: string
  points: [number, number][] // [x, y], x ascending
}

const props = withDefaults(defineProps<{
  series: Series[]
  height?: number
  yMin?: number | null
  yMax?: number | null
  refY?: number | null
  xFormat?: (x: number) => string
  yFormat?: (y: number) => string
}>(), {
  height: 240,
  yMin: null,
  yMax: null,
  refY: null,
  xFormat: (x: number) => String(x),
  yFormat: (y: number) => String(Math.round(y)),
})

const padL = 44
const padR = 14
const padT = 12
const padB = 22

const wrap = ref<HTMLElement>()
const width = ref(0)
let ro: ResizeObserver | null = null
onMounted(() => {
  ro = new ResizeObserver(entries => {
    width.value = entries[0].contentRect.width
  })
  if (wrap.value) ro.observe(wrap.value)
})
onBeforeUnmount(() => ro?.disconnect())

// data domain across all visible series
const allPts = computed(() => props.series.flatMap(s => s.points))
const xDomain = computed<[number, number]>(() => {
  const xs = allPts.value.map(p => p[0])
  if (!xs.length) return [0, 1]
  const lo = Math.min(...xs), hi = Math.max(...xs)
  return lo === hi ? [lo - 1, hi + 1] : [lo, hi]
})
const yDomain = computed<[number, number]>(() => {
  const ys = allPts.value.map(p => p[1])
  let lo = props.yMin != null ? props.yMin : (ys.length ? Math.min(...ys) : 0)
  let hi = props.yMax != null ? props.yMax : (ys.length ? Math.max(...ys) : 1)
  if (lo === hi) { lo -= 1; hi += 1 }
  const pad = (hi - lo) * 0.08
  return [props.yMin != null ? lo : lo - pad, props.yMax != null ? hi : hi + pad]
})

function xScale(x: number): number {
  const [lo, hi] = xDomain.value
  return padL + ((x - lo) / (hi - lo)) * (width.value - padL - padR)
}
function yScale(y: number): number {
  const [lo, hi] = yDomain.value
  return padT + (1 - (y - lo) / (hi - lo)) * (props.height - padT - padB)
}

function pathFor(s: Series): string {
  return s.points
    .map((p, i) => `${i ? 'L' : 'M'}${xScale(p[0]).toFixed(1)},${yScale(p[1]).toFixed(1)}`)
    .join(' ')
}

// nice-ish tick generation
function ticks(lo: number, hi: number, count: number): number[] {
  if (lo === hi) return [lo]
  const step = (hi - lo) / count
  return Array.from({ length: count + 1 }, (_, i) => lo + step * i)
}
const yTicks = computed(() => ticks(yDomain.value[0], yDomain.value[1], 4))
const xTicks = computed(() => {
  const [lo, hi] = xDomain.value
  return ticks(lo, hi, Math.min(5, Math.max(2, allPts.value.length - 1)))
})

// hover: snap to nearest x among the union of series x-values
const hoverX = ref<number | null>(null)
function onMove(e: MouseEvent) {
  const rect = (e.currentTarget as SVGElement).getBoundingClientRect()
  hoverX.value = e.clientX - rect.left
}
const hover = computed(() => {
  if (hoverX.value == null || !allPts.value.length) return null
  const [lo, hi] = xDomain.value
  // invert pixel -> data x
  const frac = (hoverX.value - padL) / (width.value - padL - padR)
  const xv0 = lo + frac * (hi - lo)
  // snap to nearest existing x across series
  const xs = Array.from(new Set(allPts.value.map(p => p[0]))).sort((a, b) => a - b)
  let xv = xs[0]
  for (const x of xs) if (Math.abs(x - xv0) < Math.abs(xv - xv0)) xv = x
  const dots = props.series
    .map(s => {
      const pt = s.points.find(p => p[0] === xv)
      return pt ? { label: s.label, color: s.color, v: pt[1], y: yScale(pt[1]) } : null
    })
    .filter(Boolean) as { label: string; color: string; v: number; y: number }[]
  if (!dots.length) return null
  return { x: xScale(xv), xv, dots }
})
const tipStyle = computed(() => {
  if (!hover.value) return ''
  const left = hover.value.x > width.value / 2 ? hover.value.x - 8 : hover.value.x + 8
  const anchor = hover.value.x > width.value / 2 ? 'translateX(-100%)' : ''
  return `left:${left}px; top:${padT}px; transform:${anchor}`
})
</script>

<style scoped>
.lc-wrap { position: relative; width: 100%; }
.lc-svg { display: block; overflow: visible; }
.lc-grid line { stroke: rgba(148, 163, 184, 0.22); stroke-width: 1; }
.lc-grid text { fill: #94a3b8; font-size: 10px; font-family: 'JetBrains Mono', monospace; }
.lc-xaxis text { fill: #94a3b8; font-size: 10px; font-family: 'JetBrains Mono', monospace; }
.lc-ref { stroke: rgba(148, 163, 184, 0.55); stroke-width: 1; stroke-dasharray: 4 4; }
.lc-cross { stroke: rgba(100, 116, 139, 0.5); stroke-width: 1; stroke-dasharray: 3 3; }
.lc-tip {
  position: absolute;
  pointer-events: none;
  background: rgba(15, 25, 35, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 11px;
  color: #e2e8f0;
  z-index: 10;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.lc-tip-x { font-family: 'JetBrains Mono', monospace; color: #94a3b8; margin-bottom: 3px; font-size: 10px; }
.lc-tip-row { display: flex; align-items: center; gap: 6px; }
.lc-tip-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.lc-tip-label { flex: 1; }
.lc-tip-val { font-family: 'JetBrains Mono', monospace; font-weight: 700; }
</style>
