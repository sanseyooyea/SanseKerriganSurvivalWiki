"""
Audit每个英雄的"真实可用技能"，以游戏数据(命令卡 + 需求链)为准，对出 seed 里
过时的技能。解决的痛点：英雄废弃技能在地图静态文件里残留极完整(AbilArray、CButton、
GameStrings、触发器都还在)，单看"AbilArray/卡牌按钮是否存在"会误判(典型：灵魂的偏转、
滑翔)。可靠信号是命令卡按钮 + 按钮 Requirements 的语义分类。

判定一个英雄技能(排除 move/stop/attack/build 等通用命令)：
  - 主命令卡【没有】它的按钮            -> dead   (永不显示，已废弃，如灵魂滑翔)
  - 有按钮，且按钮 Requirements 为空     -> base   (基础技能，如闪现)
  - 有按钮，Requirements 只门控【自身/召唤物】状态 -> base   (如灵魂分裂灵魂：没分身时可放)
  - 有按钮，Requirements 门控【需先造某建筑】     -> conditional (建筑解锁的情境技能，如灵魂偏转需水晶球)

"base" 才是 Wiki roles 应列的英雄技能；conditional/dead 不列(或单独标注)。

用法：
  PYTHONUTF8=1 /c/Python313/python.exe scripts/audit_hero_skills.py            # 用默认地图，全英雄
  PYTHONUTF8=1 /c/Python313/python.exe scripts/audit_hero_skills.py Spirit     # 只看某英雄(nameEn)
  PYTHONUTF8=1 /c/Python313/python.exe scripts/audit_hero_skills.py --map "<path.s2ma>"
"""
import json
import os
import re
import sys

import lib_map as L

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
SEED = os.path.join(WIKI, 'data', 'seed', 'roles.seed.json')

# 通用命令/建造/子菜单按钮，不算英雄技能
GENERIC_ABILS = {'move', 'stop', 'attack', 'Warpable', 'patrol', 'HoldPos'}
GENERIC_PREFIXES = ('CommonMove', 'CommonStop', 'CommonAttack')
# 通用/系统/被动类命令(各英雄都有自己的 Move/Attack/选择变体)，不算技能。
# 注意：ScannerSweep(悉像扫描/雷达扫描) 是凯瑞甘方英雄的真实主动技能，不能过滤——
# 曾被误当作战役单位的普通侦察扫描而删掉，导致凯瑞甘方全体缺此共有技能。
GENERIC_HINT = re.compile(
    r'Move|Attack|Stop|HoldPos|Patrol|AddToSelection|RemoveFromSelection|'
    r'AutocreepTimer|MoveOrder')
# 建造/采集/经济类(按 *Build* / 名字判断)，不算战斗技能
BUILD_HINT = re.compile(r'Build|Train|Learn|Research|Market|Bank|Casino|CrystalBall|Salvage|Deposit|Withdraw')

HERO_UNIT_OVERRIDE = {'Jinara': 'JinaraJinara', 'Skitter': 'SkitterSkitter'}


def hero_unit_id(role):
    return HERO_UNIT_OVERRIDE.get(role['nameEn']) or (role.get('heroUnits') or [None])[0]


def index_raw_cunits(archive):
    """unit id -> 原始 <CUnit>…</CUnit> XML 文本(取最后一个定义，胜出者)。"""
    out = {}
    for xf in L.gamedata_xml_files(archive):
        d = archive.read_file(xf).decode('utf-8', 'ignore')
        for mt in re.finditer(r'<CUnit id="([^"]+)">(.*?)</CUnit>', d, re.S):
            out[mt.group(1)] = mt.group(0)
    return out


def index_requirements(archive):
    """id -> dict(tag, raw)  覆盖所有 CRequirement* 元素，用于解析需求链。"""
    out = {}
    for xf in L.gamedata_xml_files(archive):
        d = archive.read_file(xf).decode('utf-8', 'ignore')
        for mt in re.finditer(r'<(CRequirement\w*) id="([^"]+)">(.*?)</\1>', d, re.S):
            out[mt.group(2)] = (mt.group(1), mt.group(0))
    return out


def main_card_abilcmds(cunit_xml):
    """主命令卡(第一个 <CardLayouts>，无 CardId 或 CardId=0001)里的 (face, abilId)。"""
    # 切出第一个 CardLayouts 块(主卡)；带 CardId 的子菜单在其后，排除掉
    blocks = re.split(r'<CardLayouts(?:\s+CardId="[^"]*")?>', cunit_xml)
    # blocks[0] 是 CardLayouts 之前的内容；blocks[1] 是第一个(主)卡内容
    if len(blocks) < 2:
        return []
    main = blocks[1].split('</CardLayouts>')[0]
    res = []
    for mt in re.finditer(r'<LayoutButtons\b([^/>]*)/?>', main):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', mt.group(1)))
        if attrs.get('Type') != 'AbilCmd':
            continue
        abilcmd = attrs.get('AbilCmd', '')
        abil = abilcmd.split(',')[0] if abilcmd else ''
        res.append((attrs.get('Face', ''), abil))
    return res


def units_referenced(req_id, reqs, seen=None):
    """递归收集需求树里 Count Link="<unit>" 引用的全部单位 id。"""
    if seen is None:
        seen = set()
    if req_id in seen or req_id not in reqs:
        return set()
    seen.add(req_id)
    tag, raw = reqs[req_id]
    units = set(re.findall(r'<Count\b[^>]*\bLink="([^"]+)"', raw))
    # 跟进 NodeArray Link / OperandArray value 指向的子需求
    for child in re.findall(r'<(?:NodeArray|OperandArray)\b[^>]*(?:Link|value)="([^"]+)"', raw):
        units |= units_referenced(child, reqs, seen)
    return units


def classify(abil_id, abil_catalog, reqs, CU):
    """返回 (kind, detail). kind ∈ base|conditional|dead 由调用方结合卡牌按钮决定 dead。"""
    a = abil_catalog.get(abil_id, {})
    req = a.get('CmdButtonArray.Requirements')
    if not req:
        return 'base', '无需求'
    ref_units = units_referenced(req, reqs)
    structures = [u for u in ref_units if CU.get(u, {}).get('Attributes[Structure]') == '1']
    if structures:
        return 'conditional', f'需建筑 {req} -> {sorted(structures)}'
    return 'base', f'自身/召唤物状态 {req} -> {sorted(ref_units) or "?"}'


def main():
    argv = sys.argv[1:]
    map_path = None
    if '--map' in argv:
        i = argv.index('--map')
        map_path = argv[i + 1]
        del argv[i:i + 2]
    only = argv[0] if argv else None

    archive = L.open_map(map_path) if map_path else L.open_map()
    cat = L.build_catalog(archive)
    CU, ABIL = cat['Unit'], cat['Abil']
    cunits_raw = index_raw_cunits(archive)
    reqs = index_requirements(archive)

    seed = json.load(open(SEED, encoding='utf-8'))
    mismatches = 0
    for role in seed:
        if only and role['nameEn'] != only:
            continue
        uid = hero_unit_id(role)
        raw = cunits_raw.get(uid)
        if not raw:
            print(f"[{role['nameEn']}] 英雄单位 {uid} 无原始 CUnit，跳过")
            continue
        card = main_card_abilcmds(raw)
        # 候选技能：卡牌里非通用、非建造的 AbilCmd
        card_abils = []
        for face, abil in card:
            if not abil or abil in GENERIC_ABILS or abil in card_abils:  # 去重
                continue
            if abil.startswith(GENERIC_PREFIXES) or BUILD_HINT.search(abil):
                continue
            if GENERIC_HINT.search(abil):
                continue
            card_abils.append(abil)

        base, conditional = [], []
        for abil in card_abils:
            kind, detail = classify(abil, ABIL, reqs, CU)
            (base if kind == 'base' else conditional).append((abil, detail))

        seed_abils = role.get('abilities', [])
        base_ids = [a for a, _ in base]
        # 对比：seed 应 == base(基础技能)
        missing = [a for a in base_ids if a not in seed_abils]      # 数据应有但 seed 没有
        stale = [a for a in seed_abils if a not in base_ids]        # seed 有但数据判定非基础/废弃
        flag = '  <<< 不一致' if (missing or stale) else ''
        if missing or stale:
            mismatches += 1
        print(f"\n=== {role['nameEn']} ({role['nameZh']}) uid={uid}{flag}")
        print(f"  seed.abilities : {seed_abils}")
        print(f"  data.base      : {base_ids}")
        if conditional:
            print(f"  data.conditional(建筑解锁,不入基础): {[a for a,_ in conditional]}")
            for a, d in conditional:
                print(f"      - {a}: {d}")
        if missing:
            print(f"  ! seed 缺少基础技能: {missing}")
        if stale:
            print(f"  ! seed 含非基础/废弃技能: {stale}")

    print(f"\n{'='*50}\n不一致英雄数: {mismatches}")


if __name__ == '__main__':
    main()
