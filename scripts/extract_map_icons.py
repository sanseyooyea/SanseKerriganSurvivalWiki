"""Extract the map's own local .dds art (Assets/**.dds) to public/ui-icons/*.png.

地图里自带的小图（Assets/Buttons、Assets/hero_ui 等，共 ~100 个）不在基础游戏导出里，
所以 build_tech_icons.py 索引不到它们。这里直接从 SC2Map 解出来转 png，
文件名规则与 lib_tech._icon_png_name 一致（小写、空格→-）。

用法：python scripts/extract_map_icons.py [map路径] [输出目录]
"""
import io
import os
import re
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_map as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_PATH = sys.argv[1] if len(sys.argv) > 1 else L.MAP_PATH
# 默认落到 sc2_btn_icons_raw 同级的暂存目录：build_tech_icons.py 会把它当第二个源目录，
# 统一转进 public/tech-icons/（前端只认一个目录，无需回退链）。
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else r'D:/starcraft2/sc2_map_icons_raw'

try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass


def png_name(path):
    base = path.replace('\\', '/').rsplit('/', 1)[-1].lower()
    base = re.sub(r'\.dds$', '', base)
    return re.sub(r'\s+', '-', base.strip()) + '.png'


def main():
    archive = L.open_map(MAP_PATH)
    os.makedirs(OUT_DIR, exist_ok=True)
    ok, err, skip = [], [], 0
    for f in L._listfile(archive):
        if not f.lower().endswith('.dds') or 'Assets\\' not in f:
            continue
        data = archive.read_file(f)
        if not data:
            skip += 1
            continue
        name = png_name(f)
        try:
            Image.open(io.BytesIO(data)).convert('RGBA').save(os.path.join(OUT_DIR, name))
            ok.append(name)
        except Exception as ex:  # PIL 不支持的 dds 压缩
            err.append((name, str(ex)[:60]))
    print(f'地图自带图标：转换 {len(ok)} 个 → {OUT_DIR}')
    if skip:
        print(f'  跳过 {skip} 个（读不出内容）')
    for n, e in err:
        print(f'  转换失败 {n}: {e}')


if __name__ == '__main__':
    main()
