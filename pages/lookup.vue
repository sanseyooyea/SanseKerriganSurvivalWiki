<template>
  <div class="max-w-2xl mx-auto py-6">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">玩家查询</h1>

    <div class="wiki-card p-5 mb-6">
      <div class="flex gap-2">
        <input v-model="handleInput" type="text" placeholder="输入句柄，如 5-S2-1-1194668"
          @keyup.enter="search"
          class="flex-1 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-300 font-mono" />
        <button @click="search" :disabled="searching"
          class="px-5 py-2 text-sm font-medium text-white bg-survivor-600 rounded-lg hover:bg-survivor-700 disabled:opacity-50 transition whitespace-nowrap">
          {{ searching ? '查询中...' : '查询' }}
        </button>
      </div>
      <p v-if="error" class="mt-2 text-sm text-red-500">{{ error }}</p>
    </div>

    <template v-if="mmrData || creditsData">
      <div v-if="mmrData" class="grid grid-cols-2 gap-4 mb-6">
        <div class="wiki-card p-4">
          <div class="text-xs text-survivor-600 dark:text-survivor-400 mb-1">生存者</div>
          <div class="text-2xl font-bold text-survivor-700 dark:text-survivor-300">{{ mmrData.cores.survivor }}</div>
          <div class="text-sm text-gray-500">{{ mmrData.ranks.survivor.tier }} · Top {{ mmrData.ranks.survivor.percentile }}%</div>
        </div>
        <div class="wiki-card p-4">
          <div class="text-xs text-kerrigan-600 dark:text-kerrigan-400 mb-1">凯瑞甘</div>
          <div class="text-2xl font-bold text-kerrigan-700 dark:text-kerrigan-300">{{ mmrData.cores.kerrigan }}</div>
          <div class="text-sm text-gray-500">{{ mmrData.ranks.kerrigan.tier }} · Top {{ mmrData.ranks.kerrigan.percentile }}%</div>
        </div>
      </div>

      <div v-else class="wiki-card p-4 mb-6 text-sm text-gray-500 dark:text-gray-400">
        该玩家暂无天梯 MMR 数据（可能为外服玩家或未打过天梯），以下为积分信息。
      </div>

      <div v-if="creditsData" class="wiki-card p-4 mb-6">
        <div class="section-title">积分信息</div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-gray-500">总积分</span>
            <div class="font-mono font-bold text-gray-900 dark:text-gray-100">{{ creditsData.totalCredits?.toLocaleString() }}</div>
          </div>
          <div>
            <span class="text-gray-500">Lucy积分</span>
            <div class="font-mono font-bold text-gray-900 dark:text-gray-100">{{ creditsData.baseCredits }}</div>
          </div>
          <div>
            <span class="text-gray-500">录像数</span>
            <div class="font-mono font-bold text-gray-900 dark:text-gray-100">{{ creditsData.replays }}</div>
          </div>
          <div>
            <span class="text-gray-500">惩罚</span>
            <div class="font-mono font-bold" :class="creditsData.penalty > 0 ? 'text-red-500' : 'text-green-600'">{{ creditsData.penalty }}</div>
          </div>
        </div>
      </div>

      <NuxtLink :to="`/player/${handleInput.trim()}`"
        class="inline-flex items-center gap-1 text-sm text-survivor-600 hover:underline">
        查看完整资料 →
      </NuxtLink>
    </template>
  </div>
</template>

<script setup lang="ts">
const handleInput = ref('')
const searching = ref(false)
const error = ref('')
const mmrData = ref<any>(null)
const creditsData = ref<any>(null)

async function search() {
  const val = handleInput.value.trim()
  if (!val) { error.value = '请输入句柄'; return }
  error.value = ''
  searching.value = true
  mmrData.value = null
  creditsData.value = null
  try {
    const [mmr, credits] = await Promise.all([
      $fetch<any>('/api/mmr', { params: { handle: val } }).catch(() => null),
      $fetch<any>('/api/credits', { params: { handle: val } }).catch(() => null),
    ])
    // MMR 与积分独立：只要有任一数据就展示（外服玩家常无 MMR 但有积分）
    if (!mmr && !credits) { error.value = '未找到该玩家'; return }
    mmrData.value = mmr
    creditsData.value = credits
  } catch {
    error.value = '查询失败，请检查句柄格式'
  } finally {
    searching.value = false
  }
}
</script>
