<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center">
      <!-- 遮罩 -->
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in" @click="$emit('close')"></div>

      <!-- 面板 -->
      <div class="relative w-full sm:max-w-lg max-h-[88vh] overflow-y-auto bg-white dark:bg-gray-800 rounded-t-2xl sm:rounded-2xl shadow-elevated animate-slide-up">
        <!-- 头部 -->
        <div class="sticky top-0 z-10 flex items-start justify-between gap-3 px-5 pt-5 pb-3 bg-white/90 dark:bg-gray-800/90 backdrop-blur border-b border-surface-200 dark:border-gray-700">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold shrink-0" :class="medalClass">
                {{ player.rank }}
              </span>
              <h3 class="text-lg font-bold text-gray-900 dark:text-gray-100 truncate">{{ player.display_name || '未知玩家' }}</h3>
            </div>
            <p v-if="player.identity" class="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">{{ player.identity }}</p>
            <p class="text-[11px] font-mono text-gray-400 dark:text-gray-500 mt-0.5">{{ handle }}</p>
          </div>
          <button @click="$emit('close')"
            class="shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-700 transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="p-5 space-y-5">
          <!-- 加载骨架 -->
          <div v-if="loading" class="space-y-4">
            <div class="grid grid-cols-2 gap-3">
              <div class="h-20 rounded-xl bg-surface-100 dark:bg-gray-700 animate-pulse"></div>
              <div class="h-20 rounded-xl bg-surface-100 dark:bg-gray-700 animate-pulse"></div>
            </div>
            <div class="h-32 rounded-xl bg-surface-100 dark:bg-gray-700 animate-pulse"></div>
          </div>

          <div v-else-if="!playerData" class="py-8 text-center text-sm text-gray-400">
            未能获取该玩家的详细数据
          </div>

          <template v-else>
            <!-- 双核心分 -->
            <div class="grid grid-cols-2 gap-3">
              <div class="rounded-xl border border-survivor-100 dark:border-survivor-800/40 bg-survivor-50/50 dark:bg-survivor-800/10 p-3">
                <div class="text-xs text-survivor-600 dark:text-survivor-400 mb-1">生存者核心</div>
                <div class="text-2xl font-bold font-mono text-survivor-700 dark:text-survivor-300">{{ playerData.cores.survivor }}</div>
                <div class="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">{{ playerData.ranks.survivor.tier }} · Top {{ playerData.ranks.survivor.percentile }}%</div>
              </div>
              <div class="rounded-xl border border-kerrigan-100 dark:border-kerrigan-800/40 bg-kerrigan-50/50 dark:bg-kerrigan-800/10 p-3">
                <div class="text-xs text-kerrigan-600 dark:text-kerrigan-400 mb-1">凯瑞甘核心</div>
                <div class="text-2xl font-bold font-mono text-kerrigan-700 dark:text-kerrigan-300">{{ playerData.cores.kerrigan }}</div>
                <div class="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">{{ playerData.ranks.kerrigan.tier }} · Top {{ playerData.ranks.kerrigan.percentile }}%</div>
              </div>
            </div>

            <!-- 角色战绩（取分最高的一方，最多 5 个） -->
            <div v-if="topRoles.length">
              <div class="section-title">主力角色</div>
              <RoleTable :roles="topRoles" :team="topTeam" />
            </div>

            <!-- 积分 -->
            <div v-if="creditsData">
              <div class="section-title">积分信息</div>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div class="rounded-lg bg-surface-50 dark:bg-gray-700/40 px-3 py-2">
                  <div class="text-xs text-gray-500 dark:text-gray-400">总积分</div>
                  <div class="font-mono font-bold text-gray-900 dark:text-gray-100">{{ creditsData.totalCredits?.toLocaleString() }}</div>
                </div>
                <div class="rounded-lg bg-surface-50 dark:bg-gray-700/40 px-3 py-2">
                  <div class="text-xs text-gray-500 dark:text-gray-400">Lucy积分</div>
                  <div class="font-mono font-bold text-gray-900 dark:text-gray-100">{{ creditsData.baseCredits }}</div>
                </div>
              </div>
            </div>
          </template>

          <!-- 跳转完整资料 -->
          <NuxtLink :to="`/player/${handle}`"
            class="flex items-center justify-center gap-1 w-full py-2.5 rounded-xl text-sm font-medium text-white bg-survivor-600 hover:bg-survivor-700 transition">
            查看完整资料
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </NuxtLink>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const props = defineProps<{ player: any }>()
defineEmits<{ close: [] }>()

const handle = computed(() => props.player.handles?.[0] ?? '')

const loading = ref(true)
const playerData = ref<any>(null)
const creditsData = ref<any>(null)

const medalClass = computed(() => {
  if (props.player.rank === 1) return 'bg-yellow-400 text-yellow-900'
  if (props.player.rank === 2) return 'bg-gray-300 text-gray-700'
  if (props.player.rank === 3) return 'bg-amber-600 text-amber-50'
  return 'bg-surface-200 dark:bg-gray-600 text-gray-600 dark:text-gray-200'
})

// 取核心分更高的一方作为主力角色展示
const topTeam = computed<'survivor' | 'kerrigan'>(() => {
  const s = playerData.value?.cores?.survivor ?? 0
  const k = playerData.value?.cores?.kerrigan ?? 0
  return k >= s ? 'kerrigan' : 'survivor'
})

const topRoles = computed(() => {
  const key = topTeam.value === 'kerrigan' ? 'roles_kerrigan' : 'roles_survivor'
  return (playerData.value?.[key] ?? []).slice(0, 5)
})

async function load() {
  if (!handle.value) { loading.value = false; return }
  loading.value = true
  try {
    const [mmr, credits] = await Promise.all([
      $fetch<any>('/api/mmr', { params: { handle: handle.value } }),
      $fetch<any>('/api/credits', { params: { handle: handle.value } }).catch(() => null),
    ])
    playerData.value = mmr
    creditsData.value = credits
  } catch {
    playerData.value = null
  } finally {
    loading.value = false
  }
}

// 锁定背景滚动
onMounted(() => {
  document.body.style.overflow = 'hidden'
  load()
})
onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>
