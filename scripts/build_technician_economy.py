"""
Generate data/technician-economy.json — Technician's unique transmute-based economy.
Standalone file (not merged into economy.json, whose passive income/period/chrono
schema does not fit Technician). All numbers verified from 凯瑞甘生存2 最新版.SC2Map:
  - factory build/upgrade costs: CUnit CostResource + CAbil UpgradeTo*.Cost
  - transmute recipes: PARSED from Button/Name 文本（嬗变X矿物为Y矿物 / 嬗变X矿物和Zg为Y矿物）
    —— 不再硬编码，避免与地图脱节（曾把 +20%/+44% 误写成递减公式）
  - kill bounty formula + multiplier: Scripts/hero/technician.galaxy
"""
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import lib_map as L

TIERS = [1, 2, 4, 8, 16, 32, 64, 128]

# 从地图按钮文本解析转化配方（每档投入矿固定 = TIER 基数 ×100）
_ar = L.open_map()
_gs = L.game_strings(_ar)
_cat = L.build_catalog(_ar)
_CU = _cat.get('Unit', {})
_CA = _cat.get('Abil', {})


def _factory_costs():
    """从地图提取各档工厂造价，杜绝硬编码（教训：CONTRIBUTING「别硬编码」）。
    BUILD = 工厂单位从零建造价 CUnit.CostResource；
    UPGRADE = 升级 morph 花费。

    升级是 CAbilMorph。旧版把 Cost.Resource 硬编码成「高档−低档」建造差价
    （如 +1→+2 = 150−50 = 100）；新版(2026-07-09)删掉了显式 Cost.Resource，
    改由引擎按 morph 的「目标单位造价 − 当前单位造价」自动扣费。因此当显式
    Cost.Resource 缺失时，回退到建造差价 build[t] − build[prev]（两版结果一致，
    且保持「直接造 == 逐级升上来」总价相等的自洽经济）。免费升级会破坏经济
    （+1 造25 一路升到 +128 仅25），故不能取 0。"""
    build, upgrade = {}, {}
    for t in TIERS:
        uc = L.num(_CU.get(f'TechnicianTransmutationFactory{t}', {}).get('CostResource'))
        if uc is not None:
            build[t] = uc
        ac = L.num(_CA.get(f'TechnicianUpgradeToTransmutationFactory{t}', {}).get('Cost.Resource'))
        if ac is not None:
            upgrade[t] = ac
    # 回退：显式升级花费缺失时，用建造差价（引擎实际扣费口径）。
    for i, t in enumerate(TIERS):
        if i == 0:
            continue  # +1 直接建造，无升级来源
        prev = TIERS[i - 1]
        if upgrade.get(t) is None and build.get(t) is not None and build.get(prev) is not None:
            upgrade[t] = build[t] - build[prev]
    return build, upgrade


BUILD, UPGRADE = _factory_costs()


def _parse_recipes():
    """解析 TechnicianTransmute<N>Minerals（纯矿）与 *<G>Gas（矿+气）按钮文本。
    纯矿: 嬗变{in}矿物为{out}矿物
    矿气: 嬗变{in}矿物和{g}瓦斯为{out}矿物
    返回 {min_in: (min_in, min_out)} 与 {min_in: (min_in, gas, gas_out)}。"""
    mineral, gas = {}, {}
    for key, val in _gs.items():
        if 'Button/Name/TechnicianTransmute' not in key:
            continue
        m = re.search(r'嬗变(\d+)矿物和(\d+)瓦斯为(\d+)矿物', val)
        if m:
            mi, g, out = int(m.group(1)), int(m.group(2)), int(m.group(3))
            gas[mi] = (mi, g, out)
            continue
        m = re.search(r'嬗变(\d+)矿物为(\d+)矿物', val)
        if m:
            mi, out = int(m.group(1)), int(m.group(2))
            mineral[mi] = (mi, out)
    return mineral, gas


_MIN, _GAS = _parse_recipes()
# 每档投入矿 = tier × 100（+1 投入100，+2 投入200…）
MIN_RECIPE = {t: _MIN[t * 100] for t in TIERS}
GAS_RECIPE = {t: _GAS[t * 100] for t in TIERS}

# 转化周期（地图实测）：投入 5s（Transmute.InfoArray.Time）+ 转化 15s
# （TransmutationFactoryTransmuting.Duration）= 完整周期 20s（冷却 20s 覆盖整周期）。
INVEST_SEC = 5
TRANSMUTE_SEC = 15
CYCLE_SEC = INVEST_SEC + TRANSMUTE_SEC  # 20

factories = []
for t in TIERS:
    m_in, m_out = MIN_RECIPE[t]
    g_min, g_gas, g_out = GAS_RECIPE[t]
    mineral_net = m_out - m_in
    gas_net = g_out - g_min
    gas_value = round((g_out - m_out) / g_gas, 2)  # 每 1 点气换来的额外矿
    min_net_per_sec = round(mineral_net / CYCLE_SEC, 2)
    gas_net_per_sec = round(gas_net / CYCLE_SEC, 2)
    # 回本时间 = 总成本 ÷ 每秒净产出。总成本 = 建造费 + 单次投入矿（纯矿配方投入 = m_in）。
    # 投入资金计入成本（用户要求）：建好工厂并垫付一次投入，多久靠净赚赚回这总投入。
    total_cost = BUILD[t] + m_in
    payback_sec = round(total_cost / min_net_per_sec) if min_net_per_sec else None
    factories.append({
        "tier": t,
        "nameZh": f"转化工厂 +{t}",
        "id": f"TechnicianTransmutationFactory{t}",
        "buildCost": BUILD[t],
        "upgradeCost": UPGRADE.get(t),  # None for +1 (base, built directly)
        "totalCost": total_cost,        # 建造费 + 单次投入矿（回本分子）
        "paybackSec": payback_sec,      # 回本秒数 = 总成本 ÷ 纯矿每秒净产出
        "mineralRecipe": {
            "in": m_in, "out": m_out, "net": mineral_net,
            "returnPct": round(mineral_net / m_in * 100, 1),
            "netPerSec": min_net_per_sec
        },
        "gasRecipe": {
            "mineralIn": g_min, "gasIn": g_gas, "out": g_out, "net": gas_net,
            "returnPct": round(gas_net / g_min * 100, 1),
            "netPerSec": gas_net_per_sec,
            "gasValue": gas_value
        }
    })

data = {
    "hero": "Technician",
    "roleId": 23,
    "nameZh": "技术员",
    "economyType": "transmute",
    "summary": ("技术员的经济是一套主动闭环：防御塔击杀凯瑞甘单位获得气体，"
                "气体经倍增器放大后，喂入转化工厂将「矿+气」转化为更多矿，循环滚雪球。"
                "与加速技能强相关——加速使塔更快击杀、出气更快。"),
    "killBounty": {
        "baseFormula": "ceil(被杀单位总造价(矿+气) / 5)",
        "baseDescription": "塔击杀凯瑞甘单位时，按其总造价的 1/5 折算为基础气体收入。",
        "awards": ["气体", "经验"],
        "multiplier": {
            "source": "倍增器（蓄电器 Accumulator）范围光环",
            "radiusNote": "范围随等级递增：x2=6 / x3=8 / x4=10 格",
            "refreshSec": 4,
            "buffDurationSec": 5,
            "note": "范围内塔的击杀，气体与经验同时按倍数结算；技术员本体在塔附近(≤10格)时经验按(倍数-1)结算。",
            "tiers": [
                {"level": "x2", "multiplier": 2, "buildCost": 125, "radiusCells": 6},
                {"level": "x3", "multiplier": 3, "upgradeFromX2": 250, "radiusCells": 8},
                {"level": "x4", "multiplier": 4, "upgradeFromX3": 500, "radiusCells": 10}
            ],
            "sellable": True
        },
        "customBounty": [
            {"target": "高级塔 (AdvancedTowers)", "gas": 7},
            {"target": "顶级塔 / 墙体 (SuperiorTowers / WallTechnician)", "gas": 10}
        ]
    },
    "transmutation": {
        "ability": "转化工厂 (TransmutationFactory)",
        "investSec": INVEST_SEC,
        "transmuteSec": TRANSMUTE_SEC,
        "cycleSec": CYCLE_SEC,
        "cooldownSec": 20,
        "autoCast": True,
        "autoUpgrade": True,
        "autoUpgradeNote": "余矿足够支付「升级费 + 在产工厂转化所需矿」时，工厂自动逐级升档。",
        "mineralReturnRule": "纯矿回报率固定 +20%（投入N矿 → 1.2N矿，所有档位一致）",
        "gasReturnRule": "矿气回报率固定 +44%（投入N矿+0.01N气 → 1.44N矿，所有档位一致）",
        "paybackNote": "回本时间 = 总成本 ÷ 纯矿每秒净产出；总成本 = 建造费 + 单次投入矿（净产出 = 单次净赚 ÷ 20s 周期）。",
        "factories": factories
    },
    "acceleration": {
        "ability": "加速 (Accelerate)",
        "speedupPct": 400,
        "speedupNote": "建筑运作速度提升 400%（TimeScale 5 = 5 倍速）。",
        "durationSec": 10,
        "gasCost": 5,
        "energyCost": 50,
        "cooldownSec": 60,
        "autoCast": True,
        "unitEffectFraction": 0.25,
        "allyEffectFraction": 0.25,
        "effectNote": "对单位、对盟友建筑的加速效果仅为 1/4。",
        # 5 级：搜索半径来自地图 AccelerationSearchArea1~5（2/3/4/5/6 格）；
        # 范围内最多加速的建筑数为范围副产物上限（galaxy 脚本计数，实测 6/9/12/16/25）。
        "levels": [
            {"level": 1, "radiusCells": 2, "maxStructures": 6},
            {"level": 2, "radiusCells": 3, "maxStructures": 9},
            {"level": 3, "radiusCells": 4, "maxStructures": 12},
            {"level": 4, "radiusCells": 5, "maxStructures": 16},
            {"level": 5, "radiusCells": 6, "maxStructures": 25},
        ],
        "economyRelation": ("加速提升塔的开火节奏 → 单位时间击杀更多 → 出气更快 → "
                            "转化更多矿。加速直接决定整套经济引擎的转速。")
    },
    "_source": "凯瑞甘生存2 最新版.SC2Map (verified 2026-06-11)"
}

with open('data/technician-economy.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('wrote data/technician-economy.json')
print('factories:', len(factories), '| tiers:', [f["tier"] for f in factories])
