<template>
  <div class="min-h-screen flex flex-col">
    <AppHeader />
    <main class="flex-1 max-w-6xl mx-auto w-full px-4 md:px-6 py-6 md:py-8">
      <slot />
    </main>
    <footer class="border-t border-surface-200 dark:border-gray-700 py-5 text-center space-y-1.5">
      <p class="text-xs text-gray-400 dark:text-gray-500">
        凯瑞甘生存2 Wiki · 非官方社区项目 · 数据来源于游戏文件
      </p>
      <p class="text-xs text-gray-400 dark:text-gray-500">
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener"
          class="hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
          浙ICP备2026041261号-1
        </a>
      </p>
    </footer>
    <Transition name="fade">
      <button v-if="showTop" @click="scrollToTop"
        class="fixed bottom-6 right-6 w-10 h-10 rounded-full bg-white dark:bg-gray-800 border border-surface-200 dark:border-gray-700 shadow-elevated flex items-center justify-center text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:shadow-card-hover transition-all z-40">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
        </svg>
      </button>
    </Transition>
  </div>
</template>

<script setup lang="ts">
const showTop = ref(false)

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  window.addEventListener('scroll', () => {
    showTop.value = window.scrollY > 300
  }, { passive: true })
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
