"""把 CascView 导出的 SC2 升级图标(.dds)转成 web 用的 png，落到 public/tech-icons/。

前置：用 CascView 从 D:/StarCraft II 打开存储，把 assets/textures 下的 btn-*.dds（及少量
ui-*.dds）导出到 SRC_DIR（默认 D:/starcraft2/sc2_btn_icons_raw，可含子目录）。

流程：
  1. 读 data/tech.json，收集所有升级组 icon（png 名）→ 反推需要的 dds basename。
  2. 在 SRC_DIR 递归建 basename(小写、空格→-) → 路径 索引。
  3. 命中的用 PIL 转 png（RGBA）写入 public/tech-icons/；报告命中/缺失清单。

零硬编码图标名——需求全部来自 tech.json，故新增英雄后重跑即可。
"""
import glob
import json
import os
import re
import sys

from PIL import Image

# Windows 控制台默认 GBK,无法输出 ✔ 与中文提示(会 UnicodeEncodeError / mojibake)。
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECH_JSON = os.path.join(ROOT, 'data', 'tech.json')
UNITS_JSON = os.path.join(ROOT, 'data', 'units-v2.json')
OUT_DIR = os.path.join(ROOT, 'public', 'tech-icons')
# 两个源目录：CascView 导出的基础游戏 dds + extract_map_icons.py 从地图里解的本地贴图。
SRC_DIRS = [d for d in (
    sys.argv[1] if len(sys.argv) > 1 else r'D:/starcraft2/sc2_btn_icons_raw',
    sys.argv[2] if len(sys.argv) > 2 else r'D:/starcraft2/sc2_map_icons_raw',
) if d]


def _norm(basename):
    """dds/png basename → 规范 key(小写、去扩展名、空格→-)。与 lib_tech._icon_png_name 对齐。"""
    b = basename.lower()
    b = re.sub(r'\.(dds|png)$', '', b)
    b = re.sub(r'\s+', '-', b.strip())
    return b


def needed_icons():
    """科技升级图标 + 兵种数据库（data/units-v2.json）里引用的单位/建筑图标。
    units-v2 的 icon 可能是 'btn-*.png'，也可能是 wiki 已有的 '/icons/NN.png'（跳过）。"""
    need = set()
    for e in json.load(open(TECH_JSON, encoding='utf-8')):
        for g in e.get('upgrades', []):
            if g.get('icon'):
                need.add(g['icon'])  # 已是 png 名
    if os.path.exists(UNITS_JSON):
        units = json.load(open(UNITS_JSON, encoding='utf-8')).get('units', {})
        for u in units.values():
            icon = u.get('icon')
            if icon and not icon.startswith('/'):
                need.add(icon)
    return need


def index_source():
    """所有 SRC_DIRS 递归 → {规范key: 绝对路径}（前面的目录优先，支持 png 源）。"""
    idx = {}
    for d in SRC_DIRS:
        if not os.path.isdir(d):
            continue
        for pat in ('*.dds', '*.png'):
            for p in glob.glob(os.path.join(d, '**', pat), recursive=True):
                idx.setdefault(_norm(os.path.basename(p)), p)
    return idx


def main():
    live = [d for d in SRC_DIRS if os.path.isdir(d)]
    if not live:
        print('[x] 源目录都不存在:')
        for d in SRC_DIRS:
            print(f'    {d}')
        print('    请先用 CascView 从 D:/StarCraft II 导出 btn-*.dds，')
        print('    并跑 scripts/extract_map_icons.py 解出地图自带贴图。')
        sys.exit(1)
    for d in SRC_DIRS:
        if not os.path.isdir(d):
            print(f'[!] 源目录缺失（跳过）: {d}')
    os.makedirs(OUT_DIR, exist_ok=True)
    need = needed_icons()
    idx = index_source()
    print(f'需要 {len(need)} 个图标；源目录索引 {len(idx)} 个 dds')

    def lookup(key):
        """精确命中；否则前缀匹配（如 btn-unit-protoss-scout → …-scout-purifier）。
        多个候选时取名字最短的，保证确定性。"""
        if key in idx:
            return idx[key]
        cands = [k for k in idx if k.startswith(key + '-')]
        if not cands:
            return None
        return idx[min(cands, key=len)]

    hit, miss, err = [], [], []
    for png_name in sorted(need):
        key = _norm(png_name)
        src = lookup(key)
        if not src:
            miss.append(png_name)
            continue
        try:
            im = Image.open(src).convert('RGBA')
            im.save(os.path.join(OUT_DIR, png_name))
            hit.append(png_name)
        except Exception as ex:  # PIL 不支持的 dds 压缩格式等
            err.append((png_name, str(ex)[:60]))

    print(f'\n转换成功 {len(hit)}/{len(need)} → public/tech-icons/')
    if err:
        print(f'转换失败 {len(err)}（PIL 不支持的格式，需 texconv 兜底）:')
        for n, e in err:
            print(f'  {n}: {e}')
    if miss:
        print(f'源目录缺失 {len(miss)}（CascView 导出未覆盖，或在 ui/ 等其它目录）:')
        for n in miss:
            print(f'  {n}')
    if not err and not miss:
        print('全部命中 ✔')


if __name__ == '__main__':
    main()
