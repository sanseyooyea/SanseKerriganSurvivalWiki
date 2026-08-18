"""
One-time (re-runnable) harvest of every KS2 terrain we can find in the Battle.net cache.

The live map only bakes ONE terrain from a 22-map pool per release; the author rotates it
each publish. The Battle.net cache keeps the .s2ma of every version we've downloaded, so the
cache history preserves ~two dozen distinct terrains. This script pulls them all so /terrain
can offer a multi-map selector, not just the currently-live terrain.

Pipeline:
  1. Scan the cache for KS2 .s2ma files (DocumentHeader name contains '凯瑞甘生存').
  2. Group by Minimap.tga md5 -> one representative (newest mtime) per distinct terrain.
  3. Resolve each representative's identity (build_terrain.resolve_identity).
  4. Assign a key: the newest edit of a terrain gets the clean pool key (e.g. four_seasons);
     older edits of the SAME terrain get a dated suffix (four_seasons_20260214) so all 23
     survive rather than collapsing.
  5. Extract each via build_terrain.extract_map -> public/terrain/<key>.json + public/maps/<key>.png.
  6. Rebuild data/terrain.json index.

The live on-disk map always owns the canonical (undated) key for ITS terrain, so run
build_terrain.py (or build_all.py) afterwards to keep the live map authoritative.

Usage:  python scripts/harvest_terrains.py
"""
import hashlib
import os
import re
from datetime import datetime, timezone

import mpyq

import build_terrain as BT

CACHE = r'C:\ProgramData\Blizzard Entertainment\Battle.net\Cache'


def is_ks2(archive):
    """True if this archive's DocumentHeader names a KS2 map."""
    try:
        header = archive.read_file('DocumentHeader') or b''
    except Exception:
        return False
    return b'\xe5\x87\xaf\xe7\x91\x9e\xe7\x94\x98\xe7\x94\x9f\xe5\xad\x98' in header  # '凯瑞甘生存'


def minimap_md5(archive):
    try:
        tga = archive.read_file('Minimap.tga')
    except Exception:
        return None
    return hashlib.md5(tga).hexdigest() if tga else None


def scan_cache():
    """Yield (path, mtime) for every .s2ma under the cache (recursive)."""
    for root, _dirs, files in os.walk(CACHE):
        for name in files:
            if name.lower().endswith('.s2ma'):
                p = os.path.join(root, name)
                try:
                    yield p, os.path.getmtime(p)
                except OSError:
                    continue


def harvest():
    # md5 -> best (newest) representative for that distinct terrain
    reps = {}   # md5 -> {'path','mtime'}
    scanned = kept = 0
    for path, mtime in scan_cache():
        try:
            arc = mpyq.MPQArchive(path)
        except Exception:
            continue
        if not is_ks2(arc):
            continue
        scanned += 1
        md5 = minimap_md5(arc)
        if not md5:
            continue
        cur = reps.get(md5)
        if cur is None or mtime > cur['mtime']:
            reps[md5] = {'path': path, 'mtime': mtime}
            kept = len(reps)
    print(f'KS2 archives: {scanned}, distinct terrains (by minimap): {len(reps)}')

    # resolve identity for each distinct terrain, ordered newest-first so the freshest
    # edit of any pool terrain wins the clean (undated) key
    resolved = []
    for md5, rep in reps.items():
        arc = mpyq.MPQArchive(rep['path'])
        camel, snake, zh, tileset = BT.resolve_identity(arc)
        date = datetime.fromtimestamp(rep['mtime'], tz=timezone.utc).strftime('%Y-%m-%d')
        resolved.append({
            'md5': md5, 'path': rep['path'], 'mtime': rep['mtime'], 'date': date,
            'camel': camel, 'snake': snake, 'zh': zh, 'tileset': tileset,
        })
    resolved.sort(key=lambda r: r['mtime'], reverse=True)

    # assign keys: first (newest) instance of a snake -> clean key; later ones -> dated
    used = set()
    for r in resolved:
        base = r['snake']
        if base not in used:
            r['key'] = base
        else:
            r['key'] = f"{base}_{r['date'].replace('-', '')}"
        used.add(base)

    ok = 0
    for r in sorted(resolved, key=lambda r: r['key']):
        try:
            arc = mpyq.MPQArchive(r['path'])
            BT.extract_map(arc, r['key'], r['camel'], r['snake'], r['zh'], r['tileset'], date=r['date'])
            ok += 1
        except Exception as e:
            print(f'  SKIP {r["key"]} ({r["tileset"]}): {e}')
    print(f'extracted {ok}/{len(resolved)} terrains')

    BT.build_index()


if __name__ == '__main__':
    harvest()
