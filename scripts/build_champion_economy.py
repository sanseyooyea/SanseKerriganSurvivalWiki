"""Generate / update the "Champion" (冠军, roleId 25) entry in data/economy.json.

冠军是 economy.json 的「探机建造 + 独立产矿建筑 + 星灵折跃加速（手动）」型：由探机
(ChampionProbe，25 矿) 通过 ChampionBuild 建造，经济建筑是 3 座**各自独立、可直接建造**的
产矿建筑（不是升级链），被动直接产矿、无需采集。无英雄专属产气建筑（H-Champion.xml
无任何 AwardVespene）。

经济建筑（从 ChampionBuild 可建单位里筛出「带 MineralIncome* 行为」的 CUnit）：
  水晶碎片 +2   (ChampionShard)     每 4s 产 2 矿    100 矿
  闪亮水晶塔 +10 (ChampionCrystal)   每 4s 产 10 矿   400 矿 + 4 气
  先古遗迹 +25  (ChampionArtifact25) 每 4s 产 25 矿  1200 矿 + 10 气
每座挂 Champion<N>/ChampionCrystal2 行为 → PeriodicEffect=MineralIncome<N>（与
[[ks2-nova-economy]] 同款全生存者通用产矿模型，只是周期 4s、且是并列多档而非升级链）。

星灵折跃加速（ChampionChrono{Shard,Crystal,Monolith}，**手动**）：每座建筑自带一个主动
技能，对自身施加**永久** +50% 运作速度 buff（ChampionChronoBoost：Modification.TimeScale
=1.5，无 Duration = 永久）。三座的加速倍率一致(×1.5)，但气耗随建筑档位不同（碎片 1 气 /
水晶塔 4 气 / 遗迹 10 气，各 1 充能、可回充；因 buff 永久，施一次即长效）。因是玩家按气体
是否充裕决定的可选操作，故走 economy.json 的 chrono[] 字段（HeroEconomy.vue 渲染「加速
回本」列），而非折进头条产矿数字；气耗随建筑变化，用 costLabel 展示。

所有数值从 凯瑞甘生存2 最新版.SC2Map 提取，零硬编码。本脚本只新增/替换 Champion 一条，
其余原样保留，按原文件 CRLF + indent=2 ensure_ascii=False 回写。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import lib_map as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECON_JSON = os.path.join(ROOT, 'data', 'economy.json')
CHAMPION_XML = 'Base.SC2Data\\GameData\\Heroes\\Builder\\H-Champion.xml'

_ar = L.open_map()
_cat = L.build_catalog(_ar)
_gs = L.game_strings(_ar, 'Unit/Name/')
_CE = _cat.get('Effect', {})
_CB = _cat.get('Behavior', {})
_CA = _cat.get('Abil', {})


def _xml():
    return _ar.read_file(CHAMPION_XML).decode('utf-8', 'ignore')


def _build_targets():
    """ChampionBuild 可建造的单位列表（保序）。"""
    xml = _xml()
    m = re.search(r'<CAbilBuild id="ChampionBuild">(.*?)</CAbilBuild>', xml, re.S)
    return re.findall(r'Unit="([^"]+)"', m.group(1)) if m else []


def _unit_body(xml, uid):
    m = re.search(r'<CUnit id="' + re.escape(uid) + r'">(.*?)</CUnit>', xml, re.S)
    return m.group(1) if m else None


def _income_of(beh):
    """行为 → (每周期产矿, 周期秒)，若非产矿行为返回 None。"""
    b = _CB.get(beh, {})
    pe = b.get('PeriodicEffect')
    if not pe:
        return None
    amt = L.num(_CE.get(pe, {}).get('Resources[Minerals]'))
    if amt is None:
        return None
    per = L.num(b.get('Period'))
    return amt, (per if per is not None else 4)


def _chrono_of(body):
    """建筑自带的折跃加速技能 → (气耗, TimeScale, Duration|None)，无 → None。"""
    for ab in re.findall(r'AbilArray Link="([^"]+)"', body):
        if 'Chrono' not in ab:
            continue
        d = _CA.get(ab, {})
        eff = d.get('Effect')
        buff = _CB.get(_CE.get(eff, {}).get('Behavior'), {}) if eff else {}
        ts = L.num(buff.get('Modification.TimeScale'))
        if ts is None:
            continue
        gas = L.num(d.get('Cost.Resource[Vespene]')) or L.num(d.get('Cost.Resource')) or 0
        dur = L.num(buff.get('Duration'))
        return int(gas), ts, dur
    return None


def _name(uid):
    return _gs.get(uid, uid)


def _fmt(n):
    return int(n) if float(n) == int(n) else round(n, 2)


def build_entry():
    xml = _xml()
    buildings = []
    chrono_ts = None
    chrono_dur = None
    gas_by_name = []  # (显示名, 气耗) 用于 costLabel
    for uid in _build_targets():
        body = _unit_body(xml, uid)
        if not body:
            continue
        # 找该单位的产矿行为
        inc = None
        for beh in re.findall(r'BehaviorArray Link="([^"]+)"', body):
            got = _income_of(beh)
            if got:
                inc = got
                break
        if not inc:
            continue  # 非经济建筑（英雄大厅/锻造核心/信标等）跳过
        amt, per = inc
        cm = re.search(r'<CostResource index="Minerals" value="(\d+)"', body)
        cg = re.search(r'<CostResource index="Vespene" value="(\d+)"', body)
        minerals = int(cm.group(1)) if cm else 0
        gas = int(cg.group(1)) if cg else 0
        ch = _chrono_of(body)
        nm = _name(uid)
        notes = '由探机(ChampionProbe)直接建造，各档独立、无升级链。'
        notes += f'每 {_fmt(per)}s 产出 {_fmt(amt)} 晶矿。'
        if ch:
            cg_gas, ts, dur = ch
            chrono_ts = ts
            chrono_dur = dur
            gas_by_name.append((nm, cg_gas))
            notes += (f'可施放「星灵折跃加速」（{cg_gas} 气、每座 1 充能），'
                      f'{"永久" if dur is None else str(_fmt(dur)) + "s"}提升自身运作速度 '
                      f'×{_fmt(ts)}，产矿随之加快。')
        if gas:
            notes += f'建造额外需 {gas} 气。'
        notes += '可拆解回收(CommonSalvage)。'
        buildings.append({
            'id': uid,
            'nameZh': nm,
            'income': _fmt(amt),
            'incomePeriod': _fmt(per),
            'cost': minerals,
            'buildTime': None,
            'food': None,
            'upgradeTo': None,
            'gasCost': gas,
            'notes': notes,
        })
    buildings.sort(key=lambda b: b['income'])

    entry = {
        'hero': 'Champion',
        'incomeModel': (
            '冠军是「探机建造 + 独立产矿建筑 + 星灵折跃加速（手动）」型经济：由探机（25 矿）'
            '建造经济建筑，建筑被动直接产矿、无需采集，也没有英雄专属的产气建筑。'
            '\n\n'
            '【三档产矿建筑——并列、非升级链】水晶碎片 +2（100 矿）、闪亮水晶塔 +10（400 矿 + 4 气）、'
            '先古遗迹 +25（1200 矿 + 10 气）各自独立、可直接建造，不是逐级升级的关系；每座每 4 秒'
            '产出对应数量的晶矿（+2 / +10 / +25）。高档建筑建造需要额外气体。'
            '\n\n'
            '【星灵折跃加速】每座建筑都带一个手动主动技能，对自身施加**永久** +50% 运作速度'
            '（TimeScale ×1.5），产矿节奏随之加快约 50%——即「加速回本」列所示的回本时间。三座'
            '倍率一致，但气耗随档位不同：水晶碎片 1 气、水晶塔 4 气、遗迹 10 气（各 1 充能、可回充；'
            '因加速永久，施一次即长效）。是否施放由玩家按气体是否充裕决定，故头条产矿数字不折算加速。'
            '\n\n'
            '气体主要通过全局机制（如通用击杀奖励）获得，而非本英雄的专属产气建筑。'
            '所有建筑均可拆解(CommonSalvage)回收。'
        ),
        'buildings': buildings,
    }
    if chrono_ts is not None:
        cost_label = ' / '.join(f'{nm.split(" ")[0]} {g} 气' for nm, g in gas_by_name)
        entry['chrono'] = {
            'name': '星灵折跃加速',
            'timeScale': _fmt(chrono_ts),
            'duration': 'permanent' if chrono_dur is None else _fmt(chrono_dur),
            'costLabel': cost_label + '（随建筑档位）',
        }
    return entry


def main():
    with open(ECON_JSON, 'rb') as f:
        raw = f.read()
    crlf = b'\r\n' in raw
    trailing_nl = raw.endswith(b'\n')
    data = json.loads(raw.decode('utf-8'))

    entry = build_entry()
    idx = next((i for i, e in enumerate(data) if e.get('hero') == 'Champion'), None)
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
    print(f'{action} Champion entry in data/economy.json')
    print(f'  chrono: {entry.get("chrono")}')
    print(f'  buildings: {[(x["nameZh"], x["income"], x["incomePeriod"], x["cost"], x["gasCost"], x["upgradeTo"]) for x in b]}')


if __name__ == '__main__':
    main()
