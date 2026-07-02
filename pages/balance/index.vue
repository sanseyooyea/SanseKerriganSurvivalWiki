<template>
  <div>
    <header class="mb-4">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">英雄胜率 · 平衡性</h1>
    </header>

    <!-- 标签：时段排行 / 跨版本走势 -->
    <div class="flex rounded-lg bg-surface-100 dark:bg-gray-800 p-0.5 text-sm mb-6 w-fit">
      <button v-for="t in TABS" :key="t.value" @click="setTab(t.value)"
        class="px-4 py-1.5 rounded-md font-medium transition-colors"
        :class="tab === t.value
          ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
          : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'">
        {{ t.label }}
      </button>
    </div>

    <BalanceRanking v-if="tab === 'ranking'" />
    <BalanceTrends v-else />
  </div>
</template>

<script setup lang="ts">
type Tab = 'ranking' | 'trends'
const TABS: { value: Tab; label: string }[] = [
  { value: 'ranking', label: '时段排行' },
  { value: 'trends', label: '跨版本走势' },
]

const route = useRoute()
const router = useRouter()

const tab = ref<Tab>(route.query.tab === 'trends' ? 'trends' : 'ranking')

function setTab(t: Tab) {
  tab.value = t
  // 反映到 URL（可分享/回退），不新增历史记录
  router.replace({ query: t === 'trends' ? { tab: 'trends' } : {} })
}

// 支持外部直接带 ?tab= 进入（旧 /balance/trends 重定向到此）
watch(() => route.query.tab, v => {
  tab.value = v === 'trends' ? 'trends' : 'ranking'
})

useHead({ title: '英雄胜率 · 平衡性 - 凯瑞甘生存2 Wiki' })
</script>
