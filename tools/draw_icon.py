"""Draw the Furmula app icon: a blue water drop + white summation sign.

The drop is a circle with two tangent lines meeting at an apex on top,
filled with a vertical blue gradient, a soft gloss highlight and a light
rim. The white sigma sits in the visual centre of the drop.

Writes assets/app_icon/:
  icon_1024.png / icon_512.png / icon_256.png / icon_128.png / icon_64.png /
  icon_32.png / icon_16.png / app.ico (multi-size)
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "assets", "app_icon")

GRAD_TOP = (86, 143, 255)      # lighter deep blue
GRAD_BOT = (18, 47, 148)       # deeper navy
SYMBOL = "\u2211"              # n-ary summation

# drop geometry (fractions of the canvas)
APEX = (0.5, 0.07)             # top point of the drop
CIRCLE_C = (0.5, 0.60)         # centre of the round bottom
CIRCLE_R = 0.295               # its radius


def vertical_gradient(size, top, bottom):
    w, h = size
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1)
        col.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return col.resize(size, Image.BILINEAR)


def _drop_points(size):
    """Outline of the drop: apex -> right tangent -> bottom arc -> left tangent."""
    s = size
    cx, cy = CIRCLE_C[0] * s, CIRCLE_C[1] * s
    r = CIRCLE_R * s
    ax, ay = APEX[0] * s, APEX[1] * s

    d = math.hypot(ax - cx, ay - cy)
    theta = math.atan2(ay - cy, ax - cx)          # direction C -> apex
    beta = math.acos(min(1.0, r / d))             # half-angle between the tangents
    a0, a1 = theta - beta, theta + beta           # tangent-point angles

    # arc from a1 going the long way (through the bottom) to a0 + 2π
    pts = [(ax, ay)]
    steps = 120
    start, end = a1, a0 + 2 * math.pi
    for i in range(steps + 1):
        ang = start + (end - start) * i / steps
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def draw_master(size, bold_symbol=False):
    s = size

    # --- drop silhouette mask ---------------------------------------------
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(_drop_points(s), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(1.0, s / 2000)))

    canvas = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = vertical_gradient((s, s), GRAD_TOP, GRAD_BOT).convert("RGBA")
    canvas.paste(grad, (0, 0), mask)

    # --- black outline along the drop edge ---------------------------------
    rim = Image.new("L", (s, s), 0)
    ImageDraw.Draw(rim).polygon(_drop_points(s), outline=255,
                                width=max(2, int(s * 0.012)))
    canvas.paste((10, 12, 20, 255), (0, 0), rim)

    # --- white summation sign ----------------------------------------------
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

    # symbol target: offset to the lower-right of the drop for a playful,
    # artistic look (instead of dead-centre)
    box_cx, box_cy = s * 0.56, s * 0.645
    box_w = 2 * CIRCLE_R * s * 0.50
    if font_path and not bold_symbol:
        fs = box_w * 1.9
        font = ImageFont.truetype(font_path, int(fs))
        while font.getlength(SYMBOL) > box_w and fs > 8:
            fs *= 0.95
            font = ImageFont.truetype(font_path, int(fs))
        bb = font.getbbox(SYMBOL)
        tw = font.getlength(SYMBOL)
        ascent, descent = font.getmetrics()
        # render on its own layer so the glyph can be tilted slightly
        layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(layer)
        x0 = s * 0.5 - tw / 2 - bb[0]
        y0 = s * 0.5 - (ascent - descent) / 2 - bb[1]
        ldraw.text((x0, y0), SYMBOL, font=font, fill=(255, 255, 255, 255))
        layer = layer.rotate(-12, resample=Image.BICUBIC, center=(s * 0.5, s * 0.5))
        canvas.alpha_composite(layer, (int(box_cx - s * 0.5), int(box_cy - s * 0.5)))
    else:
        # vector sigma; the bold variant (small sizes) uses much thicker
        # strokes so the glyph survives downscaling
        ln = max(2, int(s * (0.09 if bold_symbol else 0.045)))
        hw, hh = box_w / 2, box_w * 0.44          # half width / height
        ox, oy = box_cx - s * 0.5, box_cy - s * 0.5  # same lower-right offset

        def seg(p1, p2):
            draw.line([(p1[0] * s + ox, p1[1] * s + oy),
                       (p2[0] * s + ox, p2[1] * s + oy)],
                      fill=(255, 255, 255, 255), width=ln)

        seg((0.5 - hw / s, 0.5 - hh / s), (0.5 + hw / s, 0.5 - hh / s))
        seg((0.5 + hw / s, 0.5 - hh * 0.72 / s), (0.5 - hw * 0.18 / s, 0.5 + hh * 0.06 / s))
        seg((0.5 - hw * 0.18 / s, 0.5 + hh * 0.28 / s), (0.5 + hw * 0.80 / s, 0.5 + hh / s))
    return canvas


def main():
    os.makedirs(OUT, exist_ok=True)
    master = draw_master(1024)
    master.save(os.path.join(OUT, "icon_1024.png"))
    for px in (512, 256, 128, 64):
        master.resize((px, px), Image.LANCZOS).save(os.path.join(OUT, f"icon_{px}.png"))
    # small sizes: bold-stroke sigma so the glyph stays legible when tiny
    bold = draw_master(1024, bold_symbol=True)
    for px in (32, 16):
        bold.resize((px, px), Image.LANCZOS).save(os.path.join(OUT, f"icon_{px}.png"))
    # ico candidates: every requested size provided exactly; 16/32 use bold
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    candidates = []
    for px in ico_sizes:
        src = bold if px in (16, 32) else master
        candidates.append(src.resize((px, px), Image.LANCZOS))
    master.save(
        os.path.join(OUT, "app.ico"),
        format="ICO",
        sizes=[(px, px) for px in ico_sizes],
        append_images=candidates,
    )
    print("icons written to", OUT)


if __name__ == "__main__":
    sys.exit(main())
