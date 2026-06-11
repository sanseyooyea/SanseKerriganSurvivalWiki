<template>
  <div class="max-w-sm mx-auto py-12">
    <div class="wiki-card p-6">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
        {{ isRegister ? '注册' : '登录' }}
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
        {{ isRegister ? '创建账号以参与Wiki编辑' : '登录以编辑Wiki内容' }}
      </p>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">用户名</label>
          <input v-model="username" type="text" required minlength="2"
            class="w-full border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">密码</label>
          <input v-model="password" type="password" required minlength="6"
            class="w-full border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800" />
        </div>
        <div v-if="isRegister">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">游戏句柄</label>
          <input v-model="handle" type="text" placeholder="例如: 5-S2-1-1194668"
            class="w-full border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800" />
          <p class="text-xs text-gray-400 mt-1">用于显示段位信息，可留空</p>
        </div>

        <p v-if="error" class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50">
          {{ loading ? '处理中...' : (isRegister ? '注册' : '登录') }}
        </button>
      </form>

      <p class="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
        <button @click="isRegister = !isRegister" class="text-survivor-600 dark:text-survivor-400 hover:underline">
          {{ isRegister ? '已有账号？登录' : '没有账号？注册' }}
        </button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
const { setAuth } = useAuth()
const router = useRouter()

const isRegister = ref(false)
const username = ref('')
const password = ref('')
const handle = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const endpoint = isRegister.value ? '/api/auth/register' : '/api/auth/login'
    const body: any = { username: username.value, password: password.value }
    if (isRegister.value && handle.value) body.handle = handle.value
    const res = await $fetch<{ token: string; user: any }>(endpoint, {
      method: 'POST',
      body
    })
    setAuth(res.token, res.user)
    router.push('/')
  } catch (e: any) {
    error.value = e.data?.message || '操作失败'
  } finally {
    loading.value = false
  }
}
</script>
