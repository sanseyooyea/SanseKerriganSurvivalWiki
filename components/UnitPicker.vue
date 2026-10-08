<template>
  <div ref="root" class="relative">
    <!-- 当前选择 -->
    <button
      type="button"
      class="flex w-full items-center gap-2.5 rounded-lg border border-surface-200 bg-white px-3 py-2 text-left transition-colors
             hover:border-surface-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-survivor-500/40
             dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600"
      @click="toggle"
    >
      <template v-if="selected">
        <UnitIcon :icon="selected.icon" :alt="selected.nameZh" size="sm" />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-medium text-gray-800 dark:text-gray-100">
            {{ selected.nameZh }}<span v-if="labelOf(selected)" class="font-normal text-gray-400"> · {{ labelOf(selected) }}</span>
          </span>
          <span class="flex items-center gap-1 text-[0.65rem] text-gray-400">
            <span class="h-1.5 w-1.5 rounded-full" :class="selected.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'" />
            {{ ownerText(selected) }}
          </span>
        </span>
      </template>
      <span v-else class="flex-1 text-sm text-gray-400">{{ placeholder }}</span>
      <svg class="h-3.5 w-3.5 shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div
      v-if="open"
      class="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-lg border border-surface-200 bg-white shadow-elevated
             dark:border-gray-700 dark:bg-gray-800"
    >
      <!-- 顶栏：搜索（跨英雄直接搜单位） + 第一步的阵营筛选 / 第二步的返回 -->
      <div class="space-y-1.5 border-b border-surface-200 p-2 dark:border-gray-700">
        <input
          ref="input"
          v-model="q"
          type="search"
          :placeholder="hero ? `在「${heroZh(hero)}」里筛选，或搜索全部单位` : '搜索英雄或单位'"
          class="w-full rounded-md border border-surface-200 bg-transparent px-2.5 py-1.5 text-sm
                 focus:border-survivor-400 focus:outline-none dark:border-gray-700"
          @keydown.esc="open = false"
        />
        <div v-if="!hero && !q" class="flex gap-1">
          <FilterChip v-for="t in TEAMS" :key="t.value" :active="team === t.value" @click="team = t.value">{{ t.label }}</FilterChip>
        </div>
        <div v-else-if="hero" class="flex items-center gap-2">
          <button type="button"
            class="inline-flex items-center gap-1 text-xs text-survivor-600 hover:underline dark:text-survivor-400"
            @click="back">
            <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            全部英雄
          </button>
          <span class="text-xs text-gray-400">/</span>
          <span class="text-xs font-medium text-gray-700 dark:text-gray-200">{{ heroZh(hero) }}</span>
        </div>
      </div>

      <div class="max-h-80 overflow-y-auto py-1">
        <!-- 第一步：选英雄 -->
        <template v-if="!hero && !q">
          <div v-for="g in heroGroups" :key="g.label">
            <div class="px-3 pb-1 pt-2 text-[0.6rem] font-medium uppercase tracking-wider text-gray-400">{{ g.label }}</div>
            <div class="grid grid-cols-2 gap-0.5 px-1.5 sm:grid-cols-3">
              <button
                v-for="h in g.heroes"
                :key="h.nameEn"
                type="button"
                class="flex items-center gap-2 rounded-md px-1.5 py-1 text-left hover:bg-surface-50 dark:hover:bg-gray-700/50"
                @click="hero = h.nameEn"
              >
                <UnitIcon :icon="`/icons/${String(h.roleId).padStart(2, '0')}.png`" :alt="h.nameZh" size="sm" />
                <span class="min-w-0 flex-1 truncate text-sm text-gray-700 dark:text-gray-200">{{ h.nameZh }}</span>
                <span class="shrink-0 font-mono text-[0.6rem] text-gray-400">{{ h.count }}</span>
              </button>
            </div>
          </div>
        </template>

        <!-- 第二步：该英雄可以出的单位（按类别分组，形态缩进挂在本体下） -->
        <template v-else-if="hero && !globalSearch">
          <div v-for="g in heroUnitGroups" :key="g.label">
            <div class="px-3 pb-1 pt-2 text-[0.6rem] font-medium uppercase tracking-wider text-gray-400">{{ g.label }}</div>
            <template v-for="row in g.rows" :key="row.unit.id">
              <UnitOption :u="row.unit" :label="labelOf(row.unit)" :indent="row.indent" :active="row.unit.id === modelValue" @pick="pick" />
            </template>
          </div>
          <p v-if="!heroUnitGroups.length" class="px-3 py-4 text-center text-xs text-gray-400">没有匹配的单位</p>
        </template>

        <!-- 搜索：直接列全部匹配单位 -->
        <template v-else>
          <UnitOption v-for="u in searchHits" :key="u.id" :u="u" :label="labelOf(u)" :owner="ownerText(u)"
            :active="u.id === modelValue" @pick="pick" />
          <p v-if="!searchHits.length" class="px-3 py-4 text-center text-xs text-gray-400">没有匹配的单位</p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { UnitEntry } from '~/composables/useUnitsData'
import { CATEGORY_LABELS } from '~/composables/useUnitsData'
import UnitIcon from '~/components/UnitIcon.vue'

const props = defineProps<{ modelValue: string | null; placeholder?: string }>()
const emit = defineEmits<{ 'update:modelValue': [id: string] }>()
const { allUnits, unitMap, heroMap, roleOf } = useUnitsData()

const open = ref(false)
const q = ref('')
const team = ref('All')
const hero = ref<string | null>(null)
const root = ref<HTMLElement>()
const input = ref<HTMLInputElement>()

const TEAMS = [
  { value: 'All', label: '全部' },
  { value: 'Survivor', label: '生存方' },
  { value: 'Kerrigan', label: '凯瑞甘方' },
]

const selected = computed(() => (props.modelValue ? unitMap[props.modelValue] : null))

function heroZh(nameEn: string) { return roleOf(nameEn)?.nameZh || nameEn }
function ownerText(u: UnitEntry) {
  // 凯瑞甘方共享兵种有十几个所属英雄，全列会把选择框撑成两三行
  const names = u.owners.map(heroZh)
  return names.length > 3 ? `${names.slice(0, 2).join('、')} 等 ${names.length} 位英雄` : names.join('、')
}

// 分级技能召出的单位同名（定点防御无人机 ×4），用技能等级区分；形态用形态名区分
const skillLevel = computed(() => {
  const m: Record<string, number> = {}
  for (const h of Object.values(heroMap)) {
    for (const s of h.skillSummons || []) for (const l of s.levels) m[l.unit] = l.level
  }
  return m
})
function labelOf(u: UnitEntry) {
  if (u.formLabel) return `${u.formLabel}形态`
  if (skillLevel.value[u.id]) return `Lv${skillLevel.value[u.id]}`
  return ''
}

// ---- 第一步：英雄列表
const heroGroups = computed(() => {
  const list = Object.entries(heroMap)
    .map(([nameEn, h]) => ({ nameEn, nameZh: heroZh(nameEn), roleId: roleOf(nameEn)?.id ?? h.roleId, team: h.team, count: h.unitIds.length }))
    .filter(h => team.value === 'All' || h.team === team.value)
    .sort((a, b) => a.roleId - b.roleId)
  const out = []
  if (team.value !== 'Kerrigan') out.push({ label: '生存方', heroes: list.filter(h => h.team === 'Survivor') })
  if (team.value !== 'Survivor') out.push({ label: '凯瑞甘方', heroes: list.filter(h => h.team === 'Kerrigan') })
  return out.filter(g => g.heroes.length)
})

// ---- 第二步：该英雄的单位
const CAT_ORDER = ['hero', 'troop', 'skill', 'summon', 'building', 'economy', 'morph']
const heroUnitGroups = computed(() => {
  const h = hero.value ? heroMap[hero.value] : null
  if (!h) return []
  const n = q.value.trim().toLowerCase()
  const match = (u: UnitEntry) => !n || u.nameZh.toLowerCase().includes(n) || u.id.toLowerCase().includes(n)
  const units = h.unitIds.map(id => unitMap[id]).filter(Boolean)
  return CAT_ORDER.map((cat) => {
    const rows: { unit: UnitEntry; indent: boolean }[] = []
    for (const u of units.filter(x => x.category === cat)) {
      const forms = (u.forms || []).map(f => unitMap[f.id]).filter(Boolean)
      const hit = match(u) || forms.some(match)
      if (!hit) continue
      rows.push({ unit: u, indent: false })
      for (const f of forms) rows.push({ unit: f, indent: true })
    }
    return { label: CATEGORY_LABELS[cat] || cat, rows }
  }).filter(g => g.rows.length)
})

// 在英雄内筛选不到时，自动退化成全局搜索（用户多半是想直接找某个单位）
const searchHits = computed(() => {
  const n = q.value.trim().toLowerCase()
  if (!n) return []
  return allUnits.value
    .filter(u => u.nameZh.toLowerCase().includes(n) || u.id.toLowerCase().includes(n) || ownerText(u).toLowerCase().includes(n))
    .slice(0, 80)
})
const globalSearch = computed(() => !!q.value.trim() && (!hero.value || !heroUnitGroups.value.length))

function toggle() {
  open.value = !open.value
  // 打开时直接定位到当前单位所属英雄，改兵种不用重新选英雄
  if (open.value) hero.value = selected.value?.owners[0] || null
}
function back() { hero.value = null; q.value = '' }
function pick(id: string) {
  emit('update:modelValue', id)
  open.value = false
  q.value = ''
}

watch(open, (v) => { if (v) nextTick(() => input.value?.focus()) })
function onDocClick(e: MouseEvent) {
  // 用事件派发时的路径判断：点「全部英雄」/英雄后该按钮会被重渲染移出 DOM，
  // 此时 root.contains(e.target) 已是 false，会误判成点在外面而把下拉关掉
  if (root.value && !e.composedPath().includes(root.value)) open.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))

// 单行选项（本文件内复用）
const UnitOption = defineComponent({
  props: {
    u: { type: Object as PropType<UnitEntry>, required: true },
    label: { type: String, default: '' },
    owner: { type: String, default: '' },
    indent: { type: Boolean, default: false },
    active: { type: Boolean, default: false },
  },
  emits: ['pick'],
  setup(p, { emit: e }) {
    return () => h('button', {
      type: 'button',
      class: ['flex w-full items-center gap-2 py-1.5 pr-3 text-left hover:bg-surface-50 dark:hover:bg-gray-700/50',
        p.indent ? 'pl-9' : 'pl-3',
        p.active ? 'bg-survivor-50 dark:bg-survivor-800/30' : ''],
      onClick: () => e('pick', p.u.id),
    }, [
      p.indent ? h('span', { class: 'text-[0.6rem] text-gray-300 dark:text-gray-600' }, '⇄') : null,
      h(UnitIcon, { icon: p.u.icon, alt: p.u.nameZh, size: 'xs' }),
      // 缩进的形态行只写形态名（本体名就在上一行），避免「破坏者（埋地） · 埋地形态」这种重复
      h('span', { class: 'min-w-0 flex-1 truncate text-sm text-gray-700 dark:text-gray-200', title: p.u.nameZh },
        p.indent && p.label
          ? [h('span', { class: 'text-gray-500 dark:text-gray-400' }, p.label)]
          : [p.u.nameZh, p.label ? h('span', { class: 'text-gray-400' }, ` · ${p.label}`) : null]),
      p.u.weapons.some(w => w.components.length)
        ? null
        : h('span', { class: 'shrink-0 text-[0.6rem] text-gray-300 dark:text-gray-600' }, '无武器'),
      p.owner ? h('span', { class: 'shrink-0 truncate text-[0.65rem] text-gray-400' }, p.owner) : null,
    ])
  },
})
</script>
