"""Generate / update the "Team Nova" (诺娃团队, roleId 11) entry in data/economy.json.

诺娃团队是刺客型「双货币」经济，属于 economy.json 的通用「建筑收入」型：

  矿 · 任务指挥部 (NovaMissionCommand +1..+32)
    直接产矿建筑，无需 SCV 采集。每档挂 NovaIncome<N> 行为，其 PeriodicEffect
    = MineralIncome<N>，每 Period(=3s) 产出 Resources[Minerals] 晶矿（+N 每 3s 产 N）。
    造价 = CUnit.CostResource（矿 + 高档另需气）。升级链 NovaUpgradeMC<N> 逐级 morph，
    Cost.Resource 缺省 → 引擎按「目标造价 − 当前造价」扣费（与技术员 2026-07-09 同款）。

  气 · 精神控制 / 本体攻击（写进 incomeModel 说明，不入 buildings）
    MindControl 完成得气 = ⌈目标(矿+气)总造价 / 5⌉；夺取建筑(customStructureSteal)
    封顶 min(bounty×2,10)/2。本体(诺娃/托什)攻击击杀敌方单位同样得气。
    公式见 Scripts/hero/nova.galaxy gt_NovaMindControlVespene_Func。

所有数值从 凯瑞甘生存2 最新版.SC2Map 提取，零硬编码（CONTRIBUTING「别硬编码」）。
economy.json 其余 18 条为手工维护：本脚本**只**新增/替换 Team Nova 一条，其余原样保留，
并按原文件的换行风格(CRLF)与 indent=2 ensure_ascii=False 回写，避免污染其它条目的 diff。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lib_map as L

TIERS = [1, 2, 4, 8, 16, 32]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECON_JSON = os.path.join(ROOT, 'data', 'economy.json')

_ar = L.open_map()
_cat = L.build_catalog(_ar)
_gs = L.game_strings(_ar)
_CU = _cat.get('Unit', {})
_CB = _cat.get('Behavior', {})
_CE = _cat.get('Effect', {})


def _mineral_cost(t):
    return L.num(_CU.get(f'NovaMissionCommand{t}', {}).get('CostResource[Minerals]')) or 0


def _gas_cost(t):
    return L.num(_CU.get(f'NovaMissionCommand{t}', {}).get('CostResource[Vespene]')) or 0


def _income(t):
    """(每周期产矿量, 周期秒) —— 读 NovaIncome<t> 行为的 PeriodicEffect(MineralIncome<t>)。"""
    beh = _CB.get(f'NovaIncome{t}', {})
    period = L.num(beh.get('Period')) or 3
    eff_id = beh.get('PeriodicEffect') or f'MineralIncome{t}'
    amt = L.num(_CE.get(eff_id, {}).get('Resources[Minerals]'))
    return (amt if amt is not None else t), period


def _name(t):
    return _gs.get(f'Unit/Name/NovaMissionCommand{t}', f'任务指挥部 +{t}')


def _fmt(n):
    return int(n) if float(n) == int(n) else round(n, 2)


def build_buildings():
    out = []
    for i, t in enumerate(TIERS):
        amt, period = _income(t)
        gas = _gas_cost(t)
        nxt = f'NovaMissionCommand{TIERS[i + 1]}' if i + 1 < len(TIERS) else None
        per_sec = _fmt(amt / period)
        notes = f'直接产矿建筑，每 {int(period)} 秒产出 {_fmt(amt)} 晶矿（≈{per_sec} 矿/秒），无需 SCV 采集。'
        if gas:
            notes += f'建造额外需 {int(gas)} 气。'
        if nxt:
            up_amt, _ = _income(TIERS[i + 1])
            notes += f'可升级为「{_name(TIERS[i + 1])}」（引擎按造价差扣费）。'
        else:
            notes += '最高档，无更高升级。'
        notes += '可拆解回收(CommonSalvage)。'
        out.append({
            'id': f'NovaMissionCommand{t}',
            'nameZh': _name(t),
            'income': _fmt(amt),
            'incomePeriod': int(period),
            'cost': int(_mineral_cost(t)),
            'buildTime': None,
            'food': None,
            'upgradeTo': nxt,
            'gasCost': int(gas),
            'notes': notes,
        })
    return out


def build_entry():
    return {
        'hero': 'Team Nova',
        'incomeModel': (
            '诺娃团队是刺客型「双货币」经济：矿由「任务指挥部」直接产出，'
            '气则靠精神控制与本体攻击从敌方单位身上榨取，把敌人的造价转化成自己的经济。'
            '\n\n'
            '【矿 · 任务指挥部】共 +1/+2/+4/+8/+16/+32 六档直接产矿建筑，'
            '每 3 秒产出对应档位的晶矿（+1 每 3 秒产 1，+32 每 3 秒产 32），无需 SCV 采集；'
            '+8 起额外需要少量气体建造。各档通过升级链逐级 morph（引擎按造价差扣费），并可拆解回收。'
            '\n\n'
            '【气 · 精神控制 / 攻击】诺娃或托什对敌方单位施放「精神控制」完成时获得气体 '
            '= ⌈目标总造价(矿+气) ÷ 5⌉；夺取敌方建筑时封顶为 min(赏金×2, 10) ÷ 2。'
            '此外本体攻击击杀敌方单位同样可获得气体。气用于建造高档指挥中心并支撑刺杀 / 支配战术。'
        ),
        'buildings': build_buildings(),
    }


def main():
    with open(ECON_JSON, 'rb') as f:
        raw = f.read()
    crlf = b'\r\n' in raw
    trailing_nl = raw.endswith(b'\n')
    data = json.loads(raw.decode('utf-8'))

    entry = build_entry()
    idx = next((i for i, e in enumerate(data) if e.get('hero') == 'Team Nova'), None)
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
    print(f'{action} Team Nova entry in data/economy.json')
    print(f'  任务指挥部 tiers: {[x["id"].replace("NovaMissionCommand", "+") for x in b]}')
    print(f'  income/3s: {[x["income"] for x in b]}  cost(min): {[x["cost"] for x in b]}  gas: {[x["gasCost"] for x in b]}')


if __name__ == '__main__':
    main()
