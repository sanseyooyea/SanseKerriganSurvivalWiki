# -*- coding: utf-8 -*-
"""
生成 KS2 文字方块 logo 的 PNG/ICO 各尺寸。
纯 Pillow 绘制：红->蓝对角渐变圆角方块 + 白色粗体 KS2。
用法:  PYTHONUTF8=1 python scripts/gen_logo_text.py
产物:  public/ 下 logo.png(1024)/logo-512/apple-touch-icon(180)/favicon-32/16/favicon.ico
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "public"
RED = (220, 38, 38)      # #dc2626 kerrigan
BLUE = (37, 99, 235)     # #2563eb survivor

# 找一个粗体无衬线字体
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
    r"C:\Windows\Fonts\arialbd.ttf",    # Arial Bold
    r"C:\Windows\Fonts\ARLRDBD.TTF",
]


def font_for(px):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def render(size, text="KS2", supersample=4):
    """绘制一张 size×size 的圆角渐变方块 logo（带文字）。"""
    S = size * supersample
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 对角渐变 (左上红 -> 右下蓝)，按 (x+y) 归一化
    grad = Image.new("RGB", (S, S))
    gpx = grad.load()
    maxd = (S - 1) * 2 or 1
    for y in range(S):
        for x in range(S):
            gpx[x, y] = lerp(RED, BLUE, (x + y) / maxd)

    # 圆角蒙版
    radius = int(S * 15 / 64)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [int(S * 2 / 64), int(S * 2 / 64), S - int(S * 2 / 64), S - int(S * 2 / 64)],
        radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # 文字
    fs = int(S * (29 / 64))
    font = font_for(fs)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (S - tw) / 2 - bbox[0]
    ty = (S - th) / 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

    return img.resize((size, size), Image.LANCZOS)


def main():
    PUB.mkdir(exist_ok=True)
    sizes = {
        "logo.png": 1024,
        "logo-512.png": 512,
        "apple-touch-icon.png": 180,
        "favicon-32.png": 32,
        "favicon-16.png": 16,
    }
    for name, size in sizes.items():
        render(size).save(PUB / name)
        print(f"  写出 {name} ({size}px)")

    # 多分辨率 favicon.ico（直接各尺寸单独渲染，保证小尺寸锐利）
    ico_imgs = [render(s) for s in (16, 32, 48)]
    ico_imgs[1].save(PUB / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)],
                     append_images=[ico_imgs[0], ico_imgs[2]])
    print("  写出 favicon.ico (16/32/48)")
    print("完成。产物在", PUB)


if __name__ == "__main__":
    main()
