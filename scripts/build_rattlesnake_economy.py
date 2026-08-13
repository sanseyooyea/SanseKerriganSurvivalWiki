"""Generate / update the "Rattlesnake" (响尾蛇, roleId 38) entry in data/economy.json.

响尾蛇是 economy.json 的「SCV 建造 + 升级链产矿建筑 + 能量折跃加速（限时可重复）」型：
由 SCV（15 矿）通过 RattlesnakebuildSCV 建造经济建筑，唯一经济建筑是『核心星站』
(RattlesnakeDominionStarport<N>)，被动直接产矿、无需采集。无英雄专属产气建筑
(H-Rattlesnake.xml 无任何 AwardVespene)。

经济建筑（从 gamedata 自动发现：BehaviorArray 含产矿行为的 RattlesnakeDominionStarport<N>）：
  核心星站 +4/+8/+16/+32   income = 4/8/16/32（每 3s）  造价 200/500/1300/3300 矿
产矿行为命名不规则（Rattlesnake4Income / Rattlesnake8Income / RattlesnakeIncome16 /
复用 DeltaSquad32Income）→ PeriodicEffect=MineralIncome<N>（与 [[ks2-nova-economy]]
同款全生存者通用产矿模型，周期 3s）。注意本英雄从 +4 起步（无 +1/+2 档）。

升级链（从 AbilArray 的 RattlesnakeUpgradetoDS<N> → InfoArray.Unit 解析目标）：只有
核心星站 +4 可由 SCV 直接建造，其余沿 +4→+8→+16→+32 单线升级；升级 abil 无显式
Cost.Resource，由引擎按「目标造价 − 当前造价」扣费。

能量折跃加速（RattlesnakeEnergyChrono，**限时、可重复**）：每座星站自带一个主动技能，
消耗建筑**自身 100 能量**（非气体！）对自身施加**限时 15s** 的 +100% 运作速度 buff
（RattlesnakeEnergyChronoBoost：Modification.TimeScale=2，Duration=15，来源=Caster），
有 15s 冷却、随能量回复可重复施放（另有 RattlesnakeUpgradeEnergyRegen05 用 1 气升级能量
回复，最多 14 次）。与 Warden/Scion/Champion 的**永久**加速不同——这是限时爆发，故
「加速回本」列表示的是**加速生效期间**的最优回本（非长期稳态）。走 economy.json 的
chrono[] 字段，用 energyCost 表达能量消耗。

所有数值从 凯瑞甘生存2 最新版.SC2Map 提取，零硬编码。本脚本只新增/替换 Rattlesnake
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
RATTLE_XML = 'Base.SC2Data\\GameData\\Heroes\\Support\\H-Rattlesnake.xml'

_ar = L.open_map()
_cat = L.build_catalog(_ar)
_gs = L.game_strings(_ar, 'Unit/Name/')
_CE = _cat.get('Effect', {})
_CB = _cat.get('Behavior', {})
_CA = _cat.get('Abil', {})


def _xml():
    return _ar.read_file(RATTLE_XML).decode('utf-8', 'ignore')


def _unit_body(xml, uid):
    m = re.search(r'<CUnit id="' + re.escape(uid) + r'">(.*?)</CUnit>', xml, re.S)
    return m.group(1) if m else None


def _income_of(beh):
    """行为 → (每周期产矿, 周期秒)；非产矿行为返回 None。"""
    b = _CB.get(beh, {})
    pe = b.get('PeriodicEffect')
    if not pe:
        return None
    amt = L.num(_CE.get(pe, {}).get('Resources[Minerals]'))
    if amt is None:
        return None
    per = L.num(b.get('Period'))
    return amt, (per if per is not None else 3)


def _chrono():
    """能量折跃加速：能量消耗 + buff 的 TimeScale / 持续。无 → None。"""
    ab = _CA.get('RattlesnakeEnergyChrono', {})
    buff = _CB.get('RattlesnakeEnergyChronoBoost', {})
    ts = L.num(buff.get('Modification.TimeScale'))
    if ts is None:
        return None
    energy = L.num(ab.get('Cost.Vital[Energy]')) or L.num(ab.get('Cost.Vital')) or 0
    dur = L.num(buff.get('Duration'))
    return {
        'name': '能量折跃加速',
        'timeScale': _fmt(ts),
        'duration': 'permanent' if dur is None else _fmt(dur),
        'energyCost': int(energy),
    }


def _discover_starports(xml):
    """所有带产矿行为的核心星站，解析造价、产矿、升级目标、是否带 chrono。"""
    out = []
    for m in re.finditer(r'<CUnit id="(RattlesnakeDominionStarport\d+)">(.*?)</CUnit>', xml, re.S):
        uid, body = m.group(1), m.group(2)
        inc = None
        for beh in re.findall(r'BehaviorArray Link="([^"]+)"', body):
            got = _income_of(beh)
            if got:
                inc = got
                break
        if not inc:
            continue
        cm = re.search(r'<CostResource index="Minerals" value="(\d+)"', body)
        cg = re.search(r'<CostResource index="Vespene" value="(\d+)"', body)
        up = re.search(r'AbilArray Link="(RattlesnakeUpgradetoDS\d+)"', body)
        up_id = _CA.get(up.group(1), {}).get('InfoArray.Unit') if up else None
        out.append({
            'id': uid,
            'income': inc[0],
            'period': inc[1],
            'min': int(cm.group(1)) if cm else 0,
            'gas': int(cg.group(1)) if cg else 0,
            'upId': up_id,
            'hasChrono': 'RattlesnakeEnergyChrono' in body,
        })
    out.sort(key=lambda b: b['income'])
    return out


def _name(uid):
    return _gs.get(uid, uid)


def _fmt(n):
    return int(n) if float(n) == int(n) else round(n, 2)


def build_entry():
    xml = _xml()
    ports = _discover_starports(xml)
    ids = {b['id'] for b in ports}
    chrono = _chrono()
    buildings = []
    for i, b in enumerate(ports):
        up_id = b['upId'] if b['upId'] in ids else None
        notes = ('由 SCV(15 矿)直接建造的入门级核心星站。' if i == 0
                 else '由上一档升级而来。')
        notes += f'每 {_fmt(b["period"])}s 产出 {_fmt(b["income"])} 晶矿。'
        if b['hasChrono'] and chrono:
            notes += (f'可施放「{chrono["name"]}」（消耗自身 {chrono["energyCost"]} 能量、15s 冷却，'
                      f'随能量回复可重复），限时 {chrono["duration"]}s 提升自身运作速度 '
                      f'×{chrono["timeScale"]}，加速期间产矿翻倍。')
        if b['gas']:
            notes += f'建造额外需 {b["gas"]} 气。'
        if up_id:
            notes += f'可升级为「{_name(up_id)}」。'
        notes += '可拆解回收(CommonSalvage)。'
        buildings.append({
            'id': b['id'],
            'nameZh': _name(b['id']),
            'income': _fmt(b['income']),
            'incomePeriod': _fmt(b['period']),
            'cost': b['min'],
            'buildTime': None,
            'food': None,
            'upgradeTo': up_id,
            'gasCost': b['gas'],
            'notes': notes,
        })
    entry = {
        'hero': 'Rattlesnake',
        'incomeModel': (
            '响尾蛇是「SCV 建造 + 升级链产矿建筑 + 能量折跃加速（限时可重复）」型经济：由 SCV'
            '（15 矿）建造经济建筑，唯一经济建筑是『核心星站』，被动直接产矿、无需采集，也没有'
            '英雄专属的产气建筑。'
            '\n\n'
            '【核心星站升级链】SCV 只能直接建造核心星站 +4（200 矿），随后沿 +4→+8→+16→+32 单线'
            '升级，不能跨级直建；升级按「目标造价 − 当前造价」扣费。每档每 3 秒产出等于档位数的'
            '晶矿（核心星站 +32 = 每 3 秒 32 矿）。注意本英雄从 +4 起步，没有 +1/+2 小档。'
            '\n\n'
            '【能量折跃加速——限时爆发，非永久】每座星站都带一个主动技能，消耗建筑**自身 100 能量**'
            '（不是气体）对自身施加**限时 15 秒**的 +100% 运作速度（TimeScale ×2），加速期间产矿'
            '翻倍；有 15 秒冷却、随建筑能量回复可反复施放（另可用 1 气升级能量回复，最多 14 次）。'
            '与监管者/赛恩/冠军的永久加速不同，这是限时爆发，因此下表「加速回本」列表示的是'
            '**加速生效期间**的最优回本，并非长期稳态值。'
            '\n\n'
            '气体主要通过全局机制（如通用击杀奖励）获得，而非本英雄的专属产气建筑。'
            '所有星站均可拆解(CommonSalvage)回收。'
        ),
        'buildings': buildings,
    }
    if chrono:
        entry['chrono'] = chrono
    return entry


def main():
    with open(ECON_JSON, 'rb') as f:
        raw = f.read()
    crlf = b'\r\n' in raw
    trailing_nl = raw.endswith(b'\n')
    data = json.loads(raw.decode('utf-8'))

    entry = build_entry()
    idx = next((i for i, e in enumerate(data) if e.get('hero') == 'Rattlesnake'), None)
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
    print(f'{action} Rattlesnake entry in data/economy.json')
    print(f'  chrono: {entry.get("chrono")}')
    print(f'  buildings: {[(x["nameZh"], x["income"], x["incomePeriod"], x["cost"], x["gasCost"], x["upgradeTo"]) for x in b]}')


if __name__ == '__main__':
    main()
