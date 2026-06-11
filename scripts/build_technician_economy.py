"""
Generate data/technician-economy.json — Technician's unique transmute-based economy.
Standalone file (not merged into economy.json, whose passive income/period/chrono
schema does not fit Technician). All numbers verified from 凯瑞甘生存2 最新版.SC2Map:
  - factory build/upgrade costs: CUnit CostResource + CAbil UpgradeTo*.Cost
  - 16 transmute recipes: Button/Name text (100→119 ... 12800 mineral; +gas variants)
  - kill bounty formula + multiplier: Scripts/hero/technician.galaxy
"""
import json

TIERS = [1, 2, 4, 8, 16, 32, 64, 128]
BUILD = {1: 25, 2: 50, 4: 150, 8: 400, 16: 1000, 32: 2400, 64: 5600, 128: 12800}
UPGRADE = {2: 25, 4: 100, 8: 250, 16: 600, 32: 1400, 64: 3200, 128: 7200}
MIN_RECIPE = {1: (100, 119), 2: (200, 236), 4: (400, 468), 8: (800, 928),
              16: (1600, 1840), 32: (3200, 3648), 64: (6400, 7232), 128: (12800, 14336)}
GAS_RECIPE = {1: (100, 1, 143), 2: (200, 2, 282), 4: (400, 4, 556), 8: (800, 8, 1096),
              16: (1600, 16, 2160), 32: (3200, 32, 4256), 64: (6400, 64, 8384),
              128: (12800, 128, 16512)}
DURATION = 5

factories = []
for t in TIERS:
    m_in, m_out = MIN_RECIPE[t]
    g_min, g_gas, g_out = GAS_RECIPE[t]
    mineral_net = m_out - m_in
    gas_net = g_out - g_min
    gas_value = round((g_out - m_out) / g_gas, 2)  # 每 1 点气换来的额外矿
    factories.append({
        "tier": t,
        "nameZh": f"转化工厂 +{t}",
        "id": f"TechnicianTransmutationFactory{t}",
        "buildCost": BUILD[t],
        "upgradeCost": UPGRADE.get(t),  # None for +1 (base, built directly)
        "mineralRecipe": {
            "in": m_in, "out": m_out, "net": mineral_net,
            "returnPct": round(mineral_net / m_in * 100, 1),
            "netPerSec": round(mineral_net / DURATION, 1)
        },
        "gasRecipe": {
            "mineralIn": g_min, "gasIn": g_gas, "out": g_out, "net": gas_net,
            "returnPct": round(gas_net / g_min * 100, 1),
            "netPerSec": round(gas_net / DURATION, 1),
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
            "radiusCells": 6,
            "refreshSec": 4,
            "buffDurationSec": 5,
            "note": "范围内塔的击杀，气体与经验同时按倍数结算；技术员本体在塔附近(≤10格)时经验按(倍数-1)结算。",
            "tiers": [
                {"level": "x2", "multiplier": 2, "buildCost": 125},
                {"level": "x3", "multiplier": 3, "upgradeFromX2": 750},
                {"level": "x4", "multiplier": 4, "upgradeFromX3": 1500}
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
        "transmuteDurationSec": DURATION,
        "cooldownSec": 18,
        "autoCast": True,
        "autoUpgrade": True,
        "autoUpgradeNote": "余矿足够支付「升级费 + 在产工厂转化所需矿」时，工厂自动逐级升档。",
        "mineralReturnRule": "纯矿回报率 = 20% − 工厂级序%（+1=19% … +128=12%）",
        "gasReturnRule": "矿气回报率 = 44% − 工厂级序×2%（+1=43% … +128=29%）",
        "factories": factories
    },
    "acceleration": {
        "ability": "动能提升 (KineticBoost)",
        "energyCost": 30,
        "cooldownSec": 10,
        "autoCast": True,
        "rangeCells": 10,
        "economyRelation": ("加速提升塔的开火节奏 → 单位时间击杀更多 → 出气更快 → "
                            "转化更多矿。加速直接决定整套经济引擎的转速。")
    },
    "_source": "凯瑞甘生存2 最新版.SC2Map (verified 2026-06-11)"
}

with open('data/technician-economy.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('wrote data/technician-economy.json')
print('factories:', len(factories), '| tiers:', [f["tier"] for f in factories])
