<template>
  <div class="rounded-lg border overflow-hidden transition-all"
    :class="[
      expanded
        ? 'bg-gray-50 dark:bg-gray-900 border-gray-300 dark:border-gray-600'
        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
    ]">
    <!-- 标题行：名称 + 造价 + 血/甲 + 三靶 DPS -->
    <div class="flex items-center gap-2 px-3 py-2 cursor-pointer select-none" @click="expanded = !expanded">
      <div class="flex-1 min-w-0 flex items-center gap-2">
        <span class="w-6 h-6 shrink-0 rounded overflow-hidden bg-gray-100 dark:bg-gray-800 ring-1 ring-black/5 dark:ring-white/10 flex items-center justify-center">
          <img v-if="unit.icon && !iconBroken" :src="iconSrc" :alt="unit.nameZh" class="w-full h-full object-cover" loading="lazy" @error="onIconError" />
          <span v-else class="text-gray-300 dark:text-gray-600 text-[0.6rem]">◈</span>
        </span>
        <span class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{{ unit.nameZh || unit.id }}</span>
        <span v-for="a in unit.attributes" :key="a"
          class="hidden sm:inline-block px-1.5 py-px rounded text-[0.6rem] leading-4"
          :class="attrClass(a)">{{ attrLabel(a) }}</span>
      </div>

      <span class="font-mono text-xs text-gray-500 dark:text-gray-400 shrink-0 hidden md:inline">{{ costText }}</span>
      <span class="font-mono text-xs text-gray-400 shrink-0 hidden lg:inline tabular-nums">
        {{ unit.stats.hp }}<span v-if="unit.stats.shield" class="text-blue-500 dark:text-blue-400">+{{ unit.stats.shield }}</span>
        <span v-if="unit.stats.armor" class="text-gray-500"> / {{ unit.stats.armor }}甲</span>
      </span>
      <span v-if="dpsText" class="font-mono text-xs shrink-0 tabular-nums" :title="dpsTitle">
        <span class="text-gray-400">DPS</span> <span class="text-orange-600 dark:text-orange-400">{{ dpsText }}</span>
      </span>
      <svg class="w-3.5 h-3.5 text-gray-400 shrink-0 transition-transform duration-200"
        :class="expanded ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>
    </div>

    <!-- 展开区 -->
    <div v-if="expanded" class="px-3 pb-3 animate-slide-up space-y-3">
      <!-- 基础属性 -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs pl-0.5">
        <div class="flex justify-between">
          <span class="text-gray-500">生命值</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.stats.hp }}</span>
        </div>
        <div v-if="unit.stats.shield" class="flex justify-between">
          <span class="text-gray-500">护盾</span>
          <span class="font-mono text-blue-600 dark:text-blue-400">{{ unit.stats.shield }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-500">护甲</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">
            {{ unit.stats.armor }}
            <span v-if="isPlating" class="text-gray-400 font-normal">镀层</span>
          </span>
        </div>
        <div v-if="unit.stats.speed" class="flex justify-between">
          <span class="text-gray-500">移速</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.stats.speed }}</span>
        </div>
        <div v-if="unit.stats.sight" class="flex justify-between">
          <span class="text-gray-500">视野</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.stats.sight }}</span>
        </div>
        <div v-if="unit.cost.food" class="flex justify-between">
          <span class="text-gray-500">人口</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.cost.food }}</span>
        </div>
        <div v-if="unit.stats.hpRegen" class="flex justify-between">
          <span class="text-gray-500">回血/秒</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.stats.hpRegen }}</span>
        </div>
        <div v-if="unit.planes.length" class="flex justify-between col-span-1">
          <span class="text-gray-500">地形</span>
          <span class="font-mono text-gray-700 dark:text-gray-300">{{ unit.planes.join('/') }}</span>
        </div>
      </div>

      <!-- 派生指标 -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">对轻甲 DPS</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ fmtDps('dpsLight') ?? '—' }}</div>
          <div class="text-[0.6rem] text-gray-400">轻甲靶标（0 甲）</div>
        </div>
        <div class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">对重甲 DPS</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ fmtDps('dpsArmored') ?? '—' }}</div>
          <div class="text-[0.6rem] text-gray-400">重甲靶标（0 甲）</div>
        </div>
        <div class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">对凯瑞甘 DPS</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ fmtDps('dpsKerrigan') ?? '—' }}</div>
          <div class="text-[0.6rem] text-gray-400">凯瑞甘本体靶标</div>
        </div>
        <div class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">满级 DPS（对重甲）</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ unit.derived.dpsArmoredMax ?? '—' }}</div>
          <div class="text-[0.6rem] text-gray-400">unit.upgrades.length ? '全科技拉满' : '无可研究升级'</div>
        </div>
        <div v-if="unit.derived.dpsPer100" class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">每 100 资源 DPS</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ unit.derived.dpsPer100 ?? '—' }}</div>
          <div class="text-[0.6rem] text-gray-400">取轻/重甲较高者</div>
        </div>
        <div v-if="unit.derived.ehp" class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">有效血量</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ unit.derived.ehp ?? '—' }}</div>
          <div class="text-[0.6rem] text-gray-400">`每100资源 ${unit.derived.ehpPer100 ?? '—'}`</div>
        </div>
        <div v-if="unit.derived.dpsPerFood" class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">每人口 DPS</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ unit.derived.dpsPerFood ?? '—' }}</div>
        </div>
        <div v-if="unit.derived.fullUpgradeCost" class="rounded border border-gray-200 dark:border-gray-700 px-2 py-1.5">
          <div class="text-[0.65rem] text-gray-500 dark:text-gray-400">满科技花费</div>
          <div class="font-mono text-sm text-gray-800 dark:text-gray-100">{{ fmtCost(unit.derived.fullUpgradeCost) ?? '—' }}</div>
          <div class="text-[0.6rem] text-gray-400">累计资源</div>
        </div>
      </div>

      <!-- 武器 -->
      <div v-if="unit.weapons.length" class="space-y-2">
        <div class="text-xs font-semibold text-gray-700 dark:text-gray-300">武器 · {{ unit.weapons.length }}</div>
        <div v-for="w in unit.weapons" :key="w.id"
          class="rounded border border-gray-200 dark:border-gray-700 p-2 space-y-1.5">
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            <span class="font-medium text-gray-700 dark:text-gray-200">{{ w.nameZh || w.id }}</span>
            <span v-if="w.melee" class="text-[0.6rem] px-1.5 py-px rounded bg-gray-100 dark:bg-gray-700 text-gray-500">近战</span>
            <span v-if="w.suicide" class="text-[0.6rem] px-1.5 py-px rounded bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300">自杀式攻击 · 不计 DPS</span>
            <span class="font-mono text-gray-400">
              <template v-if="w.range != null">射程 {{ w.range }}</template>
              <template v-if="w.period"> · 间隔 {{ w.period }}s</template>
            </span>
            <span class="font-mono text-[0.65rem]" :title="w.targets.exclude.join(', ')">
              <span :class="w.targets.ground ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对地</span>
              <span class="text-gray-300 dark:text-gray-600">/</span>
              <span :class="w.targets.air ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对空</span>
            </span>
          </div>

          <!-- 伤害分量 -->
          <div v-for="(c, i) in w.components" :key="i"
            class="text-xs pl-2 border-l-2 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300">
            <span class="font-mono">
              {{ c.amount }}<span v-if="c.hits && c.hits !== 1" class="text-gray-400">×{{ c.hits }}</span>
              <span v-for="(v, k) in c.bonus" :key="k" class="ml-1"
                :class="v > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-red-500'">
                {{ v > 0 ? '+' : '' }}{{ v }} 对{{ targetLabel(String(k)) }}
              </span>
            </span>
            <span v-if="c.splash" class="ml-1 text-purple-600 dark:text-purple-400">
              溅射 R{{ c.splash.radius }}
            </span>
            <span v-if="c.secondary" class="ml-1 text-gray-400">（仅溅射，不打主目标）</span>
            <span v-if="c.dot" class="ml-1 text-gray-400">持续伤害</span>
            <span v-if="c.vital" class="ml-1 text-gray-400">自身生命消耗</span>
          </div>
          <div v-if="w.vitalDamage" class="text-xs text-gray-400">自伤 {{ w.vitalDamage }}</div>
          <div v-if="!w.components.length && !w.unresolved.length" class="text-xs text-gray-400">无伤害</div>

          <!-- 未解析（不猜数） -->
          <div v-if="w.unresolved.length" class="text-xs text-amber-600 dark:text-amber-400">
            ⚠ 未解析：{{ w.unresolved.join('、') }}（伤害由脚本/动态效果驱动）
          </div>
          <div v-for="n in w.notes" :key="n" class="text-[0.65rem] text-gray-400">· {{ noteLabel(n) }}</div>
        </div>
      </div>

      <!-- 升级曲线 -->
      <div v-if="unit.upgrades.length" class="space-y-2">
        <div class="text-xs font-semibold text-gray-700 dark:text-gray-300">升级影响 · {{ unit.upgrades.length }} 组</div>
        <div v-for="g in unit.upgrades" :key="g.family" class="text-xs">
          <div class="flex items-center gap-2">
            <span class="text-gray-700 dark:text-gray-200 font-medium">{{ g.nameZh }}</span>
            <span v-if="!g.researchable" class="text-[0.6rem] px-1.5 py-px rounded bg-gray-100 dark:bg-gray-700 text-gray-500">非研究解锁</span>
          </div>
          <div class="flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5 font-mono text-[0.65rem] text-gray-500 dark:text-gray-400">
            <span v-for="lv in g.levels" :key="lv.level">{{ lv.level }}级 {{ lv.minerals }}/{{ lv.gas }}</span>
          </div>
        </div>

        <!-- 累计曲线 -->
        <table v-if="unit.curve.length > 1" class="w-full text-xs font-mono mt-1">
          <thead>
            <tr class="text-gray-400">
              <th class="text-left font-normal">科技等级</th>
              <th class="text-right font-normal">累计花费</th>
              <th class="text-right font-normal">生命</th>
              <th class="text-right font-normal">护甲</th>
              <th class="text-right font-normal">对重甲 DPS</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/60">
            <tr v-for="c in unit.curve" :key="c.level">
              <td class="py-0.5 text-gray-500">{{ c.level }}</td>
              <td class="py-0.5 text-right text-gray-500">{{ c.cost.minerals }}/{{ c.cost.gas }}</td>
              <td class="py-0.5 text-right text-gray-700 dark:text-gray-300">{{ c.hp }}</td>
              <td class="py-0.5 text-right text-gray-700 dark:text-gray-300">{{ c.armor }}</td>
              <td class="py-0.5 text-right text-orange-600 dark:text-orange-400">{{ curveDps(c) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 生产来源 -->
      <div v-if="producedBy.length" class="text-xs text-gray-500 dark:text-gray-400">
        生产来源：<span v-for="(p, i) in producedBy.slice(0, 6)" :key="i">{{ i ? '、' : '' }}{{ p.from }}（{{ kindLabel(p.kind) }}{{ p.count > 1 ? ` ×${p.count}` : '' }}）</span>
      </div>
      <div v-if="unit.produces?.length" class="text-xs text-gray-500 dark:text-gray-400">
        可生产：{{ unit.produces.map(id => unitName(id)).join('、') }}
      </div>

      <NuxtLink :to="`/units/${unit.id}`"
        class="inline-flex items-center gap-1 text-xs text-survivor-600 dark:text-survivor-400 hover:underline">
        查看详情
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
        </svg>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { UnitEntry, CurvePoint } from '~/composables/useUnitsData'
import { ATTRIBUTE_LABELS, ATTRIBUTE_FALLBACK, WEAPON_NOTE_LABELS } from '~/composables/useUnitsData'

const props = defineProps<{ unit: UnitEntry }>()
const { unitMap } = useUnitsData()
const expanded = ref(false)

const unit = computed(() => props.unit)
const producedBy = computed(() => unit.value.producedBy || [])

const costText = computed(() => {
  const c = unit.value.cost
  const parts = [c.minerals && `${c.minerals}矿`, c.gas && `${c.gas}气`, c.food && `${c.food}人口`]
  return parts.filter(Boolean).join(' ') || '—'
})
const dpsText = computed(() => {
  const d = unit.value.derived
  if (!d.dpsLight && !d.dpsArmored) return ''
  return d.dpsLight === d.dpsArmored ? `${d.dpsLight}` : `${d.dpsLight}/${d.dpsArmored}`
})
const dpsTitle = '对轻甲 / 对重甲'

function attrLabel(a: string) { return ATTRIBUTE_LABELS[a]?.[0] || a }
function attrClass(a: string) { return ATTRIBUTE_LABELS[a]?.[1] || ATTRIBUTE_FALLBACK[0] }
function targetLabel(a: string) { return ATTRIBUTE_LABELS[a]?.[0] || a }
function noteLabel(n: string) { return WEAPON_NOTE_LABELS[n] || n }
function kindLabel(k: string) {
  return ({ train: '训练', build: '建造', warp: '折跃', morph: '变形', summon: '召唤', magazine: '弹药' } as Record<string, string>)[k] || k
}
function unitName(id: string) { return unitMap[id]?.nameZh || id }
function fmtDps(k: string) {
  const v = unit.value.derived[k]
  return v ? v : (unit.value.derived.dpsLight || unit.value.derived.dpsArmored ? 0 : null)
}
const iconBroken = ref(false)
const iconSrc = computed(() => {
  const i = unit.value.icon || ''
  return i.startsWith('/') ? i : `/tech-icons/${i}`
})
function onIconError() { iconBroken.value = true }

const isPlating = computed(() => !!unit.value.stats.armorName?.includes('Plating'))
function fmtCost(c: { minerals: number; gas: number }) {
  return [c.minerals && `${c.minerals}矿`, c.gas && `${c.gas}气`].filter(Boolean).join(' ') || '0'
}
function curveDps(c: CurvePoint) {
  const k = 'armored'
  return c.weapons.reduce((s, w) => s + ((w as any)[k]?.dps || 0), 0).toFixed(1)
}
</script>
