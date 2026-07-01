"""
Auto-fetch the latest KS2 production DB dump from the dev team's Google Drive,
then rebuild + commit the offline stats data (balance.json / stats.db).

The dev team uploads a fresh `*.sql.gz` pg_dump to a shared Drive folder every so
often. This script is the unattended replacement for the manual download + rebuild:

  1. `rclone lsjson` the shared folder, pick the newest *.sql.gz
  2. dedup against a local state file (Drive file id + mtime) — skip if nothing new
  3. `rclone copyto` it onto the default dump path the build scripts expect
  4. run build_balance.py + build_stats_db.py (they write absolute data/ paths)
  5. if data/balance.json or data/stats.db changed, git add + commit (NO push —
     pushing / PR / deploy stays manual, per project convention)

Idempotent: with no new dump it logs one line and exits 0, so it is safe to poll
from a scheduled task. Auth is rclone's cached OAuth token (see docs/AUTO_FETCH.md);
this script never opens a browser.

Usage:
    python scripts/fetch_dump.py [--force] [--no-build] [--no-commit]

  --force      download the newest dump even if the state file says it's current
  --no-build   download only, skip the two build scripts and the commit
  --no-commit  download + rebuild, but leave the git commit to you

Exit codes: 0 = success or nothing-to-do, 1 = error.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# ---- configuration ---------------------------------------------------------
# SECRET CONFIG lives OUTSIDE the repo so this file stays committable:
#   D:\starcraft2\tools\fetch_config.json  ->  {"folder_id": "...", "proxy": "..."}
# The Drive folder is licensed to the maintainer alone — its id IS the private
# "cloud address" and must never land in git. It is loaded at runtime from that
# external config (or the KS2_DUMP_FOLDER_ID env var); there is NO default here.
WIKI = r'D:\starcraft2\SanseKerriganSurvivalWiki'
TOOLS = r'D:\starcraft2\tools'
CONFIG = os.path.join(TOOLS, 'fetch_config.json')  # private, NOT in repo
STATE = os.path.join(TOOLS, '.fetch_state.json')   # remembers last-downloaded Drive file (outside repo)
DEST = r'D:\starcraft2\ks_prod_no_performance_stats.sql.gz'  # path the build scripts default to

BUILD_SCRIPTS = ['build_balance.py', 'build_stats_db.py', 'build_meta.py']
DATA_FILES = ['data/balance.json', 'data/stats.db', 'data/meta-history.json']


def _load_config():
    try:
        with open(CONFIG, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


_cfg = _load_config()
RCLONE = _cfg.get('rclone', r'D:\starcraft2\tools\rclone\rclone.exe')
REMOTE = _cfg.get('remote', 'gdrive:')              # rclone remote (read-only scope)
FOLDER_ID = _cfg.get('folder_id') or os.environ.get('KS2_DUMP_FOLDER_ID', '')  # PRIVATE — no default
PROXY = _cfg.get('proxy', os.environ.get('HTTPS_PROXY', 'http://127.0.0.1:7890'))  # local proxy to reach Google
# ---------------------------------------------------------------------------


def log(msg):
    ts = datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def run(cmd, **kw):
    """Run a command, raising on non-zero. Returns CompletedProcess."""
    return subprocess.run(cmd, check=True, text=True, **kw)


def rclone(*args, capture=False):
    cmd = [RCLONE, *args, '--drive-root-folder-id', FOLDER_ID]
    # rclone reaches Google directly, so it needs the local proxy (the browser's
    # system proxy isn't inherited by a CLI / headless scheduled task).
    env = os.environ.copy()
    if PROXY:
        env['HTTPS_PROXY'] = PROXY
        env['HTTP_PROXY'] = PROXY
    if capture:
        r = subprocess.run(cmd, check=True, text=True, capture_output=True, env=env)
        return r.stdout
    return run(cmd, env=env)


def newest_dump():
    """Return the newest *.sql.gz entry in the Drive folder, or None."""
    out = rclone('lsjson', REMOTE, '--files-only', capture=True)
    items = json.loads(out)
    dumps = [it for it in items if it.get('Name', '').lower().endswith('.sql.gz')]
    if not dumps:
        return None
    # ModTime is RFC3339 and lexicographically sortable; tie-break on name.
    dumps.sort(key=lambda it: (it.get('ModTime', ''), it.get('Name', '')))
    return dumps[-1]


def load_state():
    try:
        with open(STATE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(entry):
    os.makedirs(TOOLS, exist_ok=True)
    with open(STATE, 'w', encoding='utf-8') as f:
        json.dump({
            'id': entry.get('ID'),
            'name': entry.get('Name'),
            'modtime': entry.get('ModTime'),
            'size': entry.get('Size'),
            'downloaded_at': datetime.now(timezone.utc).astimezone().isoformat(),
        }, f, ensure_ascii=False, indent=2)


def git(*args, capture=False):
    cmd = ['git', '-C', WIKI, *args]
    if capture:
        return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout
    return run(cmd)


def sync_branch():
    """Best-effort fast-forward of the current branch to its upstream, so the
    auto data commit stacks on top of the latest origin (the daily task lives on
    main). Never fatal: if it can't ff (diverged / offline) we log and continue,
    and the divergence surfaces at push time. Working tree is clean here (the
    download only touched DEST, which is outside the repo)."""
    try:
        git('fetch', '--quiet')
        git('merge', '--ff-only', '--quiet', '@{u}')
        log('branch fast-forwarded to upstream')
    except subprocess.CalledProcessError:
        log('WARN: could not fast-forward to upstream (diverged/offline/no upstream?) '
            '— continuing on current HEAD; reconcile before pushing')


def commit_if_changed():
    """git add + commit the data files if they actually changed. No push."""
    status = git('status', '--porcelain', *DATA_FILES, capture=True).strip()
    if not status:
        log('data files unchanged — no commit')
        return
    # tag the commit with the dump's coverage date for traceability
    through = '?'
    try:
        with open(os.path.join(WIKI, 'data', 'balance.json'), encoding='utf-8') as f:
            through = json.load(f).get('dump_through', '?')
    except (OSError, ValueError):
        pass
    git('add', *DATA_FILES)
    git('commit', '-m', f'data: 刷新对局统计(胜率/played_like)至 {through}')
    log(f'committed refreshed stats (dump_through={through}). '
        f'Review, then `git push origin HEAD:main` (no PR) when ready.')


def main():
    force = '--force' in sys.argv
    no_build = '--no-build' in sys.argv
    no_commit = '--no-commit' in sys.argv

    if not os.path.exists(RCLONE):
        log(f'ERROR: rclone not found at {RCLONE}')
        return 1
    if not FOLDER_ID:
        log(f'ERROR: no folder_id configured. Put the private Drive folder id in '
            f'{CONFIG} (or set KS2_DUMP_FOLDER_ID). See docs/AUTO_FETCH.md.')
        return 1

    log('checking Drive folder for newest dump...')
    try:
        entry = newest_dump()
    except subprocess.CalledProcessError as e:
        log(f'ERROR: rclone lsjson failed ({e}). Is the "gdrive" remote configured? '
            f'See docs/AUTO_FETCH.md.')
        return 1

    if entry is None:
        log('no *.sql.gz found in the Drive folder — nothing to do')
        return 0

    state = load_state()
    is_new = (entry.get('ID') != state.get('id')
              or entry.get('ModTime') != state.get('modtime'))
    if not is_new and os.path.exists(DEST) and not force:
        log(f'already current: {entry["Name"]} (mtime {entry.get("ModTime")}) — nothing to do')
        return 0

    log(f'downloading {entry["Name"]} ({int(entry.get("Size", 0))/1e6:.1f} MB, '
        f'mtime {entry.get("ModTime")})...')
    try:
        rclone('copyto', f'{REMOTE}{entry["Name"]}', DEST, '--progress')
    except subprocess.CalledProcessError as e:
        log(f'ERROR: download failed ({e})')
        return 1

    if not os.path.exists(DEST):
        log('ERROR: download reported success but dest file is missing')
        return 1
    save_state(entry)
    log(f'downloaded -> {DEST}')

    if no_build:
        log('--no-build: skipping rebuild and commit')
        return 0

    # land the rebuilt data on top of latest origin before building/committing
    sync_branch()

    for script in BUILD_SCRIPTS:
        log(f'running {script}...')
        try:
            run([sys.executable, os.path.join(WIKI, 'scripts', script), DEST], cwd=WIKI)
        except subprocess.CalledProcessError as e:
            log(f'ERROR: {script} failed ({e})')
            return 1

    if no_commit:
        log('--no-commit: rebuild done, leaving git commit to you')
        return 0

    try:
        commit_if_changed()
    except subprocess.CalledProcessError as e:
        log(f'ERROR: git commit step failed ({e})')
        return 1

    log('done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
