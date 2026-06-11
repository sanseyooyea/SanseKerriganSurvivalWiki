<template>
  <div>
    <!-- Hero Section -->
    <section class="relative py-10 md:py-12 -mx-4 md:-mx-6 px-4 md:px-6 mb-8 md:mb-10 overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-br from-surface-50 via-white to-surface-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800"></div>
      <div class="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-kerrigan-50/40 dark:from-kerrigan-800/20 to-transparent rounded-full -translate-y-1/2 translate-x-1/3"></div>
      <div class="absolute bottom-0 left-0 w-80 h-80 bg-gradient-to-tr from-survivor-50/40 dark:from-survivor-800/20 to-transparent rounded-full translate-y-1/2 -translate-x-1/3"></div>

      <div class="relative text-center max-w-2xl mx-auto">
        <!-- Role icons marquee -->
        <div class="flex justify-center gap-2 mb-6 opacity-60">
          <img v-for="i in heroIcons" :key="i" :src="`/icons/${String(i).padStart(2, '0')}.png`"
            class="w-9 h-9 rounded-lg shadow-sm" loading="lazy" />
        </div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white dark:bg-gray-800 border border-surface-200 dark:border-gray-700 shadow-card text-xs font-medium text-gray-600 dark:text-gray-300 mb-5">
          <span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
          非官方社区Wiki
        </div>
        <h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-3 tracking-tight">
          凯瑞甘生存2
        </h1>
        <p class="text-lg text-gray-600 dark:text-gray-400 leading-relaxed">
          2v8 非对称对抗 — 凯瑞甘方进攻，生存者方防守
        </p>
        <div class="mt-6 flex flex-wrap justify-center gap-3">
          <NuxtLink to="/classes"
            class="px-5 py-2.5 rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors shadow-card">
            浏览全部职业
          </NuxtLink>
          <NuxtLink to="/lookup"
            class="px-5 py-2.5 rounded-lg border border-surface-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-surface-100 dark:hover:bg-gray-800 transition-colors">
            查询玩家
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- Team Cards -->
    <section class="mb-10">
      <div class="section-title">选择阵营</div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <NuxtLink to="/classes?team=Kerrigan" class="group stagger-item">
          <div class="wiki-card p-5 relative overflow-hidden">
            <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-kerrigan-100/60 to-transparent rounded-bl-full"></div>
            <div class="relative">
              <div class="flex items-center gap-3 mb-2">
                <div class="w-10 h-10 rounded-lg bg-kerrigan-50 border border-kerrigan-200 flex items-center justify-center">
                  <span class="text-kerrigan-600 font-bold text-sm">K</span>
                </div>
                <div>
                  <h2 class="text-lg font-bold text-gray-900 dark:text-gray-100 group-hover:text-kerrigan-700 transition-colors">凯瑞甘阵营</h2>
                  <p class="text-xs text-gray-500 dark:text-gray-400">进攻方 · Offense</p>
                </div>
              </div>
              <div class="flex items-baseline gap-1 mt-3">
                <span class="text-2xl font-bold text-kerrigan-600 font-mono">{{ kerriganCount }}</span>
                <span class="text-sm text-gray-500 dark:text-gray-400">个职业</span>
              </div>
            </div>
          </div>
        </NuxtLink>

        <NuxtLink to="/classes?team=Survivor" class="group stagger-item">
          <div class="wiki-card p-5 relative overflow-hidden">
            <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-survivor-100/60 to-transparent rounded-bl-full"></div>
            <div class="relative">
              <div class="flex items-center gap-3 mb-2">
                <div class="w-10 h-10 rounded-lg bg-survivor-50 border border-survivor-200 flex items-center justify-center">
                  <span class="text-survivor-600 font-bold text-sm">S</span>
                </div>
                <div>
                  <h2 class="text-lg font-bold text-gray-900 dark:text-gray-100 group-hover:text-survivor-700 transition-colors">生存者阵营</h2>
                  <p class="text-xs text-gray-500 dark:text-gray-400">防守方 · Defense</p>
                </div>
              </div>
              <div class="flex items-baseline gap-1 mt-3">
                <span class="text-2xl font-bold text-survivor-600 font-mono">{{ survivorCount }}</span>
                <span class="text-sm text-gray-500 dark:text-gray-400">个职业</span>
              </div>
            </div>
          </div>
        </NuxtLink>
      </div>
    </section>

    <!-- Category Grid -->
    <section class="mb-10">
      <div class="section-title">职业分类</div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <NuxtLink v-for="cat in categories" :key="cat.key"
          :to="`/classes?category=${cat.key}`" class="group stagger-item">
          <div class="wiki-card p-4 text-center">
            <div class="text-3xl font-bold text-gray-900 dark:text-gray-100 font-mono group-hover:text-survivor-600 transition-colors">
              {{ cat.count }}
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{{ cat.label }}</div>
            <div class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{{ cat.key }}</div>
          </div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
const { classes } = useClassData()

const kerriganCount = computed(() => classes.filter(c => c.team === 'Kerrigan').length)
const survivorCount = computed(() => classes.filter(c => c.team === 'Survivor').length)

const heroIcons = [1, 5, 9, 13, 17, 21, 25, 33, 37, 41]

const categories = computed(() => [
  { key: 'Hunter', label: '猎手', count: classes.filter(c => c.category === 'Hunter').length },
  { key: 'Builder', label: '建造者', count: classes.filter(c => c.category === 'Builder').length },
  { key: 'Support', label: '辅助', count: classes.filter(c => c.category === 'Support').length },
  { key: 'Defender', label: '防御者', count: classes.filter(c => c.category === 'Defender').length },
])
</script>