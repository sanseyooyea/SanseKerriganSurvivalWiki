<template>
  <header class="bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-surface-200 dark:border-gray-700 sticky top-0 z-50">
    <div class="max-w-6xl mx-auto px-4 md:px-6 h-14 flex items-center justify-between">
      <NuxtLink to="/" class="flex items-center gap-2 group shrink-0" @click="menuOpen = false">
        <img src="/logo.svg" alt="凯瑞甘生存2 Wiki"
          class="w-7 h-7 object-contain group-hover:scale-105 transition-transform" />
        <span class="text-base font-bold text-gray-900 dark:text-gray-100 group-hover:text-gray-700 dark:group-hover:text-gray-300 transition-colors">
          <span class="hidden sm:inline">凯瑞甘生存2 Wiki</span>
          <span class="sm:hidden">KS2 Wiki</span>
        </span>
      </NuxtLink>
      <div class="flex items-center gap-1">
        <!-- 桌面导航：分组下拉（点击切换） -->
        <nav class="hidden lg:flex gap-1">
          <div v-for="g in NAV_GROUPS" :key="g.label" class="relative">
            <button
              @click.stop="openGroup = openGroup === g.label ? '' : g.label"
              class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
              :class="(isGroupActive(g) || openGroup === g.label)
                ? 'text-survivor-600 dark:text-survivor-400 bg-survivor-50 dark:bg-survivor-900/30'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-surface-100 dark:hover:bg-gray-800'">
              {{ g.label }}
              <svg class="w-3 h-3 transition-transform" :class="{ 'rotate-180': openGroup === g.label }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <!-- 下拉面板 -->
            <div v-if="openGroup === g.label" class="absolute right-0 top-full pt-2 animate-fade-in z-50">
              <div class="min-w-[9rem] py-1.5 rounded-xl bg-white dark:bg-gray-800 border border-surface-200 dark:border-gray-700 shadow-elevated">
                <NuxtLink
                  v-for="it in g.items" :key="it.to" :to="it.to" @click="openGroup = ''"
                  class="flex items-center gap-2 px-3.5 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-700/60 hover:text-survivor-600 dark:hover:text-survivor-400 transition-colors"
                  active-class="!text-survivor-600 dark:!text-survivor-400 font-medium">
                  <span class="text-gray-300 dark:text-gray-600 text-xs font-mono">{{ it.icon }}</span>
                  {{ it.label }}
                </NuxtLink>
              </div>
            </div>
          </div>
          <NuxtLink v-if="isAdmin" to="/admin"
            class="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all"
            active-class="!text-survivor-600 dark:!text-survivor-400 bg-survivor-50 dark:bg-survivor-900/30">
            管理
          </NuxtLink>
        </nav>
        <button @click="toggle"
          class="hidden lg:inline-flex ml-2 p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all"
          :title="mode === 'dark' ? '切换到亮色模式' : '切换到暗色模式'">
          <svg v-if="mode === 'light'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
          </svg>
        </button>
        <NuxtLink v-if="!isLoggedIn" to="/login"
          class="hidden lg:inline-flex ml-1 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all">
          登录
        </NuxtLink>
        <div v-else class="hidden lg:flex ml-1 items-center gap-1.5">
          <NuxtLink v-if="user?.handle" :to="`/player/${user.handle}`" class="flex items-center gap-1 hover:opacity-80 transition">
            <RankBadge :handle="user.handle" />
            <span class="text-xs text-gray-500 dark:text-gray-400">{{ user.username }}</span>
          </NuxtLink>
          <span v-else class="text-xs text-gray-500 dark:text-gray-400">{{ user?.username }}</span>
          <NuxtLink to="/settings"
            class="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all"
            title="个人设置">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </NuxtLink>
          <button @click="logout"
            class="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all"
            title="退出登录">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
          </button>
        </div>
        <button @click="menuOpen = !menuOpen"
          class="lg:hidden ml-2 p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all">
          <svg v-if="!menuOpen" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>
    <!-- 移动端面板：分组列表 -->
    <div v-if="menuOpen" class="lg:hidden border-t border-surface-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <nav class="px-4 py-3 space-y-3">
        <div v-for="g in NAV_GROUPS" :key="g.label">
          <div class="px-3 mb-1 text-[0.65rem] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">{{ g.label }}</div>
          <NuxtLink v-for="it in g.items" :key="it.to" :to="it.to" @click="menuOpen = false"
            class="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all"
            active-class="!text-survivor-600 dark:!text-survivor-400">
            <span class="text-gray-300 dark:text-gray-600 text-xs font-mono w-4">{{ it.icon }}</span>
            {{ it.label }}
          </NuxtLink>
        </div>
        <NuxtLink v-if="isAdmin" to="/admin" @click="menuOpen = false"
          class="block px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all">
          管理
        </NuxtLink>
      </nav>
      <div class="px-4 py-3 border-t border-surface-200 dark:border-gray-700 flex flex-col gap-2">
        <button @click="toggle"
          class="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all w-full text-left">
          <svg v-if="mode === 'light'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
          </svg>
          {{ mode === 'dark' ? '切换到亮色模式' : '切换到暗色模式' }}
        </button>
        <template v-if="!isLoggedIn">
          <NuxtLink to="/login" @click="menuOpen = false"
            class="px-3 py-2.5 rounded-lg text-sm font-medium text-survivor-600 dark:text-survivor-400 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all">
            登录 / 注册
          </NuxtLink>
        </template>
        <template v-else>
          <div class="flex items-center justify-between px-3 py-2">
            <div class="flex items-center gap-2">
              <RankBadge v-if="user?.handle" :handle="user.handle" />
              <span class="text-sm text-gray-700 dark:text-gray-300">{{ user?.username }}</span>
            </div>
            <div class="flex items-center gap-1">
              <NuxtLink to="/settings" @click="menuOpen = false"
                class="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                </svg>
              </NuxtLink>
              <button @click="logout(); menuOpen = false"
                class="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-surface-100 dark:hover:bg-gray-800 transition-all">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                </svg>
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const route = useRoute()
const { mode, toggle } = useColorMode()
const { user, isLoggedIn, isAdmin, logout } = useAuth()

const NAV_GROUPS = [
  {
    label: '资料',
    items: [
      { to: '/classes', label: '职业列表', icon: '◆' },
      { to: '/balance', label: '英雄胜率', icon: '%' },
      { to: '/balance/trends', label: '版本Meta', icon: '∿' },
      { to: '/economy', label: '经济系统', icon: '$' },
      { to: '/wiki', label: 'Wiki', icon: '#' },
    ],
  },
  {
    label: '玩家',
    items: [
      { to: '/lookup', label: '查询', icon: '?' },
      { to: '/leaderboard', label: '排行榜', icon: '▲' },
    ],
  },
  {
    label: '社区',
    items: [
      { to: '/changelog', label: '更新日志', icon: '∆' },
      { to: '/council', label: '钻石议会', icon: '◇' },
      { to: '/feedback', label: '建议反馈', icon: '▸' },
    ],
  },
]

function isGroupActive(g: { items: { to: string }[] }) {
  return g.items.some(it => route.path === it.to || route.path.startsWith(it.to + '/'))
}

const menuOpen = ref(false)
const openGroup = ref('')

// 点击页面其他位置时关闭桌面下拉
function closeDropdown() { openGroup.value = '' }
onMounted(() => document.addEventListener('click', closeDropdown))
onBeforeUnmount(() => document.removeEventListener('click', closeDropdown))

watch(() => route.fullPath, () => {
  menuOpen.value = false
  openGroup.value = ''
})
</script>
