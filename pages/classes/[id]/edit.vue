<template>
  <ClientOnly>
    <div v-if="!canEdit" class="text-center py-20">
      <p class="text-gray-400 text-lg">需要编辑者权限</p>
      <NuxtLink to="/login" class="text-survivor-600 hover:underline mt-2 inline-block">登录</NuxtLink>
    </div>
    <div v-else-if="cls">
      <NuxtLink :to="`/classes/${cls.id}`"
        class="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors mb-4">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        返回 {{ cls.nameZh }}
      </NuxtLink>
      <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-5">
        编辑：{{ cls.nameZh || cls.nameEn }}
      </h1>

      <!-- 边界提示：双轨制 -->
      <div class="rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 px-4 py-3 mb-4 text-sm text-amber-800 dark:text-amber-200">
        在线编辑仅用于<strong>职业简介</strong>和<strong>社区攻略</strong>。
        属性数值、技能、兵种/建筑数据来自游戏地图，如需修正请
        <NuxtLink to="/feedback" class="underline">提交反馈</NuxtLink>，由开发者核实后更新。
      </div>

      <!-- Description -->
      <section class="wiki-card p-5 mb-4">
        <div class="section-title">职业描述</div>
        <textarea v-model="form.description" rows="3"
          class="edit-textarea" />
      </section>

      <!-- Notes -->
      <section class="wiki-card p-5 mb-4">
        <div class="section-title">社区攻略 (Markdown)</div>
        <textarea v-model="form.notes" rows="6" placeholder="攻略提示、注意事项..."
          class="edit-textarea" />
      </section>

      <!-- Save -->
      <div class="flex items-center gap-3 mb-10">
        <button @click="save" :disabled="saving"
          class="px-5 py-2 text-sm font-medium text-white bg-survivor-600 rounded-lg hover:bg-survivor-700 disabled:opacity-50 transition">
          {{ saving ? '保存中...' : '保存所有修改' }}
        </button>
        <span v-if="error" class="text-sm text-red-500">{{ error }}</span>
        <span v-if="saved" class="text-sm text-green-600">已保存</span>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup lang="ts">
const route = useRoute()
const classId = Number(route.params.id)
const { canEdit, authHeaders } = useAuth()
const { getById } = useClassData()

const cls = computed(() => getById(classId))

// 双轨制：在线编辑只改文案（职业简介 + 社区攻略）。
// 属性/技能/兵种等结构化数据走 git + seed，不在此编辑。
const form = reactive({
  description: '',
  notes: '',
})

const saving = ref(false)
const error = ref('')
const saved = ref(false)

onMounted(async () => {
  if (!cls.value) return
  form.description = cls.value.description || ''
  try {
    const ov = await $fetch<any>(`/api/classes/${classId}`)
    if (ov) {
      if (ov.description) form.description = ov.description
      if (ov.notes) form.notes = ov.notes
    }
  } catch {}
})

async function save() {
  saving.value = true
  error.value = ''
  saved.value = false
  try {
    await $fetch(`/api/classes/${classId}`, {
      method: 'PUT',
      headers: authHeaders.value,
      body: {
        description: form.description,
        notes: form.notes,
      },
    })
    saved.value = true
  } catch (e: any) {
    error.value = e.data?.message || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.edit-textarea {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-family: monospace;
  background: white;
  color: #111;
  resize: vertical;
}
.edit-input {
  border: 1px solid #e5e7eb;
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-family: monospace;
  background: white;
  color: #111;
}
.edit-add-btn {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #86c7a3;
  color: #2d7a50;
}
.edit-del-btn {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  color: #9ca3af;
  font-size: 1.125rem;
  line-height: 1;
  cursor: pointer;
}
.edit-del-btn:hover {
  color: #ef4444;
  background: #fef2f2;
}
:root.dark .edit-textarea,
:root.dark .edit-input {
  background: #1f2937;
  color: #f3f4f6;
  border-color: #4b5563;
}
</style>