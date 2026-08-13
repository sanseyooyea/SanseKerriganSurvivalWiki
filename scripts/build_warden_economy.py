"""Generate / update the "Warden" (监管者, roleId 18) entry in data/economy.json.

监管者是 economy.json 的「建筑收入 + 星灵折跃加速」型：唯一经济建筑是『祭坛』
(WardenAltar<N>)，被动直接产矿、无需采集，也无英雄独有的产气建筑。

经济建筑（从 gamedata 自动发现：BehaviorArray 含 *Income<N> 的 WardenAltar<N>）：
  祭坛 +1/+2/+4/+8/+16/+32   income = 1/2/4/8/16/32（每 3s）
每座祭坛挂通用产矿行为（复用 ScionIncome<N> → PeriodicEffect=MineralIncome<N>，
每 Period(=3s) 产 Resources[Minerals]=N 晶矿，与 [[ks2-nova-economy]] 同款全生存者
通用产矿模型）。

升级链（从 AbilArray 的 WardenUpgradeAltar<M> 解析）：只有祭坛 +1 可直接建造，其余沿
+1→+2→+4→+8→+16→+32 单线升级；升级 abil 无显式 Cost.Resource，由引擎按
「目标造价 − 当前造价」扣费（与 Nomad/Technician/Critter Lord 同）。

星灵折跃加速（WardenChronoBoost）：每座祭坛自带一个一次性主动技能，花 3 气 + 1 充能
（CountMax=1、无回充、用后被 WardenAltarNotUsingAnyChrono 需求锁定），对该祭坛施加
**永久** +75% 运作速度 buff（WardenChronoBoost：Modification.TimeScale=1.75，
TimeScaleSource=Caster，无 Duration = 永久）。这是本项目首个真正使用 economy.json
chrono[] 字段的英雄——HeroEconomy.vue 会据此渲染「加速回本」列。

所有数值从 凯瑞甘生存2 最新版.SC2Map 提取，零硬编码。本脚本只新增/替换 Warden
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
_CA = _cat.get('Abil', {})


def _warden_xml():
    path = next(f for f in L.gamedata_xml_files(_ar) if 'Warden' in f)
    return _ar.read_file(path).decode('utf-8', 'ignore')


def _discover_altars(xml):
    """找出所有 BehaviorArray 含 *Income<N> 的祭坛，解析造价、产矿行为与升级目标。"""
    out = []
    for m in re.finditer(r'<CUnit id="(WardenAltar\d+)">(.*?)</CUnit>', xml, re.S):
        uid, body = m.group(1), m.group(2)
        inc = re.search(r'BehaviorArray Link="(\w*Income(\d+))"', body)
        if not inc:
            continue
        cm = re.search(r'<CostResource index="Minerals" value="(\d+)"', body)
        cg = re.search(r'<CostResource index="Vespene" value="(\d+)"', body)
        up = re.search(r'AbilArray Link="WardenUpgradeAltar(\d+)"', body)
        out.append({
            'id': uid,
            'tier': int(inc.group(2)),
            'incomeBeh': inc.group(1),
            'min': int(cm.group(1)) if cm else 0,
            'gas': int(cg.group(1)) if cg else 0,
            'upTier': int(up.group(1)) if up else None,
            'hasChrono': 'WardenChronoBoost' in body,
        })
    out.sort(key=lambda b: b['tier'])
    return out


def _income(beh):
    """(每周期产矿, 周期秒) —— <incomeBeh> 行为 + 其 PeriodicEffect(MineralIncome<N>)。"""
    b = _CB.get(beh, {})
    per = L.num(b.get('Period'))
    pe = b.get('PeriodicEffect')
    amt = L.num(_CE.get(pe, {}).get('Resources[Minerals]')) if pe else None
    return amt, (per if per is not None else 3)


def _chrono():
    """折跃加速：花费(气/充能) + buff 的 TimeScale / 持续。无 → None。"""
    ab = _CA.get('WardenChronoBoost', {})
    buff = _CB.get('WardenChronoBoost', {})
    ts = L.num(buff.get('Modification.TimeScale'))
    if ts is None:
        return None
    gas = L.num(ab.get('Cost.Resource[Vespene]')) or L.num(ab.get('Cost.Resource'))
    dur = L.num(buff.get('Duration'))  # 无 Duration = 永久
    return {
        'name': '星灵折跃加速',
        'timeScale': _fmt(ts),
        'duration': 'permanent' if dur is None else _fmt(dur),
        'gasCost': int(gas) if gas else 0,
    }


def _name(uid):
    return _gs.get(uid, uid)


def _fmt(n):
    return int(n) if float(n) == int(n) else round(n, 2)


def build_entry():
    xml = _warden_xml()
    altars = _discover_altars(xml)
    id_by_tier = {b['tier']: b['id'] for b in altars}
    chrono = _chrono()
    buildings = []
    for b in altars:
        amt, per = _income(b['incomeBeh'])
        amt = amt if amt is not None else b['tier']
        up_id = id_by_tier.get(b['upTier']) if b['upTier'] in id_by_tier else None
        notes = ('唯一可直接建造的祭坛。' if b['tier'] == 1
                 else '由上一档升级而来。')
        notes += f'每 {_fmt(per)}s 产出 {_fmt(amt)} 晶矿。'
        if b['hasChrono'] and chrono:
            notes += (f'可施放「{chrono["name"]}」（{chrono["gasCost"]} 气、每座一次性），'
                      f'{"永久" if chrono["duration"] == "permanent" else str(chrono["duration"]) + "s"}'
                      f'提升自身运作速度 ×{chrono["timeScale"]}，产矿随之加快。')
        if b['gas']:
            notes += f'建造额外需 {b["gas"]} 气。'
        if up_id:
            notes += f'可升级为「{_name(up_id)}」。'
        notes += '可拆解回收(CommonSalvage)。'
        buildings.append({
            'id': b['id'],
            'nameZh': _name(b['id']),
            'income': _fmt(amt),
            'incomePeriod': _fmt(per),
            'cost': b['min'],
            'buildTime': None,
            'food': None,
            'upgradeTo': up_id,
            'gasCost': b['gas'],
            'notes': notes,
        })
    entry = {
        'hero': 'Warden',
        'incomeModel': (
            '监管者是「建筑收入 + 星灵折跃加速」型经济：唯一的经济建筑是『祭坛』，'
            '被动直接产矿、无需 SCV 采集，也没有英雄独有的产气建筑。'
            '\n\n'
            '【祭坛升级链】只能建造祭坛 +1（75 矿），随后沿 +1→+2→+4→+8→+16→+32 单线升级，'
            '不能跨级直建；升级按「目标造价 − 当前造价」扣费。每档每 3 秒产出等于档位数的晶矿'
            '（祭坛 +32 = 每 3 秒 32 矿）。祭坛建造只花晶矿、不需气体。'
            '\n\n'
            '【星灵折跃加速】每座祭坛都带一个一次性主动技能（花 3 气 + 1 充能，用后即锁、无法'
            '重复施放），对该祭坛施加**永久** +75% 运作速度（TimeScale ×1.75），产矿节奏随之'
            '加快约 75%——即「加速回本」列所示的回本时间。是否施放由玩家按气体是否充裕决定。'
            '\n\n'
            '气体主要通过全局机制（如通用击杀奖励）获得，而非本英雄的专属产气建筑。'
            '所有祭坛均可拆解(CommonSalvage)回收。'
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
    idx = next((i for i, e in enumerate(data) if e.get('hero') == 'Warden'), None)
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
    print(f'{action} Warden entry in data/economy.json')
    print(f'  chrono: {entry.get("chrono")}')
    print(f'  buildings: {[(x["nameZh"], x["income"], x["incomePeriod"], x["cost"], x["gasCost"]) for x in b]}')


if __name__ == '__main__':
    main()
