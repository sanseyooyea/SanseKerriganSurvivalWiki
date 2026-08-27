<template>
  <div class="max-w-3xl mx-auto">
    <!-- 头部 -->
    <header class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">支持本站</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
        凯瑞甘生存2 Wiki 是一个非官方的社区项目，由个人利用业余时间开发和维护。
        网站的服务器、域名和带宽都是自费支出。如果这个站点对你有帮助，欢迎请我喝杯咖啡——
        <span class="text-gray-600 dark:text-gray-300">所有支持仅用于覆盖服务器与域名开销，本站不会因此设置任何付费内容。</span>
      </p>
    </header>

    <!-- 说明条 -->
    <div class="flex items-start gap-2.5 mb-6 p-3.5 rounded-lg bg-survivor-50 dark:bg-survivor-900/20 border border-survivor-100 dark:border-survivor-800/60">
      <svg class="w-5 h-5 shrink-0 mt-0.5 text-survivor-500 dark:text-survivor-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <p class="text-xs text-survivor-800/90 dark:text-survivor-200/80 leading-relaxed">
        本站为星际争霸2 自定义地图的粉丝向非官方资料站，与暴雪娱乐及地图作者均无隶属关系。
        支持完全出于自愿，不构成任何商品或服务的购买，也不会带来任何站内特权。
      </p>
    </div>

    <!-- 收款渠道 -->
    <div class="grid gap-4 sm:grid-cols-2 mb-8">
      <!-- 爱发电 -->
      <div class="rounded-xl border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-card flex flex-col">
        <div class="flex items-center gap-2 mb-3">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-orange-50 dark:bg-orange-900/30 text-orange-500 text-lg">⚡</span>
          <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">爱发电</h2>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-4 flex-1 leading-relaxed">
          通过爱发电支持，可选择一次性赞助或持续为爱发电。适合希望长期支持本站运营的朋友。
        </p>
        <a v-if="data.afdianUrl" :href="data.afdianUrl" target="_blank" rel="noopener"
          class="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium bg-survivor-600 hover:bg-survivor-700 dark:bg-survivor-500 dark:hover:bg-survivor-600 text-white transition-colors">
          前往爱发电
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
          </svg>
        </a>
        <div v-else
          class="inline-flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-medium bg-surface-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed select-none">
          链接即将开放
        </div>
      </div>

      <!-- 微信收款码 -->
      <div class="rounded-xl border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-card flex flex-col">
        <div class="flex items-center gap-2 mb-3">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-500 text-lg">💬</span>
          <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">微信收款码</h2>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-4 leading-relaxed">
          使用微信扫描下方二维码，即可直接转账支持。金额随意，心意最重要。
        </p>
        <div class="flex justify-center">
          <img :src="data.wechatQr" alt="微信收款码"
            class="w-44 h-44 rounded-lg border border-surface-200 dark:border-gray-600 object-contain bg-white" />
        </div>
      </div>
    </div>

    <!-- 赞助者名单 -->
    <section>
      <div class="flex items-center gap-2 mb-3">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">赞助者名单</h2>
        <span v-if="data.sponsors.length"
          class="px-2 py-0.5 rounded-full text-xs font-mono bg-surface-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
          {{ data.sponsors.length }}
        </span>
      </div>

      <div v-if="data.sponsors.length" class="flex flex-wrap gap-2">
        <div v-for="(s, i) in data.sponsors" :key="i"
          class="inline-flex items-baseline gap-1.5 px-3 py-1.5 rounded-lg border border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm">
          <span class="font-medium text-gray-800 dark:text-gray-200">{{ s.name }}</span>
          <span v-if="s.amount" class="text-xs font-mono text-survivor-600 dark:text-survivor-400">¥{{ s.amount }}</span>
        </div>
      </div>

      <div v-else
        class="rounded-xl border border-dashed border-surface-300 dark:border-gray-600 bg-surface-50/60 dark:bg-gray-800/40 px-5 py-8 text-center">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          感谢每一位支持者 —— 名单将在这里陆续更新。
        </p>
        <p class="text-xs text-gray-400 dark:text-gray-500 mt-1.5">
          你会是第一个吗？
        </p>
      </div>

      <p class="mt-4 text-xs text-gray-400 dark:text-gray-500 leading-relaxed">
        如不希望公开显示或希望修改署名，请通过
        <NuxtLink to="/feedback" class="text-survivor-600 dark:text-survivor-400 hover:underline">建议反馈</NuxtLink>
        告知。
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import sponsors from '~/data/sponsors.json'

const data = sponsors as {
  afdianUrl: string
  wechatQr: string
  sponsors: { name: string; amount?: number }[]
}

useHead({
  title: '支持本站 · 凯瑞甘生存2 Wiki',
  meta: [
    { name: 'description', content: '支持凯瑞甘生存2 Wiki 的服务器与域名开销。可通过爱发电或微信收款码自愿赞助。' },
  ],
})
</script>
