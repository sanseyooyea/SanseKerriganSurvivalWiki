/**
 * 兵种数值引擎（纯函数，前后端通用）。
 *
 * 输入只有 units-v2.json 里的「基础数值 + 升级效果」，任意科技组合下的数值都在这里现算：
 *   - effective(unit, levels)    套用指定科技等级后的单位（生命/护甲/武器…）
 *   - weaponVs(weapon, target)   一把武器对某个目标：能否攻击、单次伤害、DPS
 *   - duel(attacker, defender)   一方攻击另一方：每击伤害（先护盾后生命）、攻击次数、击杀时间
 *   - snapshot / combatCurve / optionSnapshots / derived  —— 给曲线、对比、总览表用
 *
 * 和 scripts/build_units_v2.py 的口径保持一致；那边只负责从地图抽数据，不再预算曲线。
 */
import type { UnitEntry, UnitWeapon, UnitComponent, UpgradeGroup } from '~/composables/useUnitsData'

export type Levels = Record<string, number> // 科技家族 → 已研究到第几级（0 = 未研究）
type Val = number | string

export interface Target {
  attributes: string[]
  armor: number
  shieldArmor?: number
  plane?: 'Ground' | 'Air'
}

/** 标准靶：只体现属性加成与能否攻击（凯瑞甘 = 英雄 + 巨型 + 首领，地面单位）。 */
export const TARGETS: Record<string, Target> = {
  base: { attributes: [], armor: 0, plane: 'Ground' },
  light: { attributes: ['Light'], armor: 0, plane: 'Ground' },
  armored: { attributes: ['Armored'], armor: 0, plane: 'Ground' },
  heroic: { attributes: ['Heroic'], armor: 0, plane: 'Ground' },
  kerrigan: { attributes: ['Heroic', 'Massive', 'MapBoss', 'Biological'], armor: 0, plane: 'Ground' },
}

// 单位字段 ←→ 升级引用里的字段名
const UNIT_FIELDS: Record<string, string> = {
  LifeMax: 'hp', ShieldsMax: 'shield', LifeArmor: 'armor', ShieldArmor: 'shieldArmor',
  Speed: 'speed', Sight: 'sight', EnergyMax: 'energy',
  LifeRegenRate: 'hpRegen', ShieldRegenRate: 'shieldRegen', ShieldsRegenRate: 'shieldRegen',
}
const ATTRIBUTE_NAMES = new Set(['Light', 'Armored', 'Biological', 'Mechanical', 'Massive',
  'Structure', 'Psionic', 'Heroic', 'MapBoss', 'Robotic', 'Summoned'])

function applyOp(op: string, base: Val, cur: Val, v: Val): Val {
  if (typeof v === 'string') return v // TargetFilters 等字符串字段：Set 覆盖
  const b = typeof base === 'number' ? base : 0
  const c = typeof cur === 'number' ? cur : b
  switch (op) {
    case 'Add': return c + v
    case 'Subtract': return c - v
    case 'Multiply': return c * v
    case 'Divide': return v ? c / v : c
    case 'AddBaseMultiply': return c + b * v
    case 'SubtractBaseMultiply': return c - b * v
    case 'Set': return v
    case 'Max': return Math.max(c, v)
    case 'Min': return Math.min(c, v)
    default: return c + v
  }
}

/** 'Ground,Visible;Ally,Missile' → 能否对地/对空 + 排除/要求的属性 */
export function parseTargetFilters(filters: string | null | undefined) {
  if (!filters) return { ground: true, air: true, exclude: [] as string[], require: [] as string[] }
  const [req = '', exc = ''] = filters.split(';')
  const r = req.split(',').filter(x => x && x !== '-')
  const e = exc.split(',').filter(Boolean)
  return {
    ground: !r.includes('Air') || r.includes('Ground'),
    air: !r.includes('Ground') || r.includes('Air'),
    exclude: e,
    require: r.filter(x => ATTRIBUTE_NAMES.has(x)),
  }
}

function baseValues(u: UnitEntry): Map<string, Val> {
  const m = new Map<string, Val>()
  for (const [f, k] of Object.entries(UNIT_FIELDS)) {
    const v = (u.stats as any)[k]
    if (typeof v === 'number') m.set(`Unit,${u.id},${f}`, v)
  }
  for (const w of u.weapons) {
    m.set(`Weapon,${w.id},Period`, w.period ?? 0)
    m.set(`Weapon,${w.id},Range`, w.range ?? 0)
    m.set(`Weapon,${w.id},RateMultiplier`, 1)
    for (const c of w.components) {
      m.set(`Effect,${c.effect},Amount`, c.amount)
      for (const [a, v] of Object.entries(c.bonus || {})) m.set(`Effect,${c.effect},AttributeBonus[${a}]`, v)
      for (const [a, v] of Object.entries((c as any).attrFactor || {})) m.set(`Effect,${c.effect},AttributeFactor[${a}]`, v as number)
    }
  }
  return m
}

export function researchable(u: UnitEntry): UpgradeGroup[] {
  return (u.upgrades || []).filter(g => g.researchable)
}

/** 全满：每个可研究科技拉到最高级（kind 不传 = 全部）。 */
export function maxLevels(u: UnitEntry, kind?: 'combat' | 'option'): Levels {
  const out: Levels = {}
  for (const g of researchable(u)) {
    if (!kind || g.kind === kind) out[g.family] = g.levels.length
  }
  return out
}

function resolve(u: UnitEntry, levels: Levels) {
  const base = baseValues(u)
  const vals = new Map(base)
  const cost = { minerals: 0, gas: 0 }
  for (const g of u.upgrades || []) {
    const n = Math.min(levels[g.family] || 0, g.levels.length)
    for (const lv of g.levels.slice(0, n)) {
      cost.minerals += lv.minerals || 0
      cost.gas += lv.gas || 0
      for (const ef of lv.effects) {
        if (/Start$/.test(ef.ref)) continue // LifeStart/ShieldsStart 只是出生值，和 Max 重复
        const b = base.has(ef.ref) ? base.get(ef.ref)! : (typeof ef.value === 'string' ? '' : 0)
        const cur = vals.has(ef.ref) ? vals.get(ef.ref)! : b
        vals.set(ef.ref, applyOp(ef.op, b, cur, ef.value as Val))
      }
    }
  }
  return { vals, cost }
}

export interface EffComponent {
  amount: number
  bonus: Record<string, number>
  attrFactor: Record<string, number>
  armorReduction: number
  hits: number
  secondary: boolean
  vital: boolean
  splashRadius: number | null
}
export interface EffWeapon {
  id: string
  nameZh: string | null
  period: number | null
  range: number | null
  splashRadius: number | null
  suicide: boolean
  melee: boolean
  targets: { ground: boolean; air: boolean; exclude: string[]; require: string[] }
  components: EffComponent[]
  unresolved: string[]
}
export interface EffUnit {
  unit: UnitEntry
  levels: Levels
  cost: { minerals: number; gas: number }
  hp: number
  shield: number
  armor: number
  shieldArmor: number
  speed: number
  sight: number
  attributes: string[]
  planes: string[]
  weapons: EffWeapon[]
}

const num = (v: Val | undefined, d = 0) => (typeof v === 'number' ? v : d)

export function effective(u: UnitEntry, levels: Levels = {}): EffUnit {
  const { vals, cost } = resolve(u, levels)
  const U = (f: string, d = 0) => num(vals.get(`Unit,${u.id},${f}`), d)
  const weapons: EffWeapon[] = u.weapons.map((w: UnitWeapon) => {
    const rate = num(vals.get(`Weapon,${w.id},RateMultiplier`), 1) || 1
    const per = num(vals.get(`Weapon,${w.id},Period`), w.period ?? 0)
    const tf = vals.get(`Weapon,${w.id},TargetFilters`)
    const targets = typeof tf === 'string' && tf
      ? parseTargetFilters(tf)
      : { ...w.targets, require: (w.targets as any).require || [] }
    const comps = w.components.map((c: UnitComponent): EffComponent => {
      const bonus: Record<string, number> = { ...(c.bonus || {}) }
      const factor: Record<string, number> = { ...((c as any).attrFactor || {}) }
      for (const [k, v] of vals) {
        if (!k.startsWith(`Effect,${c.effect},`) || typeof v !== 'number') continue
        const mb = /AttributeBonus\[(\w+)\]$/.exec(k)
        if (mb) bonus[mb[1]] = v
        const mf = /AttributeFactor\[(\w+)\]$/.exec(k)
        if (mf) factor[mf[1]] = v
      }
      return {
        amount: num(vals.get(`Effect,${c.effect},Amount`), c.amount),
        bonus, attrFactor: factor,
        armorReduction: c.armorReduction ?? 1,
        hits: c.hits ?? 1,
        secondary: !!c.secondary,
        vital: !!c.vital,
        splashRadius: c.splash?.radius ?? null,
      }
    })
    const splash = comps.reduce<number | null>((m, c) => (c.splashRadius ? Math.max(m ?? 0, c.splashRadius) : m), null)
    return {
      id: w.id, nameZh: w.nameZh,
      period: per ? per / rate : null,
      range: num(vals.get(`Weapon,${w.id},Range`), w.range ?? 0),
      splashRadius: splash,
      suicide: !!w.suicide, melee: !!w.melee,
      targets, components: comps, unresolved: w.unresolved || [],
    }
  })
  return {
    unit: u, levels, cost,
    hp: U('LifeMax', u.stats.hp), shield: U('ShieldsMax', u.stats.shield),
    armor: U('LifeArmor', u.stats.armor), shieldArmor: U('ShieldArmor', u.stats.shieldArmor || 0),
    speed: U('Speed', u.stats.speed), sight: U('Sight', u.stats.sight),
    attributes: u.attributes, planes: u.planes, weapons,
  }
}

// ---------------------------------------------------------------- 伤害

/** 主目标吃到的伤害分量：仅溅射（ExcludeArray Target）和自身消耗不算，除非武器只有溅射。 */
function primary(w: EffWeapon) {
  const comps = w.components.filter(c => !c.vital)
  const prim = comps.filter(c => !c.secondary)
  return prim.length ? prim : comps
}

function rawHit(c: EffComponent, attrs: string[]) {
  let dmg = c.amount + Object.entries(c.bonus).reduce((s, [k, v]) => (attrs.includes(k) ? s + v : s), 0)
  for (const [k, v] of Object.entries(c.attrFactor)) if (attrs.includes(k)) dmg *= 1 + v
  return dmg
}

/** 为什么打不了（null = 能打）。 */
export function cannotAttack(w: EffWeapon, t: Target): string | null {
  if (!primary(w).length) return w.unresolved.length ? '伤害未解析' : '没有伤害'
  if (t.plane === 'Air' && !w.targets.air) return '无法对空'
  if (t.plane !== 'Air' && !w.targets.ground) return '无法对地'
  const ex = w.targets.exclude.find(a => t.attributes.includes(a))
  if (ex) return `无法攻击「${ATTR_ZH[ex] || ex}」目标`
  const miss = w.targets.require.find(a => !t.attributes.includes(a))
  if (miss) return `只能攻击「${ATTR_ZH[miss] || miss}」目标`
  return null
}

export const ATTR_ZH: Record<string, string> = {
  Light: '轻甲', Armored: '重甲', Biological: '生物', Mechanical: '机械', Massive: '巨型',
  Structure: '建筑', Psionic: '灵能', Heroic: '英雄', MapBoss: '首领', Robotic: '机器人',
}

export interface WeaponVs {
  weapon: EffWeapon
  blocked: string | null
  /** 一次攻击（所有分量 × 次数）对生命（护甲后）的伤害 */
  perAttack: number
  dps: number | null
}

export function weaponVs(w: EffWeapon, t: Target): WeaponVs {
  const blocked = cannotAttack(w, t)
  if (blocked) return { weapon: w, blocked, perAttack: 0, dps: blocked ? 0 : null }
  let per = 0
  for (const c of primary(w)) {
    const raw = rawHit(c, t.attributes)
    if (raw <= 0) continue
    per += Math.max(0.5, raw - t.armor * c.armorReduction) * c.hits
  }
  per = round(per)
  return { weapon: w, blocked: null, perAttack: per, dps: w.suicide || !w.period ? null : round(per / w.period) }
}

/** 单位对目标：取能打的武器里 DPS 最高的那把（不把对空/对地武器叠加）。 */
export function bestWeapon(e: EffUnit, t: Target): WeaponVs | null {
  const all = e.weapons.map(w => weaponVs(w, t))
  const ok = all.filter(x => !x.blocked)
  if (!ok.length) return all[0] || null
  return ok.sort((a, b) => (b.dps ?? b.perAttack) - (a.dps ?? a.perAttack))[0]
}

const round = (x: number, d = 2) => Math.round(x * 10 ** d) / 10 ** d

// ---------------------------------------------------------------- 对战

export interface DuelResult {
  ok: boolean
  reason?: string
  weapon?: EffWeapon
  /** 首击：打在护盾 / 打在生命 上各多少 */
  firstHit?: { shield: number; life: number }
  /** 护盾打空后，每次攻击对生命的伤害 */
  lifePerAttack?: number
  attacks?: number
  /** 击杀时间（秒）= 攻击次数 × 攻击间隔（每次攻击都按一个完整攻击周期计，一击必杀也要 1 个间隔） */
  time?: number | null
  effectiveDps?: number | null
  suicide?: boolean
  killed?: boolean
  remaining?: { shield: number; life: number }
}

/**
 * 攻击方持续攻击防守方直到击杀。
 * 伤害规则（SC2）：每个伤害分量先算属性加成；有护盾时扣「护盾护甲」打护盾，
 * 打穿后溢出部分再扣「生命护甲」进生命；没护盾时直接扣生命护甲。单次最少 0.5。
 * 不计：回血/回盾、射程与走位、英雄等级与属性点、技能和 buff。
 */
export function duel(att: EffUnit, def: EffUnit, opts: { ignoreTeam?: boolean } = {}): DuelResult {
  if (!opts.ignoreTeam && att.unit.team === def.unit.team) {
    return { ok: false, reason: att.unit.team === 'Kerrigan' ? '同为凯瑞甘方，友军无法攻击' : '同为生存方，友军无法攻击' }
  }
  const target: Target = {
    attributes: def.attributes,
    armor: def.armor,
    shieldArmor: def.shieldArmor,
    plane: def.planes.includes('Air') && !def.planes.includes('Ground') ? 'Air' : 'Ground',
  }
  if (!att.weapons.length) return { ok: false, reason: '没有武器' }
  const best = bestWeapon(att, target)
  if (!best || best.blocked) return { ok: false, reason: best?.blocked || '无法攻击', weapon: best?.weapon }
  const w = best.weapon
  const comps = primary(w)

  let shield = def.shield
  let life = def.hp
  // 一次攻击 = 每个分量打 hits 次（小数部分按比例）
  const hitOnce = (c: EffComponent, scale: number) => {
    const raw = rawHit(c, target.attributes) * scale
    if (raw <= 0) return { s: 0, l: 0 }
    if (shield > 0) {
      const d = Math.max(0.5 * scale, raw - def.shieldArmor * c.armorReduction)
      if (d <= shield) { shield -= d; return { s: d, l: 0 } }
      const over = d - shield
      const s = shield
      shield = 0
      const l = Math.max(0, over - def.armor * c.armorReduction)
      life -= l
      return { s, l }
    }
    const l = Math.max(0.5 * scale, raw - def.armor * c.armorReduction)
    life -= l
    return { s: 0, l }
  }
  const attackOnce = () => {
    let s = 0, l = 0
    for (const c of comps) {
      const whole = Math.floor(c.hits)
      for (let i = 0; i < whole; i++) { const r = hitOnce(c, 1); s += r.s; l += r.l }
      const frac = c.hits - whole
      if (frac > 1e-6) { const r = hitOnce(c, frac); s += r.s; l += r.l }
    }
    return { s, l }
  }

  const first = attackOnce()
  let attacks = 1
  if (w.suicide) {
    return {
      ok: true, weapon: w, suicide: true, attacks: 1, time: 0,
      firstHit: { shield: round(first.s), life: round(first.l) },
      killed: life <= 0,
      remaining: { shield: round(Math.max(0, shield)), life: round(Math.max(0, life)) },
    }
  }
  // 护盾阶段逐次模拟（护盾量有限），之后每次对生命的伤害恒定 → 直接除
  while (life > 0 && shield > 0 && attacks < 100000) {
    attackOnce()
    attacks++
  }
  let lifePer = 0
  for (const c of comps) {
    const raw = rawHit(c, target.attributes)
    if (raw > 0) lifePer += Math.max(0.5, raw - def.armor * c.armorReduction) * c.hits
  }
  if (life > 0) {
    if (lifePer <= 0) return { ok: false, reason: '伤害被完全抵消', weapon: w }
    attacks += Math.ceil(life / lifePer - 1e-9)
  }
  const time = w.period ? round(attacks * w.period, 2) : null
  return {
    ok: true, weapon: w, attacks, time,
    firstHit: { shield: round(first.s), life: round(first.l) },
    lifePerAttack: round(lifePer),
    effectiveDps: time ? round((def.hp + def.shield) / time) : null,
    killed: true,
  }
}

// ---------------------------------------------------------------- 曲线 / 快照 / 总览指标

export interface Snapshot {
  level: number | 'max'
  cost: { minerals: number; gas: number }
  stats: { hp: number; shield: number; armor: number; shieldArmor: number; speed: number; sight: number }
  weapons: {
    id: string
    range: number | null
    period: number | null
    splashRadius: number | null
    targets: EffWeapon['targets']
    [target: string]: any
  }[]
  ehp: number
  [k: string]: any
}

export function snapshot(u: UnitEntry, levels: Levels, level: number | 'max' = 0): Snapshot {
  const e = effective(u, levels)
  const ally = u.team === 'Kerrigan'
  const weapons = e.weapons.map((w) => {
    const row: any = { id: w.id, range: w.range, period: w.period, splashRadius: w.splashRadius, targets: w.targets }
    for (const [k, t] of Object.entries(TARGETS)) {
      if (k === 'kerrigan' && ally) { row[k] = { perAttack: null, dps: null, ally: true }; continue }
      const r = weaponVs(w, t)
      row[k] = { perAttack: r.perAttack, dps: r.blocked ? 0 : r.dps, blocked: r.blocked }
    }
    return row
  })
  const snap: Snapshot = {
    level, cost: e.cost,
    stats: { hp: round(e.hp), shield: round(e.shield), armor: round(e.armor), shieldArmor: e.shieldArmor, speed: e.speed, sight: e.sight },
    weapons, ehp: round(e.hp + e.shield, 1),
  }
  for (const k of Object.keys(TARGETS)) {
    const key = `dps${k[0].toUpperCase()}${k.slice(1)}`
    if (k === 'kerrigan' && ally) { snap[key] = null; continue }
    // 多把武器取能打该靶标的最高 DPS（对空/对地武器不叠加）
    const best = bestWeapon(e, TARGETS[k])
    snap[key] = best && !best.blocked ? (best.dps ?? 0) : 0
  }
  return snap
}

/** 攻防科技曲线：所有攻防科技同时推进到第 k 级。没有攻防科技的单位退回全部可研究科技。 */
export function combatCurve(u: UnitEntry): Snapshot[] {
  let groups = researchable(u).filter(g => g.kind === 'combat')
  if (!groups.length) groups = researchable(u)
  const max = Math.max(0, ...groups.map(g => g.levels.length))
  const out: Snapshot[] = []
  for (let k = 0; k <= max; k++) {
    const lv: Levels = {}
    for (const g of groups) lv[g.family] = Math.min(k, g.levels.length)
    out.push(snapshot(u, lv, k))
  }
  return out
}

/** 额外科技：只研究这一项（拉满）时的快照。 */
export function optionSnapshots(u: UnitEntry) {
  return researchable(u).filter(g => g.kind === 'option').map(g => {
    const lv = { [g.family]: g.levels.length }
    const snap = snapshot(u, lv, 'max')
    return {
      family: g.family, nameZh: g.nameZh, category: g.category,
      dimensions: g.dimensions, unmodeled: g.unmodeled, levels: g.levels,
      cost: snap.cost, snapshot: snap,
    }
  })
}

/** 总览表 / 性价比指标：0 级与全科技满级。 */
export function derived(u: UnitEntry) {
  const b = snapshot(u, {}, 0)
  const m = snapshot(u, maxLevels(u), 'max')
  const res = (u.cost.minerals || 0) + (u.cost.gas || 0)
  const d: Record<string, any> = {}
  for (const k of Object.keys(TARGETS)) {
    const key = `dps${k[0].toUpperCase()}${k.slice(1)}`
    d[key] = b[key]
    d[`${key}Max`] = m[key]
  }
  d.ehp = b.ehp
  d.ehpMax = m.ehp
  d.kerriganIsAlly = u.team === 'Kerrigan'
  if (res) {
    for (const t of ['Light', 'Armored', 'Kerrigan']) {
      const v = d[`dps${t}`]
      d[`dpsPer100${t}`] = v == null ? null : round(v * 100 / res)
      const vm = d[`dps${t}Max`]
      d[`dpsPer100${t}Max`] = vm == null ? null : round(vm * 100 / res)
    }
    d.hpPer100 = round(d.ehp * 100 / res, 1)
  }
  if (u.cost.food) {
    d.dpsPerFoodLight = round((d.dpsLight || 0) / u.cost.food)
    d.dpsPerFoodArmored = round((d.dpsArmored || 0) / u.cost.food)
  }
  d.fullUpgradeCost = m.cost
  d.techReliance = d.dpsArmored ? round(d.dpsArmoredMax / d.dpsArmored) : null
  return d
}
