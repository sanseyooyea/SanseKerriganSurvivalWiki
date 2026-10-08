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
    if any(INCOME_RE.search(b) for b in info['behaviors']) or 'KSSurvivorEcoUnit' in info['behaviors']:
        return 'economy'
    if info['isStructure']:
        return 'building'
    kinds = {e['kind'] for e in edges_in}
    if kinds and kinds <= {'morph'}:
        return 'morph'
    if kinds and kinds <= {'summon'}:
        return 'summon'
    return 'troop'


def apply(op, base, cur, v):
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
                c['attrFactor'] = af
            if c.get('splash'):
                splash = max(splash or 0, c['splash'].get('radius') or 0)
            comps.append(c)
        q['components'] = comps
        entry = {
            'id': p['id'], 'range': q['range'], 'period': q['period'],
            'splashRadius': splash,
            'vitalDamage': U.vital_damage(q) or None,
            'targets': {'ground': p['targets']['ground'], 'air': p['targets']['air'],
                        'exclude': p['targets']['exclude']},
        }
        for tkey, tval in U.TARGETS.items():
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
            vals[key] = round(apply(ef['op'], b, vals.get(key, b), ef['value']), 4)
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
    node['ehp'] = round((s['hp'] + s['shield']) * (1 + 0.1 * max(0, s['armor'])), 1)
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
        # 粗略有效血量：护甲每点按抵消一次 10 点打击的 10% 计（仅用于横向比较）
        if not snap:
            return 0
        s = snap['stats']
        return round((s['hp'] + s['shield']) * (1 + 0.1 * max(0, s['armor'])), 1)

    d = {}
    for tkey in U.TARGETS:
        suf = TARGET_SUFFIX[tkey]
        d[f'dps{suf}'] = dps(base_snap, tkey)
        d[f'dps{suf}Max'] = dps(maxed_snap, tkey)
    d['ehp'] = ehp(base_snap)
    d['ehpMax'] = ehp(maxed_snap)
    d['targets'] = list(U.TARGETS)
    d['dpsPeak'] = max(d.get('dpsLight', 0), d.get('dpsArmored', 0))
    if res:
        d['dpsPer100'] = round(d['dpsPeak'] * 100 / res, 2)
        d['ehpPer100'] = round(d['ehp'] * 100 / res, 1)
    if cost['food']:
        d['dpsPerFood'] = round(d['dpsPeak'] / cost['food'], 2)
    if maxed_snap:
        d['fullUpgradeCost'] = maxed_snap['cost']
    d['techReliance'] = round(d['dpsArmoredMax'] / d['dpsArmored'], 2) if d['dpsArmored'] else None
    return d


def edge_out(e):
    out = {k: e[k] for k in ('from', 'abil', 'index', 'kind', 'time') if e.get(k) is not None}
    for k in ('cooldown', 'charge', 'requirements', 'button', 'count'):
        if e.get(k):
            out[k] = e[k]
    if e.get('costDelta'):
        out['costDelta'] = e['costDelta']
    out['units'] = sorted(set(e['units']), key=e['units'].index)
    if len(e['units']) > 1 and len(set(e['units'])) == 1:
        out['count'] = len(e['units'])
    return out


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
        heroes[hero] = {'team': r['team'], 'category': r.get('category'), 'roleId': r['id'],
                        'heroUnits': hu, 'unitIds': order,
                        'edges': [edge_out(e) for e in edges]}
        for uid in order:
            if uid in units:
                if hero not in units[uid]['owners']:
                    units[uid]['owners'].append(hero)
                continue
            info = U.unit_stats(gi, uid)
            info['id'] = uid
            edges_in = [e for e in edges if uid in e['units']]
            profiles = [U.weapon_profile(gi, w) for w in info['weapons']]
            profiles = [p for p in profiles if p['components'] or p['unresolved']]
            weapons_total += len(profiles)
            unresolved_total += sum(1 for p in profiles if p['unresolved'])
            groups = upgrade_groups(info, profiles, ui, gs_btn)
            curves, maxed, options = build_curves(info, profiles, groups)
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
