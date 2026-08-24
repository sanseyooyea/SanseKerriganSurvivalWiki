"""
Build data/abilities.json from the seed ability lists (union of every hero's
abilities in roles.seed.json) + the map's GameStrings.

For each ability id, resolve:
  nameEn   Abil/Name (English) — fallback to id
  nameZh   Button/Name via the ability's button face, then multi-strategy match,
           then Abil/Name; English kept only if no Chinese exists in the map
  tooltip  Button/Tooltip via multi-strategy match (cleaned of markup, <d ref> -> [?])

No menu-button filtering needed: the seed lists are already the curated, clean set
of real hero abilities (that filtering was only needed when scraping CardLayouts).
"""
import json
import os
import re

import lib_map as L

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
SEED = os.path.join(DATA, 'seed', 'roles.seed.json')
NAME_SEED = os.path.join(DATA, 'seed', 'ability-names.seed.json')
FACE_SEED = os.path.join(DATA, 'seed', 'ability-face.seed.json')
OUT = os.path.join(DATA, 'abilities.json')

CLASS_PREFIXES = [
    'DJ', 'DS', 'DT', 'Kerrigan', 'Alarak', 'Artanis', 'Ares', 'Andor', 'Aewyn',
    'Brakk', 'Glevig', 'Chew', 'Nova', 'Stukov', 'Scion', 'Mira', 'Nomad', 'Dehaka',
    'Izsha', 'Kraith', 'Warfield', 'Warden', 'Rattlesnake', 'SgtHammer', 'Sophia',
    'Selendis', 'Nightingale', 'Jinara', 'SirRoachington', 'Sjlerk', 'Thakras',
    'DeltaSquad', 'Helios', 'Phaegore', 'Champion', 'Energizer', 'Elementalist',
    'Prophet', 'Technician', 'Swann', 'Niadra',
]

archive = L.open_map()
button_tooltips = L.game_strings(archive, 'Button/Tooltip/')
button_names = L.game_strings(archive, 'Button/Name/')
abil_names = L.game_strings(archive, 'Abil/Name/')
catalog = L.build_catalog(archive)
ABIL = catalog.get('Abil', {})
BTN = catalog.get('CButton', {})

tooltips_lower = {k.lower(): v for k, v in button_tooltips.items()}
names_lower = {k.lower(): v for k, v in button_names.items()}


def _icon_png_name(dds_path):
    """'Assets\\Textures\\Btn-Foo Bar.dds' -> 'btn-foo-bar.png'（小写、空格→-）。
    与 lib_tech._icon_png_name 一致，技能图标与科技图标共用同一套命名。"""
    base = dds_path.replace('\\', '/').rsplit('/', 1)[-1].lower()
    if base.endswith('.dds'):
        base = base[:-4]
    base = re.sub(r'\s+', '-', base.strip())
    return base + '.png'


def find_icon(ab_id):
    """技能图标 png 名。取 CButton 的 Icon(dds 路径)转 png：
      1. 技能 id 直接就是 CButton id
      2. 否则经技能的 CmdButtonArray.DefaultButtonFace 跳一层查 CButton
    找不到返回 ''（少数召唤/研究/被动类技能无按钮图标）。"""
    for bid in (ab_id, ABIL.get(ab_id, {}).get('CmdButtonArray.DefaultButtonFace')):
        if not bid:
            continue
        val = BTN.get(bid, {}).get('Icon')
        if val:
            return _icon_png_name(val)
    return ''

# Hand-curated name fallbacks for abilities the map has no name for.
NAME_OVERRIDE = {k: v for k, v in json.load(
    open(NAME_SEED, encoding='utf-8')).items() if not k.startswith('_')}

# 策展映射：技能 id -> 指令卡按钮面(CButton id)，显示信息(name/icon/tooltip)从该 face 派生。
_face_seed = json.load(open(FACE_SEED, encoding='utf-8'))
FACE_GLOBAL = {k: v for k, v in _face_seed.get('global', {}).items() if not k.startswith('_')}
FACE_PERHERO = {k: v for k, v in _face_seed.get('perHero', {}).items() if not k.startswith('_')}


def face_display(face_id):
    """从一个按钮面(CButton id)派生 (nameZh, tooltip, icon)。tooltip 为空则返回 ''，
    由调用方决定是否回退技能自身的 tooltip。名字非中文则原样返回(交由上层再兜底)。"""
    name = button_names.get(face_id, '').strip()
    tip = clean_tooltip(button_tooltips.get(face_id, ''))
    dds = BTN.get(face_id, {}).get('Icon')
    icon = _icon_png_name(dds) if dds else ''
    return name, tip, icon


def clean_tooltip(raw):
    if not raw:
        return ''
    c = raw
    c = re.sub(r'<n/>', '\n', c)
    c = re.sub(r'<c[^>]*>', '', c)
    c = re.sub(r'</c>', '', c)
    c = re.sub(r'<d ref="[^"]*"/>', '[?]', c)
    c = re.sub(r'<[^>]+>', '', c)
    c = re.sub(r'\n{3,}', '\n\n', c)
    return c.strip()


def find_tooltip(ab_id):
    if ab_id in button_tooltips:
        return clean_tooltip(button_tooltips[ab_id])
    if ab_id.lower() in tooltips_lower:
        return clean_tooltip(tooltips_lower[ab_id.lower()])
    # the ability's own button face (e.g. SpiritCloneSpirit -> SpiritClone,
    # CommonBlinkHero -> SurvivorBlink): the tooltip lives on the face, not the id
    face = ABIL.get(ab_id, {}).get('CmdButtonArray.DefaultButtonFace')
    if face and face in button_tooltips:
        return clean_tooltip(button_tooltips[face])
    for suffix in ('KS2', 'Ks2', 'ks2'):
        key = (ab_id + suffix).lower()
        if key in tooltips_lower:
            return clean_tooltip(tooltips_lower[key])
    for prefix in CLASS_PREFIXES:
        if ab_id.startswith(prefix) and len(ab_id) > len(prefix):
            stripped = ab_id[len(prefix):]
            if stripped.lower() in tooltips_lower:
                return clean_tooltip(tooltips_lower[stripped.lower()])
            for suffix in ('', 'KS2'):
                key = (stripped + suffix).lower()
                if key in tooltips_lower:
                    return clean_tooltip(tooltips_lower[key])
    candidates = [(k, v) for k, v in button_tooltips.items()
                  if ab_id.lower() in k.lower() and len(v) > 10]
    if candidates:
        candidates.sort(key=lambda x: len(x[0]))
        return clean_tooltip(candidates[0][1])
    return ''


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def find_name_zh(ab_id, name_en):
    """Chinese name. Precedence (matches the old pipeline):
      1. the ability's OWN Button/Name (direct id) if it is Chinese
      2. case-insensitive / KS2-suffix variants if Chinese
      3. the default button face's Button/Name if Chinese (last-resort fallback;
         the face is sometimes a Cancel/variant button, so it ranks below the
         ability's own name)
      4. any English name we can find (own button name, then Abil/Name)
    """
    if ab_id in button_names and not is_ascii(button_names[ab_id]):
        return button_names[ab_id].strip()
    if ab_id.lower() in names_lower and not is_ascii(names_lower[ab_id.lower()]):
        return names_lower[ab_id.lower()].strip()
    for suffix in ('KS2', 'Ks2'):
        key = (ab_id + suffix).lower()
        if key in names_lower and not is_ascii(names_lower[key]):
            return names_lower[key].strip()
    face = ABIL.get(ab_id, {}).get('CmdButtonArray.DefaultButtonFace')
    if face and face in button_names and not is_ascii(button_names[face]):
        return button_names[face].strip()
    return (button_names.get(ab_id) or names_lower.get(ab_id.lower())
            or name_en).strip()


# Collect the union of ability ids from the seed (preserve first-seen order).
seed = json.load(open(SEED, encoding='utf-8'))
ab_ids = []
seen = set()
for role in seed:
    cond_ids = [c['id'] for c in role.get('conditionalAbilities', [])]
    for aid in list(role.get('abilities', [])) + cond_ids:
        if aid not in seen:
            seen.add(aid)
            ab_ids.append(aid)

out = {}
untranslated = []
no_tooltip = []
no_icon = []
for aid in ab_ids:
    name_en = abil_names.get(aid, button_names.get(aid, aid)).strip()
    name_zh = find_name_zh(aid, name_en)
    # map has no Chinese name -> prefer hand-curated override over the raw id
    if is_ascii(name_zh) and aid in NAME_OVERRIDE:
        name_zh = NAME_OVERRIDE[aid]
        if name_en == aid:
            name_en = NAME_OVERRIDE[aid]
    tooltip = find_tooltip(aid)
    icon = find_icon(aid)
    # 策展 face 覆盖(global)：显示身份取指令卡按钮面，而非技能自身默认 face。
    # tooltip 优先 face，face 无则保留技能自身的 tooltip；名字/图标以 face 为准。
    if aid in FACE_GLOBAL:
        fname, ftip, ficon = face_display(FACE_GLOBAL[aid])
        if fname:
            name_zh = fname
        if ftip:
            tooltip = ftip
        if ficon:
            icon = ficon
    if is_ascii(name_zh):
        untranslated.append(aid)
    if not tooltip:
        no_tooltip.append(aid)
    if not icon:
        no_icon.append(aid)
    entry = {'nameZh': name_zh, 'nameEn': name_en, 'tooltip': tooltip}
    if icon:
        entry['icon'] = icon
    # 策展 face 覆盖(perHero)：同 id 被多英雄共用、各自 face 不同名，写入按英雄的覆盖。
    if aid in FACE_PERHERO:
        per = {}
        for hero, face_id in FACE_PERHERO[aid].items():
            if hero.startswith('_'):
                continue
            fname, ftip, ficon = face_display(face_id)
            o = {}
            if fname:
                o['nameZh'] = fname
            o['tooltip'] = ftip or tooltip
            if ficon:
                o['icon'] = ficon
            per[hero] = o
        if per:
            entry['perHero'] = per
    out[aid] = entry

json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f'Wrote {len(out)} abilities to abilities.json')
print(f'  with tooltip: {len(out) - len(no_tooltip)}, no tooltip: {len(no_tooltip)}')
print(f'  with icon: {len(out) - len(no_icon)}, no icon: {len(no_icon)}')
print(f'  untranslated (kept English): {len(untranslated)}')
if untranslated:
    print('   ' + ', '.join(untranslated))
if no_icon:
    print('  no-icon abilities: ' + ', '.join(no_icon))
