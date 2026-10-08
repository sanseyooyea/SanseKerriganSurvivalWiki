<template>
  <div v-if="unit">
    <a href="javascript:history.back()" class="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors mb-6">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      返回
    </a>

    <div class="wiki-card p-6 mb-6">
      <div class="flex flex-wrap items-center gap-3 mb-4">
        <div class="w-3 h-3 rounded-full"
          :class="unit.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'" />
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ unit.nameZh || unitId }}</h1>
        <span class="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
          {{ CATEGORY_LABELS[unit.category] || unit.category }}
        </span>
        <span v-for="a in unit.attributes" :key="a"
          class="text-xs px-1.5 py-0.5 rounded" :class="attrClass(a)">{{ attrLabel(a) }}</span>
      </div>

      <p v-if="ownerLinks.length" class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        所属职业：
        <template v-for="(o, i) in ownerLinks" :key="o.name">
          <span v-if="i"> · </span>
          <NuxtLink v-if="o.id >= 0" :to="`/classes/${o.id}`" class="text-survivor-600 dark:text-survivor-400 hover:underline">{{ o.zh }}</NuxtLink>
          <span v-else>{{ o.zh }}</span>
        </template>
      </p>

      <div class="section-title">基础属性</div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-1.5 text-sm mb-5">
        <div class="flex justify-between"><span class="text-gray-500">生命值</span><span class="font-mono">{{ unit.stats.hp }}</span></div>
        <div v-if="unit.stats.shield" class="flex justify-between"><span class="text-gray-500">护盾</span><span class="font-mono text-blue-600 dark:text-blue-400">{{ unit.stats.shield }}</span></div>
        <div class="flex justify-between">
          <span class="text-gray-500">护甲</span>
          <span class="font-mono">{{ unit.stats.armor }}<span v-if="isPlating" class="text-gray-400 text-xs"> 镀层</span></span>
        </div>
        <div v-if="unit.stats.speed" class="flex justify-between"><span class="text-gray-500">移动速度</span><span class="font-mono">{{ unit.stats.speed }}</span></div>
        <div v-if="unit.stats.sight" class="flex justify-between"><span class="text-gray-500">视野</span><span class="font-mono">{{ unit.stats.sight }}</span></div>
        <div v-if="unit.stats.hpRegen" class="flex justify-between"><span class="text-gray-500">回血/秒</span><span class="font-mono">{{ unit.stats.hpRegen }}</span></div>
        <div v-if="unit.cost.minerals || unit.cost.gas" class="flex justify-between">
          <span class="text-gray-500">造价</span>
          <span class="font-mono">{{ unit.cost.minerals }}<span v-if="unit.cost.gas">/{{ unit.cost.gas }}</span></span>
        </div>
        <div v-if="unit.cost.food" class="flex justify-between"><span class="text-gray-500">人口</span><span class="font-mono">{{ unit.cost.food }}</span></div>
      </div>

      <!-- 三种靶标 DPS -->
      <div class="section-title">火力（按靶标）</div>
      <table class="w-full text-sm mb-5">
        <thead>
          <tr class="text-xs text-gray-400">
            <th class="text-left font-normal py-1">靶标</th>
            <th class="text-right font-normal py-1">0 级 DPS</th>
            <th class="text-right font-normal py-1">满级 DPS</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          <tr v-for="t in targetRows" :key="t.key">
            <td class="py-1.5 text-gray-600 dark:text-gray-400">{{ t.label }}</td>
            <td class="py-1.5 text-right font-mono text-orange-600 dark:text-orange-400">{{ unit.derived[t.base] ?? 0 }}</td>
            <td class="py-1.5 text-right font-mono text-gray-700 dark:text-gray-300">{{ unit.derived[t.max] ?? 0 }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 武器明细 -->
      <template v-if="unit.weapons.length">
        <div class="section-title">武器 · {{ unit.weapons.length }}</div>
        <div class="space-y-3">
          <div v-for="w in unit.weapons" :key="w.id" class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <span class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ w.nameZh || w.id }}</span>
              <span v-if="w.melee" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">近战</span>
              <span v-if="w.suicide" class="text-xs px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300">自杀式攻击</span>
              <span class="font-mono text-xs text-gray-500">
                射程 {{ w.range ?? '—' }}<template v-if="w.period"> · 间隔 {{ w.period }}s</template>
              </span>
              <span class="font-mono text-xs">
                <span :class="w.targets.ground ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对地</span>
                <span class="text-gray-300">/</span>
                <span :class="w.targets.air ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对空</span>
              </span>
            </div>
            <div v-for="(c, i) in w.components" :key="i"
              class="text-sm pl-3 border-l-2 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 mb-1">
              <span class="font-mono">{{ c.amount }}<span v-if="c.hits && c.hits !== 1" class="text-gray-400">×{{ c.hits }}</span></span>
              <span v-for="(v, k) in c.bonus" :key="k" class="ml-2 font-mono"
                :class="v > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-red-500'">
                {{ v > 0 ? '+' : '' }}{{ v }} 对{{ attrLabel(String(k)) }}
              </span>
              <span v-if="c.splash" class="ml-2 text-purple-600 dark:text-purple-400">溅射半径 {{ c.splash.radius }}</span>
              <span v-if="c.secondary" class="ml-2 text-gray-400">仅溅射</span>
              <span v-if="c.dot" class="ml-2 text-gray-400">持续伤害</span>
              <span v-if="c.vital" class="ml-2 text-gray-400">自身消耗</span>
            </div>
            <div v-if="w.vitalDamage" class="text-sm text-gray-400">自伤 {{ w.vitalDamage }}</div>
            <div v-if="!w.components.length && !w.unresolved.length" class="text-sm text-gray-400">无伤害</div>
            <div v-if="w.unresolved.length" class="text-xs text-amber-600 dark:text-amber-400 mt-1">
              ⚠ 未解析：{{ w.unresolved.join('、') }}
            </div>
            <div v-for="n in w.notes" :key="n" class="text-xs text-gray-400 mt-0.5">· {{ noteLabel(n) }}</div>
            <table v-if="w.targets.exclude.length" class="mt-1">
              <tbody>
                <tr class="text-xs text-gray-400">
                  <td>不可攻击属性：</td>
                  <td class="pl-1">{{ w.targets.exclude.map(attrLabel).join('、') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- 升级曲线 -->
      <template v-if="unit.curve.length > 1">
        <div class="section-title mt-5">升级曲线（全科技逐级叠加）</div>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-xs text-gray-400">
              <th class="text-left font-normal py-1">科技等级</th>
              <th class="text-right font-normal py-1">累计花费</th>
              <th class="text-right font-normal py-1">生命</th>
              <th class="text-right font-normal py-1">护甲</th>
              <th class="text-right font-normal py-1">对重甲 DPS</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="c in unit.curve" :key="c.level">
              <td class="py-1.5 text-gray-500 font-mono">{{ c.level }}</td>
              <td class="py-1.5 text-right font-mono text-gray-500">{{ c.cost.minerals }}/{{ c.cost.gas }}</td>
              <td class="py-1.5 text-right font-mono">{{ c.hp }}</td>
              <td class="py-1.5 text-right font-mono">{{ c.armor }}</td>
              <td class="py-1.5 text-right font-mono text-orange-600 dark:text-orange-400">{{ curveDps(c) }}</td>
            </tr>
          </tbody>
        </table>
      </template>

      <template v-if="unit.upgrades.length">
        <div class="section-title mt-5">受影响的研究升级 · {{ unit.upgrades.length }} 组</div>
        <div class="space-y-2">
          <div v-for="g in unit.upgrades" :key="g.family" class="text-sm">
            <div class="flex items-center gap-2">
              <span class="text-gray-700 dark:text-gray-200">{{ g.nameZh }}</span>
              <span v-if="!g.researchable" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">非研究解锁</span>
            </div>
            <div class="font-mono text-xs text-gray-500 dark:text-gray-400">
              <span v-for="lv in g.levels" :key="lv.level" class="mr-3">{{ lv.level }}级 {{ lv.minerals }}/{{ lv.gas }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 生产来源 / 可生产 -->
      <template v-if="producers.length || unit.produces?.length">
        <div class="section-title mt-5">生产</div>
        <div v-if="producers.length" class="text-sm text-gray-600 dark:text-gray-400 mb-1">
          由
          <span v-for="(p, i) in producers" :key="i">
            <span v-if="i">、</span>
            <NuxtLink :to="`/units/${p.edge.from}`" class="text-survivor-600 dark:text-survivor-400 hover:underline">{{ unitName(p.edge.from) }}</NuxtLink>
            <span class="text-gray-400">（{{ kindLabel(p.edge.kind) }}{{ p.edge.time ? ` ${p.edge.time}s` : '' }}{{ p.edge.count && p.edge.count > 1 ? ` ×${p.edge.count}` : '' }}）</span>
          </span>
          生产。
        </div>
        <div v-if="unit.produces?.length" class="text-sm text-gray-600 dark:text-gray-400">
          可生产：
          <NuxtLink v-for="(id, i) in unit.produces" :key="id" :to="`/units/${id}`"
            class="text-survivor-600 dark:text-survivor-400 hover:underline">
            <span v-if="i">、</span>{{ unitName(id) }}
          </NuxtLink>
        </div>
      </template>
    </div>
  </div>
  <div v-else class="text-center py-20 text-gray-400">
    <p class="text-lg">单位未找到</p>
    <NuxtLink to="/units" class="text-sm text-survivor-600 hover:underline">查看全部兵种</NuxtLink>
  </div>
</template>

<script setup lang="ts">
import { CATEGORY_LABELS, ATTRIBUTE_LABELS, ATTRIBUTE_FALLBACK, WEAPON_NOTE_LABELS } from '~/composables/useUnitsData'
import type { CurvePoint } from '~/composables/useUnitsData'

const route = useRoute()
const unitId = route.params.id as string
const { getUnit, producersOf, unitMap, heroMap } = useUnitsData()
const { classes } = useClassData()

const unit = computed(() => getUnit(unitId))
const producers = computed(() => (unit.value ? producersOf(unit.value.id) : []))

const ownerLinks = computed(() => {
  if (!unit.value) return []
  return unit.value.owners.map((nameEn) => {
    const role = classes.find(c => c.nameEn === nameEn)
    return { name: nameEn, zh: role?.nameZh || nameEn, id: role?.id ?? -1 }
  })
})

const isPlating = computed(() => !!unit.value?.stats.armorName?.includes('Plating'))

const TARGET_ROWS = [
  { key: 'base', label: '无属性基准', base: 'dpsBase', max: 'dpsBaseMax' },
  { key: 'light', label: '对轻甲', base: 'dpsLight', max: 'dpsLightMax' },
  { key: 'armored', label: '对重甲', base: 'dpsArmored', max: 'dpsArmoredMax' },
  { key: 'kerrigan', label: '对凯瑞甘（英雄/巨型/首领）', base: 'dpsKerrigan', max: 'dpsKerriganMax' },
]
const targetRows = computed(() => (unit.value ? TARGET_ROWS.filter(r => unit.value!.derived[r.base] != null) : []))

function attrLabel(a: string) { return ATTRIBUTE_LABELS[a]?.[0] || a }
function attrClass(a: string) { return ATTRIBUTE_LABELS[a]?.[1] || ATTRIBUTE_FALLBACK[0] }
function noteLabel(n: string) { return WEAPON_NOTE_LABELS[n] || n }
function unitName(id: string) { return unitMap[id]?.nameZh || id }
function kindLabel(k: string) {
  return ({ train: '训练', build: '建造', warp: '折跃', morph: '变形', summon: '召唤', magazine: '弹药' } as Record<string, string>)[k] || k
}
function curveDps(c: CurvePoint) {
  return c.weapons.reduce((s, w) => s + ((w as any).armored?.dps || 0), 0).toFixed(1)
}

useHead(() => ({ title: `${unit.value?.nameZh || unitId} · 兵种 · KS2 Wiki` }))
</script>
