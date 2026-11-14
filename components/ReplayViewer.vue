<template>
  <div class="space-y-4">
    <!-- 对局概要 -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500 dark:text-gray-400">
      <span class="font-medium text-gray-800 dark:text-gray-100">{{ mapName }}</span>
      <span>{{ dateText }}</span>
      <span class="font-mono">{{ fmtLoop(data.meta.loops) }}</span>
      <span v-if="winnerText"
        class="px-2 py-0.5 rounded-md text-xs font-medium"
        :class="data.meta.winningTeam === 1
          ? 'bg-kerrigan-50 text-kerrigan-700 dark:bg-kerrigan-800/30 dark:text-kerrigan-200'
          : 'bg-survivor-50 text-survivor-700 dark:bg-survivor-800/30 dark:text-survivor-200'">
        {{ winnerText }}
      </span>
      <span v-if="!terrain" class="text-xs text-amber-600 dark:text-amber-400">未找到该地图地形底图，以网格代替</span>
    </div>

    <!-- 可信度说明：录像没有签名，内容可能被改过；如实告知，不暗示是官方认证对局 -->
    <div class="flex items-start gap-2 rounded-lg px-3 py-2 text-xs leading-relaxed"
      :class="verifyLevel === 'unknown'
        ? 'bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-200'
        : 'bg-surface-50 text-gray-500 dark:bg-gray-800/60 dark:text-gray-400'">
      <span aria-hidden="true" class="mt-px">{{ verifyLevel === 'unknown' ? '⚠' : 'ⓘ' }}</span>
      <span>
        <template v-if="verifyLevel === 'unknown'">
          <b class="font-medium">未知地图版本</b>：本局使用的地图文件不在本站已收录的凯瑞甘生存2官方版本里，
          可能是外服版本、本站未收录的旧版本，也可能是被修改过的地图。
        </template>
        <template v-else-if="verifyLevel === 'known'">
          地图文件与本站收录的凯瑞甘生存2官方版本一致。
        </template>
        录像由玩家上传，未经官方验证，内容可能被修改过，玩家、胜负与数据<b class="font-medium">仅供参考</b>，不计入本站任何统计。
      </span>
    </div>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <!-- 地图画布 -->
      <div class="space-y-2 min-w-0">
        <div ref="stageEl"
          class="relative aspect-square w-full rounded-xl overflow-hidden bg-gray-950 ring-1 ring-black/10 dark:ring-white/10 select-none"
          @wheel.prevent="onWheel" @pointerdown="onPanStart" @pointermove="onPointerMove"
          @pointerup="onPanEnd" @pointerleave="onPointerLeave" @dblclick="resetZoom">
          <canvas ref="canvasEl" class="absolute inset-0 w-full h-full" />
          <div v-if="hoverUnit" class="rp-tip" :style="hoverTipStyle">
            <div class="font-medium">{{ hoverUnit.name }}</div>
            <div class="text-[10px] text-slate-400">{{ hoverUnit.owner }}</div>
          </div>
          <div class="absolute left-2 top-2 rounded-md bg-black/55 px-2 py-1 font-mono text-xs text-white tabular-nums">
            {{ fmtLoop(t) }}
          </div>
          <div v-if="zoom > 1.01" class="absolute right-2 top-2 rounded-md bg-black/55 px-2 py-1 text-[11px] text-white">
            {{ zoom.toFixed(1) }}× · 双击复位
          </div>
        </div>

        <!-- 播放控件 -->
        <div class="flex flex-wrap items-center gap-2">
          <button type="button" @click="togglePlay"
            class="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-survivor-600 text-white hover:bg-survivor-700 transition"
            :aria-label="playing ? '暂停' : '播放'">
            <svg v-if="!playing" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            <svg v-else class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>
          </button>
          <div class="inline-flex rounded-lg border border-surface-200 dark:border-gray-600 overflow-hidden text-xs">
            <button v-for="s in SPEEDS" :key="s" type="button" @click="speed = s"
              class="px-2 py-1.5 transition tabular-nums"
              :class="speed === s
                ? 'bg-survivor-600 text-white'
                : 'bg-surface-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-600'">
              {{ s }}×
            </button>
          </div>
          <button type="button" @click="jumpEvent(-1)" class="rp-btn" title="上一个关键事件 (←)">⏮ 上一事件</button>
          <button type="button" @click="jumpEvent(1)" class="rp-btn" title="下一个关键事件 (→)">下一事件 ⏭</button>
          <div class="ml-auto flex flex-wrap items-center gap-3 text-xs text-gray-600 dark:text-gray-300">
            <label class="flex items-center gap-1"><input v-model="show.units" type="checkbox" class="accent-survivor-600" />单位</label>
            <label class="flex items-center gap-1"><input v-model="show.deaths" type="checkbox" class="accent-survivor-600" />阵亡</label>
            <label class="flex items-center gap-1"><input v-model="show.cameras" type="checkbox" class="accent-survivor-600" />镜头</label>
            <label class="flex items-center gap-1"><input v-model="show.trails" type="checkbox" class="accent-survivor-600" />英雄轨迹</label>
          </div>
        </div>

        <!-- 时间轴 -->
        <ReplayTimeline :data="data" :t="t" :lanes="lanes" :players-by-pid="playersByPid"
          @seek="seek" />
      </div>

      <!-- 玩家面板 -->
      <aside class="space-y-3">
        <div v-for="team in teams" :key="team.key"
          class="rounded-xl border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 overflow-hidden">
          <div class="px-3 py-1.5 text-xs font-medium flex items-center justify-between"
            :class="team.key === 1
              ? 'bg-kerrigan-50 text-kerrigan-700 dark:bg-kerrigan-800/20 dark:text-kerrigan-200'
              : 'bg-survivor-50 text-survivor-700 dark:bg-survivor-800/20 dark:text-survivor-200'">
            <span>{{ team.label }}</span>
            <span v-if="data.meta.winningTeam === team.key">胜</span>
          </div>
          <button v-for="p in team.players" :key="p.pid" type="button"
            @click="focusPid = focusPid === p.pid ? null : p.pid"
            class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-sm transition border-t border-surface-100 dark:border-gray-700/60"
            :class="focusPid === p.pid ? 'bg-surface-100 dark:bg-gray-700/70' : 'hover:bg-surface-50 dark:hover:bg-gray-700/40'">
            <span class="w-2.5 h-2.5 rounded-full shrink-0 ring-2 ring-white dark:ring-gray-800" :style="{ background: p.color }" />
            <UnitIcon :icon="roleIcon(p)" size="sm" :alt="roleLabel(p)" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-gray-800 dark:text-gray-100"
                :class="{ 'line-through opacity-60': statusAt(p) === 'left' }">{{ p.name }}</span>
              <span class="block text-[11px] text-gray-500 dark:text-gray-400 truncate">
                {{ roleLabel(p) }}
                <template v-if="p.mmrBefore != null"> · {{ p.mmrBefore }}<span v-if="p.mmrAfter != null && p.mmrAfter !== p.mmrBefore"
                  :class="p.mmrAfter > p.mmrBefore ? 'text-emerald-600 dark:text-emerald-400' : 'text-kerrigan-600 dark:text-kerrigan-400'">
                  {{ p.mmrAfter > p.mmrBefore ? '+' : '' }}{{ p.mmrAfter - p.mmrBefore }}</span></template>
              </span>
            </span>
            <span class="text-[11px] shrink-0" :class="STATUS[statusAt(p)].cls">{{ STATUS[statusAt(p)].label }}</span>
          </button>
        </div>
        <p class="text-[11px] leading-relaxed text-gray-400 dark:text-gray-500">
          点击玩家可高亮其单位、筛选曲线。英雄位置在两次真实采样之间按玩家移动指令估算；
          虚线空心圈表示超过 20 秒没有位置数据，停在最后已知点。其他单位只在受伤采样（约每 10 秒）时有坐标。
        </p>
      </aside>
    </div>

    <!-- 指标曲线 -->
    <div class="rounded-xl border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 p-3">
      <div class="flex flex-wrap items-center gap-2 mb-2">
        <span class="text-sm font-medium text-gray-700 dark:text-gray-200">对局曲线</span>
        <div class="inline-flex rounded-lg border border-surface-200 dark:border-gray-600 overflow-hidden text-xs">
          <button v-for="m in METRICS" :key="m.key" type="button" @click="metric = m.key"
            class="px-2 py-1 transition"
            :class="metric === m.key
              ? 'bg-survivor-600 text-white'
              : 'bg-surface-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-600'">
            {{ m.label }}
          </button>
        </div>
        <span class="text-[11px] text-gray-400">{{ focusPid ? '仅显示所选玩家' : '点击右侧玩家可单独查看' }}</span>
      </div>
      <div class="relative">
        <LineChart :series="metricSeries" :height="200" :x-format="fmtLoop" :y-format="fmtNum" />
        <div class="pointer-events-none absolute top-3 bottom-[22px] w-px bg-amber-500/80" :style="{ left: chartPlayheadLeft }" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  type ReplayData, type ReplayPlayer, type DecodedUnit,
  decodeUnits, unitPosAt, lowerIndex, fmtLoop, roleLabel, LOOPS_PER_SEC, pickTerrainKey, MAX_INTERP_GAP,
} from '~/utils/replay'
import type { TerrainView } from '~/composables/useTerrainData'
import roleIconMap from '~/data/role-icon-map.json'

const props = defineProps<{ data: ReplayData }>()

const SPEEDS = [1, 2, 4, 8, 16]
const METRICS = [
  { key: 'army', label: '部队价值' },
  { key: 'kills', label: '击杀' },
  { key: 'damage', label: '造成伤害' },
  { key: 'minerals', label: '采集晶矿' },
  { key: 'gasFed', label: '喂气' },
  { key: 'apm', label: 'APM' },
]
const STATUS = {
  alive: { label: '存活', cls: 'text-emerald-600 dark:text-emerald-400' },
  dead: { label: '阵亡', cls: 'text-kerrigan-600 dark:text-kerrigan-400' },
  ghost: { label: '幽灵', cls: 'text-gray-400' },
  left: { label: '离开', cls: 'text-gray-400' },
  waiting: { label: '—', cls: 'text-gray-300 dark:text-gray-600' },
} as const

// ---------- 状态 ----------
const t = ref(props.data.meta.startLoop || 0)
const playing = ref(false)
const speed = ref(4)
const focusPid = ref<number | null>(null)
const metric = ref('army')
const show = reactive({ units: true, deaths: true, cameras: false, trails: true })

const playersByPid = computed(() => Object.fromEntries(props.data.players.map(p => [p.pid, p])) as Record<number, ReplayPlayer>)
const units = shallowRef<DecodedUnit[]>(decodeUnits(props.data))
watch(() => props.data, d => {
  units.value = decodeUnits(d)
  t.value = d.meta.startLoop || 0
  loadTerrain()
})

const teams = computed(() => [
  { key: 0 as const, label: '幸存者', players: props.data.players.filter(p => p.team !== 1) },
  { key: 1 as const, label: '凯瑞甘方', players: props.data.players.filter(p => p.team === 1) },
])

const mapName = computed(() => {
  const k = props.data.meta.mapKey
  const m = maps.find(x => x.key === k)
  return m?.nameZh || props.data.meta.mapEnum || props.data.meta.mapTitle
})
const dateText = computed(() => new Date(props.data.meta.date).toLocaleString('zh-CN', { hour12: false }))
// known = 地图哈希在已知官方版本清单里；unknown = 不在；legacy = 旧数据没有校验信息
const verifyLevel = computed<'known' | 'unknown' | 'legacy'>(() => {
  const v = props.data.verify
  if (!v) return 'legacy'
  return v.mapKnown && v.dependenciesOk ? 'known' : 'unknown'
})

const winnerText = computed(() => {
  const w = props.data.meta.winningTeam
  return w === 0 ? '幸存者胜利' : w === 1 ? '凯瑞甘方胜利' : ''
})

function roleIcon(p: ReplayPlayer) {
  const code = p.roleNameEn ? (roleIconMap as Record<string, string>)[p.roleNameEn] : null
  return code ? `/icons/${code}.png` : null
}

// 英雄阵亡 / 幽灵 / 离开 的时间点，供状态显示
const heroDeathAt = computed(() => {
  const m: Record<number, number> = {}
  const g: Record<number, number> = {}
  for (const e of props.data.events) {
    if (e.kind === 'hero_death' && m[e.pid] == null) m[e.pid] = e.t
    if (e.kind === 'ghost' && g[e.pid] == null) g[e.pid] = e.t
  }
  return { death: m, ghost: g }
})
function statusAt(p: ReplayPlayer): keyof typeof STATUS {
  const now = t.value
  if (p.leaveLoop != null && now >= p.leaveLoop && p.leaveLoop < props.data.meta.loops) return 'left'
  const g = heroDeathAt.value.ghost[p.pid]
  if (g != null && now >= g) return 'ghost'
  const d = heroDeathAt.value.death[p.pid]
  if (d != null && now >= d) return 'dead'
  const hero = units.value.find(u => u.hero && u.owner === p.pid)
  if (hero && now < hero.from) return 'waiting'
  return 'alive'
}

// 小地图信号（按时间升序，绘制时线性扫描）
const pings = computed(() => props.data.events.filter(
  (e): e is Extract<ReplayData['events'][number], { kind: 'ping' }> => e.kind === 'ping'))

// 时间轴泳道：关键事件按类别分道
const lanes = computed(() => [
  { key: 'key', label: '关键', kinds: ['game_start', 'kerrigan', 'hero_death', 'ghost', 'boss_kill', 'leave', 'game_end'] },
  { key: 'upgrade', label: '科技', kinds: ['upgrade'] },
  { key: 'chat', label: '聊天', kinds: ['chat'] },
])
const keyEventTimes = computed(() =>
  props.data.events.filter(e => lanes.value[0].kinds.includes(e.kind)).map(e => e.t).sort((a, b) => a - b))
function jumpEvent(dir: 1 | -1) {
  const ts = keyEventTimes.value
  const cur = t.value
  // 跳到事件前 3 秒，方便看清发生过程
  const lead = 3 * LOOPS_PER_SEC
  if (dir > 0) {
    const nx = ts.find(x => x - lead > cur + 1)
    if (nx != null) seek(nx - lead)
  } else {
    const pv = [...ts].reverse().find(x => x - lead < cur - LOOPS_PER_SEC)
    if (pv != null) seek(pv - lead)
  }
}

// ---------- 播放循环 ----------
let raf = 0
let lastTs = 0
function frame(ts: number) {
  if (!playing.value) return
  const dt = lastTs ? ts - lastTs : 0
  lastTs = ts
  t.value = Math.min(props.data.meta.loops, t.value + dt * LOOPS_PER_SEC / 1000 * speed.value)
  if (t.value >= props.data.meta.loops) playing.value = false
  raf = requestAnimationFrame(frame)
}
function togglePlay() {
  if (!playing.value && t.value >= props.data.meta.loops) t.value = 0
  playing.value = !playing.value
  if (playing.value) { lastTs = 0; raf = requestAnimationFrame(frame) } else cancelAnimationFrame(raf)
}
function seek(loop: number) {
  t.value = Math.max(0, Math.min(props.data.meta.loops, loop))
}
function onKey(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA') return
  if (e.code === 'Space') { e.preventDefault(); togglePlay() }
  else if (e.key === 'ArrowRight') { e.preventDefault(); e.shiftKey ? jumpEvent(1) : seek(t.value + 10 * LOOPS_PER_SEC) }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); e.shiftKey ? jumpEvent(-1) : seek(t.value - 10 * LOOPS_PER_SEC) }
}

// ---------- 地形 ----------
const { maps, loadMap } = useTerrainData()
const terrain = shallowRef<TerrainView | null>(null)
const mapImg = shallowRef<HTMLImageElement | null>(null)
async function loadTerrain() {
  terrain.value = null
  mapImg.value = null
  const key = pickTerrainKey(props.data.meta.mapKey, props.data.meta.date, maps)
  if (!key) { draw(); return }
  try {
    const view = await loadMap(key)
    terrain.value = view
    const img = new Image()
    img.onload = () => { mapImg.value = img; draw() }
    img.src = view.data.minimap.path
  } catch { draw() }
}
const worldSize = computed(() => terrain.value?.data.worldSize ?? 256)

// ---------- 画布 ----------
const stageEl = ref<HTMLDivElement>()
const canvasEl = ref<HTMLCanvasElement>()
const size = ref(0)
const zoom = ref(1)
const pan = reactive({ x: 0, y: 0 }) // 视图左上角对应的世界坐标偏移（像素空间，未缩放）
let ro: ResizeObserver | null = null

/** 世界坐标 → 画布 CSS 像素 */
function toScreen(x: number, y: number): [number, number] {
  const s = size.value / worldSize.value
  return [(x * s - pan.x) * zoom.value, ((worldSize.value - y) * s - pan.y) * zoom.value]
}
function clampPan() {
  const max = size.value - size.value / zoom.value
  pan.x = Math.min(Math.max(0, pan.x), max)
  pan.y = Math.min(Math.max(0, pan.y), max)
}
function onWheel(e: WheelEvent) {
  const rect = stageEl.value!.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const old = zoom.value
  const nz = Math.min(8, Math.max(1, old * (e.deltaY < 0 ? 1.2 : 1 / 1.2)))
  // 以鼠标为中心缩放
  pan.x += mx / old - mx / nz
  pan.y += my / old - my / nz
  zoom.value = nz
  clampPan()
  draw()
}
let panning: { x: number; y: number; px: number; py: number } | null = null
function onPanStart(e: PointerEvent) {
  if (zoom.value <= 1) return
  panning = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}
function onPanEnd() { panning = null }
function resetZoom() { zoom.value = 1; pan.x = 0; pan.y = 0; draw() }

// 悬停单位提示
const mouse = ref<{ x: number; y: number } | null>(null)
function onPointerMove(e: PointerEvent) {
  if (panning) {
    pan.x = panning.px - (e.clientX - panning.x) / zoom.value
    pan.y = panning.py - (e.clientY - panning.y) / zoom.value
    clampPan()
    draw()
    return
  }
  const rect = stageEl.value!.getBoundingClientRect()
  mouse.value = { x: e.clientX - rect.left, y: e.clientY - rect.top }
  draw()
}
function onPointerLeave() { panning = null; mouse.value = null; draw() }
const hoverUnit = ref<{ name: string; owner: string; sx: number; sy: number } | null>(null)
const hoverTipStyle = computed(() => {
  const h = hoverUnit.value
  if (!h) return ''
  const right = h.sx > size.value * 0.6
  return `left:${right ? h.sx - 10 : h.sx + 10}px; top:${h.sy - 10}px; ${right ? 'transform:translateX(-100%)' : ''}`
})

const isDark = () => document.documentElement.classList.contains('dark')

function draw() {
  const cv = canvasEl.value
  if (!cv || !size.value) return
  const dpr = window.devicePixelRatio || 1
  const px = Math.round(size.value * dpr)
  if (cv.width !== px) { cv.width = px; cv.height = px }
  const ctx = cv.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, size.value, size.value)
  const now = t.value
  const W = worldSize.value
  const cell = size.value / W * zoom.value

  // 底图
  if (mapImg.value) {
    ctx.globalAlpha = 0.85
    ctx.drawImage(mapImg.value, -pan.x * zoom.value, -pan.y * zoom.value, size.value * zoom.value, size.value * zoom.value)
    ctx.globalAlpha = 1
  } else {
    ctx.fillStyle = '#0b1220'
    ctx.fillRect(0, 0, size.value, size.value)
    ctx.strokeStyle = 'rgba(148,163,184,0.12)'
    ctx.lineWidth = 1
    for (let g = 0; g <= W; g += 32) {
      const [x0, y0] = toScreen(g, 0); const [x1, y1] = toScreen(g, W)
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke()
      const [a0, b0] = toScreen(0, g); const [a1, b1] = toScreen(W, g)
      ctx.beginPath(); ctx.moveTo(a0, b0); ctx.lineTo(a1, b1); ctx.stroke()
    }
  }
  // 压暗底图，让单位点更显眼
  ctx.fillStyle = 'rgba(2,6,23,0.25)'
  ctx.fillRect(0, 0, size.value, size.value)

  const P = playersByPid.value
  const colorOf = (pid: number) => P[pid]?.color ?? '#9ca3af'
  const dim = (pid: number) => focusPid.value != null && pid !== focusPid.value

  // 阵亡标记：最近 4 秒内的死亡，淡出
  if (show.deaths) {
    const D = props.data.deaths
    const win = 4 * LOOPS_PER_SEC
    const hi = lowerIndex(D, now, 4)
    for (let i = hi; i >= 0; i--) {
      const dl = D[i * 4]
      if (now - dl > win) break
      const a = 1 - (now - dl) / win
      const [sx, sy] = toScreen(D[i * 4 + 1], D[i * 4 + 2])
      const r = Math.max(2, cell * 0.6)
      ctx.strokeStyle = colorOf(D[i * 4 + 3])
      ctx.globalAlpha = a * (dim(D[i * 4 + 3]) ? 0.25 : 0.9)
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.moveTo(sx - r, sy - r); ctx.lineTo(sx + r, sy + r)
      ctx.moveTo(sx + r, sy - r); ctx.lineTo(sx - r, sy + r)
      ctx.stroke()
    }
    ctx.globalAlpha = 1
  }

  // 小地图信号：触发后 3 秒内画扩散圆环（信号很多，不进时间轴，只在画面上提示）
  {
    const win = 3 * LOOPS_PER_SEC
    for (const e of pings.value) {
      if (e.t > now) break
      if (now - e.t > win) continue
      if (dim(e.pid)) continue
      const k = (now - e.t) / win
      const [sx, sy] = toScreen(e.x, e.y)
      ctx.strokeStyle = colorOf(e.pid)
      ctx.globalAlpha = 1 - k
      ctx.lineWidth = 2
      ctx.beginPath(); ctx.arc(sx, sy, 6 + k * 18, 0, Math.PI * 2); ctx.stroke()
    }
    ctx.globalAlpha = 1
  }

  // 镜头框（聚焦玩家或全部）
  if (show.cameras) {
    const cams = props.data.cameras
    // 镜头约 ~32×18 格（1080p 默认缩放下的大致可视范围）
    const cw = 32, ch = 18
    for (const pidStr of Object.keys(cams)) {
      const pid = Number(pidStr)
      if (focusPid.value != null && pid !== focusPid.value) continue
      const c = cams[pidStr]
      const i = lowerIndex(c, now, 3)
      if (i < 0) continue
      const [sx, sy] = toScreen(c[i * 3 + 1] - cw / 2, c[i * 3 + 2] + ch / 2)
      ctx.strokeStyle = colorOf(pid)
      ctx.globalAlpha = 0.8
      ctx.lineWidth = 1.5
      ctx.strokeRect(sx, sy, cw * cell, ch * cell)
    }
    ctx.globalAlpha = 1
  }

  // 英雄轨迹：过去 30 秒
  const US = units.value
  if (show.trails) {
    const back = 30 * LOOPS_PER_SEC
    for (const u of US) {
      if (!u.hero || now < u.from || now > u.to) continue
      if (dim(u.owner)) continue
      const i1 = lowerIndex(u.loops, now)
      if (i1 < 0) continue
      ctx.strokeStyle = colorOf(u.owner)
      ctx.globalAlpha = 0.45
      ctx.lineWidth = 2
      ctx.lineJoin = 'round'
      ctx.beginPath()
      let prevT = -Infinity
      for (let k = Math.max(0, lowerIndex(u.loops, now - back)); k <= i1; k++) {
        const [sx, sy] = toScreen(u.xs[k], u.ys[k])
        // 间隔过大的两点之间路线未知：断开，不画穿墙直线
        if (u.loops[k] - prevT > MAX_INTERP_GAP) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy)
        prevT = u.loops[k]
      }
      const [cx, cy, stale] = unitPosAt(u, now)
      if (!stale) { const [sx, sy] = toScreen(cx, cy); ctx.lineTo(sx, sy) }
      ctx.stroke()
    }
    ctx.globalAlpha = 1
  }

  // 单位
  let best: { d: number; u: DecodedUnit; sx: number; sy: number } | null = null
  const m = mouse.value
  const ring = isDark() ? '#0f172a' : '#0f172a'
  for (const u of US) {
    if (now < u.from || now > u.to) continue
    if (!u.hero && !show.units) continue
    const [x, y, stale] = unitPosAt(u, now)
    const [sx, sy] = toScreen(x, y)
    if (sx < -10 || sy < -10 || sx > size.value + 10 || sy > size.value + 10) continue
    const faded = dim(u.owner)
    if (u.hero) {
      const r = Math.max(5, cell * 1.1)
      ctx.globalAlpha = faded ? 0.35 : 1
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2)
      if (stale) {
        // 位置不确定：空心虚线圈，停在最后已知点
        ctx.setLineDash([3, 2])
        ctx.strokeStyle = colorOf(u.owner)
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.setLineDash([])
      } else {
        ctx.fillStyle = colorOf(u.owner)
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2
        ctx.fill(); ctx.stroke()
      }
      if (!faded) {
        const label = roleLabel(P[u.owner]) || ''
        ctx.font = '600 11px "Noto Sans SC", sans-serif'
        ctx.textAlign = 'center'
        ctx.lineWidth = 3
        ctx.strokeStyle = 'rgba(2,6,23,0.85)'
        ctx.strokeText(label, sx, sy - r - 4)
        ctx.fillStyle = '#f8fafc'
        ctx.fillText(label, sx, sy - r - 4)
      }
    } else {
      if (stale) continue
      const r = Math.max(1.5, cell * 0.45)
      ctx.globalAlpha = faded ? 0.15 : 0.9
      ctx.fillStyle = colorOf(u.owner)
      ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.fill()
      ctx.strokeStyle = ring
      ctx.lineWidth = 0.75
      ctx.stroke()
    }
    if (m) {
      const d = Math.hypot(sx - m.x, sy - m.y)
      const hitR = u.hero ? 12 : 7
      if (d < hitR && (!best || d < best.d || (u.hero && !best.u.hero))) best = { d, u, sx, sy }
    }
  }
  ctx.globalAlpha = 1

  if (best) {
    const ty = props.data.types[best.u.type]
    const p = P[best.u.owner]
    hoverUnit.value = {
      name: ty?.nameZh || ty?.id || '单位',
      owner: p ? `${p.name}${roleLabel(p) ? ' · ' + roleLabel(p) : ''}` : '中立 / 电脑',
      sx: best.sx, sy: best.sy,
    }
  } else hoverUnit.value = null
}

watch([t, focusPid, () => ({ ...show })], draw)

onMounted(() => {
  ro = new ResizeObserver(entries => {
    size.value = entries[0].contentRect.width
    clampPan()
    draw()
  })
  if (stageEl.value) ro.observe(stageEl.value)
  window.addEventListener('keydown', onKey)
  loadTerrain()
})
onBeforeUnmount(() => {
  ro?.disconnect()
  cancelAnimationFrame(raf)
  window.removeEventListener('keydown', onKey)
})

// ---------- 曲线 ----------
const metricSeries = computed(() => {
  const ps = props.data.players.filter(p => focusPid.value == null || p.pid === focusPid.value)
  return ps
    .map(p => {
      const flat = p.perf[metric.value] || []
      const pts: [number, number][] = []
      for (let i = 0; i < flat.length; i += 2) pts.push([flat[i], flat[i + 1]])
      return { label: `${p.name}（${roleLabel(p)}）`, color: p.color, points: pts }
    })
    .filter(s => s.points.length)
})
// LineChart 的横轴取各序列 x 的最小/最大值；按同样的定义算播放线位置
const chartPlayheadLeft = computed(() => {
  const xs = metricSeries.value.flatMap(s => s.points.map(p => p[0]))
  if (!xs.length) return '-10px'
  const lo = Math.min(...xs), hi = Math.max(...xs)
  if (t.value < lo || t.value > hi || hi === lo) return '-10px'
  const frac = (t.value - lo) / (hi - lo)
  // 与 LineChart 的 padL=44 / padR=14 对齐
  return `calc(44px + (100% - 58px) * ${frac})`
})
function fmtNum(v: number) {
  return Math.abs(v) >= 10000 ? `${(v / 1000).toFixed(0)}k` : String(Math.round(v))
}
</script>

<style scoped>
.rp-btn {
  @apply px-2.5 py-1.5 text-xs rounded-lg border border-surface-200 dark:border-gray-600 bg-surface-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-600 transition;
}
.rp-tip {
  position: absolute;
  pointer-events: none;
  background: rgba(15, 25, 35, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12px;
  color: #e2e8f0;
  white-space: nowrap;
  z-index: 10;
}
</style>
