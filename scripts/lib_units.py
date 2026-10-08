"""
Shared parser for per-hero UNIT extraction (roster / production tree / weapons / upgrades).

Unlike the legacy build_units.py (seed-driven + lib_map.build_catalog flattener), this
reads raw GameData XML with ElementTree so repeated arrays (WeaponArray, InfoArray,
AreaArray, EffectArray, AttributeBonus) survive intact. See lib_tech for the same
rationale on the research side.

Pieces:
  GameIndex            all GameData entries keyed by (family, id), with in-map parent=
                       inheritance. Parents outside the map (DU_WEAP, MISSILE, EA_WEAP …
                       live in the base-game mods) are unknown → field simply missing.
  discover_roster()    BFS from hero units through Train/Build/WarpTrain/Morph abilities
                       (and CEffectCreateUnit summons) → units + production edges.
  unit_stats()         hp/shield/armor/speed/sight/food/cost/attributes/planes/flags.
  weapon_profile()     walk a weapon's effect tree to damage components
                       {amount, bonus{Attr:n}, armorReduction, hits, splash, dot, notes}.
                       Nodes we cannot evaluate statically are recorded in `unresolved`
                       rather than guessed.
  damage_vs()          per-attack / DPS against a target {attributes, armor}.
  UpgradeIndex         every CUpgrade EffectArray reverse-indexed by (Catalog,Id) with
                       research cost from any CAbilResearch slot; apply() replays them.
"""
import re

import lib_map as L
import lib_tech as T

_num = T._num

FAMILY_PREFIX = (
    ('CUnit', 'Unit'), ('CWeapon', 'Weapon'), ('CEffect', 'Effect'), ('CAbil', 'Abil'),
    ('CBehavior', 'Behavior'), ('CUpgrade', 'Upgrade'), ('CButton', 'Button'),
)

# 标准靶：只体现属性加成，不含护甲（护甲另列，见 damage_vs 的 armor 参数）。
TARGETS = {
    'base': {'attributes': [], 'armor': 0},
    'light': {'attributes': ['Light'], 'armor': 0},
    'armored': {'attributes': ['Armored'], 'armor': 0},
    'heroic': {'attributes': ['Heroic'], 'armor': 0},
    # 凯瑞甘本体：Biological/Massive/Heroic/MapBoss，基础护甲 0（无 LifeArmor，
    # 靠 ZergGroundArmor 升级位加甲）。武器 TargetFilters 排除 MapBoss 的会得 0。
    'kerrigan': {'attributes': ['Heroic', 'Massive', 'MapBoss'], 'armor': 0},
}

MAX_DEPTH = 12

# 父类在基础游戏 mod（地图外）的武器：只补地图里缺的 Period/Range。
# 数值取自原版 SC2 数据（Liberty/Swarm），有新的再加；伤害仍以地图效果为准。
EXTERNAL_WEAPON_DEFAULTS = {
    'KaiserBlades': {'period': 0.861, 'range': 1},
}


def family_of(tag):
    for p, fam in FAMILY_PREFIX:
        if tag.startswith(p):
            return fam
    return None


class Entry:
    """One catalog entry = possibly several XML elements (partial overrides across
    files) + an optional in-map parent Entry."""
    __slots__ = ('family', 'id', 'tag', 'elems', 'parent_id', 'parent', 'source')

    def __init__(self, family, eid, tag, source):
        self.family, self.id, self.tag, self.source = family, eid, tag, source
        self.elems, self.parent_id, self.parent = [], None, None

    def _chain(self):
        e, seen = self, set()
        while e is not None and e.id not in seen:
            seen.add(e.id)
            yield e
            e = e.parent

    def find(self, tag):
        """Last child <tag> in own elements, else inherited from parent chain."""
        for e in self._chain():
            hit = None
            for el in e.elems:
                for c in el.findall(tag):
                    hit = c
            if hit is not None:
                return hit
        return None

    def value(self, tag, attr='value'):
        c = self.find(tag)
        return c.get(attr) if c is not None else None

    def num(self, tag, attr='value'):
        return _num(self.value(tag, attr))

    def findall(self, tag):
        """All <tag> children from the nearest level of the chain that defines any."""
        for e in self._chain():
            out = [c for el in e.elems for c in el.findall(tag)]
            if out:
                return out
        return []

    def indexed(self, tag, attr='value'):
        """{index: value} merged parent→child for arrays like Attributes/AttributeBonus."""
        merged = {}
        for e in reversed(list(self._chain())):
            for el in e.elems:
                for c in el.findall(tag):
                    idx = c.get('index')
                    if idx is not None:
                        merged[idx] = c.get(attr)
        return merged

    @property
    def external_parent(self):
        return self.parent_id if self.parent_id and self.parent is None else None


class GameIndex:
    def __init__(self, archive):
        self.archive = archive
        self.entries = {}   # (family, id) -> Entry
        self.roots = {}     # archive path -> root
        for f in L.gamedata_xml_files(archive):
            data = archive.read_file(f)
            if not data or len(data) < 20:
                continue
            try:
                root = T.parse_hero_xml(data)
            except Exception:
                continue
            self.roots[f] = root
            for el in root:
                eid = el.get('id')
                fam = family_of(el.tag)
                if not eid or not fam:
                    continue
                k = (fam, eid)
                ent = self.entries.get(k)
                if ent is None:
                    ent = self.entries[k] = Entry(fam, eid, el.tag, f)
                ent.elems.append(el)
                if el.get('parent'):
                    ent.parent_id = el.get('parent')
        for ent in self.entries.values():
            if ent.parent_id:
                ent.parent = self.entries.get((ent.family, ent.parent_id))

    def get(self, family, eid):
        return self.entries.get((family, eid)) if eid else None

    def unit(self, uid):
        return self.get('Unit', uid)


# ---------------------------------------------------------------- roster

PRODUCE_TAGS = ('CAbilTrain', 'CAbilBuild', 'CAbilWarpTrain', 'CAbilMorph',
                'CAbilMorphPlacement', 'CAbilArmMagazine', 'CAbilSpecialize')
EDGE_KIND = {'CAbilTrain': 'train', 'CAbilBuild': 'build', 'CAbilWarpTrain': 'warp',
             'CAbilMorph': 'morph', 'CAbilMorphPlacement': 'morph',
             'CAbilArmMagazine': 'magazine', 'CAbilSpecialize': 'morph'}


def unit_abil_ids(ent):
    ids = []
    for c in ent.findall('AbilArray'):
        if c.get('Link'):
            ids.append(c.get('Link'))
    for card in ent.findall('CardLayouts'):
        for b in card.findall('LayoutButtons'):
            ac = b.get('AbilCmd')
            if ac:
                ids.append(ac.split(',')[0])
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _res(el):
    out = {}
    for r in el.findall('Resource'):
        v = _num(r.get('value'))
        if v:
            out[r.get('index')] = v
    return out


def ability_edges(gi, abil_id):
    """Production edges defined by one ability. Each edge: {abil, index, kind, units[],
    time, cooldown, charge, requirements, button, costDelta}."""
    ab = gi.get('Abil', abil_id)
    if ab is None or ab.tag not in PRODUCE_TAGS:
        return []
    kind = EDGE_KIND[ab.tag]
    edges = []
    infos = ab.findall('InfoArray')
    for info in infos:
        units = [u.get('value') for u in info.findall('Unit') if u.get('value')]
        if info.get('Unit'):
            units = [x for x in info.get('Unit').split(',') if x] + units
        if not units:
            continue
        btn = info.find('Button')
        cd = info.find('Cooldown')
        ch = info.find('Charge')
        time = _num(info.get('Time'))
        if time is None and kind == 'morph':
            for sec in info.findall('SectionArray'):
                for d in sec.findall('DurationArray'):
                    if d.get('index') == 'Delay':
                        time = _num(d.get('value'))
        if time is None and kind == 'morph':
            for sec in ab.findall('SectionArray'):
                if sec.get('index') == 'Stats':
                    for d in sec.findall('DurationArray'):
                        if d.get('index') == 'Delay':
                            time = _num(d.get('value'))
        edges.append({
            'abil': abil_id,
            'index': info.get('index'),
            'kind': kind,
            'units': units,
            'time': time,
            'cooldown': _num(cd.get('TimeUse')) if cd is not None else None,
            'charge': _charge(ch),
            'requirements': btn.get('Requirements') if btn is not None else None,
            'button': btn.get('DefaultButtonFace') if btn is not None else None,
            'costDelta': _res(info),
        })
    return edges


def _charge(ch):
    if ch is None:
        return None
    tu = ch.find('TimeUse')
    cm = ch.find('CountMax')
    out = {}
    if tu is not None:
        out['timeUse'] = _num(tu.get('value'))
    if cm is not None:
        out['countMax'] = _num(cm.get('value'))
    return out or None


def produced_unit_edges(gi, abil_id):
    """CAbilEffectTarget 的 <ProducedUnitArray>：召唤/空降类产出（NomadCalldownSCV 等）。"""
    ab = gi.get('Abil', abil_id)
    if ab is None:
        return []
    units = []
    for c in ab.findall('ProducedUnitArray'):
        units += [x for x in (c.get('value') or '').split(',') if x]
    if not units:
        return []
    return [{'abil': abil_id, 'index': None, 'kind': 'summon', 'units': units, 'count': 1,
             'time': None, 'cooldown': None, 'charge': None, 'requirements': None,
             'button': None, 'costDelta': {}}]


def summon_edges(gi, abil_id, depth=0, seen=None):
    """CEffectCreateUnit reachable from a (non-production) ability's effect tree."""
    ab = gi.get('Abil', abil_id)
    if ab is None or ab.tag in PRODUCE_TAGS:
        return []
    roots = []
    for tag in ('Effect', 'EffectArray'):
        for c in ab.findall(tag):
            v = c.get('value')
            if v:
                roots.extend(v.split(','))
    out = []
    seen = set()

    def walk(eid, d):
        if not eid or d > 6 or eid in seen:
            return
        seen.add(eid)
        e = gi.get('Effect', eid)
        if e is None:
            return
        if e.tag == 'CEffectCreateUnit':
            units = [c.get('value') for c in e.findall('SpawnUnit') if c.get('value')]
            cnt = e.num('SpawnCount') or 1
            if units:
                out.append({'abil': abil_id, 'index': None, 'kind': 'summon', 'units': units,
                            'count': cnt, 'time': None, 'cooldown': None, 'charge': None,
                            'requirements': None, 'button': None, 'costDelta': {}})
        for nxt in _child_effects(e):
            walk(nxt, d + 1)

    for r in roots:
        walk(r, 0)
    return out


def _child_effects(e):
    out = []
    for tag in ('EffectArray', 'PeriodicEffectArray', 'ImpactEffect', 'LaunchEffect',
                'InitialEffect', 'FinalEffect', 'ExpireEffect', 'CaseDefault'):
        for c in e.findall(tag):
            v = c.get('value')
            if v:
                out.extend(v.split(','))
    for c in e.findall('AreaArray'):
        if c.get('Effect'):
            out.append(c.get('Effect'))
    for c in e.findall('CaseArray'):
        if c.get('Effect'):
            out.append(c.get('Effect'))
    return out


def resolve_hero_units(gi, hero_en, declared):
    """roles.json 的 heroUnits 有的指向不存在的 id（Jinara/Skitter 写的是不存在的简称）。
    能解析就直接用（形态/召唤单位由 BFS 自己找，不要在这里多塞）；
    全部解析不到时才用「同名前缀 + FlagArray Hero」兜底，取命令卡最丰富的那个。"""
    out = [u for u in declared if gi.unit(u)]
    if out:
        return out
    prefix = hero_en.replace(' ', '').replace('_', '')
    cand = []
    for (fam, uid), ent in gi.entries.items():
        if fam != 'Unit' or not uid.startswith(prefix):
            continue
        n = len(unit_abil_ids(ent))
        if ent.indexed('FlagArray').get('Hero') == '1':
            cand.append((n + 100, uid))
        elif n > 4:
            cand.append((n, uid))
    cand.sort(reverse=True)
    return [uid for _, uid in cand[:1]]


def is_real_unit(gi, uid):
    """Filter out missiles / placeholders / dummies that production or summon chains
    sometimes reach."""
    ent = gi.unit(uid)
    if ent is None:
        return False
    chain_parents = [e.parent_id or '' for e in ent._chain()]
    if any(p.upper().startswith(('MISSILE', 'PLACEHOLDER', 'ITEM')) for p in chain_parents):
        return False
    flags = ent.indexed('FlagArray')
    if flags.get('Missile') == '1':
        return False
    if 'Dummy' in uid or uid.endswith('WarpinDummy'):
        return False
    return True


def discover_roster(gi, hero_units, max_units=400):
    """BFS from hero unit ids → (unit_ids in discovery order, edges with `from`)."""
    order, edges, seen = [], [], set()
    queue = list(hero_units)
    while queue and len(order) < max_units:
        uid = queue.pop(0)
        if uid in seen:
            continue
        seen.add(uid)
        ent = gi.unit(uid)
        if ent is None:
            continue
        order.append(uid)
        for aid in unit_abil_ids(ent):
            es = (ability_edges(gi, aid) or summon_edges(gi, aid)
                  or produced_unit_edges(gi, aid))
            for e in es:
                e = dict(e, **{'from': uid})
                e['units'] = [u for u in e['units'] if is_real_unit(gi, u)]
                if not e['units']:
                    continue
                edges.append(e)
                for u in e['units']:
                    if u not in seen:
                        queue.append(u)
    return order, edges


# ---------------------------------------------------------------- unit stats

BUILDING_PLATING = ('TerranBuildingPlating', 'ProtossBuildingPlating', 'ZergBuildingArmor')


def life_armor_from_name(name):
    """LifeArmor 缺席时按 LifeArmorName 推基础护甲：建筑镀层=1，其余升级位=0。"""
    if not name:
        return 0
    return 1 if any(p in name for p in BUILDING_PLATING) else 0


def unit_stats(gi, uid):
    ent = gi.unit(uid)
    if ent is None:
        return None
    attrs = [k for k, v in ent.indexed('Attributes').items() if v == '1']
    planes = [k for k, v in ent.indexed('PlaneArray').items() if v == '1']
    flags = [k for k, v in ent.indexed('FlagArray').items() if v == '1']
    cost = {k: _num(v) for k, v in ent.indexed('CostResource').items() if _num(v)}
    food = ent.num('Food')
    behaviors = [c.get('Link') for c in ent.findall('BehaviorArray') if c.get('Link')]
    armor_name = ent.value('LifeArmorName')
    armor = ent.num('LifeArmor')
    if armor is None:
        armor = life_armor_from_name(armor_name)
    s = {
        'hp': ent.num('LifeMax') or 0,
        'shield': ent.num('ShieldsMax') or 0,
        'armor': armor,
        'shieldArmor': ent.num('ShieldArmor') or 0,
        'hpRegen': ent.num('LifeRegenRate') or 0,
        'shieldRegen': ent.num('ShieldRegenRate') or 0,
        'energy': ent.num('EnergyMax') or 0,
        'speed': ent.num('Speed') or 0,
        'creepSpeedMul': ent.num('SpeedMultiplierCreep'),
        'sight': ent.num('Sight') or 0,
        'armorName': (armor_name or '').rsplit('/', 1)[-1],
        'armorLevel': ent.num('LifeArmorLevel') or 0,
        'shieldArmorLevel': ent.num('ShieldArmorLevel') or 0,
        'radius': ent.num('Radius'),
    }
    return {
        'stats': s,
        'cost': {'minerals': cost.get('Minerals', 0), 'gas': cost.get('Vespene', 0),
                 'food': -food if food and food < 0 else 0,
                 'supplyProvided': food if food and food > 0 else 0},
        'attributes': attrs,
        'planes': planes,
        'isStructure': 'Structure' in attrs,
        'isHeroic': 'Heroic' in attrs,
        'flags': [f for f in flags if f in ('Invulnerable', 'Untargetable', 'NoArmor', 'Uncommandable', 'Unselectable')],
        'behaviors': behaviors,
        'weapons': [c.get('Link') for c in ent.findall('WeaponArray') if c.get('Link')],
        'abilities': unit_abil_ids(ent),
        'externalParent': ent.external_parent,
        'source': ent.source,
    }


# ---------------------------------------------------------------- weapons

def _targets(filters):
    """'Ground,Visible;Ally,Missile,…' → {'ground':bool,'air':bool,'excl':[...]}"""
    if not filters:
        return {'ground': True, 'air': True, 'require': [], 'exclude': []}
    req, _, exc = filters.partition(';')
    req = [x for x in req.split(',') if x and x != '-']
    exc = [x for x in exc.split(',') if x]
    ground = 'Air' not in req or 'Ground' in req
    air = 'Ground' not in req or 'Air' in req
    return {'ground': ground, 'air': air, 'require': req, 'exclude': exc}


def weapon_profile(gi, wid):
    w = gi.get('Weapon', wid)
    if w is None:
        return {'id': wid, 'missing': True, 'period': None, 'range': None, 'minRange': None,
                'melee': False, 'targets': _targets(None), 'displayAttackCount': None,
                'components': [], 'effects': [], 'unresolved': [f'Weapon:{wid}'], 'notes': []}
    eff = w.value('Effect') or (wid if gi.get('Effect', wid) else None)
    disp = w.value('DisplayEffect')
    ctx = {'unresolved': [], 'effects': set(), 'notes': set()}
    comps = walk_damage(gi, eff, ctx) if eff else []
    if not comps and disp and disp != eff:
        comps = walk_damage(gi, disp, ctx)
        ctx['notes'].add('displayEffect')
    if any(c['amount'] == 0 and not c['bonus'] for c in comps):
        ctx['notes'].add('zeroAmountDropped')
        comps = [c for c in comps if c['amount'] or c['bonus']]
    period = w.num('Period')
    rng = w.num('Range')
    ext = EXTERNAL_WEAPON_DEFAULTS.get(w.external_parent or '')
    if ext:
        period = period if period is not None else ext.get('period')
        rng = rng if rng is not None else ext.get('range')
        ctx['notes'].add('baseGameParent')
    if period is None:
        ctx['notes'].add('periodInherited')
    suicide = any('Suicide' in x for x in ctx['effects'])
    opts = [k for k, v in w.indexed('Options').items() if v == '1']
    return {
        'id': wid,
        'tag': w.tag,
        'period': period,
        'range': rng,
        'suicide': suicide,
        'minRange': w.num('MinimumRange'),
        'melee': 'Melee' in opts,
        'targets': _targets(w.value('TargetFilters')),
        'displayAttackCount': w.num('DisplayAttackCount'),
        'components': comps,
        'effects': sorted(ctx['effects']),
        'unresolved': ctx['unresolved'],
        'notes': sorted(ctx['notes']),
    }


def walk_damage(gi, eid, ctx, mult=1.0, splash=None, depth=0, path=(), secondary=False):
    """Collect damage components reachable from effect `eid`.
    mult = hits multiplier (PeriodCount / buff ticks), splash = innermost area ring."""
    if not eid or depth > MAX_DEPTH or eid in path:
        return []
    e = gi.get('Effect', eid)
    if e is None:
        ctx['unresolved'].append(eid)
        return []
    path = path + (eid,)
    ctx['effects'].add(eid)
    tag = e.tag
    out = []
    if tag == 'CEffectDamage':
        amt = e.num('Amount')
        if amt is None and e.external_parent:
            ctx['notes'].add('amountInherited')
        bonus = {k: _num(v) for k, v in e.indexed('AttributeBonus').items() if _num(v)}
        ar = e.num('ArmorReduction')
        vital = bool(e.findall('VitalArray'))
        out.append({
            'effect': eid,
            'amount': amt or 0,
            'bonus': bonus,
            'armorReduction': 1 if ar is None else ar,
            'hits': round(mult, 4),
            'splash': splash,
            'kind': e.value('Kind') or ('Splash' if 'SPLASH' in (e.parent_id or '') else None),
            'secondary': secondary,
            'vital': vital,
        })
        # damage effects can chain further effects (rare) — follow them too
        for nxt in _child_effects(e):
            out += walk_damage(gi, nxt, ctx, mult, splash, depth + 1, path, secondary)
        return out
    if tag == 'CEffectSet':
        for c in e.findall('EffectArray'):
            for v in (c.get('value') or '').split(','):
                out += walk_damage(gi, v, ctx, mult, splash, depth + 1, path, secondary)
        if e.indexed('Flags').get('Random') == '1' or e.value('RandomCount'):
            ctx['notes'].add('randomSet')
        return out
    if tag == 'CEffectLaunchMissile':
        out += walk_damage(gi, e.value('ImpactEffect'), ctx, mult, splash, depth + 1, path, secondary)
        return out
    if tag == 'CEffectCreatePersistent':
        pc = e.num('PeriodCount')
        periodic = [v for c in e.findall('PeriodicEffectArray')
                    for v in (c.get('value') or '').split(',') if v]
        offsets = {c.get('value') for c in e.findall('PeriodicOffsetArray')}
        flags = e.indexed('Flags')
        if pc is None:
            pc = 1
            if periodic and flags.get('PersistUntilDestroyed') == '1':
                ctx['notes'].add('persistUntilDestroyed')
        # 多偏移 = 扫射/线形，每个目标只会被其中一小段命中 → 不按 PeriodCount 放大
        per_target = 1 if len(offsets) > 1 else pc
        sweep = len(offsets) > 1
        if sweep:
            ctx['notes'].add('sweep')
        for v in periodic:
            share = per_target / len(periodic) if len(periodic) > 1 else per_target
            out += walk_damage(gi, v, ctx, mult * share, splash, depth + 1, path, secondary or sweep)
        for tag2 in ('InitialEffect', 'FinalEffect', 'ExpireEffect'):
            v = e.value(tag2)
            if v and v not in periodic:
                out += walk_damage(gi, v, ctx, mult, splash, depth + 1, path, secondary)
        return out
    if tag == 'CEffectEnumArea':
        areas = e.findall('AreaArray')
        rings = []
        for a in areas:
            r = _num(a.get('Radius'))
            fr = _num(a.get('Fraction'))
            rings.append({'radius': r, 'fraction': 1 if fr is None else fr, 'effect': a.get('Effect')})
        if not rings:
            return out
        # 主目标吃最内圈（同一单位只结算一个圈）；整组圈记录在 splash 里供前端展示
        inner = min(rings, key=lambda x: x['radius'] or 0)
        sp = {'radius': max((x['radius'] or 0) for x in rings),
              'rings': [{'radius': x['radius'], 'fraction': x['fraction']} for x in rings]}
        mc = e.num('MaxCount')
        if mc:
            sp['maxCount'] = mc
        # ExcludeArray Value=Target = 只打周围不打主目标（溅射副伤害）
        excl = any((c.get('Value') or '') == 'Target' for c in e.findall('ExcludeArray'))
        out += walk_damage(gi, inner['effect'], ctx, mult * inner['fraction'],
                           sp, depth + 1, path, secondary or excl)
        return out
    if tag == 'CEffectSwitch':
        cases = [c.get('Effect') for c in e.findall('CaseArray') if c.get('Effect')]
        dflt = e.value('CaseDefault')
        ctx['notes'].add('switch')
        pick = dflt or (cases[0] if cases else None)
        out += walk_damage(gi, pick, ctx, mult, splash, depth + 1, path, secondary)
        return out
    if tag == 'CEffectApplyBehavior':
        bid = e.value('Behavior')
        b = gi.get('Behavior', bid)
        if b is None:
            return out
        pe = b.value('PeriodicEffect')
        if pe:
            dur, per = b.num('Duration'), b.num('Period')
            ticks = int(dur / per) if dur and per else 1
            if not dur:
                ctx['notes'].add('dotUntilRemoved')
            sub = walk_damage(gi, pe, ctx, mult * ticks, splash, depth + 1, path, secondary)
            for c in sub:
                c['dot'] = {'behavior': bid, 'duration': dur, 'period': per}
            out += sub
        return out
    if tag in ('CEffectModifyUnit', 'CEffectRemoveBehavior', 'CEffectCreateUnit',
               'CEffectTeleport', 'CEffectIssueOrder', 'CEffectModifyPlayer',
               'CEffectCreateHealer', 'CEffectApplyForce', 'CEffectDestroyPersistent'):
        return out   # 非伤害效果
    ctx['unresolved'].append(f'{tag}:{eid}')
    return out


def vital_damage(profile):
    return sum(c['amount'] for c in profile['components'] if c.get('vital'))


def primary_components(profile):
    """Components that land on the attacked unit. Area-only parts (ExcludeArray Target,
    sweeps) are skipped unless nothing else exists (pure sweep weapons like Lurker)."""
    comps = [c for c in profile['components'] if not c.get('vital')]
    prim = [c for c in comps if not c.get('secondary')]
    return prim or comps


def _hit(comp, target):
    base = comp['amount'] + sum(v for k, v in comp['bonus'].items() if k in target['attributes'])
    return max(0.5, base - target['armor'] * comp['armorReduction']) if base > 0 else 0


def damage_vs(profile, target):
    """(per-attack damage, dps) against a target. Splash components count at the
    innermost-ring fraction (already in hits)."""
    t = profile['targets']
    if any(a in t['exclude'] for a in target['attributes']):
        return 0, 0
    per = sum(_hit(c, target) * c['hits'] for c in primary_components(profile))
    per = round(per, 2)
    if profile.get('suicide'):
        return per, None
    p = profile.get('period')
    return per, (round(per / p, 2) if p else None)


# ---------------------------------------------------------------- upgrades

_LEVEL_SUFFIX = re.compile(r'(?:Level|Tier|Kerrigan)?\d+$')


def upgrade_family(upid):
    fam = _LEVEL_SUFFIX.sub('', upid)
    return fam or upid


# None = SC2 默认的 Add。Set 是「直接覆盖」，也要建模（Sight/回血/延迟大量用它）。
NUMERIC_OPS = {'Add', 'Subtract', 'Multiply', 'Divide', 'AddBaseMultiply',
               'SubtractBaseMultiply', 'Set', 'Max', 'Min', None}


# 升级对单位的数值类字段 → snapshot 键（其它字段仍记录为「未建模」）。
UPGRADE_UNIT_FIELDS = {
    'LifeMax': 'hp', 'LifeStart': 'hp', 'ShieldsMax': 'shield', 'ShieldsStart': 'shield',
    'LifeArmor': 'armor', 'ShieldArmor': 'shieldArmor', 'Speed': 'speed', 'Sight': 'sight',
    'LifeRegenRate': 'hpRegen', 'ShieldRegenRate': 'shieldRegen', 'ShieldsRegenRate': 'shieldRegen',
    'EnergyMax': 'energy', 'EnergyStart': 'energy', 'EnergyRegenRate': 'energyRegen',
    'Food': 'food', 'Radius': 'radius', 'RepairTime': 'repairTime',
    'LifeRegenDelay': 'hpRegenDelay', 'ShieldRegenDelay': 'shieldRegenDelay',
    'EnergyArmor': 'energyArmor',
}
UPGRADE_COST_FIELDS = {'CostResource[Minerals]': 'minerals', 'CostResource[Vespene]': 'gas'}
# 字符串型字段（不是数值，单独应用）：决定武器对空/对地等目标筛选。
UPGRADE_STRING_FIELDS = {'TargetFilters', 'SearchFilters'}


def upgrade_category(ent):
    """CUpgrade 的 EditorCategories UpgradeType:*（攻击/防御/技能研究/天赋），无则 None。"""
    ec = ent.value('EditorCategories') or ''
    m = re.search(r'UpgradeType:(\w+)', ec)
    return m.group(1) if m else None


class UpgradeIndex:
    """refs[(Cat, Id)] -> [upgradeId]；每个升级含 effects（已建模数值）/ other（未建模）。"""

    def __init__(self, gi):
        self.gi = gi
        self.refs = {}
        self.upgrades = {}
        for (fam, uid), ent in gi.entries.items():
            if fam != 'Upgrade':
                continue
            effs, other = [], []
            for c in ent.findall('EffectArray'):
                ref, val, op = c.get('Reference'), c.get('Value'), c.get('Operation')
                if not ref:
                    continue
                parts = ref.split(',', 2)
                if len(parts) != 3:
                    continue
                cat, tid, field = parts
                if cat not in ('Unit', 'Weapon', 'Effect', 'Abil'):
                    continue
                v = _num(val)
                is_string_field = field in UPGRADE_STRING_FIELDS
                modelable = ((op in NUMERIC_OPS and v is not None) or is_string_field) \
                    and field not in ('Level', 'LifeArmorLevel', 'ShieldArmorLevel',
                                      'EnergyArmorLevel', 'Icon')
                if modelable:
                    effs.append((cat, tid, field, op or 'Set' if is_string_field else op or 'Add',
                                 v if not is_string_field else val))
                    self.refs.setdefault((cat, tid), []).append(uid)
                else:
                    other.append((cat, tid, field, op, val))
            self.upgrades[uid] = {'effects': effs, 'other': other,
                                  'maxLevel': ent.num('MaxLevel') or 1,
                                  'name': ent.value('Name') or '',
                                  'category': upgrade_category(ent)}
        self.research = {}   # upgradeId -> [slot,...] (repeated slots = multi-level)
        for root in gi.roots.values():
            for slot in T.extract_research(root):
                self.research.setdefault(slot['upgrade'], []).append(slot)

    def relevant(self, keys):
        """Upgrade ids touching any of (Cat,Id) keys, grouped by family with level order."""
        ups = set()
        for k in keys:
            ups.update(self.refs.get(k, []))
        fams = {}
        for u in ups:
            fams.setdefault(upgrade_family(u), []).append(u)
        out = []
        for fam, ids in fams.items():
            ids.sort(key=lambda x: (_num(re.search(r'(\d+)$', x).group(1)) if re.search(r'(\d+)$', x) else 0, x))
            levels = []
            for u in ids:
                slots = self.research.get(u, [])
                n = len(slots) or 1
                for i in range(n):
                    levels.append({'upgrade': u, 'slot': slots[i] if i < len(slots) else None})
            out.append({'family': fam, 'levels': levels,
                        'researchable': any(lv['slot'] for lv in levels)})
        out.sort(key=lambda x: x['family'])
        return out
