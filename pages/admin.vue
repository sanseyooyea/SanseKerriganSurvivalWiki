<template>
  <div v-if="!isAdmin" class="text-center py-20">
    <p class="text-gray-400 text-lg">需要管理员权限</p>
  </div>
  <div v-else>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">用户管理</h1>
    <div class="wiki-card overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-50 dark:bg-gray-800 text-left text-xs text-gray-500 dark:text-gray-400">
            <th class="px-4 py-3 font-medium">用户名</th>
            <th class="px-4 py-3 font-medium">句柄</th>
            <th class="px-4 py-3 font-medium">角色</th>
            <th class="px-4 py-3 font-medium">注册时间</th>
            <th class="px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-for="u in users" :key="u.id">
            <td class="px-4 py-3 text-gray-900 dark:text-gray-100 font-medium">{{ u.username }}</td>
            <td class="px-4 py-3 text-xs text-gray-500">
              <NuxtLink v-if="u.handle" :to="`/player/${u.handle}`" class="text-survivor-600 hover:underline">{{ u.handle }}</NuxtLink>
              <span v-else class="text-gray-300">-</span>
            </td>
            <td class="px-4 py-3">
              <select :value="u.role" @change="changeRole(u.id, ($event.target as HTMLSelectElement).value)"
                class="text-xs border border-gray-200 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200">
                <option value="user">user</option>
                <option value="editor">editor</option>
                <option value="admin">admin</option>
              </select>
            </td>
            <td class="px-4 py-3 text-gray-500 dark:text-gray-400">{{ formatDate(u.created_at) }}</td>
            <td class="px-4 py-3 text-xs text-gray-400">ID: {{ u.id }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
const { isAdmin, authHeaders } = useAuth()
const users = ref<any[]>([])

async function loadUsers() {
  try {
    const res = await $fetch<any>('/api/admin/users', { headers: authHeaders.value })
    users.value = res.users || res
  } catch {}
}

async function changeRole(userId: number, role: string) {
  try {
    await $fetch('/api/admin/users', {
      method: 'PATCH',
      headers: authHeaders.value,
      body: { userId, role },
    })
    await loadUsers()
  } catch {}
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('zh-CN')
}

onMounted(loadUsers)
</script>
