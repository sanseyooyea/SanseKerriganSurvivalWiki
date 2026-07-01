"""
Build data/stats.db (read-only reference SQLite) from a KS2 prod DB dump.

Holds per-player history that the public gateway (194823.xyz) does not expose,
queried by handle at runtime via server/api. Currently:

  played_like  -- per game: the MMR a player effectively "played like"
  handles      -- player_handle -> battle_tag (to resolve a handle to identity)
  mmr_history  -- per player: time series of core (survivor/kerrigan) + role MMR

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
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )

    n_handles = 0
    for player_handle, battle_tag, _ds in copy_rows(dump, 'handles'):
        bt = None if battle_tag == '\\N' else battle_tag
        cur.execute('INSERT OR REPLACE INTO handles VALUES (?, ?)', (player_handle, bt))
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

    cur.executescript(
        """
        CREATE INDEX idx_pl_identity ON played_like (identity, datetime_of_game DESC);
        CREATE INDEX idx_handles_btag ON handles (battle_tag);
        """
    )
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('played_like_through', latest or ''))
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('mmr_history_through', mmr_through))
    con.commit()
    con.close()
    print(f'wrote {OUT}: {n_handles} handles, {n_pl} played_like rows, '
          f'{n_mmr} mmr_history rows, through {latest}')


if __name__ == '__main__':
    main()
