<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">录像回放</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      上传凯瑞甘生存2的 <code class="text-xs">.SC2Replay</code> 录像，在地形底图上回放英雄走位与交战，
      英雄阵亡、科技、离开等关键事件标注在时间轴上。
    </p>

    <!-- 上传 -->
    <div class="mb-6">
      <label v-if="isLoggedIn"
        class="flex flex-col items-center justify-center gap-1 px-4 py-6 rounded-xl border-2 border-dashed transition text-sm"
        :class="[
          uploading ? 'opacity-60 cursor-wait' : 'cursor-pointer',
          dragOver
            ? 'border-survivor-500 bg-survivor-50 dark:bg-survivor-900/20'
            : 'border-surface-200 dark:border-gray-700 hover:border-survivor-300 dark:hover:border-survivor-700',
        ]"
        @dragover.prevent="dragOver = true" @dragleave="dragOver = false" @drop.prevent="onDrop">
        <input type="file" accept=".SC2Replay" class="hidden" :disabled="uploading" @change="onPick" />
        <span class="text-gray-700 dark:text-gray-200">{{ uploading ? '上传中…' : '拖入或点击选择 .SC2Replay 录像' }}</span>
        <span class="text-xs text-gray-400">单个不超过 5MB · 每小时 20 个 · 上传后公开可见</span>
        <span class="text-[11px] text-gray-400">
          录像位置：文档\StarCraft II\Accounts\…\Replays\Multiplayer
        </span>
      </label>
      <div v-else class="px-4 py-4 rounded-xl border border-surface-200 dark:border-gray-700 text-sm text-gray-500 dark:text-gray-400">
        <NuxtLink to="/login?redirect=/replays" class="text-survivor-600 dark:text-survivor-400 hover:underline">登录</NuxtLink>
        后即可上传录像；浏览他人上传的录像无需登录。
      </div>
      <p v-if="uploadError" class="mt-2 text-sm text-kerrigan-600 dark:text-kerrigan-400">{{ uploadError }}</p>

      <!-- 我的处理中/失败的录像 -->
      <ul v-if="pendingList.length" class="mt-3 space-y-1.5">
        <li v-for="r in pendingList" :key="r.hash"
          class="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-50 dark:bg-gray-800/60 text-sm">
          <span class="truncate flex-1 text-gray-700 dark:text-gray-200">{{ r.fileName }}</span>
          <span v-if="r.status === 'queued'" class="text-xs text-gray-500">
            排队中<template v-if="aheadOf[r.hash]"> · 前面还有 {{ aheadOf[r.hash] }} 个</template>
          </span>
          <span v-else-if="r.status === 'processing'" class="text-xs text-survivor-600 dark:text-survivor-400 inline-flex items-center gap-1">
            <span class="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />解析中
          </span>
          <template v-else-if="r.status === 'failed'">
            <span class="text-xs text-kerrigan-600 dark:text-kerrigan-400">{{ r.error || '解析失败' }}</span>
            <button type="button" class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200" @click="remove(r.hash)">移除</button>
          </template>
        </li>
      </ul>
    </div>

    <!-- 列表 -->
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-sm font-medium text-gray-700 dark:text-gray-200">全部录像<span v-if="total" class="text-gray-400 font-normal"> · {{ total }}</span></h2>
    </div>
    <div v-if="pending && !list.length" class="text-sm text-gray-400">加载中…</div>
    <div v-else-if="!list.length" class="text-sm text-gray-400">还没有录像，来上传第一个吧。</div>
    <ul v-else class="grid gap-2 sm:grid-cols-2">
      <li v-for="r in list" :key="r.hash" class="relative group">
        <NuxtLink :to="`/replays/${r.hash}`"
          class="block rounded-xl border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800/60 p-3 hover:shadow-card-hover hover:border-survivor-300 dark:hover:border-survivor-700 transition">
          <div class="flex items-center gap-2 text-sm">
            <span class="font-medium text-gray-800 dark:text-gray-100">{{ mapName(r.summary?.mapKey) }}</span>
            <span class="text-gray-400 font-mono text-xs">{{ r.summary ? fmtLoop(r.summary.loops) : '' }}</span>
            <span v-if="r.summary?.winningTeam != null" class="ml-auto px-1.5 py-0.5 rounded text-[11px]"
              :class="r.summary.winningTeam === 1
                ? 'bg-kerrigan-50 text-kerrigan-700 dark:bg-kerrigan-800/30 dark:text-kerrigan-200'
                : 'bg-survivor-50 text-survivor-700 dark:bg-survivor-800/30 dark:text-survivor-200'">
              {{ r.summary.winningTeam === 1 ? '凯瑞甘胜' : '幸存者胜' }}
            </span>
            <span v-else class="ml-auto px-1.5 py-0.5 rounded text-[11px] bg-surface-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400">未完赛</span>
          </div>
          <div class="text-xs text-gray-400 mt-0.5">
            {{ r.summary ? fmtDate(r.summary.date) : '' }}
            <span v-if="r.uploader"> · {{ r.uploader }} 上传</span>
          </div>
          <div class="mt-1.5 flex flex-wrap gap-1">
            <span v-for="(p, i) in r.summary?.players || []" :key="i" class="px-1.5 py-0.5 rounded text-[11px]"
              :class="p.team === 1
                ? 'bg-kerrigan-50 text-kerrigan-700 dark:bg-kerrigan-800/20 dark:text-kerrigan-200'
                : 'bg-surface-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'">
              {{ p.role || '?' }}
            </span>
          </div>
        </NuxtLink>
        <button v-if="r.mine || isAdmin" type="button" title="删除"
          class="absolute top-2 right-2 hidden group-hover:flex items-center justify-center w-6 h-6 rounded-md bg-white/90 dark:bg-gray-700 text-gray-400 hover:text-kerrigan-600 ring-1 ring-black/5"
          @click="remove(r.hash)">✕</button>
      </li>
    </ul>

    <div v-if="total > pageSize" class="mt-4 flex items-center justify-center gap-2 text-sm">
      <button type="button" class="rp-page" :disabled="page <= 1" @click="page--">上一页</button>
      <span class="text-gray-500 tabular-nums">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <button type="button" class="rp-page" :disabled="page >= Math.ceil(total / pageSize)" @click="page++">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { fmtLoop } from '~/utils/replay'

useHead({ title: '录像回放 · 凯瑞甘生存2 Wiki' })

interface Summary {
  mapKey: string | null
  loops: number
  date: string
  winningTeam: 0 | 1 | null
  players: { name: string; role: string | null; team: 0 | 1 | null }[]
}
interface Row {
  hash: string
  status: 'queued' | 'processing' | 'done' | 'failed'
  error: string
  fileName: string
  uploader: string | null
  mine: boolean
  summary: Summary | null
}

const { isLoggedIn, isAdmin, authHeaders } = useAuth()
const { maps } = useTerrainData()
const mapName = (k?: string | null) => maps.find(m => m.key === k)?.nameZh || k || '未知地图'
const fmtDate = (s: string) => new Date(s).toLocaleString('zh-CN', { hour12: false })

const page = ref(1)
const pageSize = ref(24)
const total = ref(0)
const list = ref<Row[]>([])
const pendingList = ref<Row[]>([])
const aheadOf = reactive<Record<string, number>>({})
const pending = ref(true)

async function load() {
  pending.value = true
  try {
    const res = await $fetch<{ total: number; pageSize: number; replays: Row[]; mine: Row[] }>('/api/replays', {
      query: { page: page.value, mine: isLoggedIn.value ? 1 : undefined },
      headers: authHeaders.value,
    })
    total.value = res.total
    pageSize.value = res.pageSize
    list.value = res.replays
    // 合并：保留本地刚上传、服务端列表里也有的记录
    pendingList.value = res.mine
    schedulePoll()
  } finally {
    pending.value = false
  }
}
watch(page, load)
watch(isLoggedIn, load)
onMounted(load)

// ---------- 上传 ----------
const uploading = ref(false)
const uploadError = ref('')
const dragOver = ref(false)

async function upload(f?: File) {
  uploadError.value = ''
  if (!f) return
  if (!/\.SC2Replay$/i.test(f.name)) { uploadError.value = '请选择 .SC2Replay 文件'; return }
  if (f.size > 5 * 1024 * 1024) { uploadError.value = '文件过大（上限 5MB）'; return }
  uploading.value = true
  try {
    // 原始字节直传（不用 multipart：服务端流式读取、按字节封顶，内存占用≈文件大小）
    const res = await $fetch<{ replay: Row; duplicate: boolean }>('/api/replays', {
      method: 'POST',
      body: await f.arrayBuffer(),
      headers: {
        ...authHeaders.value,
        'Content-Type': 'application/octet-stream',
        'X-File-Name': encodeURIComponent(f.name),
      },
    })
    if (res.replay.status === 'done') {
      // 别人已经传过同一局，直接打开
      await navigateTo(`/replays/${res.replay.hash}`)
      return
    }
    if (!pendingList.value.some(r => r.hash === res.replay.hash)) pendingList.value.unshift(res.replay)
    schedulePoll(true)
  } catch (e: any) {
    uploadError.value = e?.data?.message || e?.message || '上传失败'
  } finally {
    uploading.value = false
  }
}
function onDrop(e: DragEvent) { dragOver.value = false; upload(e.dataTransfer?.files?.[0]) }
function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  upload(input.files?.[0])
  input.value = ''
}

// ---------- 轮询未完成的任务 ----------
let pollTimer: ReturnType<typeof setTimeout> | null = null
function schedulePoll(now = false) {
  if (pollTimer) clearTimeout(pollTimer)
  if (!pendingList.value.some(r => r.status === 'queued' || r.status === 'processing')) return
  pollTimer = setTimeout(poll, now ? 800 : 2000)
}
async function poll() {
  const active = pendingList.value.filter(r => r.status === 'queued' || r.status === 'processing')
  let finished = false
  await Promise.all(active.map(async (r) => {
    try {
      const res = await $fetch<{ replay: Row; ahead: number }>(`/api/replays/${r.hash}/status`)
      aheadOf[r.hash] = res.ahead
      Object.assign(r, { status: res.replay.status, error: res.replay.error })
      if (res.replay.status === 'done') finished = true
    } catch {}
  }))
  if (finished) {
    // 完成的移出待处理列表并刷新第一页
    pendingList.value = pendingList.value.filter(r => r.status !== 'done')
    if (page.value === 1) await load(); else page.value = 1
    return
  }
  schedulePoll()
}
onBeforeUnmount(() => { if (pollTimer) clearTimeout(pollTimer) })

async function remove(hash: string) {
  if (!confirm('确定删除这个录像？')) return
  try {
    await $fetch(`/api/replays/${hash}`, { method: 'DELETE', headers: authHeaders.value })
    pendingList.value = pendingList.value.filter(r => r.hash !== hash)
    list.value = list.value.filter(r => r.hash !== hash)
    total.value = Math.max(0, total.value - 1)
  } catch (e: any) {
    alert(e?.data?.message || '删除失败')
  }
}
</script>

<style scoped>
.rp-page {
  @apply px-3 py-1.5 rounded-lg border border-surface-200 dark:border-gray-600 bg-surface-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-600 transition disabled:opacity-40 disabled:cursor-not-allowed;
}
</style>
