<template>
  <div class="max-w-sm mx-auto py-12">
    <div class="wiki-card p-6">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">重置密码</h1>

      <div v-if="!token" class="text-sm text-red-600 dark:text-red-400">
        <p>无效的重置链接。</p>
        <NuxtLink to="/forgot-password" class="inline-block mt-3 text-survivor-600 dark:text-survivor-400 hover:underline">
          重新申请
        </NuxtLink>
      </div>

      <form v-else @submit.prevent="submit" class="space-y-4 mt-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">新密码</label>
          <input v-model="password" type="password" required minlength="6"
            class="w-full border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800"
            placeholder="至少 6 位" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">确认密码</label>
          <input v-model="confirm" type="password" required minlength="6"
            class="w-full border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800"
            placeholder="再次输入新密码" />
        </div>

        <p v-if="error" class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50">
          {{ loading ? '重置中...' : '设置新密码' }}
        </button>

        <p class="text-center text-sm text-gray-500 dark:text-gray-400">
          <NuxtLink to="/login" class="text-survivor-600 dark:text-survivor-400 hover:underline">
            返回登录
          </NuxtLink>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const { setAuth } = useAuth()

const token = computed(() => {
  const t = route.query.token
  return typeof t === 'string' && /^[0-9a-f]{64}$/.test(t) ? t : ''
})

const password = ref('')
const confirm = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  loading.value = true
  try {
    const res = await $fetch<{ token: string; user: any }>('/api/auth/reset-password', {
      method: 'POST',
      body: { token: token.value, password: password.value },
    })
    setAuth(res.token, res.user)
    router.push('/')
  } catch (e: any) {
    error.value = e.data?.message || '重置失败，链接可能已过期'
  } finally {
    loading.value = false
  }
}
</script>