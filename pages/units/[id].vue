<template>
  <div v-if="unit">
    <NuxtLink
      :to="ownerLink"
      class="mb-5 inline-flex items-center gap-1 text-sm text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-gray-300"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      返回{{ ownerLinkLabel }}
    </NuxtLink>

    <!-- 概览 -->
    <section class="wiki-card mb-6 p-6">
      <div class="flex flex-wrap items-start gap-4">
        <UnitIcon :icon="unit.icon" :alt="unit.nameZh" size="lg" />

        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2.5">
            <h1 class="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">{{ unit.nameZh || unitId }}</h1>
            <span class="inline-flex items-center gap-1.5 rounded-md bg-surface-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400">
              <span class="h-1.5 w-1.5 rounded-full" :class="unit.team === 'Kerrigan' ? 'bg-kerrigan-500' : 'bg-survivor-500'" />
              {{ CATEGORY_LABELS[unit.category] || unit.category }}
            </span>
          </div>

          <div class="mt-2 flex flex-wrap gap-1">
            <span v-for="a in unit.attributes" :key="a" class="rounded px-1.5 py-px text-[0.65rem] leading-5" :class="attrClass(a)">{{ attrLabel(a) }}</span>
          </div>

          <p class="mt-3 text-sm text-gray-500 dark:text-gray-400">
            所属职业：
            <template v-for="(o, i) in ownerLinks" :key="o.name">
              <span v-if="i" class="text-gray-300 dark:text-gray-600"> · </span>
              <NuxtLink v-if="o.id >= 0" :to="`/classes/${o.id}`" class="text-survivor-600 hover:underline dark:text-survivor-400">{{ o.zh }}</NuxtLink>
              <span v-else>{{ o.zh }}</span>
            </template>
          </p>
        </div>
      </div>

      <!-- 火力表 -->
      <h2 class="section-title mt-6 mb-2">火力 · 按靶标</h2>
      <div class="overflow-hidden rounded-lg border border-surface-200 dark:border-gray-700">
        <table class="w-full text-sm">
          <thead class="bg-surface-50 text-[0.65rem] uppercase tracking-wider text-gray-400 dark:bg-gray-900/40 dark:text-gray-500">
            <tr>
              <th class="px-3 py-2 text-left font-medium">靶标</th>
              <th class="px-3 py-2 text-right font-medium">0 级 DPS</th>
              <th class="px-3 py-2 text-right font-medium">满级 DPS</th>
              <th class="px-3 py-2 text-right font-medium">满级增益</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-200 dark:divide-gray-700">
            <tr v-for="t in targetRows" :key="t.key">
              <td class="px-3 py-2 text-gray-600 dark:text-gray-400">{{ t.label }}</td>
              <td class="px-3 py-2 text-right font-mono tabular-nums text-orange-600 dark:text-orange-400">{{ unit.derived[t.base] ?? 0 }}</td>
              <td class="px-3 py-2 text-right font-mono tabular-nums text-gray-700 dark:text-gray-300">{{ unit.derived[t.max] ?? 0 }}</td>
              <td class="px-3 py-2 text-right font-mono text-xs tabular-nums" :class="gain(t.base, t.max) > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-300 dark:text-gray-600'">
                {{ gain(t.base, t.max) > 0 ? `+${gain(t.base, t.max).toFixed(0)}%` : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 效率 -->
      <h2 class="section-title mt-5 mb-2">性价比</h2>
      <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        <div
          v-for="m in metrics"
          :key="m.label"
          class="rounded-lg border border-surface-200 bg-surface-50 px-3 py-2.5 dark:border-gray-700 dark:bg-gray-900/40"
        >
          <div class="text-[0.7rem] leading-tight text-gray-500 dark:text-gray-400">{{ m.label }}</div>
          <div class="mt-1 font-mono text-base font-semibold tabular-nums" :class="m.class || 'text-gray-800 dark:text-gray-100'">{{ m.value ?? '—' }}</div>
          <div v-if="m.note" class="mt-0.5 text-[0.65rem] leading-tight text-gray-400 dark:text-gray-500">{{ m.note }}</div>
        </div>
      </div>
    </section>

    <!-- 基础属性 -->
    <section class="wiki-card mb-6 p-6">
      <h2 class="section-title">基础属性</h2>
      <div class="grid grid-cols-2 gap-x-8 gap-y-2 sm:grid-cols-3 lg:grid-cols-4">
        <div v-for="f in statFields" :key="f.label" class="flex items-baseline justify-between gap-3 text-sm">
          <span class="text-gray-500 dark:text-gray-400">{{ f.label }}</span>
          <span class="font-mono tabular-nums" :class="f.class || 'text-gray-800 dark:text-gray-200'">{{ f.value }}</span>
        </div>
      </div>
    </section>

    <!-- 武器 -->
    <section v-if="unit.weapons.length" class="wiki-card mb-6 p-6">
      <h2 class="section-title">武器 · {{ unit.weapons.length }}</h2>
      <div class="space-y-3">
        <article
          v-for="w in unit.weapons"
          :key="w.id"
          class="rounded-lg border border-surface-200 p-4 dark:border-gray-700"
        >
          <header class="mb-2.5 flex flex-wrap items-center gap-2">
            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ w.nameZh || w.id }}</h3>
            <Badge v-if="w.melee" tone="neutral">近战</Badge>
            <Badge v-if="w.suicide" tone="danger">自杀式攻击</Badge>
            <span class="font-mono text-xs tabular-nums text-gray-500 dark:text-gray-400">
              <template v-if="w.range != null">射程 {{ w.range }}</template>
              <template v-if="w.range != null && w.period"> · </template>
              <template v-if="w.period">间隔 {{ w.period }}s</template>
            </span>
            <span class="font-mono text-xs">
              <span :class="w.targets.ground ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对地</span>
              <span class="text-gray-300 dark:text-gray-600">/</span>
              <span :class="w.targets.air ? 'text-gray-600 dark:text-gray-300' : 'text-gray-300 dark:text-gray-600'">对空</span>
            </span>
            <Badge v-if="enablesAir(w.id)" tone="accent">需研发：{{ airUpgrades(w.id).join('、') }}</Badge>
          </header>

          <div class="space-y-1.5">
            <div
              v-for="(c, i) in w.components"
              :key="i"
              class="border-l-2 border-surface-200 pl-3 text-sm text-gray-600 dark:border-gray-600 dark:text-gray-300"
            >
              <span class="font-mono font-semibold tabular-nums text-gray-800 dark:text-gray-100">
                {{ c.amount }}<span v-if="c.hits && c.hits !== 1" class="font-normal text-gray-400">×{{ c.hits }}</span>
              </span>
              <span
                v-for="(v, k) in c.bonus"
                :key="k"
                class="ml-2 font-mono font-semibold tabular-nums"
                :class="v > 0 ? 'text-orange-600 dark:text-orange-400' : 'text-rose-600 dark:text-rose-400'"
              >{{ v > 0 ? '+' : '' }}{{ v }} 对{{ attrLabel(String(k)) }}</span>
              <span v-if="c.splash" class="ml-2 text-violet-600 dark:text-violet-400">溅射半径 {{ c.splash.radius }}</span>
              <span v-if="c.secondary" class="ml-2 text-gray-400">仅溅射，不打主目标</span>
              <span v-if="c.dot" class="ml-2 text-gray-400">持续伤害</span>
              <span v-if="c.vital" class="ml-2 text-gray-400">自身消耗</span>
            </div>
          </div>

          <div v-if="w.vitalDamage" class="mt-1.5 text-sm text-gray-400">自杀伤害 {{ w.vitalDamage }}</div>
          <div v-if="!w.components.length && !w.unresolved.length" class="text-sm text-gray-400">无伤害</div>

          <p v-if="w.unresolved.length" class="mt-2 rounded-md bg-amber-50 px-2.5 py-1.5 text-xs leading-relaxed text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
            未解析：{{ w.unresolved.join('、') }} —— 伤害由脚本或动态效果驱动，不做估算
          </p>
          <p v-for="n in w.notes" :key="n" class="mt-1 text-xs text-gray-400 dark:text-gray-500">· {{ noteLabel(n) }}</p>
          <p v-if="w.targets.exclude.length" class="mt-1.5 text-xs text-gray-400 dark:text-gray-500">
            不可攻击：{{ w.targets.exclude.map(attrLabel).join('、') }}
          </p>
        </article>
      </div>
    </section>

    <!-- 攻防科技曲线 -->
    <section v-if="combatCurve.length > 1" class="wiki-card mb-6 p-6">
      <h2 class="section-title">攻防科技 · 战力成长</h2>
      <p class="mb-3 max-w-3xl text-xs leading-relaxed text-gray-500 dark:text-gray-400">
        随建造顺序自然获得的攻防升级（{{ combatGroups.map(g => g.nameZh).join('、') }}）。
        口径：所有攻防科技同时推进到第 N 级，累计花费是该等级下的总研究成本。
      </p>

      <div class="mb-4 flex items-end gap-1.5" :style="`height: 5rem`">
        <div
          v-for="(c, i) in combatCurve"
          :key="c.level"
          class="relative flex-1 rounded-t transition-colors"
          :class="i === 0 ? 'bg-surface-200 dark:bg-gray-700' : 'bg-survivor-500/70 hover:bg-survivor-500 dark:bg-survivor-400/60 dark:hover:bg-survivor-400'"
          :style="`height: ${barHeight(c)}%`"
          :title="`${c.level} 级 · 对重甲 ${fmt(curveDps(c))} DPS`"
        />
      </div>

      <div class="overflow-hidden rounded-lg border border-surface-200 dark:border-gray-700">
        <table class="w-full font-mono text-xs">
          <thead class="bg-surface-50 text-[0.65rem] uppercase tracking-wider text-gray-400 dark:bg-gray-900/40 dark:text-gray-500">
            <tr>
              <th v-for="h in CURVE_COLS" :key="h.key" class="px-3 py-2 font-medium"
                :class="h.align === 'right' ? 'text-right' : 'text-left'">{{ h.label }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-200 dark:divide-gray-700">
            <tr v-for="c in combatCurve" :key="c.level" class="transition-colors hover:bg-surface-50 dark:hover:bg-gray-700/30">
              <td class="px-3 py-1.5 text-gray-500">{{ c.level }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums text-gray-500">{{ c.cost.minerals }}/{{ c.cost.gas }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums text-gray-700 dark:text-gray-300">{{ c.stats.hp }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums text-gray-700 dark:text-gray-300">{{ c.stats.armor }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums text-gray-700 dark:text-gray-300">{{ c.stats.sight }}</td>
              <td class="px-3 py-1.5 text-right tabular-nums text-gray-500">{{ c.stats.speed }}</td>
              <td class="px-3 py-1.5 text-right font-semibold tabular-nums text-orange-600 dark:text-orange-400">{{ fmt(curveDps(c)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 武器逐级明细：射程 / 间隔 / 溅射的变化都落在这张表 -->
      <div v-if="weaponCurveRows.length" class="mt-4">
        <h3 class="mb-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">武器逐级明细</h3>
        <div class="overflow-x-auto rounded-lg border border-surface-200 dark:border-gray-700">
          <table class="w-full min-w-[34rem] font-mono text-xs">
            <thead class="bg-surface-50 text-[0.65rem] uppercase tracking-wider text-gray-400 dark:bg-gray-900/40 dark:text-gray-500">
              <tr>
                <th v-for="h in WEAPON_COLS" :key="h.key" class="px-3 py-2 font-medium"
                  :class="h.align === 'right' ? 'text-right' : 'text-left'">{{ h.label }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-surface-200 dark:divide-gray-700">
              <tr v-for="r in weaponCurveRows" :key="r.level" class="transition-colors hover:bg-surface-50 dark:hover:bg-gray-700/30">
                <td class="px-3 py-1.5 text-gray-500">{{ r.level }}</td>
                <td v-for="(c, i) in r.cells" :key="i" class="px-3 py-1.5 text-right tabular-nums"
                  :class="c.changed ? 'font-semibold text-emerald-600 dark:text-emerald-400' : 'text-gray-700 dark:text-gray-300'"
                >{{ c.text }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 额外科技 -->
    <section v-if="optionGroups.length" class="wiki-card mb-6 p-6">
      <h2 class="section-title">额外科技 · 可选 {{ optionGroups.length }} 项</h2>
      <p class="mb-3 max-w-3xl text-xs leading-relaxed text-gray-500 dark:text-gray-400">
        独立于攻防科技的研究项目，玩家按需选择。下表是「只研究这一项」后的数值变化。
      </p>

      <div class="grid gap-3 lg:grid-cols-2">
        <article
          v-for="o in optionGroups"
          :key="o.family"
          class="rounded-lg border border-surface-200 p-4 dark:border-gray-700"
        >
          <header class="flex flex-wrap items-center gap-2">
            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ o.nameZh }}</h3>
            <span class="font-mono text-xs tabular-nums text-gray-400">{{ fmtCost(o.cost) }}</span>
          </header>

          <div class="mt-1.5 flex flex-wrap gap-1">
            <span v-for="d in o.dimensions" :key="d"
              class="rounded px-1.5 py-px text-[0.65rem] leading-5" :class="dimClass(d)">{{ dimensionLabel(d) }}</span>
          </div>

          <div v-if="delta(o).length" class="mt-2.5 space-y-1">
            <div v-for="d in delta(o)" :key="d.label" class="flex items-center justify-between gap-2 font-mono text-xs">
              <span class="text-gray-500 dark:text-gray-400">{{ d.label }}</span>
              <span class="tabular-nums">
                <span class="text-gray-400">{{ d.from }}</span>
                <span class="mx-1 text-gray-300 dark:text-gray-600">→</span>
                <span class="font-semibold text-emerald-600 dark:text-emerald-400">{{ d.to }}</span>
              </span>
            </div>
          </div>
          <p v-else class="mt-2 text-xs text-gray-400">数值在建模维度内无变化</p>

          <div class="mt-2 border-t border-surface-200 pt-2 font-mono text-[0.65rem] tabular-nums text-gray-500 dark:border-gray-700 dark:text-gray-400">
            <span v-for="lv in o.levels" :key="lv.level" class="mr-3">{{ lv.level }}级 {{ lv.minerals }}/{{ lv.gas }}<span v-if="lv.time"> · {{ lv.time }}s</span></span>
          </div>

          <p v-if="o.unmodeled.length" class="mt-1.5 text-[0.65rem] text-gray-400 dark:text-gray-500">
            另改动：{{ o.unmodeled.map(prettyField).join('、') }}
          </p>
        </article>
      </div>
    </section>

    <!-- 生产 -->
    <section v-if="producers.length || unit.produces?.length" class="wiki-card p-6">
      <h2 class="section-title">生产链</h2>
      <p v-if="producers.length" class="text-sm leading-relaxed text-gray-600 dark:text-gray-400">
        <span class="text-gray-400">由</span>
        <template v-for="(p, i) in producers" :key="i">
          <span v-if="i" class="text-gray-300 dark:text-gray-600"> · </span>
          <NuxtLink :to="`/units/${p.edge.from}`" class="text-survivor-600 hover:underline dark:text-survivor-400">{{ unitName(p.edge.from) }}</NuxtLink>
          <span class="text-gray-400">（{{ kindLabel(p.edge.kind) }}{{ p.edge.time ? ` ${p.edge.time}s` : '' }}{{ p.edge.count > 1 ? ` ×${p.edge.count}` : '' }}）</span>
        </template>
        <span class="text-gray-400">生产</span>
      </p>
      <p v-if="unit.produces?.length" class="mt-1.5 text-sm leading-relaxed text-gray-600 dark:text-gray-400">
        <span class="text-gray-400">可生产 ·</span>
        <NuxtLink v-for="(id, i) in unit.produces" :key="id" :to="`/units/${id}`"
          class="text-survivor-600 hover:underline dark:text-survivor-400">
          <span v-if="i" class="text-gray-300 dark:text-gray-600">、</span>{{ unitName(id) }}
        </NuxtLink>
      </p>
    </section>
  </div>

  <!-- 空态 -->
  <div v-else class="flex flex-col items-center gap-3 py-24 text-center">
    <span class="text-3xl text-gray-300 dark:text-gray-600">◈</span>
    <p class="text-lg text-gray-500 dark:text-gray-400">找不到单位 {{ unitId }}</p>
    <NuxtLink to="/units" class="text-sm font-medium text-survivor-600 hover:underline dark:text-survivor-400">浏览兵种数据库</NuxtLink>
  </div>
</template>

<script setup lang="ts">
import { CATEGORY_LABELS, ATTRIBUTE_LABELS, ATTRIBUTE_FALLBACK, WEAPON_NOTE_LABELS, DIMENSION_LABELS } from '~/composables/useUnitsData'
import type { CurvePoint, UnitOption } from '~/composables/useUnitsData'

const route = useRoute()
const unitId = route.params.id as string
const { getUnit, producersOf, unitMap, curveDps: curveDpsOf, dimensionLabel } = useUnitsData()
const curveDps = (c: CurvePoint) => curveDpsOf(c, 'armored')
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
const ownerLink = computed(() => (ownerLinks.value[0]?.id >= 0 ? `/classes/${ownerLinks.value[0].id}` : '/units'))
const ownerLinkLabel = computed(() => (ownerLinks.value.length === 1 ? ` · ${ownerLinks.value[0].zh}` : ''))

const isPlating = computed(() => !!unit.value?.stats.armorName?.includes('Plating'))

const combatGroups = computed(() => (unit.value?.upgrades || []).filter(g => g.kind === 'combat'))
const optionGroups = computed(() => unit.value?.options || [])
const combatCurve = computed(() => unit.value?.curves?.combat || [])
const baseSnap = computed(() => combatCurve.value[0])

/** 该武器当前不能对空，但存在能让它对空的科技 → 标出来。 */
function enablesAir(wid: string) {
  return airUpgrades(wid).length > 0
}
/** 能让该武器对空的科技名（当前不能对空时才有意义）。 */
function airUpgrades(wid: string) {
  const bs = (baseSnap.value?.weapons || []).find(w => w.id === wid)
  if (!bs || bs.targets?.air) return []
  return optionGroups.value
    .filter(o => (o.snapshot?.weapons || []).some(w => w.id === wid && w.targets?.air))
    .map(o => o.nameZh.replace(/^(?:研发|研究|升级)\s*/, ''))
}

const CURVE_COLS = [
  { key: 'level', label: '科技等级', align: 'left' },
  { key: 'cost', label: '累计花费', align: 'right' },
  { key: 'hp', label: '生命', align: 'right' },
  { key: 'armor', label: '护甲', align: 'right' },
  { key: 'sight', label: '视野', align: 'right' },
  { key: 'speed', label: '移速', align: 'right' },
  { key: 'dps', label: '对重甲 DPS', align: 'right' },
]

const WEAPON_COLS = [
  { key: 'level', label: '等级', align: 'left' },
  { key: 'range', label: '射程', align: 'right' },
  { key: 'period', label: '攻击间隔', align: 'right' },
  { key: 'splash', label: '溅射半径', align: 'right' },
  { key: 'light', label: '对轻甲 DPS', align: 'right' },
  { key: 'armored', label: '对重甲 DPS', align: 'right' },
]

/** 武器逐级明细：射程 / 间隔 / 溅射半径 / 各靶标 DPS（与 0 级不同即高亮）。
 *  多武器的单位按武器拆成多组行。 */
const weaponCurveRows = computed(() => {
  const curve = combatCurve.value
  const u = unit.value
  if (!curve.length || !u) return []
  const n = (curve[0].weapons || []).length
  if (!n) return []
  const rows: { level: number | string; cells: { text: string; changed: boolean }[] }[] = []
  for (let w = 0; w < n; w++) {
    const base = curve[0].weapons[w]
    for (const c of curve) {
      const s2 = c.weapons[w]
      if (!s2) continue
      const mk = (text: string, changed: boolean) => ({ text, changed })
      const cells = [
        mk(fmt(s2.range), s2.range !== base.range),
        mk(fmt(s2.period), s2.period !== base.period),
        mk(fmt(s2.splashRadius), s2.splashRadius !== base.splashRadius),
        mk(fmt(s2.light?.dps), s2.light?.dps !== base.light?.dps),
        mk(fmt(s2.armored?.dps), s2.armored?.dps !== base.armored?.dps),
      ]
      const prefix = n > 1 ? `${u.weapons[w]?.nameZh || s2.id} · ` : ''
      rows.push({ level: `${prefix}${c.level}`, cells })
    }
  }
  return rows
})

/** 额外科技的数值前后对比：只看真正变化的那些维度。 */
function delta(o: UnitOption) {
  const before = baseSnap.value
  const after = o.snapshot
  if (!before || !after) return []
  const out: { label: string; from: string; to: string }[] = []
  for (const [key, dim] of [['hp', 'hp'], ['shield', 'shield'], ['armor', 'armor'],
                            ['sight', 'sight'], ['speed', 'speed'], ['energy', 'energy']] as const) {
    const a = before.stats[key]
    const b = after.stats[key]
    if (a !== b) out.push({ label: dimensionLabel(dim), from: fmt(a), to: fmt(b) })
  }
  for (let i = 0; i < (before.weapons || []).length; i++) {
    const a = before.weapons[i]
    const b = after.weapons[i]
    if (!a || !b) continue
    const tag = (before.weapons || []).length > 1 ? `#${i + 1} ` : ''
    if (a.range !== b.range) out.push({ label: `${tag}射程`, from: fmt(a.range), to: fmt(b.range) })
    if (a.period !== b.period) out.push({ label: `${tag}攻击间隔`, from: fmt(a.period), to: fmt(b.period) })
    if (a.splashRadius !== b.splashRadius) out.push({ label: `${tag}溅射半径`, from: fmt(a.splashRadius), to: fmt(b.splashRadius) })
    if (!!a.targets?.air !== !!b.targets?.air) {
      out.push({ label: `${tag}对空`, from: a.targets?.air ? '可对空' : '不可', to: b.targets?.air ? '可对空' : '不可' })
    }
    for (const t of ['light', 'armored', 'kerrigan'] as const) {
      const da = a[t]?.dps
      const db = b[t]?.dps
      if (da !== db) out.push({ label: `${tag}${attrLabel(t)} DPS`, from: fmt(da), to: fmt(db) })
    }
  }
  return out.slice(0, 8)
}

const DIM_TONE: Record<string, string> = {
  range: 'bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
  sight: 'bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300',
  splash: 'bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-300',
  damage: 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  bonus: 'bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  period: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  rateMultiplier: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  hp: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  armor: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  speed: 'bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
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

const statFields = computed(() => {
  const u = unit.value
  if (!u) return []
  const s = u.stats
  const out = [
    { label: '生命值', value: s.hp },
    { label: '护盾', value: s.shield, class: 'text-sky-600 dark:text-sky-400' },
    { label: '护甲', value: isPlating.value ? `${s.armor}（建筑镀层）` : s.armor },
    { label: '移动速度', value: s.speed },
  ]
  if (s.sight) out.push({ label: '视野', value: s.sight })
  if (s.hpRegen) out.push({ label: '回血/秒', value: s.hpRegen })
  if (s.energy) out.push({ label: '能量', value: s.energy })
  if (u.cost.minerals || u.cost.gas) out.push({ label: '造价', value: `${u.cost.minerals} 矿${u.cost.gas ? ` / ${u.cost.gas} 气` : ''}` })
  if (u.cost.food) out.push({ label: '人口', value: u.cost.food })
  if (u.cost.supplyProvided) out.push({ label: '提供人口', value: u.cost.supplyProvided })
  if (u.planes.length) out.push({ label: '地形', value: u.planes.join(' / ') })
  return out.filter(f => f.value !== 0 && f.value != null)
})

const metrics = computed(() => {
  const d = unit.value?.derived
  if (!d) return []
  const out = []
  if (d.dpsPer100Light) out.push({ label: '每 100 资源 · 对轻甲', value: d.dpsPer100Light, note: '晶矿 + 气体，未对气体加权' })
  if (d.dpsPer100Armored) out.push({ label: '每 100 资源 · 对重甲', value: d.dpsPer100Armored })
  if (d.dpsPer100Kerrigan) out.push({ label: '每 100 资源 · 对凯瑞甘', value: d.dpsPer100Kerrigan })
  if (d.ehp) out.push({ label: '有效血量', value: d.ehp, note: '生命 + 护盾（护甲不折算）' })
  if (d.hpPer100) out.push({ label: '每 100 资源血量', value: d.hpPer100 })
  if (d.dpsPerFoodLight) out.push({ label: '每人口 · 对轻甲', value: d.dpsPerFoodLight })
  if (d.fullUpgradeCost) out.push({ label: '满科技累计', value: fmtCost(d.fullUpgradeCost), note: '矿 / 气' })
  return out
})

const TARGET_ROWS = [
  { key: 'base', label: '无属性基准', base: 'dpsBase', max: 'dpsBaseMax' },
  { key: 'light', label: '对轻甲', base: 'dpsLight', max: 'dpsLightMax' },
  { key: 'armored', label: '对重甲', base: 'dpsArmored', max: 'dpsArmoredMax' },
  { key: 'heroic', label: '对英雄', base: 'dpsHeroic', max: 'dpsHeroicMax' },
  { key: 'kerrigan', label: '对凯瑞甘（英雄 / 巨型 / 首领）', base: 'dpsKerrigan', max: 'dpsKerriganMax' },
]
const targetRows = computed(() => (unit.value ? TARGET_ROWS.filter(r => unit.value!.derived[r.base] != null) : []))

const maxCurveDps = computed(() => {
  const c = combatCurve.value
  if (!c?.length) return 1
  return Math.max(1, ...c.map(p => Number(curveDps(p))))
})
function barHeight(c: CurvePoint) {
  return Math.max(6, (Number(curveDps(c)) / maxCurveDps.value) * 100)
}
function gain(base: string, max: string) {
  const a = unit.value?.derived[base] || 0
  const b = unit.value?.derived[max] || 0
  return a > 0 ? ((b - a) / a) * 100 : 0
}

function attrLabel(a: string) { return ATTRIBUTE_LABELS[a]?.[0] || a }
function attrClass(a: string) { return ATTRIBUTE_LABELS[a]?.[1] || ATTRIBUTE_FALLBACK[0] }
function noteLabel(n: string) { return WEAPON_NOTE_LABELS[n] || n }
function unitName(id: string) { return unitMap[id]?.nameZh || id }
function kindLabel(k: string) {
  return ({ train: '训练', build: '建造', warp: '折跃', morph: '变形', summon: '召唤', magazine: '弹药' } as Record<string, string>)[k] || k
}
function fmtCost(c: { minerals: number; gas: number }) {
  return [c.minerals && `${c.minerals}矿`, c.gas && `${c.gas}气`].filter(Boolean).join(' / ') || '0'
}
useHead(() => ({ title: `${unit.value?.nameZh || unitId} · 兵种 · KS2 Wiki` }))
</script>
