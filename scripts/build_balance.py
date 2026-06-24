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

Usage:
    python scripts/build_balance.py [path/to/dump.sql.gz]

The dump is supplied out-of-band (not in the build_all.py pipeline, which only
needs map+seed). Re-run this whenever a fresh dump is provided.
"""
import gzip
import json
import os
import sys
from datetime import datetime

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

    # balance_games: game_id -> outcome (0/1 only); global tallies + latest date
    game_outcome = {}
    surv_wins = kerr_wins = 0
    latest = None
    for game_id, dt, _region, outcome, _ds in copy_rows(dump, 'balance_games'):
        o = int(outcome)
        if o not in (0, 1):
            continue
        game_outcome[game_id] = o
        if o == 0:
            surv_wins += 1
        else:
            kerr_wins += 1
        if dt != '\\N' and (latest is None or dt > latest):
            latest = dt
    games = surv_wins + kerr_wins
    print(f'balance_games (outcome in 0/1): {games}')

    # balance_players: per-hero plays/wins (win = role team == game outcome)
    plays = {}   # role_name -> int
    wins = {}    # role_name -> int
    skipped_no_game = skipped_no_role = 0
    for game_id, _handle, role_name, _ds in copy_rows(dump, 'balance_players'):
        o = game_outcome.get(game_id)
        if o is None:
            skipped_no_game += 1
            continue
        info = roles.get(role_name)
        if info is None:
            skipped_no_role += 1
            continue
        plays[role_name] = plays.get(role_name, 0) + 1
        if info[1] == o:
            wins[role_name] = wins.get(role_name, 0) + 1
    print(f'balance_players: {sum(plays.values())} counted '
          f'(skipped {skipped_no_game} no-game, {skipped_no_role} unknown-role)')

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
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'wrote {OUT}: {len(heroes)} heroes, '
          f'global survivor {out["global"]["survivor_win_rate"]} / '
          f'kerrigan {out["global"]["kerrigan_win_rate"]}, through {latest}')


if __name__ == '__main__':
    main()
