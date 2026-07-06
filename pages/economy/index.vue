<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">经济系统</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      生存者方通过建造经济建筑获取晶矿收入，不同职业拥有不同的经济体系。点击英雄展开其经济详情。
    </p>

    <!-- 工具条：搜索 + 一键展开/收起 -->
    <div class="flex flex-col sm:flex-row gap-2 sm:items-center mb-4">
      <div class="relative flex-1 min-w-[180px]">
        <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input v-model="search" type="text" placeholder="搜索英雄 / 经济类型…"
          class="w-full border border-surface-200 dark:border-gray-600 rounded-lg pl-8 pr-3 py-1.5 text-sm bg-surface-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800 transition" />
      </div>
      <div class="flex gap-2">
        <button type="button" @click="expandAll"
          class="px-3 py-1.5 text-sm rounded-lg border border-surface-200 dark:border-gray-600 bg-surface-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-surface-100 dark:hover:bg-gray-600 transition">
          全部展开
        </button>
        <button type="button" @click="collapseAll"
          class="px-3 py-1.5 text-sm rounded-lg border border-surface-200 dark:border-gray-600 bg-surface-50 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-surface-100 dark:hover:bg-gray-600 transition">
          全部收起
        </button>
      </div>
    </div>

    <!-- 手风琴 -->
    <div class="space-y-3">
      <div v-for="hero in filtered" :key="hero.hero" :id="slug(hero.hero)" class="wiki-card overflow-hidden stagger-item">
        <button type="button" @click="toggle(hero.hero)"
          class="w-full flex items-center gap-3 p-4 text-left hover:bg-surface-50 dark:hover:bg-gray-700/30 transition-colors">
          <img v-if="hero.roleId >= 0" :src="`/icons/${String(hero.roleId).padStart(2, '0')}.png`"
            class="w-9 h-9 rounded-lg shadow-sm shrink-0" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-semibold text-gray-900 dark:text-gray-100">{{ hero.nameZh }}</span>
              <span class="inline-flex items-center text-[0.65rem] px-1.5 py-0.5 rounded font-medium" :class="badgeClass(hero.type)">
                {{ hero.typeLabel }}
              </span>
            </div>
            <div class="text-xs text-gray-400 dark:text-gray-500">{{ hero.hero }}</div>
          </div>
          <div class="hidden sm:block text-xs font-mono text-gray-500 dark:text-gray-400 text-right shrink-0">
            {{ hero.headline }}
          </div>
          <svg class="w-4 h-4 text-gray-400 shrink-0 transition-transform duration-200" :class="{ 'rotate-180': isOpen(hero.hero) }"
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <div v-if="isOpen(hero.hero)" class="px-5 pb-5 border-t border-surface-200 dark:border-gray-700">
          <div class="pt-4">
            <NuxtLink v-if="hero.roleId >= 0" :to="`/classes/${hero.roleId}`"
              class="inline-block mb-3 text-xs text-survivor-600 dark:text-survivor-400 hover:underline">
              查看 {{ hero.nameZh }} 完整职业详情 →
            </NuxtLink>
            <HeroEconomy :name="hero.hero" />
          </div>
        </div>
      </div>

      <p v-if="!filtered.length" class="text-center text-gray-500 dark:text-gray-400 py-8">
        没有匹配的英雄
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
const { allEconomyHeroes } = useEconomyData()
const route = useRoute()

// 经济类型徽章配色（全静态 class，避免 Tailwind purge 丢失）
const TYPE_BADGE: Record<string, string> = {
  generic: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  harvest: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  addon: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  miner: 'bg-cyan-50 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300',
  technician: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  spirit: 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
}
function badgeClass(type: string) {
  return TYPE_BADGE[type] || TYPE_BADGE.generic
}

const search = ref('')
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return allEconomyHeroes.value
  return allEconomyHeroes.value.filter(h =>
    h.hero.toLowerCase().includes(q) ||
    (h.nameZh && h.nameZh.toLowerCase().includes(q)) ||
    (h.typeLabel && h.typeLabel.toLowerCase().includes(q)),
  )
})

// 折叠状态（reassign new Set 触发响应式）
const openSet = ref<Set<string>>(new Set())
function isOpen(key: string) {
  return openSet.value.has(key)
}
function toggle(key: string) {
  const s = new Set(openSet.value)
  s.has(key) ? s.delete(key) : s.add(key)
  openSet.value = s
}
function expandAll() {
  openSet.value = new Set(filtered.value.map(h => h.hero))
}
function collapseAll() {
  openSet.value = new Set()
}

function slug(name: string) {
  return name.toLowerCase().replace(/\s+/g, '-')
}

// 深链：/economy#ares 自动展开并滚动到该英雄
onMounted(() => {
  const h = route.hash?.replace('#', '')
  if (!h) return
  const hero = allEconomyHeroes.value.find(x => slug(x.hero) === h)
  if (!hero) return
  const s = new Set(openSet.value)
  s.add(hero.hero)
  openSet.value = s
  nextTick(() => {
    document.getElementById(slug(hero.hero))?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
})
</script>
