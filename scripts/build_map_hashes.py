"""
生成「已知 KS2 地图版本」清单：data/ks2-map-hashes.json

录像的 replay.details.cache_handles 最后一项是本局地图文件(.s2ma)的 SHA-256。
官方发布的每个 KS2 版本都会进 Battle.net 缓存（文件名即哈希），所以本机缓存里的
KS2 地图哈希集合 = 「我们见过的官方版本」。上传的录像据此标记：
  - 地图哈希在清单里   -> 已知官方版本
  - 不在清单里         -> 未知版本（可能是我们没下载过的版本、外服版本，或改过的地图）
未知版本不拒收，只在页面上提示。

本机缓存只覆盖国服里我们玩过/下载过的版本；外服（us/eu/kr）的地图哈希不同，默认都会是
「未知」。要补外服版本，在游戏里打开一次对应录像，让客户端把地图拉进缓存再重跑本脚本。

清单只增不减：缓存被清理后旧版本仍保留（录像不会过期）。

用法：python scripts/build_map_hashes.py      （build_terrain / harvest_terrains 之后跑一次）
"""
import json
import os
from datetime import datetime, timezone

import mpyq

import build_terrain as BT
import harvest_terrains as H

OUT = os.path.join(BT.DATA, 'ks2-map-hashes.json')


def main():
    known = {}
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            known = json.load(f).get('maps', {})
    before = len(known)

    for path, mtime in H.scan_cache():
        h = os.path.basename(path).split('.')[0].lower()
        if len(h) != 64 or h in known:
            continue
        try:
            arc = mpyq.MPQArchive(path)
        except Exception:
            continue
        if not H.is_ks2(arc):
            continue
        try:
            _camel, snake, _zh, _tileset = BT.resolve_identity(arc)
        except Exception:
            snake = None
        known[h] = {
            'terrain': snake,
            'seen': datetime.fromtimestamp(mtime, tz=timezone.utc).strftime('%Y-%m-%d'),
        }

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({
            'note': '已知 KS2 官方地图文件 SHA-256（来自本机 Battle.net 缓存），由 scripts/build_map_hashes.py 生成',
            'maps': dict(sorted(known.items(), key=lambda kv: (kv[1]['seen'], kv[0]))),
        }, f, ensure_ascii=False, indent=1)
    print(f'ks2-map-hashes: {len(known)} 个版本（新增 {len(known) - before}）-> {OUT}')


if __name__ == '__main__':
    main()
