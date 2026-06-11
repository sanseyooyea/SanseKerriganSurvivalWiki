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

import lib_map as L

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
SEED = os.path.join(DATA, 'seed', 'veterancy.seed.json')
OUT = os.path.join(DATA, 'veterancy.json')

seed = json.load(open(SEED, encoding='utf-8'))

archive = L.open_map()
catalog = L.build_catalog(archive)
BEH = catalog.get('Behavior', {})

missing = [vid for vid in seed if vid not in BEH]

json.dump(seed, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f'Wrote {len(seed)} veterancy entries to veterancy.json')
if missing:
    print(f'WARNING: {len(missing)} seed veterancy ids not found in map '
          f'(possible rename): {missing}')
else:
    print('All seed veterancy ids present in map.')
