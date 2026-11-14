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

      <div class="wiki-card p-5 mb-4">
        <div class="section-title">邮箱设置</div>
        <p class="text-xs text-gray-400 mb-3">绑定邮箱后可使用「忘记密码」功能找回账号</p>
        <div class="flex gap-2">
          <input v-model="emailInput" type="email" placeholder="your@email.com"
            class="flex-1 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-survivor-300" />
          <button @click="saveEmail" :disabled="savingEmail"
            class="px-4 py-2 text-sm font-medium text-white bg-survivor-600 rounded-lg hover:bg-survivor-700 disabled:opacity-50 transition whitespace-nowrap">
            {{ savingEmail ? '保存中...' : (user?.email ? '更换' : '绑定') }}
          </button>
        </div>
        <div v-if="user?.email" class="mt-2 text-xs text-gray-500">
          当前邮箱：<span class="text-gray-700 dark:text-gray-300">{{ user.email }}</span>
        </div>
        <p v-if="emailError" class="mt-2 text-xs text-red-500">{{ emailError }}</p>
        <p v-if="emailSuccess" class="mt-2 text-xs text-green-600">{{ emailSuccess }}</p>
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
      <div class="wiki-card p-5 mt-4" id="my-reviews">
        <div class="section-title">我的投稿</div>
        <p class="text-xs text-gray-400 mb-3">你提交的 Wiki 编辑及审核状态（管理员的编辑直接发布，不在此列）</p>
        <p v-if="reviewsError" class="text-xs text-red-500">{{ reviewsError }}</p>
        <div v-else-if="!myReviews.length" class="text-xs text-gray-400 py-4 text-center">
          {{ reviewsLoading ? '加载中...' : '暂无投稿' }}
        </div>
        <ul v-else class="divide-y divide-gray-100 dark:divide-gray-700">
          <li v-for="r in myReviews" :key="r.id" class="py-2.5 text-sm">
            <div class="flex items-center gap-2">
              <span class="wk-badge" :class="'wk-badge-' + r.status">{{ statusLabel[r.status] || r.status }}</span>
              <span v-if="r.is_new" class="text-[0.65rem] text-kerrigan-600 dark:text-kerrigan-400">新建</span>
              <NuxtLink v-if="r.status === 'approved'" :to="`/wiki/${r.slug}`"
                class="font-medium text-survivor-600 hover:underline truncate">{{ r.title }}</NuxtLink>
              <span v-else class="font-medium text-gray-900 dark:text-gray-100 truncate">{{ r.title }}</span>
              <span class="text-xs text-gray-400 ml-auto whitespace-nowrap">{{ fmtDate(r.created_at) }}</span>
            </div>
            <div v-if="r.admin_note" class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              管理员备注：{{ r.admin_note }}
            </div>
          </li>
        </ul>
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

const emailInput = ref('')
const savingEmail = ref(false)
const emailError = ref('')
const emailSuccess = ref('')

interface MyReview {
  id: number
  slug: string
  is_new: number
  title: string
  status: 'pending' | 'approved' | 'rejected'
  admin_note: string | null
  created_at: string
}
const myReviews = ref<MyReview[]>([])
const reviewsLoading = ref(false)
const reviewsError = ref('')
const statusLabel: Record<string, string> = { pending: '待审', approved: '已通过', rejected: '已驳回' }

function fmtDate(s: string) {
  // SQLite datetime('now') 为 UTC、无时区标记
  const d = new Date(s.replace(' ', 'T') + 'Z')
  return isNaN(d.getTime()) ? s : d.toLocaleString('zh-CN', { hour12: false }).slice(0, 16)
}

async function loadMyReviews() {
  if (!isLoggedIn.value) return
  reviewsLoading.value = true
  reviewsError.value = ''
  try {
    const res = await $fetch<{ reviews: MyReview[] }>('/api/wiki/reviews/mine', { headers: authHeaders.value })
    myReviews.value = res.reviews
  } catch (e: any) {
    reviewsError.value = e.data?.message || '投稿记录加载失败'
  } finally {
    reviewsLoading.value = false
  }
}

onMounted(() => {
  if (user.value?.handle) handleInput.value = user.value.handle
  if (user.value?.email) emailInput.value = user.value.email
  loadMyReviews()
})
watch(isLoggedIn, (v) => { if (v) loadMyReviews() })

async function saveEmail() {
  emailError.value = ''
  emailSuccess.value = ''
  const val = emailInput.value.trim()
  if (!val) { emailError.value = '请输入邮箱地址'; return }
  savingEmail.value = true
  try {
    await $fetch('/api/auth/email', {
      method: 'PUT',
      headers: authHeaders.value,
      body: { email: val },
    })
    emailSuccess.value = '邮箱绑定成功'
    await init()
  } catch (e: any) {
    emailError.value = e.data?.message || '绑定失败'
  } finally {
    savingEmail.value = false
  }
}

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

<style scoped>
.wk-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; letter-spacing: 0.03em;
  padding: 1px 7px; border: 1px solid currentColor; border-radius: 3px; flex-shrink: 0;
}
.wk-badge-pending { color: #6b7280; }
.dark .wk-badge-pending { color: #9ca3af; }
.wk-badge-approved { color: #16a34a; }
.dark .wk-badge-approved { color: #4ade80; }
.wk-badge-rejected { color: #9ca3af; text-decoration: line-through; }
.dark .wk-badge-rejected { color: #6b7280; }
</style>
