"""
Build data/units.json from data/seed/units.seed.json + the map.

The seed defines membership (which unit id sits in each hero's troops/buildings/
economy) AND carries the previous values as a fallback. For every member we refresh
nameZh + stats from the map catalog; members the map can't resolve (base-game morph
forms like Mothership, *Burrowed) keep their seed values verbatim. Per individual
stat, if the catalog can't resolve it the old seed value is kept (additive refresh).
"""
import json
import os

import lib_map as L

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
SEED = os.path.join(DATA, 'seed', 'units.seed.json')
OUT = os.path.join(DATA, 'units.json')

STAT_FIELDS = ('hp', 'shield', 'armor', 'speed', 'damage', 'attackSpeed', 'attackCount', 'range')

archive = L.open_map()
catalog = L.build_catalog(archive)
CU, CW, CE = catalog['Unit'], catalog['Weapon'], catalog['Effect']
NAME = L.game_strings(archive, 'Unit/Name/')


def build_stats(uid):
    """Full stat dict for one unit id from catalog; None if not in catalog."""
    u = CU.get(uid)
    if not u:
        return None
    s = {}
    hp = L.num(u.get('LifeMax'))
    if hp:
        s['hp'] = hp
    sh = L.num(u.get('ShieldsMax'))
    if sh:
        s['shield'] = sh
    ar = L.num(u.get('LifeArmor'))
    if ar:
        s['armor'] = ar
    sp = L.num(u.get('Speed'))
    if sp:
        s['speed'] = sp
    ws = L.weapon_stats(CU, CW, CE, uid)
    # damage/attackSpeed/range 直采；attackCount 仅当 >1（多连击单位如攻城塔）才带，
    # 避免给单发单位添冗余字段。
    for k in ('damage', 'attackSpeed', 'range'):
        if k in ws:
            s[k] = ws[k]
    if ws.get('attackCount', 1) and ws.get('attackCount', 1) > 1:
        s['attackCount'] = ws['attackCount']
    return s


seed = json.load(open(SEED, encoding='utf-8'))
result = {}
kept_old = []
fallback_fields = []
refreshed = 0

for hero, sections in seed.items():
    new_hero = {}
    for sec in ('troops', 'buildings', 'economy'):
        if sec not in sections:
            continue
        new_list = []
        for old_m in sections[sec]:
            uid = old_m['id']
            stats = build_stats(uid)
            if stats is None:
                kept_old.append(f'{hero}/{sec}/{uid}')
                new_list.append(old_m)
                continue
            entry = {'id': uid, 'nameZh': NAME.get(uid, old_m.get('nameZh', uid))}
            for f in STAT_FIELDS:
                if f in stats:
                    entry[f] = stats[f]
                elif f in old_m:
                    entry[f] = old_m[f]
                    fallback_fields.append(f'{uid}.{f}={old_m[f]}')
            new_list.append(entry)
            refreshed += 1
        new_hero[sec] = new_list
    result[hero] = new_hero

json.dump(result, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f'Refreshed {refreshed} members across {len(result)} heroes')
print(f'Kept verbatim (not in catalog): {len(kept_old)}')
for k in kept_old:
    print(f'  KEPT {k}')
print(f'Per-field fallback to seed value (base-game data): {len(fallback_fields)}')
for k in fallback_fields:
    print(f'  FALLBACK {k}')
