"""
Generate data/technician-economy.json — Technician's unique transmute-based economy.
Standalone file (not merged into economy.json, whose passive income/period/chrono
schema does not fit Technician). All numbers verified from 凯瑞甘生存2 最新版.SC2Map:
  - factory build/upgrade costs: CUnit CostResource + CAbil UpgradeTo*.Cost
  - transmute recipes: PARSED from Scripts/hero/technician.galaxy 的真实倍率
    （lv_tRANSMUTIN_MINERALS_<N> = CeilingI(N*mult)）—— 按钮文本(Button/Name)只是
    显示标签，地图更新后未同步(仍写死 +20%/+44%)，真实产出逐档递减，必须读脚本。
  - kill bounty formula + multiplier: Scripts/hero/technician.galaxy
"""
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import lib_map as L

TIERS = [1, 2, 4, 8, 16, 32, 64, 128]

# 数据源：造价读 catalog，转化配方读 galaxy 脚本真实倍率（每档投入矿 = TIER ×100）
_ar = L.open_map()
_gs = L.game_strings(_ar)
_cat = L.build_catalog(_ar)
_CU = _cat.get('Unit', {})
_CA = _cat.get('Abil', {})
_GALAXY = _ar.read_file('Scripts\\hero\\technician.galaxy').decode('utf-8', 'ignore')


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
    """从 galaxy 脚本解析真实转化产出（游戏运行时实际发放的矿）。

    脚本按投入基数把产出写死为 CeilingI(N * 倍率)，倍率【逐档递减】：
      纯矿  lv_tRANSMUTIN_MINERALS_<N> = CeilingI(N*1.20..1.06)      → +20%..+6%
      矿气  lv_tRANSMUTIN_GAS_<N>      = CeilingI(N*(1.20..1.06+0.24)) → +44%..+30%
    按钮文本(Button/Name)是显示标签，地图更新后没同步(仍写死 +20%/+44%)，
    故必须以脚本倍率为准。返回 {min_in:(min_in,min_out)} 与
    {min_in:(min_in,gas,gas_out)}；矿气档的气投入 = 投入矿 / 100（=tier）。"""
    import math

    def grab(prefix):
        # 兼容两种倍率写法：纯矿 CeilingI(N*1.20)；矿气(2026-08 起)改为加法表达式
        # CeilingI(N*(1.20+0.24))——固定 +0.24 气加成叠加逐档递减的基数。旧正则只认
        # 单浮点 N*mult，遇括号表达式失配 → GAS 全空。改为抓 CeilingI(...) 内整段
        # 表达式并安全求值（白名单仅数字与算符），两种写法通吃。
        out = {}
        for m in re.finditer(re.escape(prefix) + r'(\d+)\s*=\s*CeilingI\(([^;]+)\)\s*;', _GALAXY):
            n, expr = int(m.group(1)), m.group(2)
            if re.fullmatch(r'[\d.+\-*/() ]+', expr):
                out[n] = math.ceil(eval(expr))
        return out

    min_out = grab('lv_tRANSMUTIN_MINERALS_')
    gas_out = grab('lv_tRANSMUTIN_GAS_')
    mineral = {n: (n, min_out[n]) for n in min_out}
    gas = {n: (n, n // 100, gas_out[n]) for n in gas_out}  # 气投入 = 矿投入/100
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
        "mineralReturnRule": "纯矿回报率逐档递减：+1 为 +20%，每升一档 -2%，+128 为 +6%",
        "gasReturnRule": "矿气回报率逐档递减：+1 为 +44%，每升一档 -2%，+128 为 +30%（每点气价值恒定 24）",
        "paybackNote": "回本时间 = 总成本 ÷ 纯矿每秒净产出；总成本 = 建造费 + 单次投入矿（净产出 = 单次净赚 ÷ 20s 周期）。",
        "factories": factories
    },
    # 加速（2026-08 重做）：由「范围光环·+400%·持续10s·60s冷却·耗能50+气5」改为
    # 「单体指向·永久+25%·充能制·耗能25·无气耗」。数值全部读自地图 H-Technician.xml：
    #   Behavior/Acceleration.Modification.TimeScale = 1.25（+25%，无 Duration = 永久）
    #   Abil/Accelerate: CAbilEffectTarget，Range=15，TargetFilters=Structure;Neutral,Enemy
    #     （仅可对己方/友方建筑施放）；Cost.Vital[Energy]=25（无 Vespene）；
    #     充能 Cost.Charge：CountMax=5，CountUse=1，回充随等级 TimeUse=60/50/40/30/20s。
    #   旧版的 AccelerationSearchArea1~5（半径2~6）已无任何引用 → AOE 机制废弃，现为单体。
    "acceleration": {
        "ability": "加速 (Accelerate)",
        "speedupPct": 25,
        "speedupNote": "为目标建筑永久附加 +25% 运作速度（TimeScale 1.25，来源=施法者）。",
        "permanent": True,
        "durationSec": None,
        "energyCost": 25,
        "gasCost": 0,
        "rangeCells": 15,
        "singleTarget": True,
        "targetNote": "单体指向技能，只能对己方/友方建筑施放（排除中立与敌方）。",
        "charges": {
            "max": 5,
            "useCost": 1,
            "rechargeByLevel": [60, 50, 40, 30, 20]
        },
        # 5 级只缩短充能回充时间（TimeUse）；每级效果与耗能相同。
        "levels": [
            {"level": 1, "rechargeSec": 60},
            {"level": 2, "rechargeSec": 50},
            {"level": 3, "rechargeSec": 40},
            {"level": 4, "rechargeSec": 30},
            {"level": 5, "rechargeSec": 20},
        ],
        "effectNote": "旧版为「范围光环 · +400% · 持续 10s · 冷却 60s · 耗能 50+气 5」，"
                      "现重做为「单体 · 永久 +25% · 5 充能 · 耗能 25 · 无气耗」。等级只缩短充能回充时间。",
        "economyRelation": ("加速为单座建筑永久提速 25%：塔开火更频繁 → 出气更快；"
                            "转化工厂周期更短 → 产矿更快。5 层充能（随等级 60→20s 回充）"
                            "让技术员可持续把关键建筑逐个铺满加速，是经济引擎的长期提速手段。")
    },
    "_source": "凯瑞甘生存2 最新版.SC2Map (verified 2026-08-13)"
}

with open('data/technician-economy.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('wrote data/technician-economy.json')
print('factories:', len(factories), '| tiers:', [f["tier"] for f in factories])
