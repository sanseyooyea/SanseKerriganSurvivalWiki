<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">兵种数据库</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        全部 {{ filtered.length }} / {{ all.length }} 个单位与建筑。DPS 分「对轻甲 / 对重甲 / 对凯瑞甘」三种靶标，
        满级列为该单位能吃到的全部研究科技拉满后的数值。点击行查看武器明细、升级曲线与生产来源。
      </p>
    </div>

    <!-- 筛选 -->
    <div class="wiki-card p-4 mb-5 space-y-3">
      <div class="flex flex-wrap gap-2 items-center">
        <span class="text-xs text-gray-500 dark:text-gray-400 w-14">阵营</span>
        <button v-for="t in teamOptions" :key="t.value" @click="team = t.value"
          class="px-2.5 py-1 rounded text-xs border transition-colors"
          :class="team === t.value
            ? 'bg-survivor-600 text-white border-survivor-600'
            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'">
          {{ t.label }}
        </button>
      </div>
      <div class="flex flex-wrap gap-2 items-center">
        <span class="text-xs text-gray-500 dark:text-gray-400 w-14">类别</span>
        <button v-for="c in categoryOptions" :key="c.value" @click="category = c.value"
          class="px-2.5 py-1 rounded text-xs border transition-colors"
          :class="category === c.value
            ? 'bg-survivor-600 text-white border-survivor-600'
            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'">
          {{ c.label }}
        </button>
      </div>
      <div class="flex flex-wrap gap-2 items-center">
        <span class="text-xs text-gray-500 dark:text-gray-400 w-14">属性</span>
        <button v-for="a in attributeOptions" :key="a" @click="toggleAttr(a)"
          class="px-2.5 py-1 rounded text-xs border transition-colors"
          :class="attrs.includes(a)
            ? 'bg-survivor-600 text-white border-survivor-600'
            : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-gray-300'">
          {{ attrLabel(a) }}
        </button>
      </div>
      <div class="flex flex-wrap gap-3 items-center">
        <input v-model="q" placeholder="搜索名称 / id…"
          class="px-3 py-1.5 rounded border border-gray-200 dark:border-gray-700 bg-transparent text-sm w-56
                 focus:outline-none focus:border-survivor-400" />
        <label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300">
          <input type="checkbox" v-model="onlyCombat" /> 仅有武器
        </label>
        <button v-if="isFiltered" @click="reset" class="text-xs text-survivor-600 dark:text-survivor-400 hover:underline">重置</button>
      </div>
    </div>

    <!-- 排序 + 表格 -->
    <div class="wiki-card overflow-x-auto">
      <table class="w-full text-sm min-w-[46rem]">
        <thead>
          <tr class="text-xs text-gray-400 border-b border-gray-200 dark:border-gray-700">
            <th class="text-left font-normal px-3 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('nameZh')">名称</th>
            <th class="text-left font-normal px-2 py-2">类别</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('cost')">造价</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('hp')">生命</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('armor')">护甲</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('dpsLight')">对轻甲</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('dpsArmored')">对重甲</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('dpsKerrigan')">对凯瑞甘</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('dpsArmoredMax')">满级·重甲</th>
            <th class="text-right font-normal px-2 py-2 cursor-pointer hover:text-gray-600" @click="sortBy('dpsPer100')">每100资源</th>
            <th class="text-left font-normal px-3 py-2">所属</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700/60">
          <tr v-for="u in filtered" :key="u.id" class="hover:bg-surface-50 dark:hover:bg-gray-800/40 transition-colors">
            <td class="px-3 py-1.5">
              <NuxtLink :to="`/units/${u.id}`" class="flex items-center gap-2 text-gray-800 dark:text-gray-200 hover:text-survivor-600 dark:hover:text-survivor-400">
                <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="u.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'" />
                <span class="truncate">{{ u.nameZh }}</span>
                <span v-for="a in u.attributes.slice(0, 2)" :key="a"
                  class="hidden md:inline-block px-1 py-px rounded text-[0.6rem]" :class="attrClass(a)">{{ attrLabel(a) }}</span>
              </NuxtLink>
            </td>
            <td class="px-2 py-1.5 text-xs text-gray-500">{{ CATEGORY_LABELS[u.category] || u.category }}</td>
            <td class="px-2 py-1.5 text-right font-mono text-xs text-gray-500">{{ costText(u) }}</td>
            <td class="px-2 py-1.5 text-right font-mono text-xs">{{ u.stats.hp }}</td>
            <td class="px-2 py-1.5 text-right font-mono text-xs">{{ u.stats.armor }}</td>
            <td class="px-2 py-1.5 text-right font-mono text-xs text-orange-600 dark:text-orange-400">{{ u.derived.dpsLight || '' }}</td>
            <td class="px-2 py-1.5 text-right font-mono text-xs text-orange-600 dark:text-orange-400">{{ u.derived.dpsArmored || '' }}</td>
            <td class="px-2 py-1.5 text-right font-mono text-xs" :class="u.derived.dpsKerrigan ? 'text-red-600 dark:text-red-400' : 'text-gray-300 dark:text-gray-600'">
              {{ u.derived.dpsKerrigan ?? '' }}
            </td>
            <td class="px-2 py-1.5 text-right font-mono text-xs text-gray-600 dark:text-gray-300">{{ u.derived.dpsArmoredMax || '' }}</td>
            <td class="px-2 py-1.5 text-right font-mono text-xs text-gray-500">{{ u.derived.dpsPer100 || '' }}</td>
            <td class="px-3 py-1.5 text-xs text-gray-500 truncate max-w-[10rem]">
              {{ u.owners.map(ownerZh).join('、') }}
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!filtered.length" class="text-center py-12 text-gray-400 text-sm">没有符合条件的单位</div>
    </div>
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
  q.value || team.value !== 'All' || category.value !== 'All' || attrs.value.length || onlyCombat.value)

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
function costText(u: UnitEntry) {
  const c = u.cost
  if (!c.minerals && !c.gas) return '—'
  return `${c.minerals}${c.gas ? '/' + c.gas : ''}`
}

useHead({ title: '兵种数据库 · KS2 Wiki' })
</script>
