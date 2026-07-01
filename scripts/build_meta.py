"""
Build data/meta-history.json from a KS2 production DB dump (gzipped pg_dump).

The `historical_balance` table is a long time series of the official balance
report: for each snapshot (one `ds`, ~one every few hours since 2023-06) it
records every role's win rate, sample size, k-adjustment and p-value. That's
the raw material for a "meta over time" view — how each role's strength has
shifted across patches.

  historical_balance(uuid, functional_role, k, sample, winrate%, p, ds)
    - rows sharing a `ds` form one complete snapshot (~49 roles)
    - `functional_role` is the English role_name (maps to 中文/icon in the UI)
    - `winrate` is a percentage (e.g. 55.33); we store it as a 0..1 fraction
    - `games.replay_version` is only a replay-format version (3/6), NOT a patch
      version, so the time axis is `ds`, not a version number.

There are ~4800 snapshots — far too many to chart — so we DOWNSAMPLE to one per
ISO week (the last snapshot of each week), yielding ~150 points over 3 years.
Output is a build-time import (like balance.json), language-neutral by role_name.

Usage:
    python scripts/build_meta.py [path/to/dump.sql.gz]

Supplied out-of-band (not in build_all.py). Re-run on each fresh dump; wired
into scripts/fetch_dump.py so auto-fetched dumps refresh it too.
"""
import gzip
import json
import math
import os
import sys
from datetime import datetime

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
DATA = os.path.join(WIKI, 'data')
OUT = os.path.join(DATA, 'meta-history.json')
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


def _float(s):
    """Parse a float field, mapping NULL / non-finite (NaN/Inf) -> None so the
    output stays valid JSON (json.dump would otherwise emit bare NaN)."""
    if s in (None, '\\N', ''):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def main():
    dump = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DUMP
    if not os.path.exists(dump):
        sys.exit(f'Dump not found: {dump}')

    # Canonical roster from the `roles` table: role_name -> team
    # (0=Survivor, 1=Kerrigan). historical_balance uses spaced names
    # ("Dark Templar") while roles uses underscores ("Dark_Templar"), so index
    # by the underscore form and normalize on lookup. Roles absent here (e.g. a
    # transient/removed "Administrator") are dropped — the meta view tracks the
    # canonical roster only.
    role_team = {}
    for role_id, role_name, team, _ds in copy_rows(dump, 'roles'):
        role_team[role_name.replace(' ', '_')] = int(team)

    def team_of(role):
        return role_team.get(role.replace(' ', '_'))

    # group historical_balance rows by snapshot date (ds)
    # snapshots[ds][role_name] = {winrate, sample, k, p}
    snapshots = {}
    roles_seen = set()
    for row in copy_rows(dump, 'historical_balance'):
        # uuid, functional_role, k, sample, winrate, p, ds
        _uuid, role, k, sample, winrate, p, ds = row
        if winrate in (None, '\\N', ''):
            continue
        if team_of(role) is None:
            continue  # not in the canonical roster (e.g. transient "Administrator")
        wr = _float(winrate)
        if wr is None:
            continue
        snap = snapshots.setdefault(ds, {})
        try:
            sample_n = int(sample)
        except (ValueError, TypeError):
            sample_n = 0
        snap[role] = {
            'winrate': round(wr / 100.0, 4),
            'sample': sample_n,
            'k': _float(k),
            'p': _float(p),
        }
        roles_seen.add(role)

    # downsample: keep the LAST snapshot of each ISO (year, week)
    def week_key(ds):
        d = datetime.strptime(ds[:19], '%Y-%m-%d %H:%M:%S')
        iso = d.isocalendar()
        return (iso[0], iso[1])

    by_week = {}
    for ds in snapshots:
        by_week[week_key(ds)] = ds  # later ds in same week overwrites -> keep last
    kept_ds = sorted(by_week.values())

    # date-only label for the x axis / snapshot picker
    snaps_out = []
    for ds in kept_ds:
        snaps_out.append({
            'ds': ds,
            'date': ds[:10],
            'roles': snapshots[ds],
        })

    # ordered role list: Survivor first then Kerrigan, alpha within team
    roles_list = sorted(
        roles_seen,
        key=lambda r: (team_of(r) or 0, r),
    )

    out = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'dump_through': kept_ds[-1][:10] if kept_ds else None,
        'roles': [{'role': r, 'team': team_of(r) or 0} for r in roles_list],
        'snapshots': snaps_out,
    }

    with open(OUT, 'w', encoding='utf-8') as f:
        # allow_nan=False: fail loudly rather than emit invalid-JSON NaN/Infinity
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    size_kb = os.path.getsize(OUT) / 1024
    print(f'wrote {OUT}: {len(snaps_out)} weekly snapshots '
          f'({len(snapshots)} raw), {len(roles_list)} roles, '
          f'through {out["dump_through"]} ({size_kb:.0f} KB)')


if __name__ == '__main__':
    main()
