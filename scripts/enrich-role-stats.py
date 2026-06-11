"""
Enrich data/roles.json with combat stats + energy regen from catalog.json.
Runs AFTER sync-data.py (which overwrites roles.json from BankEditor's 4-field
version). BankEditor's ClassData.kt has no combat stats, so these wiki-only
fields must be re-applied here as the final pipeline step.

Sources (from the rebuilt catalog.json, i.e. the current map):
  damage/attackSpeed/attackCount/range  hero unit -> WeaponArray.Link -> Weapon
  energyRegen                           hero unit EnergyRegenRate
Caster heroes whose hero unit has no weapon simply get no combat fields
(the UI hides empty stats via v-if), which is correct — no fake auto-attack.
"""
import json

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
ROLES = WIKI + r'\data\roles.json'
CATALOG = WIKI + r'\data\catalog.json'

# Hero units that don't match heroUnits[0] in roles.json
HERO_UNIT_OVERRIDE = {'Jinara': 'JinaraJinara', 'Skitter': 'SkitterSkitter'}

cat = json.load(open(CATALOG, encoding='utf-8'))
CU, CW, CE = cat['Unit'], cat['Weapon'], cat['Effect']
roles = json.load(open(ROLES, encoding='utf-8'))


def num(s):
    try:
        f = float(s)
        return int(f) if f == int(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def effect_amount(eid, depth=0, seen=None):
    seen = seen or set()
    if not eid or depth > 5 or eid in seen:
        return None
    seen.add(eid)
    e = CE.get(eid)
    if not e:
        return None
    if 'Amount' in e:
        return num(e['Amount'])
    for k, v in e.items():
        if 'Effect' in k and isinstance(v, str) and v in CE:
            r = effect_amount(v, depth + 1, seen)
            if r is not None:
                return r
    return None


def hero_unit_id(role):
    over = HERO_UNIT_OVERRIDE.get(role['nameEn'])
    if over:
        return over
    hu = role.get('heroUnits', [])
    return hu[0] if hu else None


def combat_stats(uid):
    """damage/attackSpeed/attackCount/range from the hero unit's primary weapon."""
    u = CU.get(uid, {})
    wid = u.get('WeaponArray.Link') or u.get('WeaponArray[0].Link') or u.get('WeaponArray')
    out = {}
    if wid and wid in CW:
        w = CW[wid]
        dmg = effect_amount(w.get('DisplayEffect') or w.get('Effect'))
        if dmg is not None:
            out['damage'] = dmg
        asp = num(w.get('Period'))
        if asp is not None:
            out['attackSpeed'] = asp
        cnt = num(w.get('DisplayAttackCount'))
        if cnt is not None:
            out['attackCount'] = cnt
        rng = num(w.get('Range'))
        if rng is not None:
            out['range'] = rng
    return out


enriched = 0
no_unit = []
for role in roles:
    uid = hero_unit_id(role)
    stats = role.setdefault('stats', {})
    if not uid or uid not in CU:
        no_unit.append(role['nameEn'])
        continue
    u = CU[uid]
    # combat stats
    for k, v in combat_stats(uid).items():
        stats[k] = v
    # energy regen
    regen = num(u.get('EnergyRegenRate'))
    if regen is not None:
        stats['energyRegen'] = regen
    enriched += 1

with open(ROLES, 'w', encoding='utf-8') as f:
    json.dump(roles, f, ensure_ascii=False, indent=2)

print(f'Enriched {enriched}/{len(roles)} roles with combat stats + energyRegen')
if no_unit:
    print(f'No resolvable hero unit (combat stats skipped): {no_unit}')
