"""
Shared map-reading layer for the Wiki data pipeline (no BankEditor dependency).

Everything that reads the KS2 map MPQ goes through here:
  - open_map()                  open the MPQ archive
  - game_strings(prefix=...)    parse zhCN GameStrings into a dict (optionally filtered)
  - build_catalog()             flatten all GameData XML into {Type:{Id:{field:val}}}
                                (parent inheritance, BOM strip, & escaping)
  - num()                       safe numeric coercion (int when whole, else round 4)
  - effect_amount()             follow an effect chain to the first CEffectDamage Amount
  - weapon_stats()              damage/attackSpeed/attackCount/range from a unit's weapon

The catalog is a build-time intermediate (nothing at runtime reads it). Callers can
keep it in memory; build_catalog() does not write to disk.
"""
import re
import xml.etree.ElementTree as ET

import mpyq

MAP_PATH = r'D:\starcraft2\凯瑞甘生存2 最新版.SC2Map'
GAMESTRINGS = r'zhCN.SC2Data\LocalizedData\GameStrings.txt'

TYPE_MAP = {
    'CUnit': 'Unit', 'CAbil': 'Abil', 'CEffect': 'Effect', 'CBehavior': 'Behavior',
    'CWeapon': 'Weapon', 'CUpgrade': 'Upgrade', 'CValidator': 'Validator',
}


def open_map(path=MAP_PATH):
    return mpyq.MPQArchive(path)


def _listfile(archive):
    return archive.read_file('(listfile)').decode('utf-8', 'replace').split('\r\n')


def gamedata_xml_files(archive):
    return [f for f in _listfile(archive)
            if f.endswith('.xml') and 'GameData' in f]


def game_strings(archive, prefix=None):
    """Parse GameStrings.txt into {key: value}. If prefix given, strip it and
    only keep matching keys (e.g. prefix='Unit/Name/' -> {'KerriganKerrigan': '凯瑞甘'})."""
    gs = archive.read_file(GAMESTRINGS).decode('utf-8-sig', 'replace')
    out = {}
    for line in gs.split('\n'):
        if '=' not in line:
            continue
        key, _, val = line.partition('=')
        if prefix is None:
            out[key.strip()] = val.strip()
        elif key.startswith(prefix):
            out[key[len(prefix):].strip()] = val.strip()
    return out


def _catalog_type(tag):
    for prefix, name in TYPE_MAP.items():
        if tag.startswith(prefix):
            return name
    return tag  # keep raw C-prefixed type


def _collect_fields(elem, prefix, out):
    """Index attributes + child value-bearing elements into `out` (flat dict)."""
    for attr, val in elem.attrib.items():
        if attr in ('id', 'parent', 'default'):
            continue
        key = attr if not prefix else f'{prefix}.{attr}'
        out[key] = val
    counts = {}
    for child in elem:
        tag = child.tag
        idx = counts.get(tag, 0)
        counts[tag] = idx + 1
        base = tag if not prefix else f'{prefix}.{tag}'
        indexed = f'{base}[{idx}]'
        named = child.get('index')
        named_base = f'{base}[{named}]' if named else None
        val = child.get('value')
        if val is not None:
            out[base] = val
            out[indexed] = val
            if named_base:
                out[named_base] = val
        _collect_fields(child, base, out)


def build_catalog(archive):
    """Flatten all GameData XML into {CatalogType: {EntryId: {field: 'value'}}}.
    Resolves parent= inheritance (child overrides parent). BOM-stripped, & escaped."""
    raw = {}        # (cat_type, id) -> flat field dict
    parent_of = {}  # (cat_type, id) -> parent id (same cat_type)

    for xf in gamedata_xml_files(archive):
        data = archive.read_file(xf)
        if not data or len(data) < 20:
            continue
        text = data.decode('utf-8', 'replace').lstrip('﻿')
        if not text.lstrip().startswith('<?xml'):
            text = '<?xml version="1.0"?><Root>' + text + '</Root>'
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            try:
                text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', text)
                root = ET.fromstring(text)
            except ET.ParseError:
                continue
        for elem in root.iter():
            eid = elem.get('id')
            if not eid or not elem.tag.startswith('C'):
                continue
            ctype = _catalog_type(elem.tag)
            fields = {}
            _collect_fields(elem, '', fields)
            k = (ctype, eid)
            if k in raw:
                raw[k].update(fields)
            else:
                raw[k] = fields
            p = elem.get('parent')
            if p:
                parent_of[k] = p

    def resolve(k, seen=None):
        seen = seen or set()
        if k in seen:
            return dict(raw.get(k, {}))
        seen.add(k)
        own = raw.get(k, {})
        pid = parent_of.get(k)
        if not pid:
            return dict(own)
        pk = (k[0], pid)
        merged = resolve(pk, seen) if pk in raw else {}
        merged.update(own)
        merged['CopySource'] = pid
        return merged

    catalog = {}
    for (ctype, eid) in raw:
        if eid.startswith('_'):
            continue
        catalog.setdefault(ctype, {})[eid] = resolve((ctype, eid))
    return catalog


def num(s):
    """Safe numeric coercion: int when whole, else round to 4dp, None on failure."""
    try:
        f = float(s)
        return int(f) if f == int(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def effect_amount(CE, eid, depth=0, seen=None):
    """Follow an effect chain to the first CEffectDamage Amount."""
    seen = seen if seen is not None else set()
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
            r = effect_amount(CE, v, depth + 1, seen)
            if r is not None:
                return r
    return None


def weapon_stats(CU, CW, CE, uid):
    """damage/attackSpeed/attackCount/range from a unit's primary weapon link.
    Returns {} if the unit has no resolvable weapon (caster heroes)."""
    u = CU.get(uid, {})
    wid = (u.get('WeaponArray.Link') or u.get('WeaponArray[0].Link')
           or u.get('WeaponArray'))
    out = {}
    if not wid or wid not in CW:
        return out
    w = CW[wid]
    dmg = effect_amount(CE, w.get('DisplayEffect') or w.get('Effect'))
    if dmg is not None:
        out['damage'] = dmg
    period = num(w.get('Period'))
    if period is not None:
        out['attackSpeed'] = period
    cnt = num(w.get('DisplayAttackCount'))
    if cnt is not None:
        out['attackCount'] = cnt
    rng = num(w.get('Range'))
    if rng is not None:
        out['range'] = rng
    return out
