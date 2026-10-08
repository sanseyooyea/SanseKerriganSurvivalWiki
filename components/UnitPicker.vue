<template>
  <div ref="root" class="relative">
    <button
      type="button"
      class="flex w-full items-center gap-2.5 rounded-lg border border-surface-200 bg-white px-3 py-2 text-left transition-colors
             hover:border-surface-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-survivor-500/40
             dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600"
      @click="open = !open"
    >
      <template v-if="selected">
        <UnitIcon :icon="selected.icon" :alt="selected.nameZh" size="sm" />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-medium text-gray-800 dark:text-gray-100">{{ selected.nameZh }}</span>
          <span class="flex items-center gap-1 text-[0.65rem] text-gray-400">
            <span class="h-1.5 w-1.5 rounded-full" :class="selected.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'" />
            {{ ownerText(selected) }}<template v-if="selected.formLabel"> · {{ selected.formLabel }}形态</template>
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
      <div class="border-b border-surface-200 p-2 dark:border-gray-700">
        <input
          ref="input"
          v-model="q"
          type="search"
          placeholder="搜索单位名、职业或 id"
          class="w-full rounded-md border border-surface-200 bg-transparent px-2.5 py-1.5 text-sm
                 focus:border-survivor-400 focus:outline-none dark:border-gray-700"
          @keydown.esc="open = false"
          @keydown.enter.prevent="matches[0] && pick(matches[0].id)"
        />
        <div class="mt-1.5 flex gap-1">
          <FilterChip v-for="t in TEAMS" :key="t.value" :active="team === t.value" @click="team = t.value">{{ t.label }}</FilterChip>
          <label class="ml-auto flex items-center gap-1 text-[0.65rem] text-gray-500">
            <input v-model="armedOnly" type="checkbox" class="rounded border-surface-300 dark:border-gray-600" /> 仅有武器
          </label>
        </div>
      </div>
      <ul class="max-h-72 overflow-y-auto py-1">
        <li v-for="u in matches" :key="u.id">
          <button
            type="button"
            class="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-surface-50 dark:hover:bg-gray-700/50"
            :class="u.id === modelValue ? 'bg-survivor-50 dark:bg-survivor-800/30' : ''"
            @click="pick(u.id)"
          >
            <UnitIcon :icon="u.icon" :alt="u.nameZh" size="xs" />
            <span class="min-w-0 flex-1 truncate text-sm text-gray-700 dark:text-gray-200">
              {{ u.nameZh }}<span v-if="u.formLabel" class="text-gray-400"> · {{ u.formLabel }}</span>
            </span>
            <span class="shrink-0 truncate text-[0.65rem] text-gray-400">{{ ownerText(u) }}</span>
          </button>
        </li>
        <li v-if="!matches.length" class="px-3 py-4 text-center text-xs text-gray-400">没有匹配的单位</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { UnitEntry } from '~/composables/useUnitsData'

const props = defineProps<{ modelValue: string | null; placeholder?: string }>()
const emit = defineEmits<{ 'update:modelValue': [id: string] }>()
const { allUnits, unitMap, roleOf } = useUnitsData()

const open = ref(false)
const q = ref('')
const team = ref('All')
const armedOnly = ref(false)
const root = ref<HTMLElement>()
const input = ref<HTMLInputElement>()

const TEAMS = [
  { value: 'All', label: '全部' },
  { value: 'Survivor', label: '生存方' },
  { value: 'Kerrigan', label: '凯瑞甘方' },
]

const selected = computed(() => (props.modelValue ? unitMap[props.modelValue] : null))

function ownerText(u: UnitEntry) {
  return u.owners.map(o => roleOf(o)?.nameZh || o).join('、')
}

const matches = computed(() => {
  const n = q.value.trim().toLowerCase()
  return allUnits.value
    .filter(u => team.value === 'All' || u.team === team.value)
    .filter(u => !armedOnly.value || u.weapons.some(w => w.components.length))
    .filter(u => !n || u.nameZh.toLowerCase().includes(n) || u.id.toLowerCase().includes(n)
      || ownerText(u).toLowerCase().includes(n))
    .slice(0, 80)
})

function pick(id: string) {
  emit('update:modelValue', id)
  open.value = false
  q.value = ''
}

watch(open, (v) => { if (v) nextTick(() => input.value?.focus()) })

function onDocClick(e: MouseEvent) {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>
