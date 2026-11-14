#!/usr/bin/env python3
"""KS2 录像解析器：.SC2Replay -> 网页回放用的紧凑 JSON。

用法：
    python scripts/replay/parse_replay.py <replay.SC2Replay> [-o out.json] [--pretty]
    python scripts/replay/parse_replay.py <目录> -o public/replay-data/   # 批量，并重建 index.json

数据来源（均来自录像本身，无需游戏客户端）：
  - tracker events：单位出生/死亡/变形/易主、科技完成、ReplayStats* 数据单位
    （KS2 地图把角色/队伍/MMR/胜负/性能指标编码成 "数据单位"，值 = x*256 + y）
  - UnitPositionsEvent：每 240 loop（15 游戏秒）记录一次"最近受过伤"的单位坐标
  - game events：玩家移动指令（配合选择追踪推算英雄走位）、镜头位置、离开
  - message events：聊天

时间单位统一为 game loop（16 loop = 1 游戏秒；"更快"速度下 22.4 loop = 1 现实秒，
游戏内计时器显示的就是 loop/22.4）。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# 优先用随包 vendor/ 依赖（服务器镜像不装 pip）；本地开发若已 pip 安装也会被这里覆盖，保证版本一致。
# 查找顺序：vendor/site（镜像构建时解压 + 预编译 .pyc，启动最快）> vendor/*.whl（zip 直接导入）> vendor/（mpyq.py）
_VENDOR = Path(__file__).resolve().parent / "vendor"
for _p in (_VENDOR, _VENDOR / "sc2reader-1.8.0-py3-none-any.whl", _VENDOR / "site"):
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import warnings  # noqa: E402
warnings.filterwarnings("ignore", category=SyntaxWarning)  # sc2reader 1.8 源码里的无效转义，无害

import sc2reader  # noqa: E402
from sc2reader.engine import GameEngine
from sc2reader.engine.plugins import ContextLoader, SelectionTracker

FORMAT_VERSION = 1

# 退出码（服务端据此给用户提示）
EXIT_OK = 0
EXIT_NOT_KS2 = 2      # 能读，但不是 KS2 录像
EXIT_BAD_REPLAY = 3   # 读不了：损坏 / 不支持的版本
EXIT_NO_MEMORY = 4    # 超出内存上限


class NotKS2Replay(Exception):
    pass
LOOPS_PER_GAME_SEC = 16.0
WIKI_ROOT = Path(__file__).resolve().parents[2]
DATA = WIKI_ROOT / "data"

# ks_constants.maps.Map 的索引顺序（ReplayStatsMapId 的值）。小写即 wiki 地形 key。
MAP_IDS = [
    "Classic", "Duck_Map", "Zerus_Volcanoes", "Ruins_Of_Imladoon", "Four_Seasons",
    "Heart_Of_Amethyst", "Vintage_Shores", "Aiur_Fountains", "Kaldir_Cliffs", "Lost_Tides",
    "Death_Valley", "Snow_Prism", "Aduns_Forgotten_Temple", "Maze", "Canal", "Sand_Fort",
    "Mar_Sara_Wastelands", "Last_Sanctuary", "No_Hope", "Celestial_Skylines", "Greenland",
    "The_Island",
]

GAME_STATS = {
    "ReplayStatsMapId": "mapId",
    "ReplayStatsRockPercentage": "rockPercentage",
    "ReplayStatsGameMode": "gameMode",
    "ReplayStatsVersion": "replayVersion",
    "ReplayStatsWinningTeam": "winningTeam",
    "ReplayStatsBalanceBankVersion": "balanceVersion",
}
PLAYER_STATS = {
    "ReplayStatsFunctionalRole": "role",
    "ReplayStatsInternalRole": "internalRole",
    "ReplayStatsTeam": "team",
    "ReplayStatsPregameMMR": "mmrBefore",
    "ReplayStatsPostgameMMR": "mmrAfter",
    "ReplayStatsTotalGamesPlayed": "gamesPlayed",
    "ReplayStatsOutcome": "outcome",
}
# 性能指标：只挑回放页有用的几条曲线（全部 28 条会让 JSON 翻倍且无人看）
PERF_STATS = {
    "ReplayStatsArmyValue": "army",
    "ReplayStatsUnitsKilled": "kills",
    "ReplayStatsMineralsGathered": "minerals",
    "ReplayStatsVespeneGathered": "gas",
    "ReplayStatsLifeDamageDealt": "damage",
    "ReplayStatsUnitsOwned": "units",
    "ReplayStatsAPM": "apm",
    "ReplayStatsGasFedToZerg": "gasFed",
}

# 不进回放画面的单位：数据单位、收入/统计占位、装饰/商店等
SKIP_UNIT_PREFIX = ("ReplayStats", "CommonReplayStats", "CommonBasicIncome", "BasicIncomeDummy")
SKIP_UNIT_EXACT = {
    "KerriganVespeneBounty", "GameContributionCredit", "ObserverDummy", "Shop",
    "CommonXelNagaTower", "MineralExtractor", "SwarmCreepTumorUsed",
}
# 外观/商店解锁类"科技"，不是对局事件
COSMETIC_UPGRADE_PREFIX = ("Unlock", "Use", "ShopUnlock", "ShopUse", "Reward", "Skin")
BOSS_UNITS = {"SwarmBrutalisk", "SwarmSOMF", "SwarmOmegalisk"}
POINT_MOVE_ABILITIES = {"", "RightClick", "Move", "Attack", "AttackMove", "MoveHoldPosition"}
DEFAULT_HERO_SPEED = 2.75
GHOST_UNIT = "GhostBuilderObserver"   # 玩家英雄阵亡后变成的幽灵（可继续建造），不算英雄


def _val(e) -> int:
    return int(e.x) * 256 + int(e.y)


def _load_json(name: str, default):
    p = DATA / name
    if not p.exists():
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


class WikiData:
    """读 wiki 自身数据，给角色/单位/科技补中文名与图标。缺文件时退化为英文 id。"""

    def __init__(self):
        roles = _load_json("roles.json", [])
        self.roles = {r["id"]: r for r in roles}
        units = _load_json("units-v2.json", {}).get("units", {})
        self.units = units
        # 英雄 = 角色表登记的英雄单位 ∪ 单位表 category=hero；排除死亡后的幽灵观察者
        self.hero_types = ({u for r in roles for u in r.get("heroUnits", [])}
                           | {k for k, v in units.items() if v.get("category") == "hero"}) - {GHOST_UNIT}
        self.upgrades = {}
        for hero in _load_json("tech.json", []):
            for up in hero.get("upgrades", []):
                self.upgrades.setdefault(up["id"], {"nameZh": up.get("nameZh"), "icon": up.get("icon")})

    def role(self, rid):
        r = self.roles.get(rid)
        if not r:
            return {"id": rid, "nameEn": f"Role{rid}", "nameZh": None}
        return {"id": rid, "nameEn": r["nameEn"], "nameZh": r.get("nameZh")}

    def unit_speed(self, utype):
        sp = (self.units.get(utype) or {}).get("stats", {}).get("speed")
        return sp if sp else DEFAULT_HERO_SPEED

    def unit_info(self, utype):
        u = self.units.get(utype) or {}
        return {"id": utype, "nameZh": u.get("nameZh"), "icon": u.get("icon"),
                "category": u.get("category")}


def _off_map(x, y) -> bool:
    # 很多单位先在 (255,255)/(0,0) 角落生成再传送，出生坐标不可信
    return x >= 254 or y >= 254 or x <= 1 or y <= 1


def parse(path: str, wiki: WikiData | None = None) -> dict:
    wiki = wiki or WikiData()
    with open(path, "rb") as f:
        raw = f.read()
    file_hash = hashlib.md5(raw).hexdigest()

    replay = sc2reader.load_replay(
        path, load_level=4, engine=GameEngine(plugins=[ContextLoader(), SelectionTracker()]))
    # sc2reader 引擎会把插件内的异常（含 MemoryError）吞成 PluginExit 继续跑，这里显式检查
    for plugin, (code, details) in getattr(replay, "plugin_result", {}).items():
        if code != 0 and "MemoryError" in str(details):
            raise MemoryError(f"{plugin}: {details}")

    # ---------- 玩家 ----------
    players = {}
    for p in replay.players:
        players[p.pid] = {
            "pid": p.pid,
            "name": ((f"<{p.clan_tag}> " if p.clan_tag else "") + p.name),
            "handle": p.toon_handle,
            "color": "#" + (p.color.hex if p.color else "888888"),
            "isHuman": bool(p.is_human),
            "role": None, "team": None, "outcome": None,
            "mmrBefore": None, "mmrAfter": None, "gamesPlayed": None,
            "deathSec": None, "leaveLoop": None, "heroType": None,
        }

    game = {}
    perf = defaultdict(lambda: defaultdict(list))  # pid -> key -> [[loop, v], ...]

    types: list[str] = []
    type_idx: dict[str, int] = {}

    def tidx(name):
        if name not in type_idx:
            type_idx[name] = len(types)
            types.append(name)
        return type_idx[name]

    units: dict[int, dict] = {}       # unit_id -> record
    events: list[dict] = []
    death_marks = []                  # [loop, x, y, ownerPid]
    first_nydus = None
    kerrigan_spawn = None

    for e in replay.tracker_events:
        n = e.name
        loop = e.frame
        if n in ("UnitBornEvent", "UnitInitEvent"):
            ut = e.unit_type_name
            if ut in GAME_STATS and e.upkeep_pid == 0:
                game[GAME_STATS[ut]] = _val(e)
                continue
            if ut in PLAYER_STATS and e.upkeep_pid in players:
                players[e.upkeep_pid][PLAYER_STATS[ut]] = _val(e)
                continue
            if ut == "ReplayStatsDeathTime" and e.upkeep_pid in players:
                # 值是地图计时器秒数（≈ 现实秒）；只在结算时统一写出，故不能用事件时间
                players[e.upkeep_pid]["deathSec"] = _val(e)
                continue
            if ut in PERF_STATS and e.upkeep_pid in players:
                perf[e.upkeep_pid][PERF_STATS[ut]].append([loop, _val(e)])
                continue
            if ut.startswith(SKIP_UNIT_PREFIX) or ut in SKIP_UNIT_EXACT:
                continue
            if ut == "SwarmNydusWorm" and first_nydus is None:
                first_nydus = loop
            owner = e.control_pid or 0
            x, y = float(e.x), float(e.y)
            rec = {
                "id": e.unit_id, "type": ut, "owner": owner, "born": loop, "died": None,
                "killer": None, "track": [] if _off_map(x, y) else [[loop, x, y]],
                "forms": [], "hero": ut in wiki.hero_types,
            }
            units[e.unit_id] = rec
            if rec["hero"] and owner in players and players[owner]["heroType"] is None:
                players[owner]["heroType"] = ut
                players[owner]["heroId"] = e.unit_id
            if ut == GHOST_UNIT and owner in players and not players[owner].get("_ghosted"):
                players[owner]["_ghosted"] = True
                events.append({"t": loop, "kind": "ghost", "pid": owner, "x": x, "y": y})
            if ut == "KerriganKerrigan" and kerrigan_spawn is None:
                kerrigan_spawn = loop
                events.append({"t": loop, "kind": "kerrigan", "pid": owner, "x": x, "y": y})
        elif n == "UnitTypeChangeEvent":
            rec = units.get(e.unit_id)
            if rec and e.unit_type_name:
                rec["forms"].append([loop, tidx(e.unit_type_name)])
                if e.unit_type_name in wiki.hero_types:
                    rec["hero"] = True
        elif n == "UnitOwnerChangeEvent":
            rec = units.get(e.unit_id)
            if rec:
                rec.setdefault("owners", []).append([loop, e.control_pid])
        elif n == "UnitDiedEvent":
            rec = units.get(e.unit_id)
            x, y = float(e.x), float(e.y)
            if rec is None:
                continue
            rec["died"] = loop
            rec["killer"] = e.killer_pid
            if not _off_map(x, y):
                rec["track"].append([loop, x, y])
                death_marks.append([loop, round(x, 1), round(y, 1), rec["owner"]])
            if rec["hero"] and rec["owner"] in players:
                events.append({"t": loop, "kind": "hero_death", "pid": rec["owner"],
                               "killer": e.killer_pid, "unit": rec["type"], "x": x, "y": y})
            elif rec["type"] in BOSS_UNITS and e.killer_pid and e.killer_pid in players:
                events.append({"t": loop, "kind": "boss_kill", "pid": e.killer_pid,
                               "unit": rec["type"], "x": x, "y": y})
        elif n == "UnitPositionsEvent":
            # e.units: {Unit 对象: (x, y)}，sc2reader 已按 index+recycle 还原成单位
            for unit, (x, y) in e.units.items():
                rec = units.get(unit.id)
                if rec is not None:
                    rec["track"].append([loop, float(x), float(y)])
        elif n == "UpgradeCompleteEvent":
            name = e.upgrade_type_name
            if e.count <= 0 or name.startswith(COSMETIC_UPGRADE_PREFIX):
                continue
            if e.pid not in players:
                continue
            events.append({"t": loop, "kind": "upgrade", "pid": e.pid, "upgrade": name})

    # KS2 地图开局必写 ReplayStatsVersion / MapId 数据单位；都没有就不是 KS2（或开局前就退了）
    if "replayVersion" not in game and "mapId" not in game:
        raise NotKS2Replay(f"不是凯瑞甘生存2录像（地图：{replay.map_name}）")

    # 游戏正式开始：最后一个虫道（重开/投票后会再刷）。早于此的科技多为开局赠送。
    start_loop = first_nydus or 0

    # ---------- 英雄走位推算 ----------
    _simulate_hero_moves(replay, units, players, wiki)

    # ---------- 玩家离开 / 聊天 / 镜头 ----------
    cameras = defaultdict(list)
    for e in replay.game_events:
        if e.name == "PlayerLeaveEvent" and e.player and e.player.pid in players:
            pl = players[e.player.pid]
            if pl["leaveLoop"] is None:
                pl["leaveLoop"] = e.frame
                events.append({"t": e.frame, "kind": "leave", "pid": e.player.pid})
        elif e.name == "CameraEvent" and e.player and e.player.pid in players:
            cam = cameras[e.player.pid]
            # 每 16 loop（1 游戏秒）最多保留一个镜头点，平滑足够
            if cam and e.frame - cam[-1][0] < 16:
                cam[-1] = [cam[-1][0], round(e.x, 1), round(e.y, 1)]
            else:
                cam.append([e.frame, round(e.x, 1), round(e.y, 1)])
    for e in replay.message_events:
        if e.name == "ChatEvent" and getattr(e, "player", None) and e.player.pid in players:
            events.append({"t": e.frame, "kind": "chat", "pid": e.player.pid,
                           "text": e.text, "toAll": bool(getattr(e, "to_all", False))})
        elif e.name == "PingEvent" and getattr(e, "player", None) and e.player.pid in players:
            # PingEvent 坐标是 1/4096 定点数
            events.append({"t": e.frame, "kind": "ping", "pid": e.player.pid,
                           "x": round(e.x / 4096, 1), "y": round(e.y / 4096, 1)})

    # Kerrigan 方两位玩家共享同一套虫族科技：同 loop 同名只留一条，归属 Kerrigan 方
    events = _dedupe_team_upgrades(events, players)

    end_loop = replay.frames
    if game.get("winningTeam") in (0, 1):
        events.append({"t": end_loop, "kind": "game_end", "winningTeam": game["winningTeam"]})
    if first_nydus is not None:
        events.append({"t": first_nydus, "kind": "game_start"})

    events.sort(key=lambda ev: (ev["t"], ev["kind"]))

    # ---------- 输出 ----------
    unit_rows = []
    for rec in units.values():
        track = _dedupe_track(rec["track"])
        if not rec["hero"] and (not track or (len(track) == 1 and track[0][0] == rec["died"])):
            # 只在死亡瞬间有坐标（大部分跳虫）：死亡标记层已覆盖，画面不画
            continue
        row = {
            "i": rec["id"], "t": tidx(rec["type"]), "o": rec["owner"],
            "b": rec["born"], "d": rec["died"],
            "p": [v for pt in track for v in (pt[0], round(pt[1], 1), round(pt[2], 1))],
        }
        if rec["hero"]:
            row["h"] = 1
        if rec["forms"]:
            row["f"] = [v for pt in rec["forms"] for v in pt]
        if rec.get("owners"):
            row["ow"] = [v for pt in rec["owners"] for v in pt]
        unit_rows.append(row)

    for pl in players.values():
        pl.pop("_ghosted", None)
        if pl["role"] is not None:
            r = wiki.role(pl["role"])
            pl["roleNameEn"], pl["roleNameZh"] = r["nameEn"], r["nameZh"]
        pl["perf"] = {k: [v for pt in pts for v in pt] for k, pts in perf[pl["pid"]].items()}

    map_id = game.get("mapId")
    map_enum = MAP_IDS[map_id] if map_id is not None and 0 <= map_id < len(MAP_IDS) else None
    utc = datetime.fromtimestamp(replay.unix_timestamp, tz=timezone.utc)

    upgrade_names = {ev["upgrade"] for ev in events if ev["kind"] == "upgrade"}
    return {
        "format": FORMAT_VERSION,
        "hash": file_hash,
        "meta": {
            "mapTitle": replay.map_name,
            "mapKey": map_enum.lower() if map_enum else None,
            "mapEnum": map_enum,
            "date": utc.isoformat(),
            "build": replay.build,
            "region": replay.region,
            "loops": end_loop,
            "startLoop": start_loop,
            "loopsPerSecond": 22.4,
            **game,
        },
        "players": sorted(players.values(), key=lambda p: p["pid"]),
        "types": [wiki.unit_info(t) for t in types],
        "upgrades": {u: wiki.upgrades.get(u, {"nameZh": None, "icon": None}) for u in sorted(upgrade_names)},
        "units": unit_rows,
        "deaths": [v for d in death_marks for v in d],
        "cameras": {str(pid): [v for pt in pts for v in pt] for pid, pts in cameras.items()},
        "events": events,
    }


def _dedupe_track(track):
    track.sort(key=lambda p: p[0])
    out = []
    for p in track:
        if out and out[-1][0] == p[0]:
            out[-1] = p
        elif out and abs(out[-1][1] - p[1]) < 0.05 and abs(out[-1][2] - p[2]) < 0.05 and len(out) > 1 \
                and abs(out[-2][1] - p[1]) < 0.05 and abs(out[-2][2] - p[2]) < 0.05:
            out[-1] = p  # 连续三点静止：只保留首尾，减小体积
        else:
            out.append(p)
    return out


def _dedupe_team_upgrades(events, players):
    seen = set()
    out = []
    for ev in events:
        if ev["kind"] == "upgrade":
            team = players[ev["pid"]].get("team")
            if team == 1:
                key = (ev["t"], ev["upgrade"])
                if key in seen:
                    continue
                seen.add(key)
                ev["team"] = 1
        out.append(ev)
    return out


def _simulate_hero_moves(replay, units, players, wiki):
    """用玩家移动指令补全英雄两次真实采样之间的走位。

    真实坐标（出生/位置采样/死亡）作为锚点；锚点之间若玩家选中英雄下达了点目标指令，
    则按英雄移速从当前位置朝目标直线前进，生成估算关键帧。下一个真实锚点到来时以真实为准。
    估算点在 track 里与真实点混排（前端统一线性插值）。
    """
    hero_by_pid = {pid: pl.get("heroId") for pid, pl in players.items() if pl.get("heroId")}
    if not hero_by_pid:
        return
    orders = defaultdict(list)  # unit_id -> [(loop, x, y)]
    for e in replay.game_events:
        if e.name not in ("TargetPointCommandEvent", "UpdateTargetPointCommandEvent"):
            continue
        if not e.player or e.player.pid not in hero_by_pid:
            continue
        ability = getattr(e, "ability_name", "") or ""
        if ability not in POINT_MOVE_ABILITIES:
            continue
        hid = hero_by_pid[e.player.pid]
        try:
            sel = e.player.selection[10]
        except (AttributeError, KeyError, IndexError):
            continue
        if any(getattr(u, "id", None) == hid for u in sel):
            orders[hid].append((e.frame, float(e.x), float(e.y)))

    for hid, cmds in orders.items():
        rec = units.get(hid)
        if not rec or not rec["track"]:
            continue
        speed = wiki.unit_speed(rec["type"]) / LOOPS_PER_GAME_SEC  # 格/loop
        anchors = sorted(rec["track"], key=lambda p: p[0])
        died = rec["died"]
        timeline = [(a[0], 0, a) for a in anchors] + [(c[0], 1, c) for c in cmds
                                                      if c[0] >= anchors[0][0] and (died is None or c[0] < died)]
        timeline.sort(key=lambda t: (t[0], t[1]))
        out = []
        pos = None
        cur_t = None
        target = None

        def advance(to_t):
            nonlocal pos, cur_t
            if pos is None or target is None or to_t <= cur_t:
                cur_t = to_t if cur_t is None or to_t > cur_t else cur_t
                return
            dx, dy = target[0] - pos[0], target[1] - pos[1]
            dist = math.hypot(dx, dy)
            reach_t = cur_t + dist / speed if speed > 0 else math.inf
            if reach_t <= to_t:
                # 途中到达：补一个到达关键帧
                out.append([int(reach_t), target[0], target[1]])
                pos = (target[0], target[1])
            else:
                k = (to_t - cur_t) * speed / dist
                pos = (pos[0] + dx * k, pos[1] + dy * k)
            cur_t = to_t

        for t, kind, item in timeline:
            if kind == 0:
                # 真实锚点：直接覆盖，目标保留（玩家可能仍在执行该指令）
                advance(t)
                pos = (item[1], item[2])
                cur_t = t
                out.append([t, pos[0], pos[1]])
                if target and math.hypot(target[0] - pos[0], target[1] - pos[1]) < 0.5:
                    target = None
            else:
                advance(t)
                if pos is not None:
                    out.append([t, pos[0], pos[1]])
                target = (item[1], item[2])
        if died is None:
            advance(replay.frames)
            if pos is not None:
                out.append([cur_t, pos[0], pos[1]])
        rec["track"] = out


def _write(data, out_path: Path, pretty: bool):
    """写 JSON；路径以 .gz 结尾时直接写 gzip（服务端原样以 Content-Encoding: gzip 下发，零 CPU）。
    先写临时文件再改名，避免进程被杀时留下半个文件。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".part")
    opener = (lambda p: gzip.open(p, "wt", encoding="utf-8", compresslevel=6)) if out_path.suffix == ".gz"         else (lambda p: open(p, "w", encoding="utf-8"))
    with opener(tmp) as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=1)
        else:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, out_path)


def _caused_by_memory(ex: BaseException) -> bool:
    seen = 0
    while ex is not None and seen < 10:
        if isinstance(ex, MemoryError) or "MemoryError" in repr(ex):
            return True
        ex = ex.__cause__ or ex.__context__
        seen += 1
    return False


def _limit_memory(mb: int):
    """Linux 下用 RLIMIT_AS 给自身设硬上限：超限时抛 MemoryError 自行退出，
    而不是撑爆容器 mem_limit 触发 OOM killer（它可能杀掉同容器里的 Node 主进程）。"""
    try:
        import resource
    except ImportError:  # Windows 本地开发：无此模块，跳过
        return
    lim = mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (lim, lim))


def _index_entry(data, file_name):
    m = data["meta"]
    return {
        "file": file_name,
        "hash": data["hash"],
        "date": m["date"],
        "mapKey": m["mapKey"],
        "loops": m["loops"],
        "winningTeam": m.get("winningTeam"),
        "players": [{"name": p["name"], "role": p.get("roleNameZh") or p.get("roleNameEn"),
                     "team": p["team"]} for p in data["players"]],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help=".SC2Replay 文件或目录")
    ap.add_argument("-o", "--out", help="输出 JSON 路径（单文件）或目录（批量）；缺省写到 stdout")
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument("--summary", action="store_true",
                    help="单文件模式：解析成功后向 stdout 打印一行列表摘要 JSON（供服务端入库）")
    ap.add_argument("--max-mem-mb", type=int, default=0,
                    help="地址空间上限（MB，仅 Linux 生效）；0 = 不限")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    if args.max_mem_mb:
        _limit_memory(args.max_mem_mb)

    wiki = WikiData()
    inp = Path(args.input)
    if inp.is_dir():
        if not args.out:
            ap.error("批量模式需要 -o 输出目录")
        out_dir = Path(args.out)
        index_path = out_dir / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
        known = {e["hash"] for e in index}
        for f in sorted(inp.glob("*.SC2Replay")):
            try:
                data = parse(str(f), wiki)
            except NotKS2Replay as ex:
                print(f"[skip] {f.name}: {ex}", file=sys.stderr)
                continue
            except Exception as ex:  # 单个坏录像不影响整批
                print(f"[skip] {f.name}: {ex}", file=sys.stderr)
                continue
            name = data["hash"] + ".json"
            _write(data, out_dir / name, args.pretty)
            if data["hash"] not in known:
                index.append(_index_entry(data, name))
                known.add(data["hash"])
            print(f"[ok] {f.name} -> {name}", file=sys.stderr)
        index.sort(key=lambda e: e["date"], reverse=True)
        _write(index, index_path, True)
        return

    try:
        data = parse(str(inp), wiki)
    except NotKS2Replay as ex:
        print(str(ex), file=sys.stderr)
        sys.exit(EXIT_NOT_KS2)
    except MemoryError:
        print("解析超出内存上限", file=sys.stderr)
        sys.exit(EXIT_NO_MEMORY)
    except Exception as ex:  # sc2reader 对损坏/新版本录像会抛各种异常
        # sc2reader 会把解压时的 MemoryError 包成 MPQError，顺着异常链找回来
        if _caused_by_memory(ex):
            print("解析超出内存上限", file=sys.stderr)
            sys.exit(EXIT_NO_MEMORY)
        print(f"无法解析录像：{type(ex).__name__}: {ex}", file=sys.stderr)
        sys.exit(EXIT_BAD_REPLAY)

    if args.out:
        try:
            _write(data, Path(args.out), args.pretty)
        except MemoryError:
            print("写出结果时超出内存上限", file=sys.stderr)
            sys.exit(EXIT_NO_MEMORY)
        if args.summary:
            print(json.dumps(_index_entry(data, Path(args.out).name), ensure_ascii=False))
    else:
        json.dump(data, sys.stdout, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
