"""
Rebuild all wiki data from the map + data/seed/, with no BankEditor dependency.

Order:
  1. build_roles.py       seed + map -> data/roles.json
  2. build_abilities.py   seed ability lists + map -> data/abilities.json
  3. resolve-tooltips.py  resolve <d ref> numeric placeholders in abilities.json
  4. build_units.py       seed membership + map -> data/units.json
  5. build_veterancy.py   seed (verbatim) -> data/veterancy.json

economy.json is hand-maintained EXCEPT the "Team Nova" and "Nomad" entries, which
build_nova_economy.py / build_nomad_economy.py extract from the map and rewrite
in-place (other entries untouched). build_technician_economy.py writes its own
standalone JSON.
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
    'build_nova_economy.py',
    'build_nomad_economy.py',
    'build_terrain.py',
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


def drift_check():
    """非致命：检查英雄技能 seed 是否与地图命令卡漂移(防废弃技能残留/新技能漏列)。
    只报告不改动——新增/情境技能需人工策展，确认后跑 sync_hero_skills.py --write。"""
    print(f'\n{"=" * 60}\n  漂移检查 sync_hero_skills.py (只读，地图更新后请关注)\n{"=" * 60}')
    env = dict(os.environ, PYTHONUTF8='1')
    env['PYTHONPATH'] = SCRIPTS + os.pathsep + env.get('PYTHONPATH', '')
    subprocess.run([sys.executable, os.path.join(SCRIPTS, 'sync_hero_skills.py')],
                   cwd=WIKI, env=env)


if __name__ == '__main__':
    for step in STEPS:
        run(step)
    drift_check()
    print(f'\n{"=" * 60}\n  All data rebuilt. Run `npm run build` to verify.\n'
          f'  若上方漂移检查有变更项，核对后跑 sync_hero_skills.py --write 再重建。\n{"=" * 60}')
