<template>
  <div>
    <header class="mb-6">
      <h1 class="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">兵种数据库</h1>
      <p class="mt-1.5 max-w-3xl text-sm leading-relaxed text-gray-500 dark:text-gray-400">
        全部 {{ all.length }} 个单位与建筑。DPS 分「对轻甲 / 对重甲 / 对凯瑞甘」三种靶标——
        凯瑞甘方是本图最高威胁目标，武器会按其属性与排除项自动结算。
        满级列为该单位能吃到的全部研究科技拉满后的数值。
      </p>
    </header>

    <!-- 筛选 -->
    <section class="wiki-card mb-5 p-4">
      <div class="space-y-3">
        <FilterRow label="阵营">
          <FilterChip v-for="t in teamOptions" :key="t.value" :active="team === t.value" @click="team = t.value">{{ t.label }}</FilterChip>
        </FilterRow>

        <FilterRow label="类别">
          <FilterChip v-for="c in categoryOptions" :key="c.value" :active="category === c.value" @click="category = c.value">{{ c.label }}</FilterChip>
        </FilterRow>

        <FilterRow label="属性">
          <FilterChip v-for="a in attributeOptions" :key="a" :active="attrs.includes(a)" @click="toggleAttr(a)">{{ attrLabel(a) }}</FilterChip>
          <span class="ml-1 self-center text-[0.65rem] text-gray-400">{{ attrs.length > 1 ? '需同时具备' : '' }}</span>
        </FilterRow>

        <div class="flex flex-wrap items-center gap-3 border-t border-surface-200 pt-3 dark:border-gray-700">
          <div class="relative">
            <svg class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 10.5a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z" />
            </svg>
            <input
              v-model="q"
              type="search"
              placeholder="搜索名称或 id"
              class="w-56 rounded-md border border-surface-200 bg-transparent py-1.5 pl-8 pr-3 text-sm
                     placeholder:text-gray-400 focus:border-survivor-400 focus:outline-none focus:ring-2 focus:ring-survivor-500/20
                     dark:border-gray-700"
            />
          </div>

          <label class="flex cursor-pointer items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
            <input v-model="onlyCombat" type="checkbox" class="rounded border-surface-300 text-survivor-600 focus:ring-survivor-500 dark:border-gray-600" />
            仅有武器
          </label>

          <span class="font-mono text-xs tabular-nums text-gray-400">{{ filtered.length }} / {{ all.length }}</span>

          <button
            v-if="isFiltered"
            type="button"
            class="ml-auto text-xs font-medium text-survivor-600 transition-colors hover:text-survivor-700 dark:text-survivor-400 dark:hover:text-survivor-300"
            @click="reset"
          >重置筛选</button>
        </div>
      </div>
    </section>

    <!-- 表格 -->
    <section class="wiki-card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[64rem] text-sm">
          <thead>
            <tr class="border-b border-surface-200 bg-surface-50 text-[0.65rem] uppercase tracking-wider text-gray-400 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-500">
              <th
                v-for="col in COLUMNS"
                :key="col.key"
                class="select-none px-3 py-2 font-medium"
                :class="[col.align === 'right' ? 'text-right' : 'text-left', col.sortable ? 'cursor-pointer transition-colors hover:text-gray-600 dark:hover:text-gray-300' : '']"
                :title="col.hint"
                @click="col.sortable && sortBy(col.key)"
              >
                <span class="inline-flex items-center gap-1" :class="col.align === 'right' ? 'flex-row-reverse' : ''">
                  {{ col.label }}
                  <svg
                    v-if="col.sortable"
                    class="h-3 w-3 transition-opacity"
                    :class="sortKey === col.key ? 'opacity-100' : 'opacity-0'"
                    :style="sortKey === col.key && sortDir === 'asc' ? 'transform: rotate(180deg)' : ''"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </span>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-200 dark:divide-gray-700/70">
            <tr
              v-for="u in filtered"
              :key="u.id"
              class="group transition-colors hover:bg-survivor-50/50 dark:hover:bg-gray-700/30"
            >
              <td class="px-3 py-2">
                <NuxtLink :to="`/units/${u.id}`" class="flex items-center gap-2.5">
                  <UnitIcon :icon="u.icon" :alt="u.nameZh" size="sm" />
                  <span class="min-w-0">
                    <span class="block font-medium leading-snug text-gray-800 group-hover:text-survivor-700 dark:text-gray-200 dark:group-hover:text-survivor-300">{{ u.nameZh }}</span>
                    <span class="mt-0.5 flex items-center gap-1">
                      <span
                        class="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                        :class="u.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'"
                        :title="u.team === 'Kerrigan' ? '凯瑞甘方' : '生存方'"
                      />
                      <span class="text-[0.65rem] leading-snug text-gray-400">{{ u.owners.map(ownerZh).join('、') }}</span>
                    </span>
                  </span>
                </NuxtLink>
              </td>
              <td class="px-2 py-2">
                <div class="flex flex-wrap gap-1">
                  <span v-for="a in u.attributes" :key="a" class="rounded px-1.5 py-px text-[0.6rem] leading-4" :class="attrClass(a)">{{ attrLabel(a) }}</span>
                </div>
              </td>
              <td class="px-2 py-2 text-right font-mono text-xs tabular-nums text-gray-500">
                <span v-if="u.cost.minerals || u.cost.gas">{{ u.cost.minerals }}<span v-if="u.cost.gas" class="text-gray-400">/{{ u.cost.gas }}</span></span>
                <span v-else class="text-gray-300 dark:text-gray-600">—</span>
              </td>
              <td class="px-2 py-2 text-right font-mono text-xs tabular-nums">{{ u.stats.hp }}</td>
              <td class="px-2 py-2 text-right font-mono text-xs tabular-nums text-gray-500">{{ u.stats.armor }}</td>
              <td class="px-2 py-2 text-right font-mono text-xs font-semibold tabular-nums" :class="dpsClass(u.derived.dpsLight)">{{ u.derived.dpsLight ?? '' }}</td>
              <td class="px-2 py-2 text-right font-mono text-xs font-semibold tabular-nums" :class="dpsClass(u.derived.dpsArmored)">{{ u.derived.dpsArmored ?? '' }}</td>
              <td class="px-2 py-2 text-right font-mono text-xs font-semibold tabular-nums" :class="u.derived.dpsKerrigan ? 'text-kerrigan-600 dark:text-kerrigan-400' : 'text-gray-300 dark:text-gray-600'">
                {{ u.derived.dpsKerrigan ?? '' }}
              </td>
              <td class="px-2 py-2 text-right font-mono text-xs tabular-nums" :class="isMaxed(u) ? 'text-gray-700 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">
                {{ u.derived.dpsArmoredMax || '' }}
              </td>
              <td class="px-2 py-2 text-right font-mono text-xs tabular-nums text-gray-500">{{ u.derived.dpsPer100Light || '' }}</td>
              <td class="px-2 py-2 text-right font-mono text-xs tabular-nums text-gray-500">{{ u.derived.dpsPer100Armored || '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 空态 -->
      <div v-if="!filtered.length" class="flex flex-col items-center gap-2 px-6 py-16 text-center">
        <span class="text-2xl text-gray-300 dark:text-gray-600">◈</span>
        <p class="text-sm text-gray-500 dark:text-gray-400">没有符合条件的单位</p>
        <button type="button" class="text-xs font-medium text-survivor-600 hover:underline dark:text-survivor-400" @click="reset">清除全部筛选</button>
      </div>
    </section>

    <p v-if="filtered.length" class="mt-3 px-1 text-[0.7rem] leading-relaxed text-gray-400 dark:text-gray-500">
      「每 100 资源」= 轻甲 / 重甲 DPS 取高者 ÷（晶矿 + 气体），用于横向比较性价比；
      气矿在 KS2 里更稀缺，该列未对气体加权。表中 <span class="font-mono">—</span> 表示该项不适用（如建筑无武器、武器排除该靶标属性）。
    </p>
  </div>
</template>

<script setup lang="ts">
import { CATEGORY_LABELS, ATTRIBUTE_LABELS, ATTRIBUTE_FALLBACK } from '~/composables/useUnitsData'
import type { UnitEntry } from '~/composables/useUnitsData'

const { allUnits, roleOf } = useUnitsData()

const q = ref('')
const team = ref('All')
const category = ref('All')
const attrs = ref<string[]>([])
const onlyCombat = ref(false)
const sortKey = ref('dpsKerrigan')
const sortDir = ref<'asc' | 'desc'>('desc')

const all = computed(() => allUnits.value)

const COLUMNS = [
  { key: 'nameZh', label: '单位', align: 'left', sortable: true },
  { key: 'attributes', label: '属性', align: 'left', sortable: false },
  { key: 'cost', label: '矿/气', align: 'right', sortable: true, hint: '晶矿 / 气体' },
  { key: 'hp', label: '生命', align: 'right', sortable: true },
  { key: 'armor', label: '护甲', align: 'right', sortable: true },
  { key: 'dpsLight', label: '对轻甲', align: 'right', sortable: true },
  { key: 'dpsArmored', label: '对重甲', align: 'right', sortable: true },
  { key: 'dpsKerrigan', label: '对凯瑞甘', align: 'right', sortable: true, hint: '凯瑞甘本体靶标：英雄 / 巨型 / 首领' },
  { key: 'dpsArmoredMax', label: '满级·重甲', align: 'right', sortable: true, hint: '全科技拉满后对重甲 DPS' },
  { key: 'dpsPer100Light', label: '每100资源·轻', align: 'right', sortable: true, hint: '每 100 资源对轻甲 DPS（未对气体加权）' },
  { key: 'dpsPer100Armored', label: '每100资源·重', align: 'right', sortable: true, hint: '每 100 资源对重甲 DPS' },
] as const

const teamOptions = [
  { value: 'All', label: '全部' },
  { value: 'Survivor', label: '生存方' },
  { value: 'Kerrigan', label: '凯瑞甘方' },
]
const categoryOptions = [
  { value: 'All', label: '全部' },
  ...['hero', 'troop', 'building', 'economy', 'morph', 'summon'].map(c => ({ value: c, label: CATEGORY_LABELS[c] })),
]
const attributeOptions = ['Light', 'Armored', 'Biological', 'Mechanical', 'Massive', 'Structure', 'Psionic']

const isFiltered = computed(() =>
  !!q.value || team.value !== 'All' || category.value !== 'All' || attrs.value.length > 0 || onlyCombat.value)

function toggleAttr(a: string) {
  attrs.value = attrs.value.includes(a) ? attrs.value.filter(x => x !== a) : [...attrs.value, a]
}
function reset() {
  q.value = ''; team.value = 'All'; category.value = 'All'; attrs.value = []; onlyCombat.value = false
  sortKey.value = 'dpsKerrigan'; sortDir.value = 'desc'
}
function sortBy(k: string) {
  if (sortKey.value === k) sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc'
  else { sortKey.value = k; sortDir.value = 'desc' }
}

function value(u: UnitEntry, k: string): number | string {
  switch (k) {
    case 'nameZh': return u.nameZh
    case 'cost': return u.cost.minerals + u.cost.gas * 2
    case 'hp': return u.stats.hp
    case 'armor': return u.stats.armor
    default: return (u.derived[k] as number) ?? -1
  }
}

const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase()
  const out = all.value.filter((u) => {
    if (team.value !== 'All' && u.team !== team.value) return false
    if (category.value !== 'All' && u.category !== category.value) return false
    if (onlyCombat.value && !u.weapons.length) return false
    if (attrs.value.length && !attrs.value.every(a => u.attributes.includes(a))) return false
    if (needle && !u.nameZh.toLowerCase().includes(needle) && !u.id.toLowerCase().includes(needle)) return false
    return true
  })
  const dir = sortDir.value === 'desc' ? -1 : 1
  return out.sort((a, b) => {
    const va = value(a, sortKey.value), vb = value(b, sortKey.value)
    if (typeof va === 'string' || typeof vb === 'string') return dir * String(va).localeCompare(String(vb))
    return dir * (va - vb)
  })
})

function attrLabel(a: string) { return ATTRIBUTE_LABELS[a]?.[0] || a }
function attrClass(a: string) { return ATTRIBUTE_LABELS[a]?.[1] || ATTRIBUTE_FALLBACK[0] }
function ownerZh(nameEn: string) { return roleOf(nameEn)?.nameZh || nameEn }
function dpsClass(v: number | null | undefined) {
  return v ? 'text-orange-600 dark:text-orange-400' : 'text-gray-300 dark:text-gray-600'
}
function isMaxed(u: UnitEntry) {
  return (u.derived.dpsArmoredMax || 0) > (u.derived.dpsArmored || 0)
}

useHead({ title: '兵种数据库 · KS2 Wiki' })
</script>
