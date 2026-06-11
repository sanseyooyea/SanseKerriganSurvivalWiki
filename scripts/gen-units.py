"""
Refresh data/units.json stats from the rebuilt catalog.json + GameStrings.
PRESERVES the curated membership (which id sits in troops/buildings/economy);
only refreshes nameZh + numeric stats. Members absent from the catalog
(morph/base-game forms like Mothership, *Burrowed) keep their old values and are logged.

Stat sources (verified against the old units.json):
  nameZh        GameStrings Unit/Name/<id>   (fallback: old value)
  hp            Unit.LifeMax
  shield        Unit.ShieldsMax              (omit if 0)
  armor         Unit.LifeArmor               (omit if 0)
  speed         Unit.Speed                   (omit if 0 — buildings)
  damage/attackSpeed/range  Unit.WeaponArray.Link -> Weapon -> DisplayEffect -> CEffectDamage.Amount
"""
import json, re

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
UNITS = WIKI + r'\data\units.json'
CATALOG = WIKI + r'\data\catalog.json'

import mpyq
MAP_PATH = r'D:\starcraft2\凯瑞甘生存2 最新版.SC2Map'

cat = json.load(open(CATALOG, encoding='utf-8'))
CU, CW, CE = cat['Unit'], cat['Weapon'], cat['Effect']
old_units = json.load(open(UNITS, encoding='utf-8'))

# GameStrings Unit/Name lookup
gs = mpyq.MPQArchive(MAP_PATH).read_file(
    r'zhCN.SC2Data\LocalizedData\GameStrings.txt').decode('utf-8-sig', 'replace')
NAME = {}
for line in gs.split('\n'):
    if line.startswith('Unit/Name/'):
        k, _, v = line.partition('=')
        NAME[k.strip()[10:]] = v.strip()


def num(s):
    try:
        f = float(s)
        return int(f) if f == int(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def effect_amount(eid, depth=0, seen=None):
    """Follow an effect chain to the first CEffectDamage Amount."""
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


def weapon_stats(uid):
    """damage / attackSpeed / range from the unit's primary weapon link."""
    u = CU.get(uid, {})
    wid = u.get('WeaponArray.Link') or u.get('WeaponArray[0].Link') or u.get('WeaponArray')
    if not wid or wid not in CW:
        return {}
    w = CW[wid]
    out = {}
    dmg = effect_amount(w.get('DisplayEffect') or w.get('Effect'))
    if dmg:
        out['damage'] = dmg
    period = num(w.get('Period'))
    if period:
        out['attackSpeed'] = period
    rng = num(w.get('Range'))
    if rng is not None:
        out['range'] = rng
    return out


def build_stats(uid):
    """Full stat dict for one unit id from catalog; empty if not in catalog."""
    u = CU.get(uid)
    if not u:
        return None
    s = {}
    hp = num(u.get('LifeMax'))
    if hp:
        s['hp'] = hp
    sh = num(u.get('ShieldsMax'))
    if sh:
        s['shield'] = sh
    ar = num(u.get('LifeArmor'))
    if ar:
        s['armor'] = ar
    sp = num(u.get('Speed'))
    if sp:
        s['speed'] = sp
    s.update(weapon_stats(uid))
    return s


# Rebuild: preserve membership + order, refresh name/stats from catalog.
# Per-field fallback: a stat the catalog can't resolve (e.g. base-game weapons
# like PhaseDisruptors/Immortal/SiegeTank not defined in the map) keeps its old
# value — refresh is strictly additive, never drops known-good data.
STAT_FIELDS = ('hp', 'shield', 'armor', 'speed', 'damage', 'attackSpeed', 'range')
result = {}
kept_old = []      # members entirely absent from catalog (kept verbatim)
fallback_fields = []   # individual stats that fell back to old value
refreshed = 0
for hero, sections in old_units.items():
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
                new_list.append(old_m)          # keep old values verbatim
                continue
            entry = {'id': uid, 'nameZh': NAME.get(uid, old_m.get('nameZh', uid))}
            for f in STAT_FIELDS:
                if f in stats:
                    entry[f] = stats[f]
                elif f in old_m:                # catalog couldn't resolve -> keep old
                    entry[f] = old_m[f]
                    fallback_fields.append(f'{uid}.{f}={old_m[f]}')
            new_list.append(entry)
            refreshed += 1
        new_hero[sec] = new_list
    result[hero] = new_hero

with open(UNITS, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'Refreshed {refreshed} members across {len(result)} heroes')
print(f'Kept verbatim (not in catalog): {len(kept_old)}')
for k in kept_old:
    print(f'  KEPT {k}')
print(f'Per-field fallback to old value (base-game data): {len(fallback_fields)}')
for k in fallback_fields:
    print(f'  FALLBACK {k}')
