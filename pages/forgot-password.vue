<template>
  <div class="max-w-sm mx-auto py-12">
    <div class="wiki-card p-6">
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">找回密码</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">
        输入你的用户名或邮箱，我们将发送重置链接
      </p>

      <div v-if="sent" class="text-sm text-green-600 dark:text-green-400 space-y-2">
        <p>✅ 如果该账号已绑定邮箱，重置链接已发送至对应邮箱。</p>
        <p class="text-xs text-gray-400">链接有效期为 1 小时。如果没有收到邮件，请检查垃圾邮件箱。</p>
        <NuxtLink to="/login" class="inline-block mt-3 text-survivor-600 dark:text-survivor-400 hover:underline text-sm">
          返回登录
        </NuxtLink>
      </div>

      <form v-else @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">用户名或邮箱</label>
          <input v-model="login" type="text" required
            class="w-full border border-surface-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-200 dark:focus:ring-survivor-800"
            placeholder="输入注册时的用户名或绑定的邮箱" />
        </div>

        <p v-if="error" class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>

        <button type="submit" :disabled="loading"
          class="w-full py-2.5 rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50">
          {{ loading ? '发送中...' : '发送重置链接' }}
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
const login = ref('')
const error = ref('')
const loading = ref(false)
const sent = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await $fetch('/api/auth/forgot-password', {
      method: 'POST',
      body: { login: login.value },
    })
    sent.value = true
  } catch (e: any) {
    error.value = e.data?.message || '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>