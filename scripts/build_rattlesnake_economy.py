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

能量折跃加速（RattlesnakeEnergyChrono，**限时、可重复、可养成永久**）：每座星站自带一个
主动技能，消耗建筑**自身 100 能量**（非气体！）对自身施加**限时 15s** 的 +100% 运作速度
buff（RattlesnakeEnergyChronoBoost：Modification.TimeScale=2，Duration=15，来源=Caster），
有 15s 冷却、随能量回复可重复施放。星站能量池 EnergyStart=50 / EnergyMax=100，一次加速正好
耗尽约一整管。

能量回复升级（RattlesnakeUpgradeEnergyRegen05）：每座星站可花 1 气/次升级自身能量回复，
每次 +0.5 能量/s（Modification.VitalRegenArray[Energy]=0.5），最多 14 次（Cost.Charge.
CountMax=14）= 满级 +7 能量/s。满级后约每 100/7≈14.3s 回满一管，短于 15s 持续/冷却周期
→ ×2 加速近乎 100% 占空、实质**永久翻倍**（代价每座 14 气）。故与 Warden/Scion/Champion
天然永久不同，响尾蛇是「用气体把限时加速养成永久」。走 economy.json 的 chrono[] 字段，用
energyCost 表达能量消耗；「加速回本」列即满级稳态下的回本。

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
    """能量折跃加速：能量消耗 + buff 的 TimeScale / 持续 + 冷却。无 → None。"""
    ab = _CA.get('RattlesnakeEnergyChrono', {})
    buff = _CB.get('RattlesnakeEnergyChronoBoost', {})
    ts = L.num(buff.get('Modification.TimeScale'))
    if ts is None:
        return None
    energy = L.num(ab.get('Cost.Vital[Energy]')) or L.num(ab.get('Cost.Vital')) or 0
    dur = L.num(buff.get('Duration'))
    cd = L.num(ab.get('Cost.Cooldown.TimeUse'))
    return {
        'name': '能量折跃加速',
        'timeScale': _fmt(ts),
        'duration': 'permanent' if dur is None else _fmt(dur),
        'energyCost': int(energy),
        '_cooldown': _fmt(cd) if cd is not None else None,  # 内部用于文案，不入 JSON
    }


def _energy_regen_upgrade():
    """能量回复升级：每次气耗、最大层数、每层 +能量/s、满级 +能量/s。无 → None。"""
    ab = _CA.get('RattlesnakeUpgradeEnergyRegen05', {})
    buff = _CB.get('RattlesnakeUpgradeEnergyRegen05', {})
    per = L.num(buff.get('Modification.VitalRegenArray[Energy]'))
    if per is None:
        return None
    gas = L.num(ab.get('Cost.Resource[Vespene]')) or L.num(ab.get('Cost.Resource')) or 0
    stacks = L.num(ab.get('Cost.Charge.CountMax'))
    stacks = int(stacks) if stacks is not None else 0
    return {
        'gas': int(gas),
        'maxStacks': stacks,
        'perStack': _fmt(per),
        'maxRegen': _fmt(per * stacks),
    }


def _starport_energy():
    """星站能量池 (EnergyStart, EnergyMax)。"""
    u = _cat.get('Unit', {}).get('RattlesnakeDominionStarport4', {})
    return L.num(u.get('EnergyStart')), L.num(u.get('EnergyMax'))


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
    regen = _energy_regen_upgrade()
    e_start, e_max = _starport_energy()
    cd = chrono.pop('_cooldown', None) if chrono else None
    buildings = []
    for i, b in enumerate(ports):
        up_id = b['upId'] if b['upId'] in ids else None
        notes = ('由 SCV(15 矿)直接建造的入门级核心星站。' if i == 0
                 else '由上一档升级而来。')
        notes += f'每 {_fmt(b["period"])}s 产出 {_fmt(b["income"])} 晶矿。'
        if b['hasChrono'] and chrono:
            cd_txt = f'{cd}s 冷却' if cd is not None else '有冷却'
            notes += (f'可施放「{chrono["name"]}」（消耗自身 {chrono["energyCost"]} 能量、{cd_txt}，'
                      f'随能量回复可重复），限时 {chrono["duration"]}s 提升自身运作速度 '
                      f'×{chrono["timeScale"]}，加速期间产矿翻倍。')
            if regen:
                notes += (f'可花 {regen["gas"]} 气/次升级自身能量回复（+{regen["perStack"]} 能量/s·次，'
                          f'最多 {regen["maxStacks"]} 次 = +{regen["maxRegen"]} 能量/s），'
                          f'满级后约每 {round(chrono["energyCost"] / regen["maxRegen"], 1)}s 即可回满一次'
                          f'{chrono["energyCost"]} 能量、近乎持续维持翻倍。')
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
            '【能量折跃加速——限时爆发，可升级至近乎永久】每座星站都带一个主动技能，消耗建筑'
            f'**自身 {chrono["energyCost"] if chrono else 100} 能量**（不是气体）对自身施加'
            f'**限时 {chrono["duration"] if chrono else 15} 秒**的 +100% 运作速度（TimeScale ×'
            f'{chrono["timeScale"] if chrono else 2}），加速期间产矿翻倍；'
            f'有 {cd if cd is not None else 15} 秒冷却、随建筑能量回复可反复施放。'
            '\n\n'
            f'星站能量池为 {int(e_start) if e_start else 50}/{int(e_max) if e_max else 100}'
            f'（起始/上限），每次加速正好耗尽约一整管能量。每座星站可花 '
            f'{regen["gas"] if regen else 1} 气/次升级自身能量回复（每次 +{regen["perStack"] if regen else 0.5} '
            f'能量/秒，最多 {regen["maxStacks"] if regen else 14} 次，满级 +{regen["maxRegen"] if regen else 7} '
            f'能量/秒）。满级后约每 '
            f'{round((chrono["energyCost"] if chrono else 100) / (regen["maxRegen"] if regen else 7), 1)} 秒'
            f'即可回满一次 {chrono["energyCost"] if chrono else 100} 能量——已短于加速的 '
            f'{chrono["duration"] if chrono else 15}s 持续/{cd if cd is not None else 15}s 冷却周期，'
            '意味着投入满额气体（每座 14 气）后 ×2 加速可近乎 100% 占空、实质变成**永久翻倍**。'
            '与监管者/赛恩/冠军天然永久的加速不同，响尾蛇是「用气体把限时加速养成永久」，因此下表'
            '「加速回本」列表示的是**加速生效期间**的回本（也即满级能量回复后的稳态目标值）。'
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
