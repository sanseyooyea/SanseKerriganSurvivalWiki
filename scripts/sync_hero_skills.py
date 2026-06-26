"""
把 data/seed/roles.seed.json 的英雄技能同步为地图命令卡的真实技能集。

复用 audit_hero_skills.py 的命令卡解析 + base/conditional 分类，叠加精修策略：

  - 系统/UI 噪音(que1 / *CancelToSelection / SpawnObserver / EnergyCapacitor /
    ProgressRally / Add|RemoveFromSelection)：永不作为技能，丢弃。
  - 跨英雄通用命令(CommonBlinkHero / Sell / Salvage / Repair*)：保留 seed 现状——
    seed 已列且命令卡仍有 → 保留；seed 没有 → 不自动加；命令卡已无 → 当废弃删。
    (避免给技术员等强行塞「闪现/修理/出售」，同时保住灵魂等把闪现当招牌技能的。)
  - 其余命令卡 base 技能：照实同步(补缺失、删废弃)，含被重做英雄的新技能名。
  - conditional(建筑解锁)：写入 role['conditionalAbilities'] = [{id, requires:[{id,nameZh}]}]，
    前端标注「需建筑解锁」。

用法：
  PYTHONUTF8=1 PYTHONPATH=scripts python scripts/sync_hero_skills.py           # dry-run，仅打印逐英雄变更
  PYTHONUTF8=1 PYTHONPATH=scripts python scripts/sync_hero_skills.py --write    # 写回 seed
"""
import json
import re
import sys

import audit_hero_skills as A
import lib_map as L

SEED = A.SEED

SYSTEM_NOISE = re.compile(
    r'^que\d+$|CancelToSelection|^Cancel|Cancel$|SpawnObserver|EnergyCapacitor|'
    r'ProgressRally|AddToSelection|RemoveFromSelection|^Upgrade|OrbCreation')
GENERIC_UTILITY = re.compile(r'^CommonBlinkHero$|^Sell$|^Salvage$|Repair')


def all_card_abil_ids(cunit_xml):
    """该英雄单位【所有】命令卡(主卡+子卡)里出现过的 AbilCmd 技能 id 集合。
    用于判断 seed 里的技能是否真的消失了——子卡技能(如召唤/训练)在这里能被看到，
    避免把实际存在于子菜单的技能误判为废弃删掉。"""
    ids = set()
    for mt in re.finditer(r'<LayoutButtons\b([^/>]*)/?>', cunit_xml):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', mt.group(1)))
        if attrs.get('Type') != 'AbilCmd':
            continue
        ac = attrs.get('AbilCmd', '')
        ab = ac.split(',')[0] if ac else ''
        if ab:
            ids.add(ab)
    return ids


def card_classification(uid, cunits_raw, reqs, CU, ABIL):
    raw = cunits_raw.get(uid)
    if not raw:
        return None, None
    card = A.main_card_abilcmds(raw)
    card_abils = []
    for _face, abil in card:
        if not abil or abil in A.GENERIC_ABILS or abil in card_abils:
            continue
        if abil.startswith(A.GENERIC_PREFIXES) or A.BUILD_HINT.search(abil):
            continue
        if A.GENERIC_HINT.search(abil):
            continue
        card_abils.append(abil)
    base, cond = [], []
    for abil in card_abils:
        kind, detail = A.classify(abil, ABIL, reqs, CU)
        (base if kind == 'base' else cond).append((abil, detail))
    return [a for a, _ in base], cond


def main():
    write = '--write' in sys.argv
    archive = L.open_map()
    cat = L.build_catalog(archive)
    CU, ABIL = cat['Unit'], cat['Abil']
    cunits_raw = A.index_raw_cunits(archive)
    reqs = A.index_requirements(archive)
    gs = L.game_strings(archive)

    def unit_zh(bid):
        return gs.get(f'Unit/Name/{bid}', bid)

    seed = json.load(open(SEED, encoding='utf-8'))
    changed = 0
    for role in seed:
        uid = A.hero_unit_id(role)
        base_ids, cond = card_classification(uid, cunits_raw, reqs, CU, ABIL)
        if base_ids is None:
            continue  # 无原始 CUnit(召唤型英雄)，跳过不动
        all_ids = all_card_abil_ids(cunits_raw.get(uid, ''))  # 主卡+子卡全部技能

        old_abils = role.get('abilities', [])
        old_order = {a: i for i, a in enumerate(old_abils)}

        # 主卡建筑解锁的情境技能(系统噪音丢弃)
        new_cond = []
        for a, detail in cond:
            if SYSTEM_NOISE.search(a):
                continue
            blds = re.findall(r"'([^']+)'", detail)
            new_cond.append({'id': a, 'requires': [{'id': b, 'nameZh': unit_zh(b)} for b in blds]})
        cond_ids = {c['id'] for c in new_cond}

        # 新 base 构造：
        new_abils = []
        # 1) 保留 seed 里仍存在于【任意命令卡】的技能(子卡技能不误删)，排除被移到情境的
        for a in old_abils:
            if a in cond_ids:
                continue
            if a in all_ids:
                new_abils.append(a)
            # 否则：所有命令卡都没有 -> 真废弃，丢弃
        # 2) 新增主卡 base 技能(系统噪音丢弃；通用命令 seed 没有就不加)；不自动加子卡技能
        for a in base_ids:
            if a in new_abils or a in cond_ids:
                continue
            if SYSTEM_NOISE.search(a):
                continue
            if GENERIC_UTILITY.search(a) and a not in old_abils:
                continue
            new_abils.append(a)
        # 去重强化变体：若 X 与 X2 同时出现，X2 是同一技能升级版，丢弃
        new_abils = [a for a in new_abils if not (a.endswith('2') and a[:-1] in new_abils)]
        new_abils.sort(key=lambda a: old_order.get(a, 10**9))

        old_cond_ids = [c['id'] for c in role.get('conditionalAbilities', [])]
        new_cond_ids = [c['id'] for c in new_cond]

        if new_abils == old_abils and new_cond_ids == old_cond_ids:
            continue
        changed += 1
        added = [a for a in new_abils if a not in old_abils]
        removed = [a for a in old_abils if a not in new_abils and a not in cond_ids]
        moved = [a for a in old_abils if a in cond_ids]
        print(f"\n=== {role['nameEn']} ({role['nameZh']})")
        print(f"  base: {old_abils}")
        print(f"     -> {new_abils}")
        if added:
            print(f"  + 新增: {added}")
        if removed:
            print(f"  - 移除(全卡未见,真废弃): {removed}")
        if moved:
            print(f"  ~ 移到情境标注: {moved}")
        if new_cond:
            print(f"  ~ 情境(建筑解锁): " +
                  "; ".join(f"{c['id']}(需 {'/'.join(r['nameZh'] for r in c['requires'])})"
                            for c in new_cond))

        role['abilities'] = new_abils
        if new_cond:
            role['conditionalAbilities'] = new_cond
        elif 'conditionalAbilities' in role:
            del role['conditionalAbilities']

    print(f"\n{'='*50}\n变更英雄数: {changed}  (write={write})")
    if write:
        json.dump(seed, open(SEED, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"已写回 {SEED}")


if __name__ == '__main__':
    main()
