"""Generate / rebuild ALL survivor-team hero entries in data/tech.json.

泛化 build_swann_tech / build_chew_tech：遍历所有生存者英雄（roles.json team='Survivor'），
定位其 `H-<NameEn>.xml`，用 lib_tech 提取 `<CAbilResearch>` 研究科技树（成本/时间/逐级效果，
$UpgradeEffectArrayValue$ 动态数值已代入 CUpgrade/EffectArray 真实值）。

英雄名 → XML 映射：nameEn 空格换下划线后匹配 `H-<key>.xml`（如 Dark Templar→H-Dark_Templar.xml、
Team Nova→H-Team_Nova.xml）。开发中/无 XML 的英雄跳过（如 Skitter=InDevelopment）；无研究槽的
英雄跳过（不写入 tech.json，角色页据 hasTech 自动隐藏科技板块）。

秋伊(Chew)特例并入本脚本：额外抽取 galaxy 驱动的「小进化」(Chewolution) 次要强化表
（chew_Upgrades.galaxy 的 gf_InitChewUpgrade，仅英文），作为补充字段 chewolution 附上。

所有数值从 凯瑞甘生存2 最新版.SC2Map 提取，零硬编码。整表重建（非逐条替换），按 economy.json
既有风格 CRLF + trailing newline + indent=2 ensure_ascii=False 回写。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lib_map as L
import lib_tech as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECH_JSON = os.path.join(ROOT, 'data', 'tech.json')
ROLES_JSON = os.path.join(ROOT, 'data', 'roles.json')

# 秋伊小进化：galaxy 驱动的次要强化表（仅英文，与研究科技树独立）。
CHEW_HERO = 'Chew'
CHEWOLUTION_GALAXY = r'Scripts\hero\chew\chew_Upgrades.galaxy'
_CHEW_INIT_RE = re.compile(
    r'gf_InitChewUpgrade\(\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*(\d+)\s*,\s*gs_CAT_(\w+)\s*\)'
)


def hero_xml_index(archive):
    """{ 'H-<key>' basename(去 .xml) : archive内路径 } —— 分隔符无关地匹配 H-*.xml。"""
    idx = {}
    for f in L._listfile(archive):
        m = re.search(r'H-([A-Za-z0-9_]+)\.xml$', f)
        if m:
            idx[m.group(1)] = f
    return idx


def survivors():
    """roles.json 里 team='Survivor' 的英雄（保持文件顺序）。"""
    roles = json.load(open(ROLES_JSON, encoding='utf-8'))
    return [r for r in roles if r.get('team') == 'Survivor']


def extract_chewolution(archive):
    """秋伊小进化表 → [{index,link,descEn,maxCount,category}]，按 index 排序。英文-only。"""
    txt = archive.read_file(CHEWOLUTION_GALAXY).decode('utf-8', 'replace')
    rows = [{
        'index': int(m.group(1)),
        'link': m.group(2),
        'descEn': m.group(3),
        'maxCount': int(m.group(4)),
        'category': m.group(5),
    } for m in _CHEW_INIT_RE.finditer(txt)]
    rows.sort(key=lambda r: r['index'])
    return rows


def build_entry(archive, hero_en, xml_path, gs_name, gs_tip):
    """单英雄 tech.json 条目；无研究槽返回 None（不写入）。"""
    root = T.parse_hero_xml(archive.read_file(xml_path))
    research = T.extract_research(root)
    if not research:
        return None
    effects = T.build_upgrade_effects(root)
    btn_icons = T.build_button_icons(root)
    groups = T.group_upgrades(research, effects, gs_name, gs_tip, btn_icons)
    abilities = sorted({r['ability'] for r in research})
    entry = {
        'hero': hero_en,
        'researchAbility': abilities[0] if abilities else None,
        'researchAbilities': abilities,
        'upgrades': groups,
    }
    if hero_en == CHEW_HERO:
        entry['chewolution'] = extract_chewolution(archive)
    return entry


def write_all(entries):
    """整表重建，保留 economy.json 风格 CRLF + trailing NL + indent=2 ensure_ascii=False。"""
    crlf = trailing_nl = True
    if os.path.exists(TECH_JSON):
        with open(TECH_JSON, 'rb') as f:
            raw = f.read()
        if raw.strip():
            crlf = b'\r\n' in raw
            trailing_nl = raw.endswith(b'\n')
    text = json.dumps(entries, ensure_ascii=False, indent=2)
    if trailing_nl:
        text += '\n'
    if crlf:
        text = text.replace('\n', '\r\n')
    with open(TECH_JSON, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def main():
    ar = L.open_map()
    xml_idx = hero_xml_index(ar)
    gs_name = L.game_strings(ar, 'Button/Name/')
    gs_tip = L.game_strings(ar, 'Button/Tooltip/')

    entries, no_xml, no_research = [], [], []
    for r in survivors():
        hero_en = r['nameEn']
        key = hero_en.replace(' ', '_')
        xml_path = xml_idx.get(key)
        if not xml_path:
            no_xml.append(hero_en)
            continue
        entry = build_entry(ar, hero_en, xml_path, gs_name, gs_tip)
        if entry is None:
            no_research.append(hero_en)
            continue
        entries.append(entry)

    write_all(entries)

    total_groups = sum(len(e['upgrades']) for e in entries)
    cats = {}
    for e in entries:
        for g in e['upgrades']:
            cats[g['category']] = cats.get(g['category'], 0) + 1
    print(f'wrote {len(entries)} heroes, {total_groups} upgrade groups -> data/tech.json')
    print(f'  categories: {cats}')
    if no_xml:
        print(f'  no XML (skipped): {no_xml}')
    if no_research:
        print(f'  no research slots (skipped): {no_research}')
    print()
    for e in entries:
        chew = f"  +{len(e['chewolution'])} chewolution" if e.get('chewolution') else ''
        print(f"  {e['hero']:16} {len(e['upgrades']):3} groups{chew}")


if __name__ == '__main__':
    main()
