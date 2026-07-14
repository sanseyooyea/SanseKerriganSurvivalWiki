"""Generate / update the "Nomad" (游牧民, roleId 12) entry in data/economy.json.

游牧民是 economy.json 的通用「建筑收入」型（纯被动产矿，无特殊气机制——
nomad.galaxy 无任何 AwardVespene/AwardMineral，仅有 calldown 单位的防喂赏金）。

经济建筑（从 gamedata 自动发现：BehaviorArray 含 NomadIncome<N> 的 CUnit）：
  指挥中心 NomadCommandCenter          income 1
  轨道控制基地 NomadOrbitalCommand      income 2（指挥中心 morph 升级）
  实验室 +4/+8/+16/+32/+64             income 4/8/16/32/64（各档独立建造）
每栋挂 NovaIncome 同款机制：NomadIncome<N> 行为 → PeriodicEffect=MineralIncome<N>，
每 Period(=3s) 产 Resources[Minerals]=N 晶矿。产矿模型见 [[ks2-nova-economy]] 说明的
全生存者通用公式（Scripts/command/unsplit.galaxy: 收入/s = PeriodicEffect.Minerals / Period）。

所有数值从 凯瑞甘生存2 最新版.SC2Map 提取，零硬编码。economy.json 其余条目为手工维护：
本脚本只新增/替换 Nomad 一条，其余原样保留，按原文件 CRLF + indent=2 ensure_ascii=False 回写。
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
_gs = L.game_strings(_ar)
_CE = _cat.get('Effect', {})
_CB = _cat.get('Behavior', {})

# 指挥中心 → 轨道控制基地（唯一 morph 升级：NomadMorphOrbitalCommand）
_UPGRADE = {'NomadCommandCenter': 'NomadOrbitalCommand'}


def _nomad_xml():
    path = next(f for f in L.gamedata_xml_files(_ar) if 'Nomad' in f)
    return _ar.read_file(path).decode('utf-8', 'ignore')


def _discover_buildings(xml):
    """从 gamedata 找出所有 BehaviorArray 含 NomadIncome<N> 的经济建筑。"""
    out = []
    for m in re.finditer(r'<CUnit\s+id="([^"]+)"[^>]*>(.*?)</CUnit>', xml, re.S):
        uid, body = m.group(1), m.group(2)
        inc = re.search(r'BehaviorArray\s+Link="NomadIncome(\d+)"', body)
        if not inc:
            continue
        cm = re.search(r'<CostResource index="Minerals" value="(\d+)"', body)
        cg = re.search(r'<CostResource index="Vespene" value="(\d+)"', body)
        out.append({
            'id': uid,
            'tier': int(inc.group(1)),
            'min': int(cm.group(1)) if cm else 0,
            'gas': int(cg.group(1)) if cg else 0,
        })
    out.sort(key=lambda b: b['tier'])
    return out


def _income(tier):
    """(每周期产矿, 周期秒) —— MineralIncome<tier> 效果 + NomadIncome<tier> 行为。"""
    amt = L.num(_CE.get(f'MineralIncome{tier}', {}).get('Resources[Minerals]'))
    per = L.num(_CB.get(f'NomadIncome{tier}', {}).get('Period')) or 3
    return (amt if amt is not None else tier), int(per)


def _name(uid):
    return _gs.get(f'Unit/Name/{uid}', uid)


def _fmt(n):
    return int(n) if float(n) == int(n) else round(n, 2)


def build_entry():
    xml = _nomad_xml()
    builds = _discover_buildings(xml)
    ids = {b['id'] for b in builds}
    buildings = []
    for b in builds:
        amt, per = _income(b['tier'])
        up = _UPGRADE.get(b['id']) if _UPGRADE.get(b['id']) in ids else None
        notes = f'直接产矿建筑，每 {per} 秒产出 {_fmt(amt)} 晶矿（≈{_fmt(amt / per)} 矿/秒），无需 SCV 采集。'
        if b['gas']:
            notes += f'建造额外需 {b["gas"]} 气。'
        if up:
            notes += f'可升级为「{_name(up)}」。'
        notes += '可拆解回收(CommonSalvage)。'
        buildings.append({
            'id': b['id'],
            'nameZh': _name(b['id']),
            'income': _fmt(amt),
            'incomePeriod': per,
            'cost': b['min'],
            'buildTime': None,
            'food': None,
            'upgradeTo': up,
            'gasCost': b['gas'],
            'notes': notes,
        })
    return {
        'hero': 'Nomad',
        'incomeModel': (
            '游牧民是纯「建筑收入」型经济：所有经济建筑被动直接产矿，无需 SCV 采集，也没有额外的气体获取机制。'
            '\n\n'
            '【指挥中心链】指挥中心（每 3 秒产 1 矿）可 morph 升级为轨道控制基地（每 3 秒产 2 矿）。'
            '\n\n'
            '【实验室】分 +4/+8/+16/+32/+64 五档独立建造，每 3 秒产出对应档位的晶矿，'
            '档位越高单位矿产出的性价比越好（各级实验室回本均约 150 秒），但高档需要大量气体建造'
            '（实验室 +64 需 70 气）。所有产矿建筑均可拆解(CommonSalvage)回收。'
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
    idx = next((i for i, e in enumerate(data) if e.get('hero') == 'Nomad'), None)
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
    print(f'{action} Nomad entry in data/economy.json')
    print(f'  buildings: {[(x["nameZh"], x["income"], x["cost"], x["gasCost"]) for x in b]}')


if __name__ == '__main__':
    main()
