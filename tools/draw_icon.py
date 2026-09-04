"""Draw the Furmula app icon: a simple deep-blue rounded tile + white sigma.

Writes assets/app_icon/:
  icon_1024.png / icon_512.png / icon_256.png / icon_128.png / icon_64.png /
  icon_32.png / icon_16.png / app.ico (multi-size)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "assets", "app_icon")

GRAD_TOP = (86, 143, 255)      # lighter deep blue
GRAD_BOT = (18, 47, 148)       # deeper navy
SYMBOL = "\u2211"              # n-ary summation
TILE = 0.86                    # tile fills this fraction of the canvas
RADIUS = 0.24                  # tile corner radius, relative to tile size


def vertical_gradient(size, top, bottom):
    w, h = size
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        col.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return col.resize(size, Image.BILINEAR)


def draw_master(size):
    s = size
    pad = s * (1 - TILE) / 2
    tile_w = tile_h = s * TILE
    radius = int(RADIUS * tile_w)

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [pad, pad, pad + tile_w, pad + tile_h], radius=radius, fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(max(1.0, s / 2000)))

    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = vertical_gradient((s, s), GRAD_TOP, GRAD_BOT).convert("RGBA")
    canvas.paste(grad, (0, 0), mask)

    # subtle top-left gloss + inner rim
    gloss = Image.new("L", (s, s), 0)
    gd = ImageDraw.Draw(gloss)
    gd.ellipse([pad - s * 0.15, pad - s * 0.22, pad + s * 0.55, pad + s * 0.42], fill=52)
    gloss = gloss.filter(ImageFilter.GaussianBlur(s * 0.06))
    canvas.paste((255, 255, 255, 255), (0, 0), gloss)

    rim = Image.new("L", (s, s), 0)
    rd = ImageDraw.Draw(rim)
    rd.rounded_rectangle(
        [pad, pad, pad + tile_w, pad + tile_h],
        radius=radius,
        outline=255,
        width=max(2, int(s * 0.006)),
    )
    canvas.paste((210, 228, 255, 220), (0, 0), rim)

    # --- white summation sign ---------------------------------------------
    draw = ImageDraw.Draw(canvas)
    for fname in ("simhei.ttf", "seguisym.ttf", "msyh.ttc", "segoeui.ttf"):
        fp = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", fname)
        if not os.path.isfile(fp):
            continue
        try:
            probe = ImageFont.truetype(fp, 96)
        except Exception:
            continue
        if probe.getlength(SYMBOL) <= 0:
            continue
        font_path = fp
        break
    else:
        font_path = None

    # symbol target: centred on the tile
    box_cx, box_cy = s * 0.5, s * 0.52
    box_w = s * TILE * 0.62
    if font_path:
        fs = box_w * 1.9
        font = ImageFont.truetype(font_path, int(fs))
        while font.getlength(SYMBOL) > box_w and fs > 8:
            fs *= 0.95
            font = ImageFont.truetype(font_path, int(fs))
        bb = font.getbbox(SYMBOL)
        tw = font.getlength(SYMBOL)
        ascent, descent = font.getmetrics()
        x0 = box_cx - tw / 2 - bb[0]
        y0 = box_cy - (ascent - descent) / 2 - bb[1]
        draw.text((x0, y0), SYMBOL, font=font, fill=(255, 255, 255, 255))
    else:
        ln = max(2, s // 170)

        def seg(p1, p2, width):
            draw.line([(p1[0] * s, p1[1] * s), (p2[0] * s, p2[1] * s)],
                      fill=(255, 255, 255, 255), width=width)

        seg((0.32, 0.34), (0.68, 0.34), ln)
        seg((0.68, 0.38), (0.44, 0.52), ln)
        seg((0.44, 0.55), (0.64, 0.66), ln)
    return canvas


def main():
    os.makedirs(OUT, exist_ok=True)
    master = draw_master(1024)
    master.save(os.path.join(OUT, "icon_1024.png"))
    for px in (512, 256, 128, 64, 32, 16):
        master.resize((px, px), Image.LANCZOS).save(os.path.join(OUT, f"icon_{px}.png"))
    master.save(
        os.path.join(OUT, "app.ico"),
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("icons written to", OUT)


if __name__ == "__main__":
    sys.exit(main())
