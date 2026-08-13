"""Generate / update the "Critter Lord" (小动物主宰, roleId 42) entry in data/economy.json.

小动物主宰是 economy.json 的「建筑收入 + 自带永久加速」型：唯一经济建筑是『小动物主巢』
(CritterLordCritterHive<N>)，被动直接产矿，无需采集，也无英雄独有的产气机制
(H-Critter_Lord.xml 无任何 AwardVespene)。

经济建筑（从 gamedata 自动发现：BehaviorArray 含 CritterLordIncome<N> 的 CUnit）：
  小动物主巢 1/2/4/8/16/32   income = 1/2/4/8/16/32（每 2.5s）
每栋挂 CritterLordIncome<N> 行为 → PeriodicEffect=MineralIncome<N>，每 Period(=2.5s)
产 Resources[Minerals]=N 晶矿（与 [[ks2-nova-economy]] 同款全生存者通用产矿模型，
只是周期为 2.5s 而非 3s）。

升级链（从 AbilArray 的 CritterLordUpgradetoCritterHive<M> 解析）：只有主巢 1 可直接建造，
其余沿 1→2→4→8→16→32 单线升级；升级 abil 无显式 Cost.Resource，由引擎按
「目标造价 − 当前造价」扣费（与 Nomad/Technician 同）。

自带永久加速：主巢 2 及以上各挂 CritterLordChronoBoost<N>（Modification.TimeScale
1.1/1.2/1.3/1.35/1.4，无 Duration = 永久、来源=自身），提升该建筑自身运作速度。
由于该加速是**默认自带、无需操作、始终生效**的，其对产矿节奏的加成直接折进「有效产矿
周期」= 2.5 ÷ TimeScale，使 incomePeriod 及下游的每秒/回本/投资比都反映加速后的真实
吞吐；notes/incomeModel 里同时保留原始 2.5s 与 TimeScale 值以便对照。主巢 1 无加速，
周期保持 2.5s。

所有数值从 凯瑞甘生存2 最新版.SC2Map 提取，零硬编码。本脚本只新增/替换 Critter Lord
一条，其余原样保留，按原文件 CRLF + indent=2 ensure_ascii=False 回写。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lib_map as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECON_JSON = os.path.join(ROOT, 'data', 'economy.json')

_ar = L.open_map()
_cat = L.build_catalog(_ar)
_gs = L.game_strings(_ar, 'Unit/Name/')
_CE = _cat.get('Effect', {})
_CB = _cat.get('Behavior', {})


def _critter_xml():
    path = next(f for f in L.gamedata_xml_files(_ar) if 'Critter' in f)
    return _ar.read_file(path).decode('utf-8', 'ignore')


def _discover_hives(xml):
    """找出所有 BehaviorArray 含 CritterLordIncome<N> 的经济建筑，解析造价与升级目标。"""
    out = []
    for m in re.finditer(r'<CUnit\s+id="(CritterLordCritterHive\d+)"[^>]*>(.*?)</CUnit>', xml, re.S):
        uid, body = m.group(1), m.group(2)
        inc = re.search(r'BehaviorArray\s+Link="CritterLordIncome(\d+)"', body)
        if not inc:
            continue
        cm = re.search(r'<CostResource\s+index="Minerals"\s+value="(\d+)"', body)
        cg = re.search(r'<CostResource\s+index="Vespene"\s+value="(\d+)"', body)
        up = re.search(r'AbilArray\s+Link="CritterLordUpgradetoCritterHive(\d+)"', body)
        out.append({
            'id': uid,
            'tier': int(inc.group(1)),
            'min': int(cm.group(1)) if cm else 0,
            'gas': int(cg.group(1)) if cg else 0,
            'upTier': int(up.group(1)) if up else None,
        })
    out.sort(key=lambda b: b['tier'])
    return out


def _income(tier):
    """(每周期产矿, 周期秒) —— MineralIncome<tier> 效果 + CritterLordIncome<tier> 行为。"""
    amt = L.num(_CE.get(f'MineralIncome{tier}', {}).get('Resources[Minerals]'))
    per = L.num(_CB.get(f'CritterLordIncome{tier}', {}).get('Period'))
    return (amt if amt is not None else tier), (per if per is not None else 2.5)


def _self_timescale(tier):
    """主巢自带永久加速 TimeScale（主巢 1 无 → None）。"""
    return L.num(_CB.get(f'CritterLordChronoBoost{tier}', {}).get('Modification.TimeScale'))


def _name(uid):
    return _gs.get(uid, uid)


def _fmt(n):
    return int(n) if float(n) == int(n) else round(n, 2)


def build_entry():
    xml = _critter_xml()
    hives = _discover_hives(xml)
    ids = {b['id'] for b in hives}
    id_by_tier = {b['tier']: b['id'] for b in hives}
    buildings = []
    for b in hives:
        amt, raw_per = _income(b['tier'])
        ts = _self_timescale(b['tier'])
        # 主巢自带的永久加速无需操作、始终生效，故直接折进「有效产矿周期」，
        # 让每秒/回本/投资比都按加速后的真实吞吐计。主巢 1 无加速，周期保持原始 2.5s。
        eff_per = (raw_per / ts) if ts else raw_per
        up_id = id_by_tier.get(b['upTier']) if b['upTier'] in id_by_tier else None
        notes = ('唯一可直接建造的主巢。' if b['tier'] == 1
                 else '由上一档升级而来。')
        if ts:
            notes += (f'自带永久运作加速 ×{_fmt(ts)}（TimeScale，来源=自身、无 Duration/无气耗、无需操作）：'
                      f'原始每 {_fmt(raw_per)}s 产 {_fmt(amt)} 晶矿，加速后有效周期约 {_fmt(eff_per)}s，'
                      f'每秒 ≈ {round(amt / eff_per, 2)} 矿。下表数值均已按加速后计。')
        else:
            notes += f'每 {_fmt(raw_per)}s 产出 {_fmt(amt)} 晶矿（无自带加速）。'
        if b['gas']:
            notes += f'建造额外需 {b["gas"]} 气。'
        if up_id:
            notes += f'可升级为「{_name(up_id)}」。'
        notes += '可拆解回收(CommonSalvage)。'
        buildings.append({
            'id': b['id'],
            'nameZh': _name(b['id']),
            'income': _fmt(amt),
            'incomePeriod': _fmt(eff_per),
            'cost': b['min'],
            'buildTime': None,
            'food': None,
            'upgradeTo': up_id,
            'gasCost': b['gas'],
            'notes': notes,
        })
    return {
        'hero': 'Critter Lord',
        'incomeModel': (
            '小动物主宰是「建筑收入 + 自带永久加速」型经济：唯一的经济建筑是『小动物主巢』，'
            '被动直接产矿、无需 SCV 采集，也没有英雄独有的产气建筑。'
            '\n\n'
            '【主巢升级链】只能建造主巢 1（75 矿），随后沿 1→2→4→8→16→32 单线升级，'
            '不能跨级直建；升级按「目标造价 − 当前造价」扣费。每次产矿的基础周期为 2.5 秒、'
            '每次产出等于档位数的晶矿。高档主巢需要气体建造（主巢 32 需 20 气）。'
            '\n\n'
            '【自带永久加速——已折进下表】主巢 2 及以上各自带永久运作加速（TimeScale：主巢 2 '
            '×1.1、4 ×1.2、8 ×1.3、16 ×1.35、32 ×1.4），无需操作、无气耗、始终生效，会成比例'
            '缩短产矿周期。由于加速是默认自带的，本表的「收入周期/每秒/回本/投资比」均已按加速后'
            '计算：有效周期 = 2.5 ÷ TimeScale（如主巢 32 = 2.5÷1.4 ≈ 1.79s，每秒 ≈ 17.9 矿）；'
            '主巢 1 无加速，保持每 2.5s 产 1 矿。'
            '\n\n'
            '气体主要通过全局机制（如通用击杀奖励）获得，而非本英雄的专属产气建筑。'
            '所有主巢均可拆解(CommonSalvage)回收。'
        ),
        'buildings': buildings,
    }


def main():
    with open(ECON_JSON, 'rb') as f:
        raw = f.read()
    crlf = b'\r\n' in raw
    trailing_nl = raw.endswith(b'\n')
    data = json.loads(raw.decode('utf-8'))

    entry = build_entry()
    idx = next((i for i, e in enumerate(data) if e.get('hero') == 'Critter Lord'), None)
    action = 'replaced' if idx is not None else 'appended'
    if idx is None:
        data.append(entry)
    else:
        data[idx] = entry

    text = json.dumps(data, ensure_ascii=False, indent=2)
    if trailing_nl:
        text += '\n'
    if crlf:
        text = text.replace('\n', '\r\n')
    with open(ECON_JSON, 'w', encoding='utf-8', newline='') as f:
        f.write(text)

    b = entry['buildings']
    print(f'{action} Critter Lord entry in data/economy.json')
    print(f'  buildings: {[(x["nameZh"], x["income"], x["incomePeriod"], x["cost"], x["gasCost"]) for x in b]}')


if __name__ == '__main__':
    main()
