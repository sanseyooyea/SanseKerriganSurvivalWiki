<template>
  <div
    class="group overflow-hidden rounded-lg border transition-all duration-200"
    :class="expanded
      ? 'border-surface-300 bg-surface-50 dark:border-gray-600 dark:bg-gray-900/60'
      : 'border-surface-200 hover:border-surface-300 dark:border-gray-700 dark:hover:border-gray-600'"
  >
    <!-- 标题行 -->
    <button
      type="button"
      class="flex w-full items-center gap-2.5 px-3 py-2.5 text-left
             focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-survivor-500"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <UnitIcon :icon="unit.icon" :alt="unit.nameZh" size="sm" />

      <span class="flex min-w-0 flex-1 items-center gap-2">
        <span class="truncate text-sm font-medium text-gray-800 dark:text-gray-200">{{ unit.nameZh || unit.id }}</span>
        <span
          v-for="a in unit.attributes.slice(0, 3)"
          :key="a"
          class="hidden shrink-0 rounded px-1.5 py-px text-[0.6rem] leading-4 sm:inline-block"
          :class="attrClass(a)"
        >{{ attrLabel(a) }}</span>
        <span v-for="f in unit.forms || []" :key="f.id"
          class="hidden shrink-0 rounded border border-surface-300 px-1.5 py-px text-[0.6rem] leading-4 text-gray-500 dark:border-gray-600 dark:text-gray-400 sm:inline-block"
          :title="`可切换为${f.nameZh}`">⇄ {{ f.label }}</span>
        <span v-if="unit.attributes.length > 3" class="hidden shrink-0 text-[0.6rem] text-gray-400 lg:inline">
          +{{ unit.attributes.length - 3 }}
        </span>
      </span>

      <span class="hidden shrink-0 font-mono text-xs tabular-nums text-gray-500 dark:text-gray-400 md:inline">{{ costText }}</span>

      <span class="hidden shrink-0 font-mono text-xs tabular-nums text-gray-400 lg:inline">
        {{ unit.stats.hp }}<span v-if="unit.stats.shield" class="text-sky-600 dark:text-sky-400">+{{ unit.stats.shield }}</span>
        <span v-if="unit.stats.armor" class="text-gray-500"> / {{ unit.stats.armor }}甲</span>
      </span>

      <span v-if="dpsText" class="shrink-0 font-mono text-xs tabular-nums" :title="dpsTitle">
        <span class="text-gray-400">DPS</span>
        <span class="ml-1 font-semibold text-orange-600 dark:text-orange-400">{{ dpsText }}</span>
      </span>

      <svg
        class="h-3.5 w-3.5 shrink-0 text-gray-400 transition-transform duration-200"
        :class="expanded ? 'rotate-180' : ''"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- 展开区 -->
    <div v-if="expanded" class="animate-slide-up space-y-4 border-t border-surface-200 px-3 pb-4 pt-3 dark:border-gray-700">
      <!-- 基础属性 -->
      <div class="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-4">
        <div v-for="f in statFields" :key="f.label" class="flex items-baseline justify-between gap-2 text-xs">
          <span class="text-gray-500 dark:text-gray-400">{{ f.label }}</span>
          <span class="font-mono tabular-nums" :class="f.class || 'text-gray-700 dark:text-gray-300'">{{ f.value }}</span>
        </div>
      </div>

      <!-- 变形 / 合体链的获取成本明细 -->
      <AcquireSteps v-if="(unit.cost as any).acquire" :acquire="(unit.cost as any).acquire" :listed="(unit.cost as any).listed" />

      <!-- 形态 -->
      <p v-if="unit.forms?.length" class="text-xs text-gray-500 dark:text-gray-400">
        <span class="text-gray-400">形态 ·</span>
        <template v-for="(f, i) in unit.forms" :key="f.id">
          <span v-if="i">、</span>
          <NuxtLink :to="`/units/${f.id}`" class="text-survivor-600 hover:underline dark:text-survivor-400">{{ f.label }}</NuxtLink>
        </template>
        <span class="text-gray-400">（同一单位的不同状态，数值见各自详情）</span>
      </p>

      <!-- 派生指标 -->
      <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        <div
          v-for="m in metrics"
          :key="m.label"
          class="rounded-md border border-surface-200 bg-white px-2.5 py-2 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="text-[0.65rem] leading-tight text-gray-500 dark:text-gray-400">{{ m.label }}</div>
          <div class="mt-0.5 font-mono text-sm font-semibold tabular-nums" :class="m.class || 'text-gray-800 dark:text-gray-100'">
            {{ m.value ?? '—' }}
          </div>
          <div v-if="m.note" class="mt-0.5 text-[0.6rem] leading-tight text-gray-400 dark:text-gray-500">{{ m.note }}</div>
        </div>
      </div>

      <!-- 武器 -->
      <section v-if="unit.weapons.length" class="space-y-2">
        <h4 class="section-title mb-0">武器 · {{ unit.weapons.length }}</h4>
        <div
          v-for="w in unit.weapons"
          :key="w.id"
          class="space-y-1.5 rounded-md border border-surface-200 bg-white p-2.5 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span class="text-xs font-medium text-gray-700 dark:text-gray-200">{{ w.nameZh || w.id }}</span>
            <Badge v-if="w.melee" tone="neutral">近战</Badge>
            <Badge v-if="w.suicide" tone="danger">自杀式 · 不计 DPS</Badge>
            <span class="font-mono text-[0.65rem] tabular-nums text-gray-400 dark:text-gray-500">
              <template v-if="w.range != null">射程 {{ w.range }}</template>
              <template v-if="w.range != null && w.period"> · </template>
              <template v-if="w.period">间隔 {{ w.period }}s</template>
            </span>
            <span class="font-mono text-[0.65rem]" :title="w.targets.exclude.length ? '不可攻击：' + w.targets.exclude.map(attrLabel).join('、') : ''">
              <span :class="w.targets.ground ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对地</span>
              <span class="text-gray-300 dark:text-gray-600">/</span>
              <span :class="w.targets.air ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对空</span>
            </span>
            <span v-if="enablesAir(w.id)" class="rounded bg-violet-50 px-1.5 py-px text-[0.6rem] leading-4 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
              需研发：{{ airUpgrades(w.id).join('、') }}
            </span>
          </div>

          <div
            v-for="(c, i) in w.components"
            :key="i"
            class="border-l-2 border-surface-200 pl-2.5 text-xs text-gray-600 dark:border-gray-600 dark:text-gray-300"
          >
            <span class="font-mono tabular-nums">
              {{ c.amount }}<span v-if="c.hits && c.hits !== 1" class="text-gray-400">×{{ c.hits }}</span>
              <span
                v-for="(v, k) in c.bonus"
                :key="k"
                class="ml-1.5 font-semibold"
                :class="v > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-rose-600 dark:text-rose-400'"
              >{{ v > 0 ? '+' : '' }}{{ v }} 对{{ targetLabel(String(k)) }}</span>
            </span>
            <span v-if="c.splash" class="ml-1.5 text-violet-600 dark:text-violet-400">溅射 R{{ c.splash.radius }}</span>
            <span v-if="c.secondary" class="ml-1.5 text-gray-400">仅溅射</span>
            <span v-if="c.dot" class="ml-1.5 text-gray-400">持续伤害</span>
            <span v-if="c.vital" class="ml-1.5 text-gray-400">自身消耗</span>
          </div>

          <div v-if="w.vitalDamage" class="text-xs text-gray-400">自伤 {{ w.vitalDamage }}</div>
          <div v-if="!w.components.length && !w.unresolved.length" class="text-xs text-gray-400">无伤害</div>

          <p v-if="w.unresolved.length" class="rounded bg-amber-50 px-2 py-1 text-[0.65rem] leading-relaxed text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
            未解析：{{ w.unresolved.join('、') }} —— 伤害由脚本或动态效果驱动，不做估算
          </p>
          <p v-for="n in w.notes" :key="n" class="text-[0.65rem] text-gray-400 dark:text-gray-500">· {{ noteLabel(n) }}</p>
        </div>
      </section>

      <!-- 攻防科技：战力曲线 -->
      <section v-if="combatCurve.length > 1" class="space-y-2">
        <h4 class="section-title mb-0">攻防科技 · 战力成长</h4>
        <p class="text-[0.65rem] leading-relaxed text-gray-400 dark:text-gray-500">
          随建造顺序自然获得的攻击 / 防御升级。{{ combatGroups.map(g => g.nameZh).join('、') }}
        </p>
        <div class="overflow-hidden rounded-md border border-surface-200 dark:border-gray-700">
          <table class="w-full font-mono text-xs">
            <thead class="bg-surface-50 dark:bg-gray-900/50">
              <tr class="text-gray-400 dark:text-gray-500">
                <th v-for="h in CURVE_COLS" :key="h.key" class="px-2 py-1.5 font-normal"
                  :class="h.align === 'right' ? 'text-right' : 'text-left'">{{ h.label }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-surface-200 dark:divide-gray-700">
              <tr v-for="c in combatCurve" :key="c.level">
                <td class="px-2 py-1 text-gray-500">{{ c.level }}</td>
                <td class="px-2 py-1 text-right tabular-nums text-gray-500">{{ c.cost.minerals }}/{{ c.cost.gas }}</td>
                <td class="px-2 py-1 text-right tabular-nums text-gray-700 dark:text-gray-300">{{ c.stats.hp }}</td>
                <td class="px-2 py-1 text-right tabular-nums text-gray-700 dark:text-gray-300">{{ c.stats.armor }}</td>
                <td class="px-2 py-1 text-right tabular-nums text-gray-700 dark:text-gray-300">{{ c.stats.sight }}</td>
                <td class="px-2 py-1 text-right tabular-nums font-semibold text-orange-600 dark:text-orange-400">{{ fmt(curveDps(c)) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 额外科技：可选项 -->
      <section v-if="optionGroups.length" class="space-y-2">
        <h4 class="section-title mb-0">额外科技 · 可选 {{ optionGroups.length }} 项</h4>
        <p class="text-[0.65rem] leading-relaxed text-gray-400 dark:text-gray-500">
          独立于攻防科技，按需研究。下表为「只研究这一项」后的数值变化。
        </p>
        <div
          v-for="o in optionGroups"
          :key="o.family"
          class="rounded-md border border-surface-200 bg-white p-2.5 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-medium text-gray-700 dark:text-gray-200">{{ o.nameZh }}</span>
            <span
              v-for="d in o.dimensions"
              :key="d"
              class="rounded px-1.5 py-px text-[0.6rem] leading-4"
              :class="dimClass(d)"
            >{{ dimensionLabel(d) }}</span>
            <span class="font-mono text-[0.65rem] tabular-nums text-gray-400">{{ fmtCost(o.cost) }}</span>
          </div>

          <!-- 关键数值前后对比 -->
          <div v-if="delta(o).length" class="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5">
            <span v-for="d in delta(o)" :key="d.label" class="font-mono text-[0.7rem] tabular-nums">
              <span class="text-gray-400">{{ d.label }}</span>
              <span class="text-gray-500">{{ d.from }}</span>
              <span class="text-gray-300">→</span>
              <span class="font-semibold text-emerald-600 dark:text-emerald-400">{{ d.to }}</span>
            </span>
          </div>

          <div class="mt-1 font-mono text-[0.65rem] tabular-nums text-gray-500 dark:text-gray-400">
            <span v-for="lv in o.levels" :key="lv.level" class="mr-3">{{ lv.level }}级 {{ lv.minerals }}/{{ lv.gas }}</span>
          </div>

          <p v-if="o.unmodeled.length" class="mt-1 text-[0.65rem] text-gray-400 dark:text-gray-500">
            另改动：{{ o.unmodeled.map(prettyField).join('、') }}
          </p>
        </div>
      </section>

      <!-- 生产 -->
      <p v-if="producedBy.length" class="text-xs leading-relaxed text-gray-500 dark:text-gray-400">
        <span class="text-gray-400">生产来源 ·</span>
        <template v-for="(p, i) in producedBy.slice(0, 6)" :key="i">
          <span v-if="i">、</span>
          <NuxtLink :to="`/units/${p.from}`" class="text-survivor-600 hover:underline dark:text-survivor-400">{{ unitName(p.from) }}</NuxtLink>
          <span class="text-gray-400">（{{ kindLabel(p.kind) }}{{ p.count > 1 ? ` ×${p.count}` : '' }}）</span>
        </template>
      </p>
      <p v-if="unit.produces?.length" class="text-xs leading-relaxed text-gray-500 dark:text-gray-400">
        <span class="text-gray-400">可生产 ·</span>
        <NuxtLink v-for="(id, i) in unit.produces" :key="id" :to="`/units/${id}`"
          class="text-survivor-600 hover:underline dark:text-survivor-400">
          <span v-if="i">、</span>{{ unitName(id) }}
        </NuxtLink>
      </p>

      <NuxtLink
        :to="`/units/${unit.id}`"
        class="inline-flex items-center gap-1 text-xs font-medium text-survivor-600 transition-colors hover:text-survivor-700 dark:text-survivor-400 dark:hover:text-survivor-300"
      >
        查看详情
        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { UnitEntry, CurvePoint, UnitOption } from '~/composables/useUnitsData'
import { unitCombatCurve, unitOptions, ATTRIBUTE_LABELS, ATTRIBUTE_FALLBACK, WEAPON_NOTE_LABELS, DIMENSION_LABELS } from '~/composables/useUnitsData'

const props = defineProps<{ unit: UnitEntry }>()
const { unitMap, curveDps: curveDpsOf, dimensionLabel } = useUnitsData()
const curveDps = (c: CurvePoint) => curveDpsOf(c, 'armored')
const expanded = ref(false)

const unit = computed(() => props.unit)
const producedBy = computed(() => unit.value.producedBy || [])
const combatGroups = computed(() => unit.value.upgrades.filter(g => g.kind === 'combat'))
/** 该武器当前不能对空，但有科技能让它对空 → 标出来。 */
function enablesAir(wid: string) {
  return airUpgrades(wid).length > 0
}
/** 能让该武器对空的科技名（当前不能对空时才有意义）。 */
function airUpgrades(wid: string) {
  const base = combatCurve.value[0]?.weapons || []
  const bs = base.find(w => w.id === wid)
  if (!bs || bs.targets?.air) return []
  return unitOptions(unit.value)
    .filter(o => (o.snapshot?.weapons || []).some(w => w.id === wid && w.targets?.air))
    .map(o => o.nameZh.replace(/^(?:研发|研究|升级)\s*/, ''))
}
const optionGroups = computed(() => unitOptions(unit.value))
const combatCurve = computed(() => unitCombatCurve(unit.value))
const baseSnap = computed(() => combatCurve.value[0])

const CURVE_COLS = [
  { key: 'level', label: '等级', align: 'left' },
  { key: 'cost', label: '累计', align: 'right' },
  { key: 'hp', label: '生命', align: 'right' },
  { key: 'armor', label: '护甲', align: 'right' },
  { key: 'sight', label: '视野', align: 'right' },
  { key: 'dps', label: '对重甲 DPS', align: 'right' },
]

/** 额外科技的数值前后对比：只看真正变化的维度（射程/视野/生命…）。 */
function delta(o: UnitOption) {
  const before = baseSnap.value
  const after = o.snapshot
  if (!before || !after) return []
  const out: { label: string; from: string; to: string }[] = []
  const unitDims: [string, keyof typeof DIMENSION_LABELS][] = [
    ['sight', 'sight'], ['hp', 'hp'], ['armor', 'armor'], ['shield', 'shield'], ['speed', 'speed'],
  ]
  for (const [key, dim] of unitDims) {
    const a = before.stats[key]
    const b = after.stats[key]
    if (a !== b) out.push({ label: dimensionLabel(dim as string), from: String(a), to: String(b) })
  }
  // 武器级别：射程 / 间隔 / 溅射 / 各靶标 DPS
  for (let i = 0; i < (before.weapons || []).length; i++) {
    const a = before.weapons[i]
    const b = after.weapons[i]
    if (!a || !b) continue
    const tag = before.weapons.length > 1 ? `#${i + 1} ` : ''
    if (a.range !== b.range) out.push({ label: `${tag}射程`, from: fmt(a.range), to: fmt(b.range) })
    if (a.period !== b.period) out.push({ label: `${tag}攻击间隔`, from: fmt(a.period), to: fmt(b.period) })
    if (a.splashRadius !== b.splashRadius) out.push({ label: `${tag}溅射`, from: fmt(a.splashRadius), to: fmt(b.splashRadius) })
    for (const t of ['light', 'armored', 'kerrigan']) {
      const da = a[t]?.dps
      const db = b[t]?.dps
      if (da !== db) out.push({ label: `${tag}${attrLabel(t)} DPS`, from: fmt(da), to: fmt(db) })
    }
  }
  return out.slice(0, 6)
}

const DIM_TONE: Record<string, string> = {
  range: 'bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  sight: 'bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300',
  splash: 'bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-300',
  damage: 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  bonus: 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  hp: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  armor: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
}
function dimClass(d: string) {
  return DIM_TONE[d] || 'bg-surface-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
}
function prettyField(f: string) {
  return f.replace(/\[(\w+)\]/g, '·$1').replace(/([a-z])([A-Z])/g, '$1 $2')
}
function fmt(v: unknown) {
  return v == null ? '—' : String(v)
}
const isPlating = computed(() => !!unit.value.stats.armorName?.includes('Plating'))

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

const statFields = computed(() => {
  const s = unit.value.stats
  const out = [
    { label: '生命值', value: s.hp },
    { label: '护盾', value: s.shield, class: 'text-sky-600 dark:text-sky-400' },
    { label: '护甲', value: isPlating.value ? `${s.armor} 镀层` : s.armor },
  ]
  if (s.speed) out.push({ label: '移速', value: s.speed })
  if (s.sight) out.push({ label: '视野', value: s.sight })
  if (unit.value.cost.food) out.push({ label: '人口', value: unit.value.cost.food })
  if (s.hpRegen) out.push({ label: '回血/秒', value: s.hpRegen })
  if (unit.value.planes.length) out.push({ label: '地形', value: unit.value.planes.join('/') })
  return out.filter(f => f.value !== 0 && f.value != null)
})

const metrics = computed(() => {
  const d = unit.value.derived
  const out = []
  if (d.dpsLight != null) out.push({ label: '对轻甲 DPS', value: d.dpsLight, note: '轻甲靶标（0 甲）' })
  if (d.dpsArmored != null) out.push({ label: '对重甲 DPS', value: d.dpsArmored, note: '重甲靶标（0 甲）' })
  if (d.dpsKerrigan != null) {
    out.push({
      label: '对凯瑞甘 DPS', value: d.dpsKerrigan, note: '英雄 / 巨型 / 首领靶标',
      class: d.dpsKerrigan ? 'text-kerrigan-600 dark:text-kerrigan-500' : 'text-gray-300 dark:text-gray-600',
    })
  }
  if (d.dpsArmoredMax != null) {
    out.push({
      label: '满级 DPS',
      value: d.dpsArmoredMax,
      note: d.techReliance > 1 ? `全科技拉满 · 基础值的 ${d.techReliance}×` : '全科技拉满·对重甲',
    })
  }
  if (d.dpsPer100Light) out.push({ label: '每 100 资源 · 对轻甲', value: d.dpsPer100Light })
  if (d.dpsPer100Armored) out.push({ label: '每 100 资源 · 对重甲', value: d.dpsPer100Armored })
  if (d.ehp) out.push({ label: '有效血量', value: d.ehp, note: `生命 + 护盾 · 每 100 资源 ${d.hpPer100 ?? '—'}` })
  if (d.dpsPerFoodLight) out.push({ label: '每人口 · 对轻甲', value: d.dpsPerFoodLight })
  if (d.fullUpgradeCost) out.push({ label: '满科技花费', value: fmtCost(d.fullUpgradeCost), note: '累计资源' })
  return out
})

function attrLabel(a: string) { return ATTRIBUTE_LABELS[a]?.[0] || a }
function attrClass(a: string) { return ATTRIBUTE_LABELS[a]?.[1] || ATTRIBUTE_FALLBACK[0] }
function targetLabel(a: string) { return ATTRIBUTE_LABELS[a]?.[0] || a }
function noteLabel(n: string) { return WEAPON_NOTE_LABELS[n] || n }
function kindLabel(k: string) {
  return ({ train: '训练', build: '建造', warp: '折跃', morph: '变形', summon: '召唤', magazine: '弹药', merge: '合体' } as Record<string, string>)[k] || k
}
function unitName(id: string) { return unitMap[id]?.nameZh || id }
function fmtDps(k: string) {
  const v = unit.value.derived[k]
  return v ? v : (unit.value.derived.dpsLight || unit.value.derived.dpsArmored ? 0 : null)
}
function fmtCost(c: { minerals: number; gas: number }) {
  return [c.minerals && `${c.minerals}矿`, c.gas && `${c.gas}气`].filter(Boolean).join(' ') || '0'
}

</script>
