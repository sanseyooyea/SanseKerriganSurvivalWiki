"""给 data/skins.json 补两类跳转信息：

1. skin.hero —— 该皮肤所属英雄（roleId 用于跳 /classes/{roleId}）。
2. component.unitId —— 该部件对应的兵种库条目（跳 /units/{unitId}）。

判定方式：
  - 皮肤英雄：看本体部件的 `from`（被替换的原始模型 id），
    到 units-v2 的 units 里找 id 等于它、或 id 以它结尾的单位，取 owners。
    取不到时退回皮肤 id 里的英雄名（ShopMechaChew → MechaChew → Chew）。
  - 部件兵种：优先精确 id，其次「以 from 结尾 + owners 含该英雄」的最短 id。
    death / other 类不挂兵种链接（死亡特效不是独立兵种条目）。
"""
import json
import re
import sys

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'

# 皮肤 id → 英雄名字段（units-v2.heroes 的 key）。Shop 前缀和常见变体在这里归一。
# 没列出的走自动推断：ShopXxxYyy 里匹配已知英雄名。
SKIN_HERO = {
    'CarbotZergling': None,
    'Catling': None,
    'PreVoidDJ': 'DJ',
    'ShopAscendantNarud': 'Ascendant',
    'ShopBaseKerrigan': 'Kerrigan',
    'ShopBattleHardenedArtanis': 'Artanis',
    'ShopCheerleaderKerrigan': 'Kerrigan',
    'ShopDOMScientist': 'Scientist',
    'ShopDarkTemplarZeratul': 'Dark Templar',
    'ShopHalarakAlarak': 'Alarak',
    'ShopHoloNomad': 'Nomad',
    'ShopImperatorStukov': 'Stukov',
    'ShopImperialAres': 'Ares',
    'ShopInfestedSpirit': 'Spirit',
    'ShopJimTeamNova': 'Team Nova',
    'ShopKaraxSpirit': 'Spirit',
    'ShopMadMalus': 'Malus',
    'ShopMechaChew': 'Chew',
    'ShopPrimalKerrigan': 'Kerrigan',
    'ShopPrimalThakras': 'Thakras',
    'ShopSarahTeamNova': 'Team Nova',
    'ShopScorpidZagara': 'Zagara',
    'ShopShrikeMira': 'Mira',
    'ShopStetmannScientist': 'Scientist',
    'ShopStormHeroKerrigan': 'Kerrigan',
    'ShopTalDarimProphet': 'Prophet',
    'ShopZweihakaDehaka': 'Dehaka',
}

# 英雄显示名 → roles.json 的 id（roleId）。roles 里有些 nameEn 和 units-v2 的 key 不一致。
HERO_ROLE_HINT = {
    'Dark Templar': 'Dark Templar',
    'Team Nova': 'Team Nova',
}


def main():
    skins = json.load(open(f'{WIKI}/data/skins.json', encoding='utf-8'))['skins']
    units_doc = json.load(open(f'{WIKI}/data/units-v2.json', encoding='utf-8'))
    roles = json.load(open(f'{WIKI}/data/roles.json', encoding='utf-8'))

    units = units_doc['units']
    heroes = units_doc['heroes']

    role_by_name = {}
    for r in roles:
        for key in (r.get('nameEn'), r.get('nameZh'), r.get('id')):
            if isinstance(key, str):
                role_by_name.setdefault(key, r)

    # 英雄 → 可用单位 id 列表（用于「以 from 结尾」的兜底匹配）
    hero_unit_ids = {}
    for hname, h in heroes.items():
        hero_unit_ids[hname] = set(h.get('unitIds') or [])

    # 全局单位 id 的长度排序，兜底匹配时优先最短（避免命中某个英雄的专属变体）
    all_ids_by_suffix = {}
    for uid, u in units.items():
        all_ids_by_suffix.setdefault(uid.lower(), []).append(uid)

    stats = {'hero': 0, 'unit': 0}

    for sid, skin in skins.items():
        hero = SKIN_HERO.get(sid)
        if hero is None and sid.startswith('Shop'):
            # 兜底：从皮肤 id 里抠出最长的已知英雄名
            rest = sid[4:]
            cands = [h for h in heroes if rest.lower().startswith(h.replace(' ', '').lower())]
            if cands:
                hero = max(cands, key=len)

        skin['hero'] = None
        if hero:
            rname = HERO_ROLE_HINT.get(hero, hero)
            role = role_by_name.get(rname)
            if role:
                skin['hero'] = {
                    'name': hero,
                    'nameZh': role.get('nameZh') or hero,
                    'roleId': role.get('id'),
                }
                stats['hero'] += 1

        for c in skin['components']:
            frm = c.get('from')
            c['unitId'] = None
            if not frm or c['role'] in ('death', 'other'):
                continue

            # 1) 精确命中
            if frm in units:
                c['unitId'] = frm
                stats['unit'] += 1
                continue

            # 2) 以 from 结尾，优先该英雄名下的单位，其次最短 id
            low = frm.lower()
            cands = [uid for k, ids in all_ids_by_suffix.items() if k.endswith(low) for uid in ids]
            if not cands:
                continue
            if hero and hero_unit_ids.get(hero):
                owned = [c2 for c2 in cands if c2 in hero_unit_ids[hero]]
                if owned:
                    cands = owned
            c['unitId'] = min(cands, key=len)
            stats['unit'] += 1

    json.dump({'skins': skins}, open(f'{WIKI}/data/skins.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('skins', len(skins), 'hero linked', stats['hero'], 'components linked', stats['unit'])

    # 抽查
    for sid in ('ShopMechaChew', 'ShopDOMScientist', 'CarbotZergling'):
        s = skins[sid]
        print(f"\n{sid} hero={s['hero']}")
        for c in s['components'][:4]:
            print('   ', c['role'], c.get('from'), '->', c['unitId'])


if __name__ == '__main__':
    main()
