# -*- coding: utf-8 -*-
"""
生成 KS2 Wiki 的 logo（刀锋女王徽记风格）。
用法:  PACKY_KEY=sk-xxx PYTHONUTF8=1 python scripts/gen_logo.py
依赖:  requests, Pillow
产物:  public/logo.png(1024透明) / logo-512.png / apple-touch-icon.png(180)
       public/favicon-32.png / favicon-16.png / public/favicon.ico
"""
import os, sys, base64, io
from pathlib import Path

try:
    import requests
    from PIL import Image
except ImportError as e:
    print("缺少依赖:", e, "\n请先 pip install requests Pillow"); sys.exit(2)

BASE = "https://www.packyapi.com"
MODEL = "gpt-image-2"
ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "public"

PROMPT = (
    "A premium app logo emblem for a StarCraft 2 fan wiki named 'Kerrigan Survival 2'. "
    "Centerpiece: a stylized Queen of Blades insignia formed by two elegant curved zerg "
    "wing-blades sweeping upward and outward in mirror symmetry, sharp bone-blade edges, "
    "subtle psionic glow. The blades enclose a clean negative-space silhouette. "
    "Color: a smooth gradient from Kerrigan crimson red (#dc2626) on the left to "
    "survivor electric blue (#2563eb) on the right, with a soft purple-magenta blend in "
    "the center. Modern flat vector emblem style, bold clean shapes, high contrast, "
    "strong silhouette that stays legible at small sizes. Centered composition, "
    "the emblem sits on a completely flat solid pure white (#ffffff) background "
    "with clear empty margin around it, no text, no letters, no words. "
    "Crisp game-icon aesthetic, premium, minimal."
)


def generate():
    key = os.environ.get("PACKY_KEY") or os.environ.get("PACKY_API_KEY")
    if not key:
        print("ERROR: 未设置环境变量 PACKY_KEY"); sys.exit(2)

    # 代理: 优先 PROXY，其次 HTTPS_PROXY/HTTP_PROXY
    proxy = (os.environ.get("PROXY") or os.environ.get("HTTPS_PROXY")
             or os.environ.get("HTTP_PROXY"))
    proxies = {"http": proxy, "https": proxy} if proxy else None
    print(f"调用 PackyAPI 生成主图 (1024, 白底)... 代理: {proxy or '无(直连)'}")

    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "size": "1024x1024",
        "quality": "high",
        "output_format": "png",
        "n": 1,
    }
    resp = None
    for attempt in range(1, 4):
        try:
            resp = requests.post(
                f"{BASE}/v1/images/generations",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json=payload, proxies=proxies, timeout=300,
            )
        except requests.RequestException as e:
            print(f"  第{attempt}次连接失败: {e}")
            if attempt == 3:
                sys.exit(1)
            continue
        if resp.status_code == 200:
            break
        print(f"  第{attempt}次返回 {resp.status_code}, 重试...")
    if resp is None or resp.status_code != 200:
        print("API 错误", resp.status_code if resp else "无响应",
              (resp.text[:500] if resp else "")); sys.exit(1)
    data = resp.json()["data"][0]
    # gpt-image-2 始终回 url（b64_json 参数会触发源站 502，故不使用）
    if data.get("b64_json"):
        return base64.b64decode(data["b64_json"])
    url = data.get("url")
    if url:
        print("拿到 url, 下载中:", url[:80])
        r = requests.get(url, proxies=proxies, timeout=120)
        r.raise_for_status()
        return r.content
    print("响应无 b64_json/url:", str(data)[:300]); sys.exit(1)


def remove_white_bg(img, tol=18):
    """从四角洪水填充，把连通的白底区域抠成透明（保留内部浅色不打洞）。"""
    from collections import deque
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    def is_white(p):
        return p[0] >= 255 - tol and p[1] >= 255 - tol and p[2] >= 255 - tol

    seen = bytearray(w * h)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        if not is_white(px[x, y]):
            continue
        px[x, y] = (0, 0, 0, 0)
        dq.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return img


def export(png_bytes):
    PUB.mkdir(exist_ok=True)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    if img.size != (1024, 1024):
        img = img.resize((1024, 1024), Image.LANCZOS)

    # 抠白底 -> 透明
    print("抠白底为透明...")
    transparent = remove_white_bg(img)
    # 留一个保险：把带白底的原图也存一份，万一抠图不理想可对照
    img.save(PUB / "logo-whitebg.png")
    img = transparent

    # 主图 + 各尺寸缩图
    out = {
        "logo.png": 1024,
        "logo-512.png": 512,
        "apple-touch-icon.png": 180,
        "favicon-32.png": 32,
        "favicon-16.png": 16,
    }
    for name, size in out.items():
        im = img if size == 1024 else img.resize((size, size), Image.LANCZOS)
        im.save(PUB / name)
        print(f"  写出 {name} ({size}px)")

    # 多分辨率 favicon.ico
    ico_sizes = [(16, 16), (32, 32), (48, 48)]
    img.save(PUB / "favicon.ico", sizes=ico_sizes)
    print("  写出 favicon.ico (16/32/48)")
    print("完成。产物在", PUB)


if __name__ == "__main__":
    export(generate())
