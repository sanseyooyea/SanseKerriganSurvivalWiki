"""
Build data/balance.json from a KS2 production DB dump (gzipped pg_dump).

Computes official-spec win rates entirely offline from the deduplicated
`balance_*` tables — no Postgres, no network. Streams three COPY blocks:

  roles           -> role_name -> (role_id, team)   team: 0=Survivor, 1=Kerrigan
  balance_games   -> game_id   -> outcome            keep only outcome in (0,1)
  balance_players -> per (game_id, functional_role); win = (role_team == outcome)

Official win-rate semantics (mirrors analyzer query.py):
  - source is the dedup balance tables, WHERE outcome IN (0,1)  (0=Survivor win, 1=Kerrigan win)
  - global team win rate is counted from balance_games (one row per game)
  - per-hero win rate is counted from balance_players: a play is a win when the
    hero's team equals the game outcome. Survivor and Kerrigan rates are not
    inter-derivable, so the two aggregations are kept independent.

Output is language-neutral (keyed by role_id + English role name); the frontend
maps to 中文名/图标 via data/roles.json.

In addition to the all-time aggregate (`global` + `heroes`, kept for backward
compatibility and the class detail pages), a `weekly` block pre-buckets the same
tallies by ISO week × server region group so the frontend can compute win rates
for any time window and either server:

  region group: cn   = China
                intl = Europe + North_America + Korea
  weeks[i]  -> Monday date "YYYY-MM-DD" of the i-th ISO week (chronological)
  weekly.global[grp][i]   = [survivor_wins, kerrigan_wins] in that week/region
  weekly.heroes[id][grp][i] = [plays, wins] for that hero in that week/region

The frontend sums the selected week range across the selected region group(s) to
derive plays/wins/win_rate on the fly — no per-window precompute needed.

Usage:
    python scripts/build_balance.py [path/to/dump.sql.gz]

The dump is supplied out-of-band (not in the build_all.py pipeline, which only
needs map+seed). Re-run this whenever a fresh dump is provided.
"""
import gzip
import json
import os
import sys
from datetime import date, datetime

# Server region -> group. China is 国服; everything else is 外服 (intl).
CN_REGIONS = {'China'}


def region_group(region):
    return 'cn' if region in CN_REGIONS else 'intl'


def iso_week_key(dt):
    """('YYYY-MM-DD HH:MM:SS') -> (iso_year, iso_week) or None for NULL/bad."""
    if not dt or dt == '\\N':
        return None
    try:
        d = datetime.strptime(dt[:10], '%Y-%m-%d')
    except ValueError:
        return None
    iso = d.isocalendar()
    return (iso[0], iso[1])

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
OUT = os.path.join(DATA, 'balance.json')
DEFAULT_DUMP = r'D:\starcraft2\ks_prod_no_performance_stats.sql.gz'

# Below this many plays a hero's win rate is statistically noisy; flagged (not
# dropped) so the frontend can gray it out. Display decision lives in the UI.
LOW_SAMPLE_THRESHOLD = 30


def copy_rows(path, table):
    """Yield tab-split field lists for the `COPY public.<table> ...` block.

    pg_dump COPY format: tab-separated, NULL is '\\N', block terminated by a
    lone '\\.'. Values may contain escaped tabs/newlines in theory, but the
    columns we read (ids, ints, timestamps, enum names) never do.
    """
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

    # roles: role_name -> (role_id, team)
    roles = {}
    for role_id, role_name, team, _ds in copy_rows(dump, 'roles'):
        roles[role_name] = (int(role_id), int(team))
    print(f'roles: {len(roles)}')

    # balance_games: game_id -> (outcome, week_key, region_group); global tallies.
    # week_key is None when datetime is NULL/unparseable (still counted all-time,
    # just not placed in the weekly buckets).
    game_meta = {}
    surv_wins = kerr_wins = 0
    latest = None
    week_keys = set()
    # weekly global tallies: (week_key, grp) -> [surv_wins, kerr_wins]
    wk_global = {}
    for game_id, dt, region, outcome, _ds in copy_rows(dump, 'balance_games'):
        o = int(outcome)
        if o not in (0, 1):
            continue
        wk = iso_week_key(dt)
        grp = region_group(region)
        game_meta[game_id] = (o, wk, grp)
        if o == 0:
            surv_wins += 1
        else:
            kerr_wins += 1
        if dt != '\\N' and (latest is None or dt > latest):
            latest = dt
        if wk is not None:
            week_keys.add(wk)
            g = wk_global.setdefault((wk, grp), [0, 0])
            g[o] += 1  # o: 0=survivor win, 1=kerrigan win
    games = surv_wins + kerr_wins
    print(f'balance_games (outcome in 0/1): {games}, {len(week_keys)} ISO weeks')

    # balance_players: per-hero plays/wins (win = role team == game outcome),
    # tallied both all-time and per (week, region group).
    plays = {}   # role_name -> int
    wins = {}    # role_name -> int
    # weekly per-hero: (role_name, week_key, grp) -> [plays, wins]
    wk_hero = {}
    skipped_no_game = skipped_no_role = 0
    for game_id, _handle, role_name, _ds in copy_rows(dump, 'balance_players'):
        meta = game_meta.get(game_id)
        if meta is None:
            skipped_no_game += 1
            continue
        info = roles.get(role_name)
        if info is None:
            skipped_no_role += 1
            continue
        o, wk, grp = meta
        won = info[1] == o
        plays[role_name] = plays.get(role_name, 0) + 1
        if won:
            wins[role_name] = wins.get(role_name, 0) + 1
        if wk is not None:
            cell = wk_hero.setdefault((role_name, wk, grp), [0, 0])
            cell[0] += 1
            if won:
                cell[1] += 1
    print(f'balance_players: {sum(plays.values())} counted '
          f'(skipped {skipped_no_game} no-game, {skipped_no_role} unknown-role)')

    # ---- assemble the weekly block (ISO week × region group) ----
    ordered_weeks = sorted(week_keys)                 # chronological
    week_index = {wk: i for i, wk in enumerate(ordered_weeks)}
    n_weeks = len(ordered_weeks)
    # Monday date label per ISO week
    week_labels = [date.fromisocalendar(y, w, 1).isoformat() for (y, w) in ordered_weeks]

    def empty_series():
        return {'cn': [[0, 0] for _ in range(n_weeks)],
                'intl': [[0, 0] for _ in range(n_weeks)]}

    weekly_global = empty_series()
    for (wk, grp), sk in wk_global.items():
        weekly_global[grp][week_index[wk]] = [sk[0], sk[1]]

    weekly_heroes = {}
    for (role_name, wk, grp), pw in wk_hero.items():
        info = roles.get(role_name)
        if info is None:
            continue
        rid = info[0]
        series = weekly_heroes.setdefault(rid, empty_series())
        series[grp][week_index[wk]] = [pw[0], pw[1]]

    heroes = []
    for role_name, (role_id, team) in sorted(roles.items(), key=lambda kv: kv[1][0]):
        p = plays.get(role_name, 0)
        w = wins.get(role_name, 0)
        heroes.append({
            'role_id': role_id,
            'role': role_name,
            'team': team,
            'plays': p,
            'wins': w,
            'win_rate': round(w / p, 4) if p else None,
            'low_sample': p < LOW_SAMPLE_THRESHOLD,
        })

    out = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'dump_through': latest,
        'low_sample_threshold': LOW_SAMPLE_THRESHOLD,
        'global': {
            'survivor_wins': surv_wins,
            'kerrigan_wins': kerr_wins,
            'games': games,
            'survivor_win_rate': round(surv_wins / games, 4) if games else None,
            'kerrigan_win_rate': round(kerr_wins / games, 4) if games else None,
        },
        'heroes': heroes,
        'weekly': {
            'weeks': week_labels,          # Monday date per ISO week, chronological
            'regions': ['cn', 'intl'],     # cn=国服(China), intl=外服(EU+NA+KR)
            # aligned to weeks[]; each cell is a pair
            'global': weekly_global,       # grp -> [[surv_wins, kerr_wins], ...]
            'heroes': {str(rid): s for rid, s in sorted(weekly_heroes.items())},
        },
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        # compact: the weekly block is a few thousand small ints
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    size_kb = os.path.getsize(OUT) / 1024
    print(f'wrote {OUT}: {len(heroes)} heroes, {n_weeks} weeks, '
          f'global survivor {out["global"]["survivor_win_rate"]} / '
          f'kerrigan {out["global"]["kerrigan_win_rate"]}, '
          f'through {latest} ({size_kb:.0f} KB)')


if __name__ == '__main__':
    main()
