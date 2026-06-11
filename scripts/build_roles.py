"""
Build data/roles.json from data/seed/roles.seed.json + the map.

seed -> id/nameEn/nameZh/category/team/heroUnits/unitIcon/portrait/baseStats/abilities
map  -> description (GameStrings) + combat stats (damage/attackSpeed/attackCount/
        range) + energyRegen from the hero unit's primary weapon / EnergyRegenRate.

Base stats (hp/speed/armor/energy) come from the seed ("以现有数据为准"). Where the
map also defines a base stat for the hero unit, we report the diff but keep the seed
value. Caster heroes whose hero unit has no weapon get no combat fields (correct).
"""
import json
import os

import lib_map as L

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
SEED = os.path.join(DATA, 'seed', 'roles.seed.json')
OUT = os.path.join(DATA, 'roles.json')

# Hero units whose primary unit id != heroUnits[0] (matches old enrich-role-stats).
HERO_UNIT_OVERRIDE = {'Jinara': 'JinaraJinara', 'Skitter': 'SkitterSkitter'}

archive = L.open_map()
catalog = L.build_catalog(archive)
CU, CW, CE = catalog['Unit'], catalog['Weapon'], catalog['Effect']

# GameStrings: Param/Value/<hash> for descriptions, plus full map for DOCSTR_*.
gs_all = L.game_strings(archive)


def resolve_desc(spec):
    keys = spec.get('keys', [])
    if spec.get('type') == 'docstr':
        return ''.join(gs_all.get(k, '') for k in keys)
    # param
    return ''.join(gs_all.get(f'Param/Value/{k}', '') for k in keys)


def hero_unit_id(role):
    over = HERO_UNIT_OVERRIDE.get(role['nameEn'])
    if over:
        return over
    hu = role.get('heroUnits', [])
    return hu[0] if hu else None


seed = json.load(open(SEED, encoding='utf-8'))
out = []
base_diffs = []   # (role, field, seed_val, map_val)
no_unit = []

for role in seed:
    base = role['baseStats']
    stats = {
        'hp': base['hp'],
        'speed': base['speed'],
        'armor': base['armor'],
        'energy': base['energy'],
    }
    uid = hero_unit_id(role)
    if uid and uid in CU:
        u = CU[uid]
        # report base-stat disagreements (map vs seed) but KEEP seed
        for f, mapkey in (('hp', 'LifeMax'), ('speed', 'Speed'), ('armor', 'LifeArmor')):
            mv = L.num(u.get(mapkey))
            if mv is not None and base[f] is not None and mv != base[f]:
                base_diffs.append(f"{role['nameEn']}.{f}: seed={base[f]} map={mv}")
        # combat stats
        for k, v in L.weapon_stats(CU, CW, CE, uid).items():
            stats[k] = v
        # energy regen
        regen = L.num(u.get('EnergyRegenRate'))
        if regen is not None:
            stats['energyRegen'] = regen
    elif uid:
        no_unit.append(f"{role['nameEn']} (uid {uid} not in catalog)")
    else:
        no_unit.append(f"{role['nameEn']} (no hero unit)")

    out.append({
        'id': role['id'],
        'nameEn': role['nameEn'],
        'nameZh': role['nameZh'],
        'heroUnits': role['heroUnits'],
        'category': role['category'],
        'team': role['team'],
        'unitIcon': role['unitIcon'],
        'portrait': role['portrait'],
        'description': resolve_desc(role['descKeys']),
        'stats': stats,
        'abilities': role['abilities'],
    })

json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f'Wrote {len(out)} roles to roles.json')
if no_unit:
    print(f'No combat stats (caster / no unit): {len(no_unit)}')
    for x in no_unit:
        print(f'  {x}')
if base_diffs:
    print(f'Base-stat diffs (kept seed value): {len(base_diffs)}')
    for x in base_diffs:
        print(f'  {x}')
