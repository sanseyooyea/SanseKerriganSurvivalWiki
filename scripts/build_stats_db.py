"""
Build data/stats.db (read-only reference SQLite) from a KS2 prod DB dump.

Holds per-player history that the public gateway (194823.xyz) does not expose,
queried by handle at runtime via server/api. Currently:

  played_like  -- per game: the MMR a player effectively "played like"
  handles      -- player_handle -> battle_tag (to resolve a handle to identity)

`played_like.identity` is a battle_tag (e.g. "Name#1234"); to look up by handle,
resolve handle -> battle_tag via `handles`, falling back to the raw handle.

This is a STATIC SNAPSHOT — fresh only up to the dump. Separate from data/wiki.db
(the app's runtime DB); regenerate and ship whenever a new dump is provided.

Usage:
    python scripts/build_stats_db.py [path/to/dump.sql.gz]
"""
import gzip
import os
import sqlite3
import sys

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

    cur.executescript(
        """
        CREATE INDEX idx_pl_identity ON played_like (identity, datetime_of_game DESC);
        CREATE INDEX idx_handles_btag ON handles (battle_tag);
        """
    )
    cur.execute('INSERT INTO meta VALUES (?, ?)', ('played_like_through', latest or ''))
    con.commit()
    con.close()
    print(f'wrote {OUT}: {n_handles} handles, {n_pl} played_like rows, through {latest}')


if __name__ == '__main__':
    main()
