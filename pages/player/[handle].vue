<template>
  <div>
    <NuxtLink to="/"
      class="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors mb-6">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      返回
    </NuxtLink>

    <div v-if="loading" class="space-y-4">
      <div class="h-8 w-48 bg-surface-200 dark:bg-gray-700 rounded-lg animate-pulse"></div>
      <div class="grid grid-cols-2 gap-4">
        <div class="wiki-card p-4 space-y-2">
          <div class="h-3 w-16 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
          <div class="h-7 w-20 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
          <div class="h-3 w-32 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
        <div class="wiki-card p-4 space-y-2">
          <div class="h-3 w-16 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
          <div class="h-7 w-20 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
          <div class="h-3 w-32 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
      </div>
      <div class="wiki-card p-5 space-y-3">
        <div class="h-3 w-24 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
        <div class="space-y-2">
          <div class="h-5 w-full bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
          <div class="h-5 w-full bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
          <div class="h-5 w-3/4 bg-surface-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
      </div>
    </div>
    <div v-else-if="!playerData" class="text-center py-12 text-gray-400">未找到玩家数据</div>
    <template v-else>
      <!-- Visible page -->
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ handle }}</h1>
        <button @click="shareAsImage" :disabled="sharing"
          class="px-3 py-1.5 text-xs font-medium border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition">
          {{ shareText }}
        </button>
      </div>

      <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="wiki-card p-4">
          <div class="text-xs text-survivor-600 dark:text-survivor-400 mb-1">生存者核心</div>
          <div class="text-2xl font-bold text-survivor-700 dark:text-survivor-300">{{ playerData.cores.survivor }}</div>
          <div class="text-sm text-gray-500 mt-0.5">{{ playerData.ranks.survivor.tier }} · Top {{ playerData.ranks.survivor.percentile }}%</div>
        </div>
        <div class="wiki-card p-4">
          <div class="text-xs text-kerrigan-600 dark:text-kerrigan-400 mb-1">凯瑞甘核心</div>
          <div class="text-2xl font-bold text-kerrigan-700 dark:text-kerrigan-300">{{ playerData.cores.kerrigan }}</div>
          <div class="text-sm text-gray-500 mt-0.5">{{ playerData.ranks.kerrigan.tier }} · Top {{ playerData.ranks.kerrigan.percentile }}%</div>
        </div>
      </div>

      <div v-if="playerData.roles_survivor?.length" class="wiki-card p-5 mb-6">
        <div class="section-title">生存者角色</div>
        <RoleTable :roles="playerData.roles_survivor" team="survivor" />
      </div>

      <div v-if="playerData.roles_kerrigan?.length" class="wiki-card p-5 mb-6">
        <div class="section-title">凯瑞甘角色</div>
        <RoleTable :roles="playerData.roles_kerrigan" team="kerrigan" />
      </div>

      <div v-if="mmrSeries.length" class="wiki-card p-5 mb-6">
        <div class="flex items-center justify-between flex-wrap gap-2 mb-1">
          <div class="section-title !mb-0">MMR 走势</div>
          <div class="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
            <span v-if="mmrThrough">截至 {{ mmrThrough }}</span>
            <button @click="shareMmr" :disabled="mmrSharing"
              class="px-2.5 py-1 text-xs font-medium border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition">
              {{ mmrShareText }}
            </button>
          </div>
        </div>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-1 mb-3">
          核心分随时间变化；点选下方角色叠加该角色有效分（核心分 + 角色调整）曲线。
        </p>
        <LineChart :series="mmrSeries" :height="260" :x-format="fmtTs" :y-format="(y:number)=>String(Math.round(y))" />
        <div v-if="mmrRoleNames.length" class="flex flex-wrap gap-1.5 mt-4">
          <button v-for="(name, i) in mmrRoleNames" :key="name" @click="toggleMmrRole(name)"
            class="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs border transition"
            :class="selectedRoles.includes(name)
              ? 'border-transparent text-white'
              : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'"
            :style="selectedRoles.includes(name) ? `background:${roleColor(name)}` : ''">
            <img :src="`/icons/${roleIcon(name)}.png`" class="w-4 h-4 rounded" :alt="name" />
            {{ roleName(name) }}
          </button>
        </div>
      </div>

      <div v-if="recentGames.length" class="wiki-card p-5 mb-6">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="section-title !mb-0">最近对局 · 等效MMR</div>
          <div class="flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
            <span v-if="playedLikeAvg">均值 <span class="font-mono font-semibold text-gray-600 dark:text-gray-300">{{ playedLikeAvg }}</span></span>
            <span v-if="playedLikeThrough">截至 {{ playedLikeThrough }}</span>
            <button @click="sharePlayedLike" :disabled="playedSharing"
              class="px-2.5 py-1 text-xs font-medium border border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition">
              {{ playedShareText }}
            </button>
          </div>
        </div>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-1 mb-3">
          每局实际打出的水平估值；高于赛前估值（▲）为超常发挥，低于（▼）为失常。
        </p>
        <div class="space-y-1 max-h-96 overflow-y-auto pr-1">
          <div v-for="(g, i) in recentGames" :key="i"
            class="flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition">
            <span class="text-xs font-mono text-gray-400 w-10 shrink-0">{{ gameDate(g.date) }}</span>
            <img :src="`/icons/${roleIcon(g.role)}.png`" class="w-6 h-6 rounded shrink-0" :alt="g.role" />
            <span class="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">{{ roleName(g.role) }}</span>
            <span class="text-xs px-1.5 py-0.5 rounded shrink-0"
              :class="g.team === 1
                ? 'bg-kerrigan-50 text-kerrigan-600 dark:bg-kerrigan-900/30 dark:text-kerrigan-400'
                : 'bg-survivor-50 text-survivor-600 dark:bg-survivor-900/30 dark:text-survivor-400'">
              {{ g.team === 1 ? '凯' : '人' }}
            </span>
            <span class="text-sm font-mono font-bold w-14 text-right shrink-0"
              :class="g.estimated != null && g.played_like != null
                ? (g.played_like >= g.estimated ? 'text-green-600' : 'text-red-500')
                : 'text-gray-700 dark:text-gray-300'">
              {{ g.played_like == null ? '—' : Math.round(g.played_like) }}
            </span>
            <span class="text-xs w-12 text-right shrink-0 text-gray-400 dark:text-gray-500">
              <template v-if="g.estimated != null && g.played_like != null">
                {{ g.played_like >= g.estimated ? '▲' : '▼' }}{{ Math.abs(Math.round(g.played_like - g.estimated)) }}
              </template>
            </span>
          </div>
        </div>
      </div>

      <div v-if="creditsData" class="wiki-card p-5 mb-6">
        <div class="section-title">积分信息</div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <div class="text-gray-500 dark:text-gray-400 mb-1">总积分</div>
            <div class="text-xl font-bold font-mono text-gray-900 dark:text-gray-100">{{ creditsData.totalCredits?.toLocaleString() }}</div>
          </div>
          <div>
            <div class="text-gray-500 dark:text-gray-400 mb-1">Lucy积分</div>
            <div class="text-xl font-bold font-mono text-gray-900 dark:text-gray-100">{{ creditsData.baseCredits }}</div>
          </div>
          <div>
            <div class="text-gray-500 dark:text-gray-400 mb-1">录像数</div>
            <div class="text-xl font-bold font-mono text-gray-900 dark:text-gray-100">{{ creditsData.replays }}</div>
          </div>
          <div>
            <div class="text-gray-500 dark:text-gray-400 mb-1">惩罚</div>
            <div class="text-xl font-bold font-mono" :class="creditsData.penalty > 0 ? 'text-red-500' : 'text-green-600'">{{ creditsData.penalty }}</div>
          </div>
        </div>
        <div v-if="creditsData.code" class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <span class="text-xs text-gray-400">兑换码：</span>
          <span class="text-xs font-mono text-gray-500 cursor-pointer hover:text-survivor-600" @click="copyCode">{{ showCode ? '已复制' : '点击复制' }}</span>
        </div>
      </div>

      <!-- Hidden share card (rendered offscreen for screenshot) -->
      <div ref="shareRef" class="share-card" aria-hidden="true">
        <img v-if="avatarExists" :src="topRoleAvatar" class="share-avatar" />
        <div v-if="avatarExists" class="share-overlay"></div>
        <div class="share-content" :style="avatarExists ? '' : 'margin-left: 0; padding: 24px 28px'">
          <div class="share-header">
            <div class="share-title">{{ handle }}</div>
            <div class="share-subtitle">凯瑞甘生存2</div>
          </div>
          <div class="share-cores">
            <div class="share-core share-core-s">
              <div class="share-core-label">生存者</div>
              <div class="share-core-value">{{ playerData.cores.survivor }}</div>
              <div class="share-core-tier">{{ playerData.ranks.survivor.tier }}</div>
            </div>
            <div class="share-core share-core-k">
              <div class="share-core-label">凯瑞甘</div>
              <div class="share-core-value">{{ playerData.cores.kerrigan }}</div>
              <div class="share-core-tier">{{ playerData.ranks.kerrigan.tier }}</div>
            </div>
          </div>
          <div v-if="creditsData" class="share-credits">
            <span>总积分 {{ creditsData.totalCredits?.toLocaleString() }}</span>
            <span>Lucy分 {{ creditsData.baseCredits }}</span>
          </div>
          <div class="share-top-roles">
            <div v-for="r in topRoles" :key="r.role_id" class="share-role-row">
              <img :src="`/icons/${roleIcon(r.role_name)}.png`" class="share-role-icon" />
              <span class="share-role-name">{{ roleName(r.role_name) }}</span>
              <span class="share-role-mmr">{{ r.mmr }}</span>
              <span class="share-role-wr" :style="`color: ${r.win_rate >= 0.5 ? '#16a34a' : '#dc2626'}`">{{ (r.win_rate * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div class="share-footer">KS2 Wiki · 最强角色: {{ topRoleChinese }}</div>
        </div>
      </div>

      <!-- Hidden played_like share card -->
      <div ref="playedShareRef" class="pl-share" aria-hidden="true">
        <div class="pl-share-head">
          <div>
            <div class="pl-share-title">{{ handle }}</div>
            <div class="pl-share-sub">凯瑞甘生存2 · 最近对局等效MMR</div>
          </div>
          <div v-if="playedLikeAvg" class="pl-share-avg">
            <div class="pl-share-avg-num">{{ playedLikeAvg }}</div>
            <div class="pl-share-avg-label">近{{ recentGames.length }}局均值</div>
          </div>
        </div>
        <div class="pl-share-rows">
          <div v-for="(g, i) in recentForShare" :key="i" class="pl-share-row">
            <span class="pl-share-date">{{ gameDate(g.date) }}</span>
            <img :src="`/icons/${roleIcon(g.role)}.png`" class="pl-share-icon" />
            <span class="pl-share-role">{{ roleName(g.role) }}</span>
            <span class="pl-share-team" :class="g.team === 1 ? 'tk' : 'ts'">{{ g.team === 1 ? '凯' : '人' }}</span>
            <span class="pl-share-mmr" :style="`color:${plColor(g)}`">{{ g.played_like == null ? '—' : Math.round(g.played_like) }}</span>
            <span class="pl-share-delta" :style="`color:${plColor(g)}`">{{ plDelta(g) }}</span>
          </div>
        </div>
        <div class="pl-share-foot">KS2 Wiki · 等效MMR=每局打出的水平 · 数据截至 {{ playedLikeThrough }}</div>
      </div>

      <!-- Hidden MMR-trend share card -->
      <div ref="mmrShareRef" class="mmr-share" aria-hidden="true">
        <div class="mmr-share-head">
          <div>
            <div class="mmr-share-title">{{ handle }}</div>
            <div class="mmr-share-sub">凯瑞甘生存2 · MMR 走势</div>
          </div>
          <div v-if="currentCore" class="mmr-share-cores">
            <div class="mmr-share-core mmr-share-core-s">
              <div class="mmr-share-core-label">生存核心</div>
              <div class="mmr-share-core-val">{{ currentCore[1] }}</div>
            </div>
            <div class="mmr-share-core mmr-share-core-k">
              <div class="mmr-share-core-label">凯瑞甘核心</div>
              <div class="mmr-share-core-val">{{ currentCore[2] }}</div>
            </div>
          </div>
        </div>
        <div class="mmr-share-chart">
          <LineChart v-if="mmrSeries.length" :series="mmrSeries" :height="220"
            :x-format="fmtTs" :y-format="(y:number)=>String(Math.round(y))" />
        </div>
        <div v-if="selectedRoles.length" class="mmr-share-legend">
          <span v-for="name in selectedRoles" :key="name" class="mmr-share-leg-item">
            <span class="mmr-share-leg-dot" :style="`background:${roleColor(name)}`"></span>{{ roleName(name) }}
          </span>
        </div>
        <div class="mmr-share-foot">KS2 Wiki · 角色分含核心调整 · 数据截至 {{ mmrThrough }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import iconMap from '~/data/role-icon-map.json'
import nameMap from '~/data/role-name-map.json'

const route = useRoute()
const handle = route.params.handle as string

const loading = ref(true)
const sharing = ref(false)
const shareText = ref('复制分享图')
const showCode = ref(false)
const playerData = ref<any>(null)
const creditsData = ref<any>(null)
const playedLikeData = ref<any>(null)
const mmrHistoryData = ref<any>(null)
const shareRef = ref<HTMLElement>()
const playedShareRef = ref<HTMLElement>()
const playedSharing = ref(false)
const playedShareText = ref('分享图')
const mmrShareRef = ref<HTMLElement>()
const mmrSharing = ref(false)
const mmrShareText = ref('分享图')

// 最近对局等效MMR（played_like）：每局玩家实际打出的水平，对比赛前估值
const recentGames = computed<any[]>(() => playedLikeData.value?.games || [])
const playedLikeAvg = computed(() => {
  const vals = recentGames.value.map(g => g.played_like).filter((v: any) => v != null)
  return vals.length ? Math.round(vals.reduce((a: number, b: number) => a + b, 0) / vals.length) : null
})
const playedLikeThrough = computed(() => {
  const t = playedLikeData.value?.through
  if (!t) return ''
  const d = new Date(String(t).replace(' ', 'T'))
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString('zh-CN')
})
function gameDate(s: string): string {
  const d = new Date(String(s).replace(' ', 'T'))
  return isNaN(d.getTime()) ? s : d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}
// 分享图只放最近 8 局，避免过长
const recentForShare = computed<any[]>(() => recentGames.value.slice(0, 8))
function plColor(g: any): string {
  if (g.estimated == null || g.played_like == null) return '#cbd5e1'
  return g.played_like >= g.estimated ? '#16a34a' : '#dc2626'
}
function plDelta(g: any): string {
  if (g.estimated == null || g.played_like == null) return ''
  const d = Math.round(g.played_like - g.estimated)
  return (d >= 0 ? '▲' : '▼') + Math.abs(d)
}

// ---- MMR 走势 ----
const ROLE_PALETTE = ['#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#14b8a6', '#a855f7']
const selectedRoles = ref<string[]>([])

const mmrThrough = computed(() => {
  const t = mmrHistoryData.value?.through
  if (!t) return ''
  const d = new Date(String(t).replace(' ', 'T'))
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString('zh-CN')
})
// 角色按数据点数排序（玩得最多的在前）
const mmrRoleNames = computed<string[]>(() => {
  const roles = mmrHistoryData.value?.roles || {}
  return Object.keys(roles).sort((a, b) => (roles[b]?.length || 0) - (roles[a]?.length || 0))
})
function roleColor(name: string): string {
  const i = mmrRoleNames.value.indexOf(name)
  return ROLE_PALETTE[((i < 0 ? 0 : i) % ROLE_PALETTE.length)]
}
function toggleMmrRole(name: string) {
  const i = selectedRoles.value.indexOf(name)
  if (i >= 0) selectedRoles.value.splice(i, 1)
  else selectedRoles.value.push(name)
}
function fmtTs(ts: number): string {
  const d = new Date(ts * 1000)
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString('zh-CN', { year: '2-digit', month: 'numeric' })
}
// 最新核心分快照 [ts, 生存, 凯]，用于分享图头部
const currentCore = computed<number[] | null>(() => {
  const core = mmrHistoryData.value?.core || []
  return core.length ? core[core.length - 1] : null
})
const mmrSeries = computed<any[]>(() => {
  const core = mmrHistoryData.value?.core || []
  if (!core.length) return []
  const out: any[] = [
    { label: '生存核心', color: '#16a34a', points: core.map((c: number[]) => [c[0], c[1]]) },
    { label: '凯瑞甘核心', color: '#dc2626', points: core.map((c: number[]) => [c[0], c[2]]) },
  ]
  const roles = mmrHistoryData.value?.roles || {}
  for (const name of selectedRoles.value) {
    if (roles[name]?.length) {
      out.push({ label: roleName(name), color: roleColor(name), points: roles[name] })
    }
  }
  return out
})

const topSurvivor = computed(() => (playerData.value?.roles_survivor || []).slice(0, 5))
const topKerrigan = computed(() => (playerData.value?.roles_kerrigan || []).slice(0, 5))

const topRole = computed(() => {
  const all = [...(playerData.value?.roles_survivor || []), ...(playerData.value?.roles_kerrigan || [])]
  if (!all.length) return null
  return all.reduce((a, b) => a.mmr > b.mmr ? a : b)
})

const topRoles = computed(() => {
  const all = [...(playerData.value?.roles_survivor || []), ...(playerData.value?.roles_kerrigan || [])]
  return all.sort((a, b) => b.mmr - a.mmr).slice(0, 5)
})

const topRoleChinese = computed(() => topRole.value ? roleName(topRole.value.role_name) : '')

const topRoleAvatar = computed(() => {
  if (!topRole.value) return ''
  const name = topRole.value.role_name.toLowerCase().replace(/_/g, '').replace(/ /g, '')
  return `/avatars/${name}.png`
})

const avatarExists = ref(false)

watch(topRoleAvatar, (url) => {
  if (!url) return
  const img = new Image()
  img.onload = () => { avatarExists.value = true }
  img.onerror = () => { avatarExists.value = false }
  img.src = url
})

onMounted(async () => {
  try {
    const [mmr, credits, playedLike, mmrHist] = await Promise.all([
      $fetch('/api/mmr', { params: { handle } }),
      $fetch('/api/credits', { params: { handle } }).catch(() => null),
      $fetch<any>('/api/played_like', { params: { handle } }).catch(() => null),
      $fetch<any>('/api/mmr_history', { params: { handle } }).catch(() => null),
    ])
    playerData.value = mmr
    creditsData.value = credits
    playedLikeData.value = playedLike
    mmrHistoryData.value = mmrHist
  } catch {}
  loading.value = false
})

function roleIcon(name: string): string {
  const map = iconMap as Record<string, string>
  return map[name] || map[name.replace(/ /g, '_')] || '00'
}

function roleName(name: string): string {
  const map = nameMap as Record<string, string>
  return map[name] || map[name.replace(/ /g, '_')] || name
}

async function copyCode() {
  showCode.value = true
  if (creditsData.value?.code) {
    await copyText(`-lucy ${creditsData.value.code}`)
  }
}

function downloadBlob(blob: Blob, suffix = '') {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ks2-${handle}${suffix}.png`
  a.click()
  URL.revokeObjectURL(url)
}

// 通用截图分享：把隐藏卡片渲染为 PNG，优先写入剪贴板，否则下载。
async function captureShare(
  el: HTMLElement | undefined,
  text: Ref<string>,
  busy: Ref<boolean>,
  idle: string,
  suffix: string,
) {
  if (!el || busy.value) return
  busy.value = true
  text.value = '生成中...'
  try {
    const { default: html2canvas } = await import('html2canvas')
    el.style.position = 'fixed'
    el.style.left = '0'
    el.style.top = '0'
    el.style.zIndex = '-9999'
    el.style.opacity = '1'
    el.style.pointerEvents = 'none'

    // 等 Web 字体(DM Sans / Noto Sans SC / JetBrains Mono)与图标加载完成再截图：
    // 否则字体异步加载后文字回流，html2canvas 已按旧高度抓了背景 → 文字与背景高度错位。
    try { await (document as any).fonts?.ready } catch {}
    await new Promise(r => setTimeout(r, 250))
    const canvas = await html2canvas(el, {
      backgroundColor: '#0f1923',
      scale: 2,
      useCORS: true,
      allowTaint: true,
      logging: false,
    })
    el.style.position = ''
    el.style.left = ''
    el.style.top = ''
    el.style.zIndex = ''
    el.style.opacity = ''

    const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/png'))
    if (blob) {
      // 图片剪贴板（ClipboardItem）仅安全上下文可用，无 execCommand 回退；
      // 非安全上下文或写入失败时回退为下载。
      const canCopyImage = window.isSecureContext && !!navigator.clipboard && typeof ClipboardItem !== 'undefined'
      if (canCopyImage) {
        try {
          await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
          text.value = '已复制!'
        } catch {
          downloadBlob(blob, suffix)
          text.value = '已下载!'
        }
      } else {
        downloadBlob(blob, suffix)
        text.value = '已下载!'
      }
    }
  } catch (e) {
    console.error('Share failed:', e)
    text.value = '分享失败'
  } finally {
    busy.value = false
    setTimeout(() => { text.value = idle }, 2000)
  }
}

function shareAsImage() {
  return captureShare(shareRef.value, shareText, sharing, '复制分享图', '')
}

function sharePlayedLike() {
  return captureShare(playedShareRef.value, playedShareText, playedSharing, '分享图', '-recent')
}

function shareMmr() {
  return captureShare(mmrShareRef.value, mmrShareText, mmrSharing, '分享图', '-mmr')
}
</script>

<style scoped>
.share-card {
  position: absolute;
  left: -9999px;
  top: 0;
  opacity: 0;
  width: 600px;
  height: 340px;
  border-radius: 16px;
  font-family: 'DM Sans', 'Noto Sans SC', sans-serif;
  color: #e2e8f0;
  background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
  overflow: hidden;
  display: flex;
}
.share-avatar {
  position: absolute;
  left: 0;
  top: 0;
  width: 300px;
  height: 340px;
  object-fit: cover;
  object-position: top center;
}
.share-overlay {
  position: absolute;
  left: 0;
  top: 0;
  width: 300px;
  height: 340px;
  background: linear-gradient(to right, transparent 30%, #0f1923 100%);
}
.share-content {
  position: relative;
  margin-left: 220px;
  padding: 24px 28px 20px 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  z-index: 1;
}
.share-header { margin-bottom: 12px; }
.share-title {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
}
.share-subtitle {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}
.share-cores {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 10px;
}
.share-core {
  padding: 8px 10px;
  border-radius: 8px;
  text-align: center;
}
.share-core-s {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
}
.share-core-k {
  background: rgba(225, 29, 72, 0.15);
  border: 1px solid rgba(225, 29, 72, 0.4);
}
.share-core-label { font-size: 9px; opacity: 0.7; }
.share-core-value {
  font-size: 20px;
  font-weight: 800;
  color: #ffffff;
  font-family: 'JetBrains Mono', monospace;
}
.share-core-tier { font-size: 10px; opacity: 0.8; }
.share-credits {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
  font-size: 10px;
  color: #94a3b8;
}
.share-top-roles { flex: 1; }
.share-role-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.share-role-icon {
  width: 18px;
  height: 18px;
  border-radius: 3px;
}
.share-role-name {
  width: 60px;
  font-size: 11px;
  color: #cbd5e1;
}
.share-role-mmr {
  font-size: 11px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #ffffff;
  width: 38px;
  text-align: right;
}
.share-role-wr {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  width: 30px;
  text-align: right;
}
.share-footer {
  font-size: 9px;
  color: #475569;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid rgba(255,255,255,0.05);
}

/* ---- played_like 分享卡 ---- */
.pl-share {
  position: absolute;
  left: -9999px;
  top: 0;
  opacity: 0;
  width: 480px;
  padding: 22px 26px 16px;
  border-radius: 16px;
  font-family: 'DM Sans', 'Noto Sans SC', sans-serif;
  color: #e2e8f0;
  background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
  box-sizing: border-box;
}
.pl-share-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}
.pl-share-title { font-size: 18px; font-weight: 700; color: #fff; }
.pl-share-sub { font-size: 10px; color: #64748b; margin-top: 2px; }
.pl-share-avg { text-align: right; }
.pl-share-avg-num {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  font-family: 'JetBrains Mono', monospace;
  line-height: 1;
}
.pl-share-avg-label { font-size: 9px; color: #94a3b8; margin-top: 3px; }
.pl-share-rows { display: flex; flex-direction: column; gap: 2px; }
.pl-share-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  /* line-height:1 让行框紧贴文字：html2canvas 对 line-height:normal 会把字渲染到
     行框底部(偏下)，flex 居中也无法补偿；设为 1 后各列文字才真正垂直居中。 */
  line-height: 1;
}
.pl-share-row > * { line-height: 1; }
.pl-share-date {
  width: 36px;
  font-size: 11px;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}
.pl-share-icon { width: 20px; height: 20px; border-radius: 4px; }
.pl-share-role { flex: 1; font-size: 12px; color: #cbd5e1; }
.pl-share-team {
  font-size: 9px;
  padding: 0 6px;
  border-radius: 4px;
  /* 单行文字用 line-height 撑起徽章高度并垂直居中：比上下 padding 更能让
     html2canvas 把「人/凯」渲染在绿/红背景框正中(padding 方式会偏移)。 */
  line-height: 16px;
  height: 16px;
}
.pl-share-team.tk { background: rgba(225,29,72,0.2); color: #fb7185; }
.pl-share-team.ts { background: rgba(16,185,129,0.18); color: #34d399; }
.pl-share-mmr {
  width: 42px;
  text-align: right;
  font-size: 13px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}
.pl-share-delta {
  width: 40px;
  text-align: right;
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
}
.pl-share-foot {
  font-size: 9px;
  color: #475569;
  margin-top: 10px;
  padding-top: 7px;
  border-top: 1px solid rgba(255,255,255,0.05);
}

/* ---- MMR 走势分享卡 ---- */
.mmr-share {
  position: absolute;
  left: -9999px;
  top: 0;
  opacity: 0;
  width: 560px;
  padding: 22px 26px 16px;
  border-radius: 16px;
  font-family: 'DM Sans', 'Noto Sans SC', sans-serif;
  color: #e2e8f0;
  background: linear-gradient(135deg, #0f1923 0%, #1a2a3a 100%);
  box-sizing: border-box;
}
.mmr-share-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}
.mmr-share-title { font-size: 18px; font-weight: 700; color: #fff; }
.mmr-share-sub { font-size: 10px; color: #64748b; margin-top: 2px; }
.mmr-share-cores { display: flex; gap: 8px; }
.mmr-share-core { padding: 6px 12px; border-radius: 8px; text-align: center; }
.mmr-share-core-s { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.4); }
.mmr-share-core-k { background: rgba(225,29,72,0.15); border: 1px solid rgba(225,29,72,0.4); }
.mmr-share-core-label { font-size: 9px; opacity: 0.75; }
.mmr-share-core-val { font-size: 18px; font-weight: 800; color: #fff; font-family: 'JetBrains Mono', monospace; }
.mmr-share-chart { width: 100%; }
.mmr-share-legend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
.mmr-share-leg-item { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: #cbd5e1; }
.mmr-share-leg-dot { width: 8px; height: 8px; border-radius: 50%; }
.mmr-share-foot {
  font-size: 9px;
  color: #475569;
  margin-top: 10px;
  padding-top: 7px;
  border-top: 1px solid rgba(255,255,255,0.05);
}
</style>
