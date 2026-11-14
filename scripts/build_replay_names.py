"""录像回放用的「全量」中文名 + 图标表 → data/replay-names.json。

背景：wiki 的 tech.json / units-v2.json 只收录英雄研究树和兵种库里的条目。录像里会出现
大量此外的单位（召唤物、建筑分档、地图小动物、特效单位）和升级（隐藏计数器、天赋记账、
分级攻防），解析器查不到中文名就只能显示英文 id。

本脚本直接从地图读取所有 CUnit / CUpgrade：
  名字：GameStrings 的 Unit/Name、Upgrade/Name、Button/Name；Name 字段引用别的 key 时
        跟随引用；仍没有就剥掉等级/形态后缀找本体名，再补上「N级」。
  图标：单位 = 演员 UnitIcon → 同名按钮 → 剥后缀后的本体；
        升级 = 研究按钮 face → 升级自身 Icon → 同名按钮 → 剥后缀后的同族升级。
只记录 public/tech-icons/ 里真实存在的图标；候选写进 iconCandidates，
build_tech_icons.py 会把它们一并转出来，再跑一次本脚本即可选上。

输出：{"units": {id: {nameZh, icon}}, "upgrades": {id: {nameZh, icon}}}
解析器（scripts/replay/parse_replay.py）在 tech.json/units-v2.json 查不到时回退到这里。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'replay', 'vendor'))
import lib_map as L  # noqa: E402
import lib_tech as T  # noqa: E402
import lib_units as U  # noqa: E402
from build_units_v2 import ICON_ALIASES, _actor_unit_icons  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'replay-names.json')
ICON_DIR = os.path.join(ROOT, 'public', 'tech-icons')
OVERRIDES = os.path.join(ROOT, 'data', 'seed', 'replay-names.overrides.json')

# 等级 / 档位 / 形态后缀（与 build_units_v2._TIER_SUFFIX 一致，额外认 Left/Right 这类左右手技能位）
TIER_RE = re.compile(r'(?:Level|Tier|L)(\d+)$|(\d+)$')
FORM_RE = re.compile(r'(?:Up|Down|Burrowed|Lowered|Sieged|Rooted|Used|Phasing|Uprooted|Flying|Placement|Left|Right|Slim)$')


def strip_variants(uid):
    """逐层剥后缀 → [(候选本体, 等级或 None), ...]。"""
    out, cur, level = [], uid, None
    for _ in range(4):
        m = TIER_RE.search(cur)
        if m:
            level = level or (m.group(1) or m.group(2))
            nxt = cur[:m.start()]
        else:
            nxt = FORM_RE.sub('', cur)
        if nxt == cur or not nxt:
            break
        out.append((nxt, level))
        cur = nxt
    return out


def name_ref(ent):
    """Name 字段：'Unit/Name/VikingFighter' 这种引用 → key；'Name/##id##' 模板 → None。"""
    v = ent.value('Name') if ent else None
    if v and '##' not in v:
        return v
    return None


def main():
    archive = L.open_map()
    gi = U.GameIndex(archive)
    gs = L.game_strings(archive)
    have = set(os.listdir(ICON_DIR)) if os.path.isdir(ICON_DIR) else set()

    btn_icons = {}
    for root in gi.roots.values():
        btn_icons.update(T.build_button_icons(root))
    actor_icons = _actor_unit_icons(gi)

    # 生产/建造按钮：unit → 训练/建造它的 button face（很多召唤物/建筑档位只在这里有图）
    produce_face = {}
    for root in gi.roots.values():
        for ab in root:
            if not ab.tag.startswith(('CAbilTrain', 'CAbilBuild', 'CAbilWarpTrain', 'CAbilMorph')):
                continue
            for info in ab.findall('InfoArray'):
                b_el = info.find('Button')
                face = b_el.get('DefaultButtonFace') if b_el is not None else None
                if not face:
                    continue
                for u in [x.get('value') for x in info.findall('Unit')] + [info.get('Unit')]:
                    if u:
                        produce_face.setdefault(u, face)

    # 研究按钮：upgrade → 研究时显示的 button face（名字与图标都以按钮为准）
    research_face = {}
    for root in gi.roots.values():
        for r in T.extract_research(root):
            if r['buttonFace']:
                research_face.setdefault(r['upgrade'], r['buttonFace'])

    def gs_name(family, eid):
        ent = gi.get(family, eid)
        ref = name_ref(ent)
        for key in ([ref] if ref else []) + [f'{family}/Name/{eid}', f'Button/Name/{eid}']:
            v = gs.get(key)
            if v and v != eid:
                return v
        return None

    def resolve_name(family, eid, extra_faces=()):
        for face in extra_faces:
            v = gs.get(f'Button/Name/{face}')
            if v:
                return v
        v = gs_name(family, eid)
        if v:
            return v
        for base, level in strip_variants(eid):
            v = gs_name(family, base) or gs.get(f'Button/Name/{base}')
            if v:
                return f'{v} {level}级' if level and family == 'Upgrade' else v
        return None

    def pick_icon(cands):
        seen = []
        for c in cands:
            if c and c not in seen:
                seen.append(c)
        return next((c for c in seen if c in have), None), seen

    def btn(cand):
        out = []
        if not cand:
            return out
        if cand in btn_icons:
            out.append(btn_icons[cand])
        alias = ICON_ALIASES.get(f'{cand}.png')
        if alias:
            out.append(alias)
        return out

    units, upgrades = {}, {}
    for (fam, uid), ent in gi.entries.items():
        if fam != 'Unit':
            continue
        cands = [actor_icons.get(uid), *btn(produce_face.get(uid)), *btn(uid), *btn(f'{uid}Icon')]
        for base, _ in strip_variants(uid):
            # +N 分档建筑（SkitterRelay16）只有 1 档挂了建造按钮
            for v in (base, f'{base}1'):
                cands += [actor_icons.get(v), *btn(produce_face.get(v)), *btn(v)]
        icon, all_c = pick_icon(cands)
        units[uid] = {'nameZh': resolve_name('Unit', uid), 'icon': icon, 'iconCandidates': all_c}

    for (fam, upid), ent in gi.entries.items():
        if fam != 'Upgrade':
            continue
        face = research_face.get(upid)
        own = ent.value('Icon')
        cands = [*(btn(face) if face else []), T._icon_png_name(own) if own else None, *btn(upid)]
        for base, _ in strip_variants(upid):
            cands += [*btn(base), *(btn(research_face[base]) if base in research_face else [])]
        # 分级升级：同族的其它等级若有研究按钮，借它的图
        fam_id = T._family(upid)
        for other, f in research_face.items():
            if f and T._family(other) == fam_id:
                cands += btn(f)
                break
        icon, all_c = pick_icon(cands)
        upgrades[upid] = {'nameZh': resolve_name('Upgrade', upid, [face] if face else []),
                          'icon': icon, 'iconCandidates': all_c}

    # 手工补表（data/seed/replay-names.overrides.json）：地图数据里没有的原版单位/系统计数器
    if os.path.exists(OVERRIDES):
        ov = json.load(open(OVERRIDES, encoding='utf-8'))
        for kind, table in (('units', units), ('upgrades', upgrades)):
            for k, v in (ov.get(kind) or {}).items():
                row = table.setdefault(k, {'nameZh': None, 'icon': None, 'iconCandidates': []})
                if v.get('nameZh'):
                    row['nameZh'] = v['nameZh']
                if v.get('icon'):
                    row['iconCandidates'] = [v['icon'], *[c for c in row['iconCandidates'] if c != v['icon']]]
                    row['icon'] = v['icon'] if v['icon'] in have else row['icon']

    data = {'units': dict(sorted(units.items())), 'upgrades': dict(sorted(upgrades.items()))}
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=0, separators=(',', ':'))
        f.write('\n')

    for k, d in data.items():
        print(f'{k}: {len(d)}  有中文名 {sum(1 for v in d.values() if v["nameZh"])}  '
              f'有图标 {sum(1 for v in d.values() if v["icon"])}  '
              f'有候选未转换 {sum(1 for v in d.values() if not v["icon"] and v["iconCandidates"])}')


if __name__ == '__main__':
    main()
