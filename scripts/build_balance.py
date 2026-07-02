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
compatibility and the class detail pages), a `daily` block pre-buckets the same
tallies by calendar day × server region group so the frontend can compute win
rates for any time window and either server:

  region group: cn   = China
                intl = Europe + North_America + Korea
  days[i]   -> "YYYY-MM-DD" of the i-th day (contiguous calendar, chronological)
  daily.global[grp]   = { s: [surv_wins/day], k: [kerr_wins/day] }
  daily.heroes[id][grp] = { p: [plays/day], w: [wins/day] }

Flat per-day arrays (not nested pairs) keep the JSON compact. The frontend sums
the selected day range across the selected region group(s) to derive
plays/wins/win_rate on the fly — no per-window precompute needed.

Usage:
    python scripts/build_balance.py [path/to/dump.sql.gz]

The dump is supplied out-of-band (not in the build_all.py pipeline, which only
needs map+seed). Re-run this whenever a fresh dump is provided.
"""
import gzip
import json
import os
import sys
from datetime import date, datetime, timedelta

# Server region -> group. China is 国服; everything else is 外服 (intl).
CN_REGIONS = {'China'}


def region_group(region):
    return 'cn' if region in CN_REGIONS else 'intl'


def day_key(dt):
    """('YYYY-MM-DD HH:MM:SS') -> 'YYYY-MM-DD' or None for NULL/bad."""
    if not dt or dt == '\\N':
        return None
    d = dt[:10]
    try:
        datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        return None
    return d

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

    # balance_games: game_id -> (outcome, day, region_group); global tallies.
    # day is None when datetime is NULL/unparseable (still counted all-time,
    # just not placed in the daily buckets).
    game_meta = {}
    surv_wins = kerr_wins = 0
    latest = None
    day_set = set()
    # daily global tallies: (day, grp) -> [surv_wins, kerr_wins]
    day_global = {}
    for game_id, dt, region, outcome, _ds in copy_rows(dump, 'balance_games'):
        o = int(outcome)
        if o not in (0, 1):
            continue
        day = day_key(dt)
        grp = region_group(region)
        game_meta[game_id] = (o, day, grp)
        if o == 0:
            surv_wins += 1
        else:
            kerr_wins += 1
        if dt != '\\N' and (latest is None or dt > latest):
            latest = dt
        if day is not None:
            day_set.add(day)
            g = day_global.setdefault((day, grp), [0, 0])
            g[o] += 1  # o: 0=survivor win, 1=kerrigan win
    games = surv_wins + kerr_wins
    print(f'balance_games (outcome in 0/1): {games}, {len(day_set)} days')

    # balance_players: per-hero plays/wins (win = role team == game outcome),
    # tallied both all-time and per (day, region group).
    plays = {}   # role_name -> int
    wins = {}    # role_name -> int
    # daily per-hero: (role_name, day, grp) -> [plays, wins]
    day_hero = {}
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
        o, day, grp = meta
        won = info[1] == o
        plays[role_name] = plays.get(role_name, 0) + 1
        if won:
            wins[role_name] = wins.get(role_name, 0) + 1
        if day is not None:
            cell = day_hero.setdefault((role_name, day, grp), [0, 0])
            cell[0] += 1
            if won:
                cell[1] += 1
    print(f'balance_players: {sum(plays.values())} counted '
          f'(skipped {skipped_no_game} no-game, {skipped_no_role} unknown-role)')

    # ---- assemble the daily block (calendar day × region group) ----
    # Contiguous calendar from first to last observed game date, so the frontend
    # can map any date to an index by offset. A day with no games is all-zeros.
    if day_set:
        d0 = date.fromisoformat(min(day_set))
        d1 = date.fromisoformat(max(day_set))
        ordered_days = []
        cur = d0
        while cur <= d1:
            ordered_days.append(cur.isoformat())
            cur += timedelta(days=1)
    else:
        ordered_days = []
    day_index = {d: i for i, d in enumerate(ordered_days)}
    n_days = len(ordered_days)

    def zeros():
        return [0] * n_days

    # global: per region {s: [...], k: [...]}  (flat per-day arrays)
    daily_global = {g: {'s': zeros(), 'k': zeros()} for g in ('cn', 'intl')}
    for (day, grp), sk in day_global.items():
        i = day_index[day]
        daily_global[grp]['s'][i] = sk[0]
        daily_global[grp]['k'][i] = sk[1]

    # heroes: per role_id, per region {p: [...], w: [...]}
    daily_heroes = {}
    for (role_name, day, grp), pw in day_hero.items():
        info = roles.get(role_name)
        if info is None:
            continue
        rid = info[0]
        series = daily_heroes.setdefault(
            rid, {g: {'p': zeros(), 'w': zeros()} for g in ('cn', 'intl')})
        i = day_index[day]
        series[grp]['p'][i] = pw[0]
        series[grp]['w'][i] = pw[1]

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
        'daily': {
            'days': ordered_days,          # contiguous "YYYY-MM-DD", chronological
            'regions': ['cn', 'intl'],     # cn=国服(China), intl=外服(EU+NA+KR)
            # flat per-day arrays aligned to days[]
            'global': daily_global,        # grp -> {s: [...], k: [...]}
            'heroes': {str(rid): s for rid, s in sorted(daily_heroes.items())},
        },
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        # compact: the daily block is tens of thousands of small ints
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    size_kb = os.path.getsize(OUT) / 1024
    print(f'wrote {OUT}: {len(heroes)} heroes, {n_days} days, '
          f'global survivor {out["global"]["survivor_win_rate"]} / '
          f'kerrigan {out["global"]["kerrigan_win_rate"]}, '
          f'through {latest} ({size_kb:.0f} KB)')


if __name__ == '__main__':
    main()
