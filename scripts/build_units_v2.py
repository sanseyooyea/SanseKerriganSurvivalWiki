"""Build data/units-v2.json — per-hero unit roster, production tree, full weapon
profiles (damage vs light/armored), upgrade curves and cost-efficiency metrics.

Survivor heroes: roles.json team='Survivor'. Kerrigan heroes: team='Kerrigan'.
Roster = BFS from roles.json heroUnits through Train/Build/WarpTrain/Morph abilities
(lib_units.discover_roster). Units reachable from several heroes (Kerrigan side's
shared Swarm.xml army, Scientist flashlights…) are stored once under `units` with
`owners[]`; each hero lists the ids it reaches.

data/seed/units.overrides.json (optional):
  { "exclude": [unitId,...],                 # never list these
    "heroExtra": { heroNameEn: [unitId,...] } # script-spawned units BFS can't see
  }

Usage: python scripts/build_units_v2.py [--heroes Swann,Zagara] [--verbose]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lib_map as L
import lib_tech as T
import lib_units as U

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'units-v2.json')
ROLES_JSON = os.path.join(ROOT, 'data', 'roles.json')
OVERRIDES = os.path.join(ROOT, 'data', 'seed', 'units.overrides.json')
ROLE_ICON_MAP = os.path.join(ROOT, 'data', 'role-icon-map.json')

INCOME_RE = re.compile(r'Income', re.I)

# 升级可改动的单位/武器字段 → snapshot 键（与 lib_units 的清单保持一致）
UNIT_FIELDS = U.UPGRADE_UNIT_FIELDS
WEAPON_FIELDS = {'Period': 'period', 'Range': 'range', 'DisplayAttackCount': 'attackCount',
                 'RateMultiplier': 'rateMultiplier'}
# 加成/减益类靶标字段由 Effect,<id>,AttributeBonus[X] / AttributeFactor[X] 驱动
ATTR_BONUS_RE = re.compile(r'AttributeBonus\[(\w+)\]')
ATTR_FACTOR_RE = re.compile(r'AttributeFactor\[(\w+)\]')
SPLASH_RE = re.compile(r'AreaArray\[(\d+)\]\.(Radius|Fraction|MaxCount)')
# 攻防科技（随建造顺序自然推进，进「战力曲线」）vs 额外科技（可选项，单独列）
COMBAT_CATEGORIES = {'AttackBonus', 'ArmorBonus'}
# 大量升级没写 EditorCategories（尤其凯瑞甘方的 Swarm 兵），按家族名兜底判定。
# 只认「攻/防」这两个语义明确的词，拿不准的一律当可选科技（宁可少算不可错算）。
COMBAT_NAME_RE = re.compile(
    r'(?:Weapons?|MeleeAttacks|RangedAttacks|MissileAttacks|GroundWeapons|AirWeapons)'
    r'(?:Level|Tier)?\d*$'
    r'|(?:Armor|Carapace|Plating|Plates)(?:Level|Tier)?\d*$', re.I)
# 只是等级记账/美术字段，不当作「未建模的数值改动」展示
NOISE_FIELDS = {'Level', 'Icon', 'LifeArmorLevel', 'ShieldArmorLevel', 'EnergyArmorLevel', ''}


def is_combat_upgrade(category, family):
    if category in COMBAT_CATEGORIES:
        return True
    if category is not None:
        return False
    return bool(COMBAT_NAME_RE.search(family))


def _hero_icon_fallback(roles):
    """英雄本体单位在按钮表里找不到图标时，回退 wiki 已有的职业头像
    data/role-icon-map.json（/icons/<NN>.png）。"""
    if not os.path.exists(ROLE_ICON_MAP):
        return {}
    m = json.load(open(ROLE_ICON_MAP, encoding='utf-8'))
    out = {}
    for r in roles:
        n = m.get(r['nameEn']) or m.get(r['nameEn'].replace(' ', '_'))
        if not n:
            continue
        for uid in r.get('heroUnits', []):
            out[uid] = f'/icons/{n}.png'
    return out


# 图标名与地图 CButton 分歧的少量别名（map 引用的 dds 在基础游戏导出里叫别的名）。
ICON_ALIASES = {
    'wireframe-terran-merccompound.png': 'btn-building-terran-merccompound.png',
    'wireframe-general-xelnagashrine.png': 'btn-building-protoss-darkshrine.png',
    'wireframe-general-xelnagatemple.png': 'wireframe-general-xelnagatower.png',
    'wireframe-general-xelnagatemple.png': 'btn-doodad-chrysalis.png',
    'wireframe-protoss-stonezealot.png': 'btn-unit-protoss-zealot-aiur.png',
    'wireframe-terran-murlocmarine.png': 'btn-unit-terran-marine.png',
    'wireframe-terran-taurenspacemarineouthouse.png': 'wireframe-terran-civilianprisoner.png',
    'wireframe-hybrid-destroyer.png': 'wireframe-protoss-hybridnemesis.png',
    'wireframe-terran-joriumstockpile.png': 'btn-tips-richminerals.png',
}
# 去掉等级/形态后缀后的名字是同一套美术（跳虫 L2/L3、建筑 +N 档、埋地形态…）。
_TIER_SUFFIX = re.compile(
    r'(?:Level|Tier|L)\d+$|(Up|Down|Burrowed|Lowered|Sieged|Rooted|Used|Phasing)$|\d+$')


def _strip_tiers(uid):
    """逐层剥掉后缀，生成候选名：SwarmZerglingL2 → SwarmZerglingL → SwarmZergling。"""
    out = []
    cur = uid
    for _ in range(4):
        nxt = _TIER_SUFFIX.sub('', cur)
        if nxt == cur or not nxt:
            break
        out.append(nxt)
        cur = nxt
    return out


def _icon_names_on_disk():
    """public/tech-icons 下已转换的图标名（前端只认这一目录）。"""
    d = os.path.join(ROOT, 'public', 'tech-icons')
    return set(os.listdir(d)) if os.path.isdir(d) else set()


def _unit_icons(gi, btn_icons, heroes):
    """单位图标优先级：生产它的按钮 face（训练/建造按钮，游戏里真正的单位图）
    → 与单位同名的 CButton → 无。找不到就留空（前端显示占位符，不裂图）。"""
    have_icons = _icon_names_on_disk()
    by_face = {}
    for h in heroes.values():
        for e in h['edges']:
            face = e.get('button')
            if not face:
                continue
            png = btn_icons.get(face)
            if not png or png not in have_icons:
                continue
            for u in e['units']:
                by_face.setdefault(u, png)
    out = dict(by_face)
    for uid in [k[1] for k, _ in gi.entries.items() if k[0] == 'Unit']:
        if uid in out:
            continue
        # 同名 CButton → 剥掉等级/形态后缀再试 → 别名表
        for cand in (uid, f'{uid}Icon', *_strip_tiers(uid)):
            if cand in btn_icons:
                out[uid] = btn_icons[cand]
                break
        if uid not in out:
            # 别名只在该图确实已转换落盘时才用，避免前端引用不存在的文件
            for cand in (uid, *_strip_tiers(uid)):
                alias = ICON_ALIASES.get(f'{cand}.png')
                if alias and alias in have_icons:
                    out[uid] = alias
                    break
    return out


def category(info, hero_units, edges_in):
    uid = info['id']
    if uid in hero_units:
        return 'hero'
    # 分级技能召出的（定点防御靶机 1~4 级）是技能的一部分，不是建筑/兵种
    if edges_in and all(e.get('level') for e in edges_in):
        return 'skill'
    if any(INCOME_RE.search(b) for b in info['behaviors']) or 'KSSurvivorEcoUnit' in info['behaviors']:
        return 'economy'
    if info['isStructure']:
        return 'building'
    kinds = {e['kind'] for e in edges_in}
    if kinds and kinds <= {'morph'}:
        return 'morph'
    if kinds and kinds <= {'summon'}:
        # 花晶矿/气体雇佣来的（亚顿/游牧者的空投）就是兵种；免费召出的才算召唤物
        if any(e.get('costDelta') for e in edges_in):
            return 'troop'
        return 'summon'
    return 'troop'


# 同一单位的不同形态（埋地/攻城/降下/相位…）：id = 本体 id + 后缀
FORM_SUFFIXES = {
    'Burrowed': '埋地', 'Sieged': '攻城模式', 'Lowered': '降下', 'Phasing': '相位模式',
    'Rooted': '扎根', 'Uprooted': '拔起', 'Unsieged': '坦克模式', 'Cloaked': '隐形',
    'Used': '已使用',
}


def form_groups(order, edges, hero_units):
    """把同一单位的形态合并：返回 {形态 id: 本体 id}。

    判定（满足其一，且两者之间有 morph 边）：
      - 形态 id = 本体 id + 形态后缀（StukovRavagerBurrowed → StukovRavager）
      - 双向变形（MiraSiegeBreakerTank ⇄ MiraSiegeBreakerSieged）
    单向的升级链（探照灯 → +1 → +2、精炼厂档位）不合并——那些是不同的建筑。
    斯托科夫的兵是「埋地状态出生 → 钻出」，召唤边落在埋地形态上，所以必须按后缀认本体，
    不能按「谁被召唤」认。英雄本体单位不参与合并（多形态英雄另有展示）。
    """
    roster = set(order)
    morph = {}
    for e in edges:
        if e['kind'] != 'morph' or e.get('level'):
            continue
        for u in e['units']:
            morph.setdefault(e['from'], set()).add(u)

    def linked(a, b):
        return b in morph.get(a, ()) or a in morph.get(b, ())

    out = {}
    for uid in order:
        if uid in hero_units:
            continue
        for suf in FORM_SUFFIXES:
            if uid.endswith(suf):
                base = uid[: -len(suf)]
                if base in roster and base not in hero_units and linked(base, uid):
                    out[uid] = base
                    break
    # 双向变形但名字不成后缀关系：按发现顺序，先出现的当本体
    pos = {u: i for i, u in enumerate(order)}
    for a, bs in morph.items():
        for b in bs:
            if a in hero_units or b in hero_units or a == b:
                continue
            if a in out or b in out or b not in roster or a not in roster:
                continue
            if a in morph.get(b, ()):
                canon, form = (a, b) if pos.get(a, 0) <= pos.get(b, 0) else (b, a)
                out[form] = canon
    # 形态的形态（CreepTumor → Burrowed → Used）一律挂到最终本体上
    for f in list(out):
        seen = set()
        while out[f] in out and out[f] not in seen:
            seen.add(out[f])
            out[f] = out[out[f]]
    return out


def form_label(form_id, canon_id, gs_unit):
    suf = form_id[len(canon_id):] if form_id.startswith(canon_id) else ''
    if suf in FORM_SUFFIXES:
        return FORM_SUFFIXES[suf]
    name = gs_unit.get(form_id) or form_id
    base = gs_unit.get(canon_id) or ''
    return name.replace(base, '').strip('（）() ') or name


def hire_cost(edges_in):
    """雇佣/空投类兵的「单只」造价：技能消耗 ÷ 一次召出数量。单位自身 CostResource 常为 0。"""
    for e in edges_in:
        cd = e.get('costDelta') or {}
        if not cd:
            continue
        n = e.get('count') or 1
        if len(e['units']) > 1 and len(set(e['units'])) == 1:
            n = max(n, len(e['units']))
        return {'minerals': round((cd.get('Minerals') or 0) / n, 2),
                'gas': round((cd.get('Vespene') or 0) / n, 2),
                'perCall': {'minerals': cd.get('Minerals') or 0, 'gas': cd.get('Vespene') or 0,
                            'count': n},
                'chargeTime': (e.get('charge') or {}).get('timeUse'),
                'chargeMax': (e.get('charge') or {}).get('countMax'),
                'abil': e['abil']}
    return None


def timed_life(gi, uid):
    """单位寿命（秒）：BehaviorArray 里带 Duration 的计时类 buff（TimedLife 派生）。"""
    ent = gi.unit(uid)
    if ent is None:
        return None
    for c in ent.findall('BehaviorArray'):
        b = gi.get('Behavior', c.get('Link'))
        if b is None:
            continue
        chain = [x.id for x in b._chain()] + [b.parent_id or '']
        if any('TimedLife' in (x or '') for x in chain):
            return b.num('Duration')
    return None


def skill_weapon_stats(u):
    """技能召出单位的火力摘要（自动炮塔这类有武器的）：单发伤害/间隔/射程/对空 + 三靶 DPS。
    没有可解析伤害的（定点防御、恢复器）返回空 dict，前端自动不显示这些列。"""
    ws = [w for w in (u.get('weapons') or []) if w.get('components')]
    if not ws:
        return {}
    w = ws[0]
    d = u.get('derived') or {}
    dmg = sum((c.get('amount') or 0) * (c.get('hits') or 1) for c in w['components'] if not c.get('vital'))
    return {
        'damage': round(dmg, 2) or None,
        'period': w.get('period'),
        'range': w.get('range'),
        'antiAir': bool(w['targets'].get('air')),
        'dpsLight': d.get('dpsLight'),
        'dpsArmored': d.get('dpsArmored'),
        'dpsKerrigan': d.get('dpsKerrigan'),
    }


def skill_summons(gi, edges, units, gs_btn, gs_abil):
    """把分级技能召出的单位聚成「技能」：每级一行，含召出单位的能量/寿命/可吸收量。

    定点防御靶机：每次拦截消耗等于被挡伤害的能量 → 一架靶机最多吸收
    「初始能量 + 回能 × 寿命」点伤害（初始即满能量，回能只在消耗后才生效）。"""
    by_abil = {}
    for e in edges:
        if e.get('level'):
            by_abil.setdefault(e['abil'], []).append(e)
    out = []
    for abil, es in by_abil.items():
        es.sort(key=lambda e: e['level'])
        ab = gi.get('Abil', abil)
        face = None
        if ab is not None:
            for c in ab.findall('CmdButtonArray'):
                face = face or c.get('DefaultButtonFace')
        name = gs_btn.get(face or '') or gs_abil.get(abil) or abil
        levels = []
        for e in es:
            uid = e['units'][0]
            u = units.get(uid) or {}
            st = u.get('stats') or {}
            ent = gi.unit(uid)
            e_start = ent.num('EnergyStart') if ent is not None else None
            e_max = st.get('energy') or (ent.num('EnergyMax') if ent is not None else None)
            regen = ent.num('EnergyRegenRate') if ent is not None else None
            life = timed_life(gi, uid)
            start = e_start if e_start is not None else e_max
            absorb = None
            # 只有「用能量挡伤害」的单位（定点防御类）才有可吸收量的概念
            blocks = ent is not None and any(
                'PointDefense' in (c.get('Link') or '') for c in ent.findall('WeaponArray'))
            if blocks and start is not None:
                absorb = round(start + (regen or 0) * (life or 0), 1)
            levels.append({
                'level': e['level'], 'unit': uid,
                'energyCost': e.get('energy'), 'cooldown': e.get('cooldown'),
                'unitEnergy': e_max, 'unitEnergyStart': start, 'unitEnergyRegen': regen,
                'duration': life, 'absorbMax': absorb,
                'hp': st.get('hp'), 'armor': st.get('armor'),
                'minerals': (u.get('cost') or {}).get('minerals'),
                **skill_weapon_stats(u),
            })
        out.append({'abil': abil, 'face': face, 'nameZh': name, 'levels': levels})
    return out


def edge_out(e):
    out = {k: e[k] for k in ('from', 'abil', 'index', 'kind', 'time') if e.get(k) is not None}
    for k in ('cooldown', 'charge', 'requirements', 'button', 'count', 'energy', 'level'):
        if e.get(k):
            out[k] = e[k]
    if e.get('costDelta'):
        out['costDelta'] = e['costDelta']
    out['units'] = sorted(set(e['units']), key=e['units'].index)
    if len(e['units']) > 1 and len(set(e['units'])) == 1:
        out['count'] = len(e['units'])
    return out


def apply(op, base, cur, v):
    if isinstance(v, str):
        return v
    if op == 'Add':
        return cur + v
    if op == 'Subtract':
        return cur - v
    if op == 'Multiply':
        return cur * v
    if op == 'Divide':
        return cur / v if v else cur
    if op == 'AddBaseMultiply':
        return cur + base * v
    if op == 'SubtractBaseMultiply':
        return cur - base * v
    if op == 'Set':
        return v
    if op == 'Max':
        return max(cur, v)
    if op == 'Min':
        return min(cur, v)
    return cur


# 靶标 → 快照字段后缀
TARGET_SUFFIX = {t: t[0].upper() + t[1:] for t in U.TARGETS}


def _hit(comp, target):
    """单次打击对靶标的伤害：基础 + 属性加成，扣护甲，再乘属性系数。"""
    base = comp['amount'] + sum(v for k, v in comp['bonus'].items() if k in target['attributes'])
    if base <= 0:
        return 0
    dmg = max(0.5, base - target['armor'] * comp['armorReduction'])
    for k, v in (comp.get('attrFactor') or {}).items():
        if k in target['attributes']:
            dmg *= (1 + v)
    return dmg


def weapon_snapshot(profiles, comp_o, weap_o):
    """每把武器在给定覆盖下的完整数值：射程/间隔/攻速/溅射 + 各靶标 DPS。"""
    out = []
    for p in profiles:
        q = dict(p)
        wo = weap_o.get(p['id'], {})
        if wo.get('Range') is not None:
            q['range'] = wo['Range']
        if wo.get('Period'):
            q['period'] = wo['Period']
        rate = wo.get('RateMultiplier')
        if rate and rate > 0 and q['period']:
            q['period'] = q['period'] / rate
        filt = wo.get('TargetFilters') or p.get('targetFilters')
        tg = U._targets(filt) if filt else p['targets']
        comps, splash = [], None
        for c in p['components']:
            c = dict(c, bonus=dict(c['bonus']))
            eo = comp_o.get(c['effect'], {})
            if 'Amount' in eo:
                c['amount'] = eo['Amount']
            af = {}
            for k, v in eo.items():
                m = ATTR_BONUS_RE.fullmatch(k)
                if m:
                    c['bonus'][m.group(1)] = v
                    continue
                m = ATTR_FACTOR_RE.fullmatch(k)
                if m:
                    af[m.group(1)] = v
                    continue
                m = SPLASH_RE.fullmatch(k)
                if m and m.group(2) == 'Radius':
                    if not isinstance(c.get('splash'), dict):
                        c['splash'] = {'radius': 0, 'rings': []}
                    c['splash']['radius'] = max(c['splash'].get('radius') or 0, v)
            if af:
                c['attrFactor'] = {**(c.get('attrFactor') or {}), **af}
            if c.get('splash'):
                splash = max(splash or 0, c['splash'].get('radius') or 0)
            comps.append(c)
        q['components'] = comps
        entry = {
            'id': p['id'], 'range': q['range'], 'period': q['period'],
            'splashRadius': splash,
            'vitalDamage': U.vital_damage(q) or None,
            'targets': {'ground': tg['ground'], 'air': tg['air'], 'exclude': tg['exclude']},
        }
        for tkey, tval in U.TARGETS.items():
            # 武器 TargetFilters 排除了靶标的任一属性（如 MapBoss）→ 打不了，记 0
            if any(a in tg['exclude'] for a in tval['attributes']):
                entry[tkey] = {'perAttack': 0, 'dps': 0, 'excluded': True}
                continue
            per = sum(_hit(c, tval) * c['hits'] for c in U.primary_components(q))
            entry[tkey] = {'perAttack': round(per, 2),
                           'dps': round(per / q['period'], 2) if q['period'] else None}
        out.append(entry)
    return out


# 字段 → 展示维度（前端用来提示「本组科技会改射程/视野…」）
DIMENSION_LABELS = {
    'hp': '生命', 'shield': '护盾', 'armor': '护甲', 'shieldArmor': '盾甲',
    'speed': '移速', 'sight': '视野', 'hpRegen': '回血', 'shieldRegen': '盾回复',
    'energy': '能量', 'energyRegen': '能量回复', 'food': '人口', 'radius': '体积',
    'repairTime': '修理时间', 'hpRegenDelay': '回血延迟', 'shieldRegenDelay': '盾回复延迟',
    'energyArmor': '能量护甲',
    'damage': '伤害', 'bonus': '属性加成', 'range': '射程', 'period': '攻击间隔',
    'attackCount': '攻击次数', 'rateMultiplier': '攻速', 'splash': '溅射', 'cost': '造价',
}


def field_dimension(field):
    if field == 'Amount':
        return 'damage'
    if ATTR_BONUS_RE.fullmatch(field) or ATTR_FACTOR_RE.fullmatch(field):
        return 'bonus'
    if field == 'Period':
        return 'period'
    if field == 'Range':
        return 'range'
    if field == 'RateMultiplier':
        return 'rateMultiplier'
    if field == 'DisplayAttackCount':
        return 'attackCount'
    if field in ('TargetFilters', 'SearchFilters'):
        return 'targets'
    if SPLASH_RE.fullmatch(field):
        return 'splash'
    if field in U.UPGRADE_COST_FIELDS:
        return 'cost'
    return U.UPGRADE_UNIT_FIELDS.get(field, field)


def upgrade_groups(info, profiles, ui, gs_name):
    """影响该单位的升级，分「攻防科技」(combat) 与「额外科技」(option)。

    额外科技 = EditorCategories 不是 AttackBonus/ArmorBonus 的专项研究，玩家可选，
    不进战力曲线，单独展示；每级记录它能改动的维度（射程/视野/溅射…）。
    """
    uid = info['id']
    keys = {('Unit', uid)}
    for p in profiles:
        keys.add(('Weapon', p['id']))
        for e in p['effects']:
            keys.add(('Effect', e))
    groups = []
    for fam in ui.relevant(keys):
        meta = ui.upgrades[fam['levels'][0]['upgrade']] if fam['levels'] else {}
        face = (fam['levels'][0]['slot'] or {}).get('buttonFace')
        raw = (gs_name.get(face) if face else None) or meta.get('name') or fam['family']
        name = re.sub(r'\s*(?:等级|等級)\s*\d+\s*$', '', raw).strip() or fam['family']

        lvls, dims = [], set()
        for i, lv in enumerate(fam['levels'], 1):
            up = ui.upgrades[lv['upgrade']]
            effs = [x for x in up['effects'] if (x[0], x[1]) in keys]
            slot = lv['slot'] or {}
            dims.update(field_dimension(f) for _, _, f, _, _ in effs)
            lvls.append({
                'level': i, 'upgrade': lv['upgrade'],
                'minerals': slot.get('minerals', 0), 'gas': slot.get('gas', 0),
                'time': slot.get('time', 0), 'researchedBy': slot.get('ability'),
                'effects': [{'ref': f'{c},{t},{f}', 'op': op, 'value': v} for c, t, f, op, v in effs],
            })
        if not any(l['effects'] for l in lvls):
            continue
        wid = {p['id'] for p in profiles}
        unmodeled = set()
        for lv in fam['levels']:
            for c, t, f, op, val in ui.upgrades[lv['upgrade']]['other']:
                if f in NOISE_FIELDS:
                    continue
                if (c == 'Weapon' and t in wid) or (c == 'Unit' and t == uid):
                    unmodeled.add(f)
        groups.append({
            'family': fam['family'], 'nameZh': name,
            'category': (ui.upgrades[fam['levels'][0]['upgrade']] or {}).get('category'),
            'kind': 'combat' if is_combat_upgrade(
                (ui.upgrades[fam['levels'][0]['upgrade']] or {}).get('category'),
                fam['family']) else 'option',
            'researchable': fam['researchable'],
            'dimensions': sorted(dims),
            'unmodeled': sorted(unmodeled)[:8],
            'levels': lvls,
        })
    groups.sort(key=lambda g: (g['kind'] != 'combat', g['family']))
    return groups


def base_snapshot(info, profiles):
    uid = info['id']
    base = {('Unit', uid, f): info['stats'][k]
            for f, k in UNIT_FIELDS.items() if info['stats'].get(k) is not None}
    for p in profiles:
        base[('Weapon', p['id'], 'Period')] = p['period'] or 0
        base[('Weapon', p['id'], 'Range')] = p['range'] or 0
        if p.get('targetFilters'):
            base[('Weapon', p['id'], 'TargetFilters')] = p['targetFilters']
        for c in p['components']:
            base[('Effect', c['effect'], 'Amount')] = c['amount']
            for a, v in c['bonus'].items():
                base[('Effect', c['effect'], f'AttributeBonus[{a}]')] = v
    return base


def apply_levels(base, levels):
    vals, cost = dict(base), {'minerals': 0, 'gas': 0}
    for lv in levels:
        cost['minerals'] += lv.get('minerals', 0)
        cost['gas'] += lv.get('gas', 0)
        for ef in lv['effects']:
            c, t, f = ef['ref'].split(',', 2)
            key = (c, t, f)
            b = base.get(key, 0)
            nv = apply(ef['op'], b, vals.get(key, b), ef['value'])
            vals[key] = nv if isinstance(nv, str) else round(nv, 4)
    return vals, cost


def snapshot_of(info, profiles, vals, cost, level):
    uid = info['id']
    unit_vals = {UNIT_FIELDS[f]: v for (c, t, f), v in vals.items()
                 if c == 'Unit' and t == uid and f in UNIT_FIELDS}
    comp_o, weap_o = {}, {}
    for (c, t, f), v in vals.items():
        if c == 'Effect':
            comp_o.setdefault(t, {})[f] = v
        elif c == 'Weapon':
            weap_o.setdefault(t, {})[f] = v
    s = dict(info['stats'])
    s.update(unit_vals)
    node = {'level': level, 'cost': cost, 'stats': s,
            'weapons': weapon_snapshot(profiles, comp_o, weap_o)}
    for tkey in U.TARGETS:
        suf = TARGET_SUFFIX[tkey]
        node[f'dps{suf}'] = round(sum((w[tkey]['dps'] or 0) for w in node['weapons']), 2)
        node[f'dps{suf}PerAttack'] = round(sum((w[tkey]['perAttack'] or 0) for w in node['weapons']), 2)
    node['ehp'] = round(s['hp'] + s['shield'], 1)
    node['costTotal'] = cost['minerals'] + cost['gas']
    return node


def build_curves(info, profiles, groups):
    """返回 (curves, maxed, options)。
    curves.combat = 只推进攻防科技（按建造顺序自然获得）→ 真实战力成长
    curves.all    = 攻防 + 额外科技全推 → 理论上限
    maxed         = 全科技满级快照（性价比列用它）
    options       = 额外科技逐项快照（只研究这一组时的数值变化）
    """
    base = base_snapshot(info, profiles)
    combat = [g for g in groups if g['kind'] == 'combat' and g['researchable']]
    option = [g for g in groups if g['kind'] == 'option' and g['researchable']]
    all_g = combat + option

    def curve_of(glist):
        max_lv = max((len(g['levels']) for g in glist), default=0)
        nodes = []
        for k in range(0, max_lv + 1):
            lvls = [lv for g in glist for lv in g['levels'][:k]]
            vals, cost = apply_levels(base, lvls)
            nodes.append(snapshot_of(info, profiles, vals, cost, k))
        return nodes

    # 没有攻防科技的（建筑/召唤物常见）退回全部可研究科技，避免曲线只有 0 级
    curves = {
        'combat': curve_of(combat) if combat else curve_of(all_g),
        'all': curve_of(all_g),
    }
    if not curves['all']:
        curves['all'] = curves['combat']

    vals, cost = apply_levels(base, [lv for g in groups if g['researchable'] for lv in g['levels']])
    maxed = snapshot_of(info, profiles, vals, cost, 'max')

    options = []
    for g in option:
        gvals, gcost = apply_levels(base, g['levels'])
        options.append({
            'family': g['family'], 'nameZh': g['nameZh'], 'category': g['category'],
            'dimensions': g['dimensions'], 'unmodeled': g['unmodeled'],
            'cost': gcost, 'levels': g['levels'],
            'snapshot': snapshot_of(info, profiles, gvals, gcost, 'max'),
        })
    return curves, maxed, options


def derived(info, base_snap, maxed_snap):
    """0 级 / 满级（全科技拉满）两套派生指标，供总览表排序与性价比对比。

    - 0 级取「未研究任何科技」的真实基础值
    - 满级取全科技拉满；两列并列即可看出该单位的科技依赖度
    """
    cost = info['cost']
    res = cost['minerals'] + cost['gas']

    def dps(snap, tkey):
        if not snap:
            return 0
        return round(sum((w[tkey]['dps'] or 0) for w in snap['weapons']), 2)

    def ehp(snap):
        # 有效血量 = 生命 + 护盾。护甲单独列，不折算进来（折算口径依赖假设的打击伤害，
        # 会把不同单位的血量横向比得不可信）。护盾另计，因为很多单位只吃其中一项。
        if not snap:
            return 0
        s = snap['stats']
        return round(s['hp'] + s['shield'], 1)

    d = {}
    for tkey in U.TARGETS:
        suf = TARGET_SUFFIX[tkey]
        d[f'dps{suf}'] = dps(base_snap, tkey)
        d[f'dps{suf}Max'] = dps(maxed_snap, tkey)
    d['ehp'] = ehp(base_snap)
    d['ehpMax'] = ehp(maxed_snap)
    d['targets'] = list(U.TARGETS)
    if res:
        # 性价比不取「轻/重甲较高者」——那种合并会掩盖专精。两个靶标各自一列。
        d['dpsPer100Light'] = round(d.get('dpsLight', 0) * 100 / res, 2)
        d['dpsPer100Armored'] = round(d.get('dpsArmored', 0) * 100 / res, 2)
        d['dpsPer100Kerrigan'] = round(d.get('dpsKerrigan', 0) * 100 / res, 2)
        d['hpPer100'] = round(d['ehp'] * 100 / res, 1)
        for tag in ('Light', 'Armored', 'Kerrigan'):
            d[f'dpsPer100{tag}Max'] = round(d.get(f'dps{tag}Max', 0) * 100 / res, 2)
    if cost['food']:
        d['dpsPerFoodLight'] = round(d.get('dpsLight', 0) / cost['food'], 2)
        d['dpsPerFoodArmored'] = round(d.get('dpsArmored', 0) / cost['food'], 2)
    if maxed_snap:
        d['fullUpgradeCost'] = maxed_snap['cost']
    d['techReliance'] = round(d['dpsArmoredMax'] / d['dpsArmored'], 2) if d['dpsArmored'] else None
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--heroes')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    ov = json.load(open(OVERRIDES, encoding='utf-8')) if os.path.exists(OVERRIDES) else {}
    exclude = set(ov.get('exclude', []))
    roles = json.load(open(ROLES_JSON, encoding='utf-8'))
    roles = [r for r in roles if r.get('team') in ('Survivor', 'Kerrigan') and r.get('heroUnits')
             and r.get('category') not in ('Random', 'Ghost')]
    if args.heroes:
        want = set(args.heroes.split(','))
        roles = [r for r in roles if r['nameEn'] in want]

    archive = L.open_map()
    gi = U.GameIndex(archive)
    ui = U.UpgradeIndex(gi)
    gs_unit = L.game_strings(archive, 'Unit/Name/')
    gs_btn = L.game_strings(archive, 'Button/Name/')
    gs_weapon = L.game_strings(archive, 'Weapon/Name/')
    btn_icons = {}
    for root in gi.roots.values():
        btn_icons.update(T.build_button_icons(root))

    units, heroes = {}, {}
    unit_icons = {}
    unresolved_total, weapons_total = 0, 0
    for r in roles:
        hero = r['nameEn']
        hu = U.resolve_hero_units(gi, hero, r['heroUnits'])
        order, edges = U.discover_roster(gi, hu)
        order += [u for u in ov.get('heroExtra', {}).get(hero, []) if u not in order and gi.unit(u)]
        order = [u for u in order if u not in exclude]
        edges = [dict(e, units=[u for u in e['units'] if u not in exclude]) for e in edges]
        edges = [e for e in edges if e['units']]
        forms = form_groups(order, edges, set(hu))
        # 本体排在它最早出现的形态的位置（斯托科夫的兵先以埋地形态被发现）
        listed, seen_c = [], set()
        for u in order:
            c = forms.get(u, u)
            if c not in seen_c:
                seen_c.add(c)
                listed.append(c)
        heroes[hero] = {'team': r['team'], 'category': r.get('category'), 'roleId': r['id'],
                        'heroUnits': hu, 'unitIds': listed,
                        'edges': [edge_out(e) for e in edges]}
        if forms:
            heroes[hero]['forms'] = forms

        def group_edges_in(uid):
            """进入该单位的边；本体还要收下「进入它各形态」的边（形态之间的互变除外）。"""
            members = {uid} | {f for f, c in forms.items() if c == uid}
            out = []
            for e in edges:
                if not (members & set(e['units'])):
                    continue
                if e['kind'] == 'morph' and (e['from'] in members or forms.get(e['from']) == uid):
                    continue
                out.append(e)
            return out

        for uid in order:
            if uid in units:
                if hero not in units[uid]['owners']:
                    units[uid]['owners'].append(hero)
                continue
            info = U.unit_stats(gi, uid)
            info['id'] = uid
            edges_in = [e for e in edges if uid in e['units']] if uid in forms else group_edges_in(uid)
            profiles = [U.weapon_profile(gi, w) for w in info['weapons']]
            profiles = [p for p in profiles if p['components'] or p['unresolved']]
            weapons_total += len(profiles)
            unresolved_total += sum(1 for p in profiles if p['unresolved'])
            groups = upgrade_groups(info, profiles, ui, gs_btn)
            curves, maxed, options = build_curves(info, profiles, groups)
            # 雇佣/空投兵：玩家实际付的是技能消耗（一次召出 N 只），单位自身的 CostResource
            # 只用于击杀/回收计价。性价比按「技能消耗 ÷ 召出数」算，原值留在 listed。
            hire = hire_cost(edges_in)
            if hire:
                info['cost'] = dict(info['cost'], minerals=hire['minerals'], gas=hire['gas'],
                                    listed={'minerals': info['cost']['minerals'],
                                            'gas': info['cost']['gas']},
                                    hire=hire)
            icon = unit_icons.get(uid)
            units[uid] = {
                'id': uid,
                'nameZh': gs_unit.get(uid, uid),
                'team': r['team'],
                'owners': [hero],
                'category': category(info, hu, edges_in),
                'stats': info['stats'],
                'cost': info['cost'],
                'attributes': info['attributes'],
                'planes': info['planes'],
                'flags': info['flags'],
                'icon': icon,
                'weapons': [{
                    'id': p['id'],
                    'nameZh': gs_weapon.get(p['id']),
                    'period': p['period'], 'range': p['range'], 'minRange': p['minRange'],
                    'melee': p['melee'], 'suicide': p.get('suicide', False),
                    'targets': {'ground': p['targets']['ground'], 'air': p['targets']['air'],
                                'exclude': [x for x in p['targets']['exclude']
                                            if x in ('Light', 'Armored', 'Biological', 'Mechanical',
                                                     'Massive', 'Structure', 'Heroic', 'MapBoss',
                                                     'Psionic')]},
                    'vitalDamage': U.vital_damage(p) or None,
                    'components': [{k: v for k, v in c.items() if v not in (None, {}, False)}
                                   for c in p['components']],
                    'unresolved': p['unresolved'],
                    'notes': p['notes'],
                } for p in profiles],
                'upgrades': groups,
                'options': options,
                'curves': curves,
                'derived': derived(info, curves['combat'][0] if curves['combat'] else None, maxed),
            }

        # 形态挂到本体上：/units/<形态> 仍可访问，但不再作为独立兵种列出
        for f, c in forms.items():
            if f not in units or c not in units:
                continue
            units[f]['category'] = 'form'
            units[f]['formOf'] = c
            units[f]['formLabel'] = form_label(f, c, gs_unit)
            fl = units[c].setdefault('forms', [])
            if f not in [x['id'] for x in fl]:
                fl.append({'id': f, 'label': units[f]['formLabel'], 'nameZh': units[f]['nameZh']})

    # 凯瑞甘方的单位和凯瑞甘方英雄是友军，「对凯瑞甘」靶标对它们没有意义 → 置空（前端显示 —）
    for u in units.values():
        if u['team'] != 'Kerrigan':
            continue
        for k in list(u['derived']):
            if k.startswith('dpsKerrigan') or k.startswith('dpsPer100Kerrigan'):
                u['derived'][k] = None
        u['derived']['kerriganIsAlly'] = True
        snaps = [n for c in (u.get('curves') or {}).values() for n in c]
        snaps += [o['snapshot'] for o in u.get('options') or []]
        for n in snaps:
            for k in list(n):
                if k.startswith('dpsKerrigan'):
                    n[k] = None
            for w in n.get('weapons') or []:
                if 'kerrigan' in w:
                    w['kerrigan'] = {'perAttack': None, 'dps': None, 'ally': True}

    # 分级技能召唤（定点防御靶机等）：挂到英雄上，按级展示能量/寿命/可吸收伤害
    gs_abil = L.game_strings(archive, 'Abil/Name/')
    # 名字优先用技能管线已策展好的 abilities.json（含 face 覆盖，避免英文/串味名）
    ab_json = os.path.join(ROOT, 'data', 'abilities.json')
    curated = json.load(open(ab_json, encoding='utf-8')) if os.path.exists(ab_json) else {}
    for hero, h in heroes.items():
        sk = skill_summons(gi, h['edges'], units, gs_btn, gs_abil)
        for s in sk:
            c = curated.get(s['abil']) or {}
            per = (c.get('perHero') or {}).get(hero) or {}
            s['nameZh'] = per.get('nameZh') or c.get('nameZh') or s['nameZh']
            s['icon'] = per.get('icon') or c.get('icon')
        if sk:
            h['skillSummons'] = sk

    # producedBy[] — 每个单位由谁生产（跨英雄去重）
    for h in heroes.values():
        for e in h['edges']:
            for u in e['units']:
                dst = units.get(u)
                if dst is None:
                    continue
                pb = dst.setdefault('producedBy', [])
                rec = {k: v for k, v in e.items() if k in ('from', 'abil', 'index', 'kind', 'time', 'count')}
                if rec not in pb:
                    pb.append(rec)

    # produces[] (reverse of edges) — 每个单位能生产什么
    for h in heroes.values():
        for e in h['edges']:
            src = units.get(e['from'])
            if src is not None:
                prod = src.setdefault('produces', [])
                for u in e['units']:
                    if u not in prod:
                        prod.append(u)

    # 图标必须等 heroes 建好后才能定（训练/建造按钮的 face 才是单位图）
    unit_icons = _unit_icons(gi, btn_icons, heroes)
    hero_icons = _hero_icon_fallback(roles)
    have_icons = _icon_names_on_disk()
    for uid, icon in {**hero_icons, **unit_icons}.items():
        if uid in units:
            units[uid]['icon'] = icon
    # 兜底：任何仍指向未落盘文件的图标一律清空 → 前端显示 ◈ 占位而不是裂图
    have_icons = _icon_names_on_disk()
    missing = 0
    for u in units.values():
        i = u.get('icon')
        if i and not i.startswith('/') and i not in have_icons:
            u['icon'] = None
            missing += 1

    # 曲线 / 额外科技快照 / 派生指标都由前端 utils/unitEngine.ts 按任意科技组合现算
    # （对战模拟需要同一套引擎），这里只在构建期用来生成技能召唤摘要，不写进数据文件，
    # 否则 json 会膨胀到 15MB+ 并整个打进前端包。
    for u in units.values():
        for k in ('curves', 'options', 'derived'):
            u.pop(k, None)

    data = {'targets': U.TARGETS, 'heroes': heroes, 'units': units}
    text = json.dumps(data, ensure_ascii=False, indent=2).replace(chr(10), chr(13) + chr(10)) + chr(13) + chr(10)
    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        f.write(text)

    print(f'heroes {len(heroes)}  units {len(units)}  weapons {weapons_total}  '
          f'weapons w/ unresolved {unresolved_total}  '
          f'icons {sum(1 for u in units.values() if u["icon"])}')

    if args.verbose:
        for hero, h in heroes.items():
            print(f'\n== {hero} ({h["team"]}) {len(h["unitIds"])} units')
            for uid in h['unitIds']:
                u = units[uid]
                d = u['derived']
                print(f'  {uid:36s} {u["category"]:8s} {u["nameZh"]:10s} '
                      f'${u["cost"]["minerals"]}/{u["cost"]["gas"]} f{u["cost"]["food"]} '
                      f'hp{u["stats"]["hp"]} ar{u["stats"]["armor"]} '
                      f'dps {d.get("dpsBase")}/{d.get("dpsLight")}/{d.get("dpsArmored")} '
                      f'max {d.get("dpsBaseMax")} ups {len(u["upgrades"])}')


if __name__ == '__main__':
    main()
