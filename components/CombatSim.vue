<template>
  <section id="sim" class="wiki-card mb-5 overflow-visible">
    <header class="flex flex-wrap items-center gap-2 border-b border-surface-200 px-4 py-3 dark:border-gray-700">
      <h2 class="text-sm font-semibold text-gray-800 dark:text-gray-100">对战模拟</h2>
      <span class="text-xs text-gray-400">选两个单位，按各自科技算出伤害与击杀时间</span>
      <label class="ml-auto flex cursor-pointer items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
        <input v-model="ignoreTeam" type="checkbox" class="rounded border-surface-300 text-survivor-600 dark:border-gray-600" />
        忽略阵营（理论对比友军）
      </label>
    </header>

    <div class="grid gap-4 p-4 lg:grid-cols-[1fr_auto_1fr]">
      <!-- A -->
      <div class="space-y-2.5">
        <div class="text-[0.65rem] font-medium uppercase tracking-wider text-gray-400">单位 A</div>
        <UnitPicker v-model="aId" placeholder="选择单位 A" />
        <template v-if="A">
          <UnitSummary :e="A" />
          <TechPicker v-model="aLv" :unit="A.unit" />
        </template>
      </div>

      <div class="flex items-start justify-center lg:pt-6">
        <button type="button" title="交换 A / B"
          class="rounded-full border border-surface-200 p-2 text-gray-400 transition-colors hover:border-surface-300 hover:text-gray-600
                 active:translate-y-px dark:border-gray-700 dark:hover:text-gray-200"
          @click="swap">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4M16 17H4m0 0l4 4m-4-4l4-4" />
          </svg>
        </button>
      </div>

      <!-- B -->
      <div class="space-y-2.5">
        <div class="text-[0.65rem] font-medium uppercase tracking-wider text-gray-400">单位 B</div>
        <UnitPicker v-model="bId" placeholder="选择单位 B" />
        <template v-if="B">
          <UnitSummary :e="B" />
          <TechPicker v-model="bLv" :unit="B.unit" />
        </template>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="A && B" class="space-y-3 border-t border-surface-200 px-4 py-4 dark:border-gray-700">
      <DuelLine :att="A" :def="B" :r="ab" />
      <DuelLine :att="B" :def="A" :r="ba" />

      <div class="rounded-lg bg-surface-50 px-3 py-2 text-sm dark:bg-gray-900/50">
        <span class="text-gray-500 dark:text-gray-400">单挑结论：</span>
        <span class="font-medium text-gray-800 dark:text-gray-100">{{ verdict }}</span>
      </div>
      <p class="text-[0.65rem] leading-relaxed text-gray-400 dark:text-gray-500">
        计算规则：每个伤害分量先加属性加成，有护盾时扣护盾护甲打护盾，打穿后的溢出再扣生命护甲；单次至少 0.5。
        第一击在 0 秒，多把武器取对该目标 DPS 最高的一把。未计：射程与走位、回血回盾、英雄等级/属性点、技能与 buff、溅射对其他单位。
      </p>
    </div>
    <p v-else class="border-t border-surface-200 px-4 py-6 text-center text-sm text-gray-400 dark:border-gray-700">
      在上方选两个单位开始模拟（也可以在单位详情页点「加入对战模拟」）
    </p>
  </section>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import { effective, duel, type Levels, type EffUnit, type DuelResult, ATTR_ZH } from '~/utils/unitEngine'

const route = useRoute()
const router = useRouter()
const { unitMap } = useUnitsData()

const aId = ref<string | null>((route.query.a as string) || 'SwannDevastationTurret')
const bId = ref<string | null>((route.query.b as string) || 'SwarmZergling')
const aLv = ref<Levels>({})
const bLv = ref<Levels>({})
const ignoreTeam = ref(false)

watch(aId, () => { aLv.value = {} })
watch(bId, () => { bLv.value = {} })
watch([aId, bId], ([a, b]) => {
  router.replace({ query: { ...route.query, a: a || undefined, b: b || undefined }, hash: route.hash })
})

const A = computed<EffUnit | null>(() => (aId.value && unitMap[aId.value] ? effective(unitMap[aId.value], aLv.value) : null))
const B = computed<EffUnit | null>(() => (bId.value && unitMap[bId.value] ? effective(unitMap[bId.value], bLv.value) : null))
const ab = computed(() => (A.value && B.value ? duel(A.value, B.value, { ignoreTeam: ignoreTeam.value }) : null))
const ba = computed(() => (A.value && B.value ? duel(B.value, A.value, { ignoreTeam: ignoreTeam.value }) : null))

function swap() {
  const [a, b, la, lb] = [aId.value, bId.value, aLv.value, bLv.value]
  aId.value = b; bId.value = a
  nextTick(() => { aLv.value = lb; bLv.value = la })
}

const verdict = computed(() => {
  const x = ab.value, y = ba.value
  const an = A.value!.unit.nameZh, bn = B.value!.unit.nameZh
  const xt = x?.ok && x.killed ? x.time : null
  const yt = y?.ok && y.killed ? y.time : null
  if (xt == null && yt == null) return '双方都无法击杀对方'
  if (xt != null && yt == null) return `${an} 胜（${bn} 无法击杀 ${an}）`
  if (yt != null && xt == null) return `${bn} 胜（${an} 无法击杀 ${bn}）`
  if (xt === yt) return `同时击杀（各 ${xt}s）`
  return xt! < yt!
    ? `${an} 胜，${xt}s 击杀；${bn} 需要 ${yt}s`
    : `${bn} 胜，${yt}s 击杀；${an} 需要 ${xt}s`
})

// ---------------- 子组件（只在本文件里用，保持模拟器自包含）
const UnitSummary = defineComponent({
  props: { e: { type: Object as PropType<EffUnit>, required: true } },
  setup(p) {
    return () => {
      const e = p.e
      const item = (k: string, v: string | number, cls = 'text-gray-700 dark:text-gray-200') =>
        h('div', { class: 'flex justify-between gap-2' }, [
          h('span', { class: 'text-gray-400' }, k),
          h('span', { class: `font-mono tabular-nums ${cls}` }, String(v)),
        ])
      const w = e.weapons.find(x => x.components.length)
      return h('div', { class: 'grid grid-cols-2 gap-x-4 gap-y-0.5 rounded-md bg-surface-50 px-2.5 py-2 text-xs dark:bg-gray-900/50' }, [
        item('生命', round(e.hp)),
        item('护甲', round(e.armor)),
        e.shield ? item('护盾', round(e.shield), 'text-sky-600 dark:text-sky-400') : null,
        e.shield ? item('盾甲', round(e.shieldArmor)) : null,
        item('属性', e.attributes.map(a => ATTR_ZH[a] || a).join(' ') || '—'),
        item('位置', e.planes.includes('Air') ? '空中' : '地面'),
        w ? item('主武器', `${w.components.reduce((s, c) => s + c.amount * c.hits, 0)} / ${w.period ?? '—'}s`) : item('主武器', '无'),
        w ? item('射程', w.range ?? '—') : null,
      ])
    }
  },
})

const DuelLine = defineComponent({
  props: {
    att: { type: Object as PropType<EffUnit>, required: true },
    def: { type: Object as PropType<EffUnit>, required: true },
    r: { type: Object as PropType<DuelResult | null>, default: null },
  },
  setup(p) {
    return () => {
      const r = p.r
      const head = h('div', { class: 'mb-1 flex flex-wrap items-baseline gap-1.5 text-sm' }, [
        h('span', { class: 'font-medium text-gray-800 dark:text-gray-100' }, p.att.unit.nameZh),
        h('span', { class: 'text-gray-400' }, '攻击'),
        h('span', { class: 'font-medium text-gray-800 dark:text-gray-100' }, p.def.unit.nameZh),
        r?.weapon ? h('span', { class: 'text-xs text-gray-400' }, `· ${r.weapon.nameZh || r.weapon.id}`) : null,
      ])
      if (!r) return null
      if (!r.ok) {
        return h('div', { class: 'rounded-lg border border-surface-200 px-3 py-2 dark:border-gray-700' }, [
          head,
          h('div', { class: 'text-sm text-kerrigan-600 dark:text-kerrigan-400' }, `无法攻击 — ${r.reason}`),
        ])
      }
      const stat = (k: string, v: string, cls = 'text-gray-800 dark:text-gray-100') =>
        h('div', [
          h('div', { class: 'text-[0.65rem] text-gray-400' }, k),
          h('div', { class: `font-mono text-sm font-semibold tabular-nums ${cls}` }, v),
        ])
      const hitText = r.firstHit!.shield
        ? `${r.firstHit!.shield} 盾${r.firstHit!.life ? ` + ${r.firstHit!.life} 血` : ''}`
        : `${r.firstHit!.life} 血`
      const cells = r.suicide
        ? [
            stat('自爆伤害', hitText, 'text-orange-600 dark:text-orange-400'),
            stat('结果', r.killed ? '击杀' : `未击杀，剩 ${r.remaining!.shield ? `${r.remaining!.shield} 盾 / ` : ''}${r.remaining!.life} 血`,
              r.killed ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500'),
          ]
        : [
            stat('首次攻击', hitText, 'text-orange-600 dark:text-orange-400'),
            stat('盾破后每击', `${r.lifePerAttack} 血`),
            stat('攻击次数', `${r.attacks}`),
            stat('击杀时间', r.time != null ? `${r.time}s` : '—', 'text-emerald-600 dark:text-emerald-400'),
            stat('有效 DPS', r.effectiveDps != null ? `${r.effectiveDps}` : '—'),
          ]
      return h('div', { class: 'rounded-lg border border-surface-200 px-3 py-2 dark:border-gray-700' }, [
        head,
        h('div', { class: 'grid grid-cols-2 gap-3 sm:grid-cols-5' }, cells),
      ])
    }
  },
})

function round(x: number) {
  return Math.round(x * 100) / 100
}
</script>
