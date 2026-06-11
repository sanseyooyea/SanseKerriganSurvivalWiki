<template>
  <ClientOnly>
    <div v-if="!isLoggedIn" class="text-center py-20">
      <p class="text-gray-400 text-lg">请先登录</p>
      <NuxtLink to="/login" class="text-survivor-600 hover:underline mt-2 inline-block">登录</NuxtLink>
    </div>
    <div v-else class="max-w-lg mx-auto py-8">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">个人设置</h1>

      <div class="wiki-card p-5 mb-4">
        <div class="section-title">账号信息</div>
        <div class="text-sm space-y-2">
          <div class="flex justify-between">
            <span class="text-gray-500">用户名</span>
            <span class="text-gray-900 dark:text-gray-100 font-medium">{{ user?.username }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">角色</span>
            <span class="text-gray-900 dark:text-gray-100">{{ user?.role }}</span>
          </div>
        </div>
      </div>

      <div class="wiki-card p-5">
        <div class="section-title">游戏句柄绑定</div>
        <p class="text-xs text-gray-400 mb-3">绑定后可显示段位图标，格式如 5-S2-1-1194668</p>
        <div class="flex gap-2">
          <input v-model="handleInput" type="text" placeholder="5-S2-1-1194668"
            class="flex-1 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-300 font-mono" />
          <button @click="bindHandle" :disabled="binding"
            class="px-4 py-2 text-sm font-medium text-white bg-survivor-600 rounded-lg hover:bg-survivor-700 disabled:opacity-50 transition whitespace-nowrap">
            {{ binding ? '验证中...' : (user?.handle ? '更换' : '绑定') }}
          </button>
        </div>
        <div v-if="user?.handle" class="mt-2 text-xs text-gray-500">
          当前绑定：<NuxtLink :to="`/player/${user.handle}`" class="text-survivor-600 hover:underline">{{ user.handle }}</NuxtLink>
        </div>
        <p v-if="handleError" class="mt-2 text-xs text-red-500">{{ handleError }}</p>
        <p v-if="handleSuccess" class="mt-2 text-xs text-green-600">{{ handleSuccess }}</p>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup lang="ts">
const { user, isLoggedIn, authHeaders, init } = useAuth()

const handleInput = ref('')
const binding = ref(false)
const handleError = ref('')
const handleSuccess = ref('')

onMounted(() => {
  if (user.value?.handle) handleInput.value = user.value.handle
})

async function bindHandle() {
  handleError.value = ''
  handleSuccess.value = ''
  const val = handleInput.value.trim()
  if (!val) { handleError.value = '请输入句柄'; return }
  binding.value = true
  try {
    await $fetch('/api/auth/handle', {
      method: 'PUT',
      headers: authHeaders.value,
      body: { handle: val },
    })
    handleSuccess.value = '绑定成功'
    await init()
  } catch (e: any) {
    handleError.value = e.data?.message || '绑定失败'
  } finally {
    binding.value = false
  }
}
</script>
