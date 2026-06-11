"""
One-time migration: build data/seed/*.json from the CURRENT wiki data (the
source of truth = "以现有数据为准") plus BankEditor's curated base-stat table
and description GameString keys.

After this runs, data/seed/ is hand-maintained and BankEditor is no longer used.

Produces:
  data/seed/roles.seed.json      per-hero curated fields (NOT the map-derived stats)
  data/seed/units.seed.json      per-hero troops/buildings/economy member id lists
  data/seed/veterancy.seed.json  veterancy str/agi/int (curated — disagree with map)

Run once from the Wiki root.
"""
import json
import os

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
SEED = os.path.join(DATA, 'seed')
os.makedirs(SEED, exist_ok=True)

# --- Curated base stats (hp/speed/armor/energy) from BankEditor extract_roles.py ---
# These are game-design values, NOT in the map cleanly; "以现有数据为准".
BASE_STATS = {
    0: (99999, 3.0, 2, 100), 1: (300, 3.25, 0, None), 2: (150, 3.25, 0, 100),
    3: (150, 3.0, 0, None), 4: (100, 5.0, 0, None), 5: (150, 3.0, 0, None),
    6: (80, 4.4, 0, 100), 7: (350, 3.25, 2, None), 8: (300, 3.0, 3, 100),
    9: (99999, 0.55, 0, 100), 10: (250, 3.5, 0, None), 11: (300, 3.25, 1, 100),
    12: (200, 2.75, 0, 150), 13: (99999, 3.24, 2, 100), 14: (300, 3.0, 0, None),
    15: (None, None, None, None), 16: (99999, 3.0, 2, 100), 17: (300, 3.25, 2, None),
    18: (500, 3.0, 3, 100), 19: (150, 2.75, 1, 150), 20: (99999, 1.6, 0, 100),
    21: (400, 3.25, 2, None), 22: (200, 3.0, 0, 100), 23: (200, 5.0, 0, 100),
    24: (425, 3.35, 0, 200), 25: (100, 4.0, 0, 100), 26: (200, 3.0, 1, 150),
    27: (99999, 3.0, 2, 100), 28: (99999, None, 1, 150), 29: (200, 3.0, 0, 100),
    30: (99999, 1.25, 0, 100), 31: (350, 3.0, 2, 100), 32: (99999, 0.5, 0, 200),
    33: (99999, 3.0, 2, 100), 34: (99999, 3.0, 5, 100), 35: (None, 2.8, None, None),
    36: (200, 2.75, 0, 100), 37: (400, 3.0, 0, None), 38: (400, 3.15, 3, 100),
    39: (400, 3.25, 1, None), 40: (500, 3.0, 1, None), 41: (125, 2.75, None, None),
    42: (200, 4.5, 0, None), 43: (125, 10.0, None, None), 44: (300, 3.0, 1, 150),
    45: (300, 3.25, None, None), 46: (None, None, None, None),
    47: (99999, 1.1, None, None), 48: (None, None, None, None),
}

# Description GameString keys per role id (from BankEditor extract_roles.py).
# Most are Param/Value/<hash>; a few are special.
DESC_KEYS = {
    0: '7A3A7726', 1: 'C5657A62', 2: '97F0E1EA', 3: '555EDCA7', 4: '1EBAC525',
    5: '88A6A53C', 6: 'D7FA74B7', 7: '6EBF4638', 8: '0E4AAF85', 9: 'E79D191C',
    10: 'B23E4F70', 11: '2657317C', 12: '6DC024B4', 13: '38FB48A1', 14: 'AAD107B7',
    15: '5847FD27', 16: '9AAC2A76', 17: '67FE7ED5', 18: 'BAD09F82', 19: '2D004A1B',
    20: '9971FD7A', 21: '62B1CB41', 22: '8D3B5041', 23: 'AD9593D4', 24: '150638D9',
    25: '27CDEDD0', 26: '4B2F243A', 27: '39661C87', 28: 'AB05F64A', 29: '2125E5BB',
    30: 'D7884056', 31: 'DF92E31B', 32: 'EA4C7050', 33: '4A4BF815', 34: '0588A176',
    35: 'DAD44D63', 36: '16A6D9FF', 37: 'E8C0FA48', 38: 'BCCB7E35', 39: '0BD195B8',
    40: '46A4FD74', 41: '9CCCF909', 42: 'AB960114', 43: '30907C8A', 44: 'DFE56009',
}
DESC_KEYS_SPECIAL = {
    45: ['22EB40C3', 'B6A7764C'],
    46: ['9757CB02', '2AE15D6F'],
}
DESC_KEYS_DOCSTR = {47: 'DOCSTR_RoachingtonDesc', 48: 'DOCSTR_SkitterDesc'}


def desc_spec(idx):
    """Return how to resolve this role's description from GameStrings, as data
    (so build_roles can reproduce it without BankEditor)."""
    if idx in DESC_KEYS:
        return {'type': 'param', 'keys': [DESC_KEYS[idx]]}
    if idx in DESC_KEYS_SPECIAL:
        return {'type': 'param', 'keys': DESC_KEYS_SPECIAL[idx]}
    if idx in DESC_KEYS_DOCSTR:
        return {'type': 'docstr', 'keys': [DESC_KEYS_DOCSTR[idx]]}
    return {'type': 'param', 'keys': []}


# --- roles.seed.json: curated fields only (map-derived stats excluded) ---
roles = json.load(open(os.path.join(DATA, 'roles.json'), encoding='utf-8'))
role_seed = []
for r in roles:
    idx = r['id']
    hp, speed, armor, energy = BASE_STATS.get(idx, (None, None, None, None))
    role_seed.append({
        'id': idx,
        'nameEn': r['nameEn'],
        'nameZh': r['nameZh'],
        'category': r['category'],
        'team': r['team'],
        'heroUnits': r.get('heroUnits', []),
        'unitIcon': r.get('unitIcon', ''),
        'portrait': r.get('portrait', ''),
        'descKeys': desc_spec(idx),
        'baseStats': {'hp': hp, 'speed': speed, 'armor': armor, 'energy': energy},
        'abilities': r.get('abilities', []),
    })
json.dump(role_seed, open(os.path.join(SEED, 'roles.seed.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print(f'roles.seed.json: {len(role_seed)} roles')

# --- units.seed.json: membership + current values (kept as fallback) ---
# Keeps the full member dict (id/nameZh/stats). build_units refreshes everything
# resolvable from the map and falls back to these seed values for base-game units
# (Immortal, SiegeTank, etc.) whose weapons aren't defined in the map.
units = json.load(open(os.path.join(DATA, 'units.json'), encoding='utf-8'))
units_seed = {}
member_count = 0
for hero, sections in units.items():
    units_seed[hero] = {}
    for sec in ('troops', 'buildings', 'economy'):
        if sec in sections:
            units_seed[hero][sec] = sections[sec]
            member_count += len(sections[sec])
json.dump(units_seed, open(os.path.join(SEED, 'units.seed.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print(f'units.seed.json: {len(units_seed)} heroes, {member_count} members')

# --- veterancy.seed.json: verbatim (curated values, disagree with map) ---
vet = json.load(open(os.path.join(DATA, 'veterancy.json'), encoding='utf-8'))
json.dump(vet, open(os.path.join(SEED, 'veterancy.seed.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print(f'veterancy.seed.json: {len(vet)} entries')

print('Migration done. data/seed/ is now the hand-maintained source.')
