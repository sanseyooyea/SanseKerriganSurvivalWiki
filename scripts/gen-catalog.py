"""
Rebuild data/catalog.json from the map's GameData XML files.
Output: { CatalogType: { EntryId: { field: "value", ... } } }
- Catalog types mapped via TYPE_MAP (Unit/Abil/Weapon/Effect/...), others keep C-prefix.
- Fields: attributes + child <X value="Y"/> (flattened, plus [idx] and [namedIndex] variants).
- parent="Template" inheritance merged (child overrides parent).
Only consumed by gen-units.py; matches the structure resolve-tooltips.py expects.
"""
import mpyq, re, json
import xml.etree.ElementTree as ET

MAP_PATH = r'D:\starcraft2\凯瑞甘生存2 最新版.SC2Map'
OUT = r'D:\starcraft2\SanseKerriganSurvivalWiki\data\catalog.json'

TYPE_MAP = {
    'CUnit': 'Unit', 'CAbil': 'Abil', 'CEffect': 'Effect', 'CBehavior': 'Behavior',
    'CWeapon': 'Weapon', 'CUpgrade': 'Upgrade', 'CValidator': 'Validator',
}

def catalog_type(tag):
    for prefix, name in TYPE_MAP.items():
        if tag.startswith(prefix):
            return name
    return tag  # keep raw C-prefixed type

archive = mpyq.MPQArchive(MAP_PATH)
flist = archive.read_file('(listfile)').decode('utf-8', 'replace').split('\r\n')
xml_files = [f for f in flist if f.endswith('.xml') and 'GameData' in f]


def collect_fields(elem, prefix, out):
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
        collect_fields(child, base, out)


# Pass 1: collect raw fields + parent link for every entry, keyed by (type, id).
# Templates (parent-only, often C-prefixed bases like GenericUnitStandard) are kept
# in `raw` for inheritance resolution but only "real" entries are emitted.
raw = {}        # (cat_type, id) -> flat field dict
parent_of = {}  # (cat_type, id) -> parent id (same cat_type)

print('Parsing XML...')
for xf in xml_files:
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
        ctype = catalog_type(elem.tag)
        fields = {}
        collect_fields(elem, '', fields)
        k = (ctype, eid)
        if k in raw:
            raw[k].update(fields)   # merge multiple <CUnit id=X> blocks
        else:
            raw[k] = fields
        p = elem.get('parent')
        if p:
            parent_of[k] = p

print(f'Collected {len(raw)} raw entries')


def resolve(k, seen=None):
    """Merge parent chain (parent fields first, child overrides)."""
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
    if pid:
        merged['CopySource'] = pid
    return merged


# Pass 2: emit. Skip pure templates whose id starts with '_' (base defs like _Unit).
catalog = {}
for (ctype, eid) in raw:
    if eid.startswith('_'):
        continue
    catalog.setdefault(ctype, {})[eid] = resolve((ctype, eid))

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(catalog, f, ensure_ascii=False, separators=(',', ':'))

total = sum(len(v) for v in catalog.values())
print(f'Wrote {len(catalog)} types, {total} entries to {OUT}')
for t in ['Unit', 'Abil', 'Weapon', 'Effect']:
    print(f'  {t}: {len(catalog.get(t, {}))}')
