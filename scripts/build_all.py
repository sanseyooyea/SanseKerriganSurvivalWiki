"""
Rebuild all wiki data from the map + data/seed/, with no BankEditor dependency.

Order:
  1. build_roles.py       seed + map -> data/roles.json
  2. build_abilities.py   seed ability lists + map -> data/abilities.json
  3. resolve-tooltips.py  resolve <d ref> numeric placeholders in abilities.json
  4. build_units.py       seed membership + map -> data/units.json
  5. build_veterancy.py   seed (verbatim) -> data/veterancy.json

economy.json is hand-maintained and not touched here.
Icons are stable; run extract_icons.py separately if the map's class icons change.

Usage:  python scripts/build_all.py        (run from the Wiki root)
"""
import os
import subprocess
import sys

WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
SCRIPTS = os.path.join(WIKI, 'scripts')

STEPS = [
    'build_roles.py',
    'build_abilities.py',
    'resolve-tooltips.py',
    'build_units.py',
    'build_veterancy.py',
    'build_technician_economy.py',
]


def run(step):
    print(f'\n{"=" * 60}\n  {step}\n{"=" * 60}')
    env = dict(os.environ, PYTHONUTF8='1')
    # build_*.py import lib_map (in scripts/); resolve-tooltips uses relative data/ paths
    env['PYTHONPATH'] = SCRIPTS + os.pathsep + env.get('PYTHONPATH', '')
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, step)],
                       cwd=WIKI, env=env)
    if r.returncode != 0:
        print(f'\n!! {step} failed (exit {r.returncode}); stopping.')
        sys.exit(r.returncode)


if __name__ == '__main__':
    for step in STEPS:
        run(step)
    print(f'\n{"=" * 60}\n  All data rebuilt. Run `npm run build` to verify.\n{"=" * 60}')
