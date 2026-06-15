"""
Build data/veterancy.json from data/seed/veterancy.seed.json.

The str/agi/int growth values are curated game-design data: the map's
CBehaviorVeterancy per-level Points DISAGREE with the displayed values (e.g. the
map gives Artanis str3/agi1/int1 while the wiki shows str4/agi2/int1), so the seed
is authoritative and copied verbatim. We still cross-check that each seed veterancy
id exists in the map and report any that no longer do (signals a map rename).
"""
import json
import os
import re

import lib_map as L

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
SEED = os.path.join(DATA, 'seed', 'veterancy.seed.json')
ROLES = os.path.join(DATA, 'seed', 'roles.seed.json')
OUT = os.path.join(DATA, 'veterancy.json')

seed = json.load(open(SEED, encoding='utf-8'))

archive = L.open_map()
catalog = L.build_catalog(archive)
BEH = catalog.get('Behavior', {})

missing = [vid for vid in seed if vid not in BEH]

# 残留误标检查：seed 把某英雄列为有等级成长，但其英雄单位实际没挂任何 Veterancy 行为，
# 多半是地图里的孤立残留定义（如灵魂 SpiritVeterancy，2026-06-16 已移除）。
# 注意：多形态英雄主单位名可能匹配不到（unit=None），那类是脚本局限而非真误标，仅作提示。
HERO_UNIT_OVERRIDE = {'Jinara': 'JinaraJinara', 'Skitter': 'SkitterSkitter'}
roles = json.load(open(ROLES, encoding='utf-8'))
name_to_unit = {}
for r in roles:
    name_to_unit[r['nameEn']] = HERO_UNIT_OVERRIDE.get(r['nameEn']) or (r.get('heroUnits') or [None])[0]

allx = '\n'.join(archive.read_file(f).decode('utf-8', 'ignore') for f in L.gamedata_xml_files(archive))
unit_behs = {}
for um in re.finditer(r'<CUnit id="([^"]+)">(.*?)</CUnit>', allx, re.S):
    unit_behs[um.group(1)] = re.findall(r'<BehaviorArray Link="([^"]+)"', um.group(2))
vet_behaviors = set(re.findall(r'<CBehaviorVeterancy id="([^"]+)"', allx))

orphan = []  # (hero, unit) where unit found but no veterancy behavior attached
for vinfo in seed.values():
    for hero in vinfo.get('heroes', []):
        uid = name_to_unit.get(hero)
        if uid and uid in unit_behs:
            behs = unit_behs[uid]
            if not any(b in vet_behaviors for b in behs):
                orphan.append((hero, uid))

json.dump(seed, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f'Wrote {len(seed)} veterancy entries to veterancy.json')
if missing:
    print(f'WARNING: {len(missing)} seed veterancy ids not found in map '
          f'(possible rename): {missing}')
else:
    print('All seed veterancy ids present in map.')
if orphan:
    print(f'WARNING: {len(orphan)} hero(es) listed with growth but unit has NO veterancy '
          f'behavior attached (likely no level system — verify, e.g. Spirit was removed): {orphan}')
