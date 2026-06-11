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

      <!-- Description -->
      <section class="wiki-card p-5 mb-4">
        <div class="section-title">职业描述</div>
        <textarea v-model="form.description" rows="3"
          class="edit-textarea" />
      </section>

      <!-- Stats -->
      <section class="wiki-card p-5 mb-4">
        <div class="section-title">基础属性</div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div v-for="sf in statFields" :key="sf.key">
            <label class="text-xs text-gray-500 dark:text-gray-400 block mb-1">{{ sf.label }}</label>
            <input v-model.number="form.stats[sf.key]" type="number" step="any" class="edit-input" />
          </div>
        </div>
      </section>

      <!-- Abilities -->
      <section class="wiki-card p-5 mb-4">
        <div class="flex items-center justify-between mb-3">
          <div class="section-title mb-0">技能</div>
          <button @click="addAbility" class="edit-add-btn">+ 添加技能</button>
        </div>
        <div class="space-y-2">
          <div v-for="(ab, i) in form.abilities" :key="i"
            class="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
            <div class="flex-1 grid grid-cols-2 gap-2">
              <input v-model="ab.nameZh" placeholder="中文名" class="edit-input text-xs" />
              <input v-model="ab.nameEn" placeholder="英文名/ID" class="edit-input text-xs" />
            </div>
            <input v-model="ab.tooltip" placeholder="描述" class="flex-[2] edit-input text-xs" />
            <button @click="form.abilities.splice(i, 1)" class="edit-del-btn">×</button>
          </div>
        </div>
      </section>
<!-- PLACEHOLDER_UNITS -->
      <!-- Troops -->
      <section class="wiki-card p-5 mb-4">
        <div class="flex items-center justify-between mb-3">
          <div class="section-title mb-0">兵种</div>
          <button @click="addUnit('troops')" class="edit-add-btn">+ 添加兵种</button>
        </div>
        <div class="space-y-2">
          <div v-for="(u, i) in form.troops" :key="i"
            class="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
            <input v-model="u.nameZh" placeholder="名称" class="w-28 edit-input text-xs" />
            <input v-model.number="u.hp" placeholder="HP" type="number" class="w-16 edit-input text-xs" />
            <input v-model.number="u.shield" placeholder="护盾" type="number" class="w-16 edit-input text-xs" />
            <input v-model.number="u.damage" placeholder="伤害" type="number" class="w-16 edit-input text-xs" />
            <input v-model.number="u.attackSpeed" placeholder="攻速" type="number" step="0.01" class="w-16 edit-input text-xs" />
            <button @click="form.troops.splice(i, 1)" class="edit-del-btn">×</button>
          </div>
        </div>
      </section>

      <!-- Buildings -->
      <section class="wiki-card p-5 mb-4">
        <div class="flex items-center justify-between mb-3">
          <div class="section-title mb-0">建筑</div>
          <button @click="addUnit('buildings')" class="edit-add-btn">+ 添加建筑</button>
        </div>
        <div class="space-y-2">
          <div v-for="(u, i) in form.buildings" :key="i"
            class="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
            <input v-model="u.nameZh" placeholder="名称" class="w-28 edit-input text-xs" />
            <input v-model.number="u.hp" placeholder="HP" type="number" class="w-16 edit-input text-xs" />
            <input v-model.number="u.shield" placeholder="护盾" type="number" class="w-16 edit-input text-xs" />
            <button @click="form.buildings.splice(i, 1)" class="edit-del-btn">×</button>
          </div>
        </div>
      </section>

      <!-- Economy -->
      <section class="wiki-card p-5 mb-4">
        <div class="flex items-center justify-between mb-3">
          <div class="section-title mb-0">经济建筑</div>
          <button @click="addUnit('economy')" class="edit-add-btn">+ 添加经济建筑</button>
        </div>
        <div class="space-y-2">
          <div v-for="(u, i) in form.economy" :key="i"
            class="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
            <input v-model="u.nameZh" placeholder="名称" class="w-28 edit-input text-xs" />
            <input v-model.number="u.hp" placeholder="HP" type="number" class="w-16 edit-input text-xs" />
            <input v-model.number="u.shield" placeholder="护盾" type="number" class="w-16 edit-input text-xs" />
            <button @click="form.economy.splice(i, 1)" class="edit-del-btn">×</button>
          </div>
        </div>
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
const { getAbility } = useAbilityData()
const { getForHero: getUnitsForHero } = useUnitData()

const cls = computed(() => getById(classId))

const statFields = [
  { key: 'hp', label: '生命值' },
  { key: 'speed', label: '移动速度' },
  { key: 'armor', label: '护甲' },
  { key: 'energy', label: '能量' },
  { key: 'damage', label: '攻击伤害' },
  { key: 'attackSpeed', label: '攻击间隔' },
  { key: 'attackCount', label: '攻击次数' },
  { key: 'range', label: '射程' },
]

interface AbilEntry { nameZh: string; nameEn: string; tooltip: string }
interface UnitEntry { id: string; nameZh: string; hp?: number; shield?: number; damage?: number; attackSpeed?: number }

const form = reactive({
  description: '',
  stats: {} as Record<string, number | null>,
  abilities: [] as AbilEntry[],
  troops: [] as UnitEntry[],
  buildings: [] as UnitEntry[],
  economy: [] as UnitEntry[],
  notes: '',
})

const saving = ref(false)
const error = ref('')
const saved = ref(false)

function addAbility() {
  form.abilities.push({ nameZh: '', nameEn: '', tooltip: '' })
}
function addUnit(list: 'troops' | 'buildings' | 'economy') {
  form[list].push({ id: '', nameZh: '' })
}

onMounted(async () => {
  if (!cls.value) return
  form.description = cls.value.description || ''
  form.stats = { ...cls.value.stats }
  form.abilities = cls.value.abilities.map(aid => {
    const ab = getAbility(aid)
    return { nameZh: ab?.nameZh || '', nameEn: ab?.nameEn || aid, tooltip: ab?.tooltip || '' }
  })
  const units = getUnitsForHero(cls.value.nameEn)
  form.troops = units.troops.map(u => ({ ...u }))
  form.buildings = units.buildings.map(u => ({ ...u }))
  form.economy = units.economy.map(u => ({ ...u }))
  try {
    const ov = await $fetch<any>(`/api/classes/${classId}`)
    if (ov) {
      if (ov.description) form.description = ov.description
      if (ov.stats) Object.assign(form.stats, ov.stats)
      if (ov.abilities) form.abilities = ov.abilities
      if (ov.troops) form.troops = ov.troops
      if (ov.buildings) form.buildings = ov.buildings
      if (ov.economy) form.economy = ov.economy
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
        stats: form.stats,
        abilities: form.abilities,
        troops: form.troops,
        buildings: form.buildings,
        economy: form.economy,
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