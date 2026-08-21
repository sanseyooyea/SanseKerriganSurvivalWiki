"""
Shared parser for per-hero TECH / RESEARCH extraction (CAbilResearch + CUpgrade).

Tech for a hero = the `<CAbilResearch>` ability(ies) in its `H-<Hero>.xml`. Each
`<InfoArray index="ResearchN" Time=.. Upgrade=..>` slot is one researchable option:
cost (Minerals/Vespene) + time live on the slot; the *effects* live on the linked
`<CUpgrade>` (EffectArray Reference/Value). Human text comes from zhCN GameStrings
`Button/Name|Tooltip/<Face>`; tooltips embed dynamic numbers via
`$UpgradeEffectArrayValue:<UpgradeId>:<Catalog,Entry,Field>$` tokens that must be
resolved against the matching CUpgrade EffectArray value.

NOTE: we parse the raw H-*.xml with ElementTree directly (NOT lib_map.build_catalog)
because the catalog flattener collapses sibling InfoArray/EffectArray entries onto a
single key — lossy for exactly the repeated arrays we need here.

Level modeling is inconsistent in the map and both forms are handled:
  (a) one CUpgrade with MaxLevel + a single repeated research slot
  (b) separate `...Level1/2/3` CUpgrade ids, one research slot each
group_upgrades() reconstructs a single multi-level view from either form.
"""
import re
import xml.etree.ElementTree as ET


def _num(s):
    """int when whole, else round 4dp, None on failure."""
    try:
        f = float(s)
        return int(f) if f == int(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


def parse_hero_xml(xml_bytes):
    """Bytes of an H-<Hero>.xml -> ElementTree root (<Catalog>)."""
    text = xml_bytes.decode('utf-8', 'replace').lstrip('﻿')
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', text)
        return ET.fromstring(text)


def extract_research(root):
    """All CAbilResearch InfoArray slots. Returns list of dicts:
    {ability,index,upgrade,time,minerals,gas,buttonFace,requirements}."""
    out = []
    for abil in root.iter('CAbilResearch'):
        aid = abil.get('id')
        for info in abil.findall('InfoArray'):
            idx = info.get('index', '')
            if not idx.startswith('Research'):
                continue
            up = info.get('Upgrade')
            if not up:
                continue
            minerals = gas = 0
            for res in info.findall('Resource'):
                v = _num(res.get('value')) or 0
                if res.get('index') == 'Minerals':
                    minerals = v
                elif res.get('index') == 'Vespene':
                    gas = v
            btn = info.find('Button')
            out.append({
                'ability': aid,
                'index': idx,
                'upgrade': up,
                'time': _num(info.get('Time')) or 0,
                'minerals': minerals,
                'gas': gas,
                'buttonFace': btn.get('DefaultButtonFace') if btn is not None else None,
                'requirements': btn.get('Requirements') if btn is not None else None,
            })
    return out


def build_upgrade_effects(root):
    """upgradeId -> {effects:{referenceStr:value}, maxLevel, category, icon}.
    effects powers $UpgradeEffectArrayValue$ token resolution."""
    upgrades = {}
    for up in root.iter('CUpgrade'):
        uid = up.get('id')
        if not uid:
            continue
        effs = {}
        for ea in up.findall('EffectArray'):
            ref = ea.get('Reference')
            if ref is not None and ea.get('Value') is not None:
                effs[ref] = ea.get('Value')
        cat = None
        ec = up.find('EditorCategories')
        if ec is not None and ec.get('value'):
            m = re.search(r'UpgradeType:(\w+)', ec.get('value'))
            if m:
                cat = m.group(1)
        ml = up.find('MaxLevel')
        icon = up.find('Icon')
        upgrades[uid] = {
            'effects': effs,
            'maxLevel': _num(ml.get('value')) if ml is not None else None,
            'category': cat,
            'icon': (icon.get('value') or '').split('\\')[-1] if icon is not None else None,
        }
    return upgrades


# $UpgradeEffectArrayValue:<UpgradeId>:<Catalog,Entry,Field>$ — optional trailing
# arithmetic like $...$*100, and the enclosing <d> may carry precision="N".
_DTOKEN = re.compile(
    r'<d\s+ref="\$UpgradeEffectArrayValue:([^:]+):([^$]+)\$(\*[\d.]+)?"'
    r'(?:\s+precision\s*=\s*"(\d+)")?\s*/?>',
    re.IGNORECASE,
)
_CTAG = re.compile(r'</?c\b[^>]*>', re.IGNORECASE)   # color spans -> strip, keep inner text
_NTAG = re.compile(r'<n\s*/?>', re.IGNORECASE)        # line break
_ANYD = re.compile(r'<d\b[^>]*/?>', re.IGNORECASE)    # any unresolved <d ...> (e.g. BehaviorStackCount)
_ANYTAG = re.compile(r'<[^>]+>')                       # residual markup safety net


def _fmt(value, precision, mult):
    n = _num(value)
    if n is None:
        return None
    if mult:
        n = n * float(mult[1:])
    if precision is not None:
        n = round(n, int(precision))
    return int(n) if float(n) == int(n) else round(n, 4)


def render_tooltip(raw, upgrade_effects, upgrade_id=None):
    """Resolve dynamic tokens against upgrade EffectArray values and strip markup.

    `upgrade_effects` = build_upgrade_effects() output. Token carries its own
    UpgradeId, so we look up that upgrade's effects by the Reference substring
    (Catalog,Entry,Field). Unresolved tokens are dropped (not left as $...$).
    Returns clean zhCN text with real numbers inlined; None/'' -> ''."""
    if not raw:
        return ''
    text = raw

    def _sub(m):
        uid, ref, mult, prec = m.group(1), m.group(2), m.group(3), m.group(4)
        effs = upgrade_effects.get(uid, {}).get('effects', {})
        val = effs.get(ref)
        out = _fmt(val, prec, mult) if val is not None else None
        return str(out) if out is not None else ''

    text = _DTOKEN.sub(_sub, text)
    text = _NTAG.sub('\n', text)
    text = _CTAG.sub('', text)
    text = _ANYD.sub('', text)     # drop any other <d> (compound formulas / BehaviorStackCount) we don't resolve
    text = _ANYTAG.sub('', text)   # safety: strip any leftover tag
    # An unresolved <d> often leaves an orphaned unit token (e.g. "…效果至<d/>%" -> "…效果至%").
    # Clean the common artifacts: a stray leading % / +% / ×N with no number in front.
    text = re.sub(r'(?<![\d.])\s*[%％]', '', text)          # % not preceded by a digit
    text = re.sub(r'[至到]\s*(?=[。，、\n]|$)', '', text)     # dangling "至/到" with nothing after
    text = re.sub(r'[+\-×*]\s*(?=[。，、\n]|$)', '', text)   # dangling operator before punctuation/eol
    # collapse >2 blank lines, trim each line
    lines = [ln.strip() for ln in text.split('\n')]
    # 编译公式残渣：形如「标签 - 秒/%/米/点」的明细行，其数字来自无法从 map 解析的
    # 裸目录路径引用（如 Abil,...,InfoArray[Build1].Time，基础值在基础 SC2 数据里）。
    # 整行删掉，避免出现「垃圾堆 - 秒」这种半空明细。带数字的正常行保留。
    lines = [ln for ln in lines
             if re.search(r'\d', ln) or not re.search(r'[-—]\s*[秒%％米点倍]+$', ln)]
    # 明细全被删后，末尾遗留的「建造时间：」这类悬空标题行也一并去掉。
    while lines and re.search(r'[:：]\s*$', lines[-1]):
        lines.pop()
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


def _tier_key(opt):
    """Sort key within an upgrade family: prefer a trailing Level<N> or Tier<N> in the
    requirements/button/upgrade id, else the numeric ResearchN slot (stable fallback)."""
    for src in (opt.get('requirements'), opt.get('buttonFace'), opt.get('upgrade')):
        if src:
            m = re.search(r'(?:Level|Tier)(\d+)', src)
            if m:
                return (0, int(m.group(1)))
    m = re.search(r'Research(\d+)', opt.get('index', ''))
    return (1, int(m.group(1)) if m else 0)


def _family(upgrade_id):
    """Collapse `FooLevel1/FooTier2` -> `Foo` so per-level CUpgrade ids group together.
    Single-CUpgrade+MaxLevel upgrades keep their own id (no suffix) -> own family."""
    return re.sub(r'(?:Level|Tier)\d+$', '', upgrade_id)


def build_button_icons(root):
    """buttonFace -> icon png basename (lowercased, .dds→.png).

    CButton 的 Icon 是游戏内真正显示的升级图标(比 CUpgrade.Icon 覆盖更全）。
    路径如 'Assets\\Textures\\btn-upgrade-terran-vehicleplatinglevel1.dds'
    → 'btn-upgrade-terran-vehicleplatinglevel1.png'。找不到 Icon 的 button 跳过。"""
    out = {}
    for btn in root.iter('CButton'):
        bid = btn.get('id')
        if not bid:
            continue
        icon = btn.find('Icon')
        val = icon.get('value') if icon is not None else None
        if not val:
            continue
        out[bid] = _icon_png_name(val)
    return out


def _icon_png_name(dds_path):
    """'Assets\\Textures\\Btn-Foo Bar.dds' -> 'btn-foo-bar.png'（小写、空格→-、URL 安全）。"""
    base = dds_path.replace('\\', '/').rsplit('/', 1)[-1].lower()
    if base.endswith('.dds'):
        base = base[:-4]
    base = re.sub(r'\s+', '-', base.strip())
    return base + '.png'


def group_upgrades(research, upgrade_effects, gs_name, gs_tooltip, button_icons=None):
    """Merge research slots into per-family multi-level upgrade groups.

    research: extract_research() output.
    upgrade_effects: build_upgrade_effects() output.
    gs_name/gs_tooltip: {buttonFace: zhText} from game_strings('Button/Name/'|'Button/Tooltip/').

    Returns list of groups:
      {id, nameZh, category, icon, levels:[{level,cost,gasCost,time,descZh}]}
    """
    fams = {}
    order = []
    for opt in research:
        fam = _family(opt['upgrade'])
        if fam not in fams:
            fams[fam] = []
            order.append(fam)
        fams[fam].append(opt)

    groups = []
    for fam in order:
        opts = sorted(fams[fam], key=_tier_key)
        # name/category/icon from the first slot's upgrade + button face
        first = opts[0]
        meta = upgrade_effects.get(first['upgrade'], {})
        face = first.get('buttonFace')
        # family name: strip a trailing " 等级 N"/level suffix from the localized button name
        raw_name = (gs_name.get(face) if face else None) or first['upgrade']
        name = re.sub(r'\s*(?:等级|等級)\s*\d+\s*$', '', raw_name).strip() or raw_name
        levels = []
        for i, opt in enumerate(opts, 1):
            f = opt.get('buttonFace')
            tip = render_tooltip(gs_tooltip.get(f, '') if f else '',
                                 upgrade_effects, opt['upgrade'])
            levels.append({
                'level': i,
                'cost': opt['minerals'],
                'gasCost': opt['gas'],
                'time': opt['time'],
                'descZh': tip,
            })
        # 图标优先取 CButton 主图标(png 名),回退 CUpgrade.Icon(把 .dds 换 png)
        icon = None
        if button_icons and face:
            icon = button_icons.get(face)
        if not icon:
            u_icon = meta.get('icon')
            if u_icon:
                icon = _icon_png_name(u_icon)
        groups.append({
            'id': fam,
            'nameZh': name,
            'category': meta.get('category'),
            'icon': icon,
            'levels': levels,
        })
    return groups
