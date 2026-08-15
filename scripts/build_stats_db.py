"""
Build data/stats.db (read-only reference SQLite) from a KS2 prod DB dump.

Holds per-player history that the public gateway (194823.xyz) does not expose,
queried by handle at runtime via server/api. Currently:

  played_like        -- per game: the MMR a player effectively "played like"
  handles            -- player_handle -> battle_tag (to resolve a handle to identity)
  mmr_history        -- per player: time series of core (survivor/kerrigan) + role MMR
  player_mmr_current -- per player: current MMR snapshot in the shape /api/mmr
                        returns, so it can serve as an offline FALLBACK when the
                        gateway's /api/player is down (see server/api/mmr.get.ts)

`played_like.identity` / `mmr_history.identity` is usually a battle_tag (e.g.
"Name#1234", sometimes a toon "N-S2-1-..."); to look up by handle, resolve
handle -> battle_tag via `handles`, falling back to the raw handle.

`player_mmrs.history` is a pickled dict
  {core_times:[ts], core_mmrs:[(survivor,kerrigan)],
   role_times:[ts], role_mmrs:[[delta per role_id]]}
where role_mmrs values are deltas RELATIVE to the core MMR; a role's effective
MMR at snapshot i = core_mmrs[i][team] + role_mmrs[i][role_id]. We store, per
player, the core series and the effective-MMR series for roles they actually
played (ever non-zero), keyed by role_name (resolved via the `roles` table).

This is a STATIC SNAPSHOT — fresh only up to the dump. Separate from data/wiki.db
(the app's runtime DB); regenerate and ship whenever a new dump is provided.

Usage:
    python scripts/build_stats_db.py [path/to/dump.sql.gz]
"""
import gzip
import json
import os
import pickle
import sqlite3
import sys
import zlib

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
OUT = os.path.join(DATA, 'stats.db')
DEFAULT_DUMP = r'D:\starcraft2\ks_prod_no_performance_stats.sql.gz'


def copy_rows(path, table):
    """Yield tab-split field lists for the `COPY public.<table> ...` block."""
    marker = f'COPY public.{table} '
    with gzip.open(path, 'rt', encoding='utf-8', newline='\n') as f:
        in_block = False
        for line in f:
            if not in_block:
                if line.startswith(marker):
                    in_block = True
                continue
            if line.startswith('\\.'):
                break
            yield line.rstrip('\n').split('\t')


def decode_bytea_pickle(field):
    """A pg_dump COPY bytea field is `\\x<hex>`; decode it back to a Python obj."""
    if not field or field == '\\N':
        return None
    xi = field.find('x')
    hex_str = ''.join(c for c in field[xi + 1:] if c in '0123456789abcdefABCDEF')
    return pickle.loads(bytes.fromhex(hex_str))


def _aslist(v):
    """Coerce numpy arrays / tuples to plain lists for json-ability."""
    return v.tolist() if hasattr(v, 'tolist') else list(v)


def build_mmr_history(dump, cur):
    """Parse roles + player_mmrs.history into the mmr_history table.

    Returns (n_players, through) where through is the latest snapshot date.
    """
    # role_id -> (role_name, team)
    role_map = {}
    for role_id, role_name, team, _ds in copy_rows(dump, 'roles'):
        role_map[int(role_id)] = (role_name, int(team))

    n = 0
    latest_ts = 0
    for identity, _ver, _core, _role, _cg, _rg, hist, _ds in copy_rows(dump, 'player_mmrs'):
        try:
            h = decode_bytea_pickle(hist)
        except Exception:
            continue
        if not h:
            continue

        core_times = [int(t) for t in h.get('core_times', [])]
        core_mmrs = [_aslist(m) for m in h.get('core_mmrs', [])]
        # core series: [ts, survivor, kerrigan]
        core = [[t, int(m[0]), int(m[1])]
                for t, m in zip(core_times, core_mmrs) if len(m) >= 2]

        role_times = [int(t) for t in h.get('role_times', [])]
        role_rows = [_aslist(r) for r in h.get('role_mmrs', [])]
        # effective role MMR = core MMR (same team) at that snapshot + delta.
        # role_times tracks core_times 1:1 in practice; align by index and only
        # emit roles the player actually played (delta ever non-zero).
        roles = {}
        for idx, (t, deltas) in enumerate(zip(role_times, role_rows)):
            base = core_mmrs[idx] if idx < len(core_mmrs) else None
            for rid, delta in enumerate(deltas):
                if not delta or rid not in role_map:
                    continue
                name, team = role_map[rid]
                if base is not None and len(base) > team:
                    mmr = int(base[team]) + int(delta)
                else:
                    mmr = int(delta)
                roles.setdefault(name, []).append([t, mmr])

        # need >= 2 core snapshots for a meaningful trend line; single-snapshot
        # players (~41k) are a flat dot — skip them (the UI hides the card when
        # there's no row). Blobs are zlib-compressed: the JSON (dense ints + near
        # timestamps) shrinks ~7x, keeping stats.db under GitHub's 100MB limit.
        if len(core) < 2:
            continue
        cur.execute(
            'INSERT OR REPLACE INTO mmr_history VALUES (?, ?, ?)',
            (identity,
             zlib.compress(json.dumps(core, separators=(',', ':')).encode()),
             zlib.compress(json.dumps(roles, separators=(',', ':'), ensure_ascii=False).encode())),
        )
        n += 1
        if core_times:
            latest_ts = max(latest_ts, core_times[-1])

    through = ''
    if latest_ts:
        from datetime import datetime, timezone
        through = datetime.fromtimestamp(latest_ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    return n, through


def _load_role_map(dump):
    """role_id -> (role_name, team). team 0 = survivor, 1 = kerrigan."""
    role_map = {}
    for role_id, role_name, team, _ds in copy_rows(dump, 'roles'):
        role_map[int(role_id)] = (role_name, int(team))
    return role_map


def _pg_int_array(s):
    """Parse a pg_dump text array like `{13,23,-62,...}` into a list of ints."""
    s = s.strip()
    if not s or s == '\\N' or s == '{}':
        return []
    return [int(x) for x in s[1:-1].split(',') if x not in ('', 'NULL')]


def build_win_stats(dump, handle_to_identity):
    """One pass over `players` -> per (identity, functional_role) [games, wins].

    A game is a win when postgame_mmr > pregame_mmr (win always nudges MMR up,
    loss down); this avoids needing the games.outcome team convention. Keyed by
    identity (resolved from player_handle via `handles`) so it lines up with
    player_mmrs, whose roles use role_name == functional_role.
    """
    from collections import defaultdict
    stats = defaultdict(lambda: [0, 0])  # (identity, role) -> [games, wins]
    for row in copy_rows(dump, 'players'):
        # (game_id, player_name, player_handle, pregame_mmr, postgame_mmr,
        #  internal_role, functional_role, ...)
        handle, pre, post, role = row[2], row[3], row[4], row[6]
        if pre in ('\\N', '') or post in ('\\N', '') or role in ('\\N', ''):
            continue
        identity = handle_to_identity.get(handle, handle)
        rec = stats[(identity, role)]
        rec[0] += 1
        if float(post) > float(pre):
            rec[1] += 1
    return stats


def build_current(dump, cur, handle_to_identity):
    """Build player_mmr_current: per player, the current-MMR payload matching the
    shape `/api/mmr` returns, so it can back an offline fallback.

    Returns (n_players, through). `tier` is intentionally omitted (the dump has no
    tier thresholds); percentile is computed from the whole population per team.
    """
    import bisect
    role_map = _load_role_map(dump)
    win_stats = build_win_stats(dump, handle_to_identity)

    # First pass: parse each player's core + roles into memory; also collect the
    # full core-MMR population per team so we can compute Top-percentile.
    players = []  # (identity, cores{0,1}, roles_by_team{0:[...],1:[...]}, latest_ds)
    pop = {0: [], 1: []}  # all core MMRs per team, for percentile
    latest_ds = ''
    for row in copy_rows(dump, 'player_mmrs'):
        identity, _ver, core_s, role_s, _cg, role_games_s, _hist, ds = row
        try:
            core = json.loads(core_s)  # {"0": survivor, "1": kerrigan}
        except Exception:
            continue
        deltas = _pg_int_array(role_s)
        try:
            role_games = json.loads(role_games_s) if role_games_s not in ('\\N', '') else {}
        except Exception:
            role_games = {}

        cores = {}
        for team in (0, 1):
            v = core.get(str(team))
            if v is not None:
                cores[team] = int(round(float(v)))
                pop[team].append(cores[team])

        roles_by_team = {0: [], 1: []}
        for rid_s, plays in role_games.items():
            rid = int(rid_s)
            if rid not in role_map:
                continue
            name, team = role_map[rid]
            base = cores.get(team)
            if base is None:
                continue
            delta = deltas[rid] if rid < len(deltas) else 0
            g, w = win_stats.get((identity, name), (0, 0))
            roles_by_team[team].append({
                'role_id': rid,
                'role_name': name,
                'mmr': base + delta,
                'plays': int(plays),
                # win_rate from the players table; None when no rated rows exist
                # for this role (UI renders it as "—" rather than a false 0%).
                'win_rate': round(w / g, 4) if g else None,
            })
        for team in (0, 1):
            roles_by_team[team].sort(key=lambda r: r['mmr'], reverse=True)

        players.append((identity, cores, roles_by_team))
        if ds != '\\N' and ds > latest_ds:
            latest_ds = ds

    # sorted ascending populations for O(log n) percentile lookups
    for team in (0, 1):
        pop[team].sort()

    def top_pct(team, mmr):
        arr = pop[team]
        if not arr:
            return None
        # fraction of players ranked strictly above -> "Top X%". Clamp to 0.1 so
        # the very top players read "Top 0.1%" instead of a confusing "Top 0%".
        above = len(arr) - bisect.bisect_right(arr, mmr)
        return max(0.1, round(above / len(arr) * 100, 1))

    n = 0
    for identity, cores, roles_by_team in players:
        payload = {
            'cores': {
                'survivor': cores.get(0, 0),
                'kerrigan': cores.get(1, 0),
            },
            'ranks': {
                'survivor': {'tier': None, 'percentile': top_pct(0, cores[0]) if 0 in cores else None},
                'kerrigan': {'tier': None, 'percentile': top_pct(1, cores[1]) if 1 in cores else None},
            },
            'roles_survivor': roles_by_team[0],
            'roles_kerrigan': roles_by_team[1],
        }
        cur.execute(
            'INSERT OR REPLACE INTO player_mmr_current VALUES (?, ?)',
            (identity, zlib.compress(json.dumps(payload, separators=(',', ':'),
                                                ensure_ascii=False).encode())),
        )
        n += 1

    through = ''
    if latest_ds and latest_ds != '\\N':
        through = latest_ds
    return n, through


def main():
    dump = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DUMP
    if not os.path.exists(dump):
        sys.exit(f'Dump not found: {dump}')

    if os.path.exists(OUT):
        os.remove(OUT)
    con = sqlite3.connect(OUT)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE handles (
            player_handle TEXT PRIMARY KEY,
            battle_tag    TEXT
        );
        CREATE TABLE played_like (
            identity         TEXT,
            datetime_of_game TEXT,
            game_id          TEXT,
            functional_role  TEXT,
            estimated_mmr    INTEGER,
            team_int         INTEGER,
            played_like      REAL
        );
        CREATE TABLE mmr_history (
            identity TEXT PRIMARY KEY,
            core     BLOB,   -- zlib(JSON [[ts, survivor_mmr, kerrigan_mmr], ...])
            roles    BLOB    -- zlib(JSON {role_name: [[ts, effective_mmr], ...]})
        );
        CREATE TABLE player_mmr_current (
            identity TEXT PRIMARY KEY,
            data     BLOB    -- zlib(JSON of the /api/mmr payload; tier omitted)
        );
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )

    n_handles = 0
    handle_to_identity = {}
    for player_handle, battle_tag, _ds in copy_rows(dump, 'handles'):
        bt = None if battle_tag == '\\N' else battle_tag
        cur.execute('INSERT OR REPLACE INTO handles VALUES (?, ?)', (player_handle, bt))
        if bt:
            handle_to_identity[player_handle] = bt
        n_handles += 1

    n_pl = 0
    latest = None
    for identity, dt, game_id, role, est, team, pl, _ds in copy_rows(dump, 'played_like'):
        cur.execute(
            'INSERT INTO played_like VALUES (?, ?, ?, ?, ?, ?, ?)',
            (identity, dt, game_id, role,
             None if est == '\\N' else int(est),
             None if team == '\\N' else int(team),
             None if pl == '\\N' else float(pl)),
        )
        n_pl += 1
        if dt != '\\N' and (latest is None or dt > latest):
            latest = dt

    n_mmr, mmr_through = build_mmr_history(dump, cur)
    n_cur, cur_through = build_current(dump, cur, handle_to_identity)

    cur.executescript(
        """
        CREATE INDEX idx_pl_identity ON played_like (identity, datetime_of_game DESC);
        CREATE INDEX idx_handles_btag ON handles (battle_tag);
        """
    )
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('played_like_through', latest or ''))
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('mmr_history_through', mmr_through))
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('player_mmr_current_through', cur_through))
    con.commit()
    con.close()
    print(f'wrote {OUT}: {n_handles} handles, {n_pl} played_like rows, '
          f'{n_mmr} mmr_history rows, {n_cur} current-mmr rows, through {latest}')


if __name__ == '__main__':
    main()
