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

# 升级可改动的字段 → snapshot 键
UNIT_FIELDS = {'LifeMax': 'hp', 'ShieldsMax': 'shield', 'LifeArmor': 'armor',
               'ShieldArmor': 'shieldArmor', 'Speed': 'speed', 'Sight': 'sight',
               'LifeRegenRate': 'hpRegen', 'ShieldRegenRate': 'shieldRegen'}
WEAPON_FIELDS = {'Period': 'period', 'Range': 'range'}


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


def _unit_icons(gi, btn_icons, heroes):
    """单位图标优先级：生产它的按钮 face（训练/建造按钮，游戏里真正的单位图）
    → 与单位同名的 CButton → 无。找不到就留空（前端显示占位符，不裂图）。"""
    by_face = {}
    for h in heroes.values():
        for e in h['edges']:
            face = e.get('button')
            if not face:
                continue
            png = btn_icons.get(face)
            if not png:
                continue
            for u in e['units']:
                by_face.setdefault(u, png)
    out = dict(by_face)
    for uid in [k[1] for k, _ in gi.entries.items() if k[0] == 'Unit']:
        if uid in out:
            continue
        for cand in (uid, f'{uid}Icon'):
            if cand in btn_icons:
                out[uid] = btn_icons[cand]
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
    return cur


def snapshot_dps(profiles, comp_override, weapon_override):
    """DPS per standard target for each weapon after applying overrides."""
    out = []
    for p in profiles:
        q = dict(p)
        wo = weapon_override.get(p['id'], {})
        if 'Period' in wo:
            q['period'] = wo['Period']
        if 'Range' in wo:
            q['range'] = wo['Range']
        comps = []
        for c in p['components']:
            c = dict(c, bonus=dict(c['bonus']))
            eo = comp_override.get(c['effect'], {})
            if 'Amount' in eo:
                c['amount'] = eo['Amount']
            for k, v in eo.items():
                m = re.match(r'AttributeBonus\[(\w+)\]', k)
                if m:
                    c['bonus'][m.group(1)] = v
            comps.append(c)
        q['components'] = comps
        out.append({'id': p['id'], 'range': q['range'], 'period': q['period'],
                    **{k: dict(zip(('perAttack', 'dps'), U.damage_vs(q, t)))
                       for k, t in U.TARGETS.items()}})
    return out


def upgrade_curve(info, profiles, ui, gs_name):
    """Per-family level-by-level deltas + a cumulative 'all researched to N' curve."""
    uid = info['id']
    keys = {('Unit', uid)}
    for p in profiles:
        keys.add(('Weapon', p['id']))
        for e in p['effects']:
            keys.add(('Effect', e))
    fams = ui.relevant(keys)
    # base values
    base = {('Unit', uid, f): info['stats'][k] for f, k in UNIT_FIELDS.items()}
    for p in profiles:
        base[('Weapon', p['id'], 'Period')] = p['period'] or 0
        base[('Weapon', p['id'], 'Range')] = p['range'] or 0
        for c in p['components']:
            base[('Effect', c['effect'], 'Amount')] = c['amount']
            for a, v in c['bonus'].items():
                base[('Effect', c['effect'], f'AttributeBonus[{a}]')] = v
    groups = []
    for fam in fams:
        lvls = []
        for i, lv in enumerate(fam['levels'], 1):
            effs = [x for x in ui.upgrades[lv['upgrade']]['effects'] if (x[0], x[1]) in keys]
            slot = lv['slot'] or {}
            lvls.append({
                'level': i,
                'upgrade': lv['upgrade'],
                'minerals': slot.get('minerals', 0),
                'gas': slot.get('gas', 0),
                'time': slot.get('time', 0),
                'researchedBy': slot.get('ability'),
                'effects': [{'ref': f'{c},{t},{f}', 'op': op, 'value': v} for c, t, f, op, v in effs],
            })
        if not any(l['effects'] for l in lvls):
            continue
        face = (fam['levels'][0]['slot'] or {}).get('buttonFace')
        name = gs_name.get(face) if face else None
        name = re.sub(r'\s*(?:等级|等級)\s*\d+\s*$', '', name or '').strip() or fam['family']
        groups.append({'family': fam['family'], 'nameZh': name,
                       'researchable': fam['researchable'], 'levels': lvls})

    # cumulative curve: step k = every researchable family at min(k, its max level)
    research_groups = [g for g in groups if g['researchable']] or groups
    max_lv = max((len(g['levels']) for g in research_groups), default=0)
    curve = []
    for k in range(0, max_lv + 1):
        vals = dict(base)
        cost = {'minerals': 0, 'gas': 0}
        for g in research_groups:
            for lv in g['levels'][:k]:
                cost['minerals'] += lv['minerals']
                cost['gas'] += lv['gas']
                for ef in lv['effects']:
                    c, t, f = ef['ref'].split(',', 2)
                    key = (c, t, f)
                    b = base.get(key, 0)
                    vals[key] = round(apply(ef['op'], b, vals.get(key, b), ef['value']), 4)
        unit_vals = {UNIT_FIELDS[f]: v for (c, t, f), v in vals.items()
                     if c == 'Unit' and t == uid and f in UNIT_FIELDS}
        comp_o, weap_o = {}, {}
        for (c, t, f), v in vals.items():
            if c == 'Effect':
                comp_o.setdefault(t, {})[f] = v
            elif c == 'Weapon':
                weap_o.setdefault(t, {})[f] = v
        curve.append({'level': k, 'cost': cost,
                      'hp': unit_vals.get('hp', info['stats']['hp']),
                      'shield': unit_vals.get('shield', info['stats']['shield']),
                      'armor': unit_vals.get('armor', info['stats']['armor']),
                      'weapons': snapshot_dps(profiles, comp_o, weap_o)})
    return groups, curve


def derived(info, curve0, curve_max):
    """0 级 / 满级 两套派生指标。DPS 按标准靶分别求和（轻甲/重甲/凯瑞甘）。"""
    cost = info['cost']
    res = cost['minerals'] + cost['gas']
    tkeys = list(U.TARGETS)

    def dps(c, tkey):
        return round(sum((w[tkey]['dps'] or 0) for w in c['weapons']), 2) if c else 0

    def ehp(c):
        # 粗略有效血量：护甲每点按抵消一次 10 点打击的 10% 计（仅用于横向比较）
        if not c:
            return 0
        return round((c['hp'] + c['shield']) * (1 + 0.1 * max(0, c['armor'])), 1)

    d = {}
    for tag, c in (('', curve0), ('Max', curve_max)):
        for t in tkeys:
            d[f'dps{t[0].upper()}{t[1:]}{tag}'] = dps(c, t)
        d[f'ehp{tag}'] = ehp(c)
    d['targets'] = tkeys
    main = 'dpsArmored'
    if res:
        d['dpsPer100'] = round(max(d.get('dpsLight', 0), d.get('dpsArmored', 0)) * 100 / res, 2)
        d['ehpPer100'] = round(d['ehp'] * 100 / res, 1)
    if cost['food']:
        d['dpsPerFood'] = round(max(d.get('dpsLight', 0), d.get('dpsArmored', 0)) / cost['food'], 2)
    if curve_max:
        d['fullUpgradeCost'] = curve_max['cost']
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
            groups, curve = upgrade_curve(info, profiles, ui, gs_btn)
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
                'curve': curve,
                'derived': derived(info, curve[0] if curve else None, curve[-1] if len(curve) > 1 else None),
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
    for uid, icon in {**hero_icons, **unit_icons}.items():
        if uid in units:
            units[uid]['icon'] = icon

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
