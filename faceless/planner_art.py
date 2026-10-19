"""Daily Quiet Money Planner artwork: one black-and-gold image per day, drawn in code (free, repeatable, identical look every run).

The owner's own pictures take priority: any file `assets/planner/source/day-NNN.<jpg|png|webp>` (cleaned of handles by planner_clean.py into
`assets/planner/clean/`) is used for that day. Every other day gets a drawn picture in the same visual language: near-black ground, one warm
light, gold coins and gold lines, no text, no people. Motifs are keyed to the lesson (compounding curve, 50/30/20 ring, balance scale...), and a
per-day seed moves the composition so no two days are the same picture.

Style lock (see channel/products/daily-quiet-money-planner/CONTEXT.md): ground #0E0E10, gold #FFD23F, deep gold #C9A227, cream #F5F1E6 for tiny
highlights only, one warm light from the upper left, 2.2:1 frame, no text in the picture (the page adds the words).
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from faceless import brand
from faceless.config import STUDIO

W, H = 1320, 600                       # delivered size; drawn at SS x for clean edges
SS = 2
INK, GOLD, DEEP, CREAM = brand.INK, brand.GOLD, brand.DEEP_GOLD, brand.CREAM
EXTS = (".jpg", ".jpeg", ".png", ".webp")
SOURCE = STUDIO / "assets" / "planner" / "source"
CLEAN = STUDIO / "assets" / "planner" / "clean"
GENERATED = STUDIO / "assets" / "planner" / "generated"
MOTIFS = ("stack", "coin", "curve", "bars", "ring", "scale", "rain", "steps", "gauge", "tree", "road", "shield", "grid", "pair")


# ---------------------------------------------------------------- ground and light

def _ground(seed: int) -> Image.Image:
    rnd = random.Random(seed)
    w, h = W * SS, H * SS
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = rnd.uniform(0.15, 0.4) * w, rnd.uniform(0.1, 0.45) * h            # the one warm light, upper left
    d = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2)
    glow = np.clip(1.0 - d * 1.55, 0, 1) ** 2.2
    vig = np.clip(1.0 - (((xx / w - 0.5) * 1.25) ** 2 + ((yy / h - 0.5) * 1.5) ** 2), 0.25, 1)
    base = np.array(INK, dtype=np.float32)
    warm = np.array((92, 68, 14), dtype=np.float32)
    rgb = (base[None, None, :] + warm[None, None, :] * glow[..., None]) * vig[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _glow(im: Image.Image, layer: Image.Image, radius: int, strength: float) -> Image.Image:
    """Add a soft bloom of `layer` (an RGB image on black) onto `im`."""
    bloom = layer.filter(ImageFilter.GaussianBlur(radius))
    bloom = bloom.point(lambda v: min(255, int(v * strength)))
    return ImageChops.add(im, bloom)


# ---------------------------------------------------------------- coins

def _coin(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, squash: float = 1.0, thick: float = 0.0, q: bool = False) -> None:
    """A gold coin. squash<1 tilts it (an ellipse); thick>0 draws the edge below it (for stacks)."""
    ry = r * squash
    t = thick * r
    if t > 0:
        steps = max(2, int(t))
        for i in range(steps, 0, -1):
            f = i / steps
            d.ellipse([cx - r, cy - ry + t * f, cx + r, cy + ry + t * f], fill=_lerp(DEEP, (120, 92, 18), f))
    d.ellipse([cx - r, cy - ry, cx + r, cy + ry], fill=GOLD)
    ring = r * 0.09
    d.ellipse([cx - r + ring, cy - ry + ring * squash, cx + r - ring, cy + ry - ring * squash], outline=DEEP, width=max(2, int(r * 0.03)))
    d.ellipse([cx - r * 0.55, cy - ry * 0.95, cx + r * 0.1, cy - ry * 0.3], fill=_lerp(GOLD, (255, 240, 170), 0.55))   # sheen
    if q and squash > 0.85:
        f = brand.font("Montserrat-Black.ttf", int(r * 1.2))
        bb = d.textbbox((0, 0), "Q", font=f)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), "Q", font=f, fill=INK)


def _gold_line(d: ImageDraw.ImageDraw, pts: list[tuple[float, float]], width: int, fill=GOLD) -> None:
    d.line(pts, fill=fill, width=width, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - width / 2, p[1] - width / 2, p[0] + width / 2, p[1] + width / 2], fill=fill)


# ---------------------------------------------------------------- motifs (each draws onto an RGB image at SS scale)

def m_stack(d, rnd, w, h):
    base_y = h * 0.82
    n_stacks = rnd.choice((2, 3, 3, 4))
    xs = [w * (0.2 + 0.6 * i / max(1, n_stacks - 1)) + rnd.uniform(-0.03, 0.03) * w for i in range(n_stacks)] if n_stacks > 1 else [w * 0.5]
    r = h * 0.15
    for i, x in enumerate(xs):
        n = rnd.randint(3, 6) + i * rnd.choice((0, 1, 2))
        for k in range(n):
            _coin(d, x, base_y - k * r * 0.2, r, 0.34, 0.2)
    if rnd.random() < 0.7:
        _coin(d, rnd.uniform(0.38, 0.62) * w, h * 0.3, r * 1.1, 0.34, 0.2)             # a coin in the air


def m_coin(d, rnd, w, h):
    r = h * 0.33
    cx = w * rnd.uniform(0.42, 0.58)
    for k, f in enumerate((1.0, 1.0)):                                                # a few echo coins behind for depth
        pass
    _coin(d, cx - r * 1.5, h * 0.62, r * 0.55, 0.9, 0)
    _coin(d, cx + r * 1.6, h * 0.66, r * 0.42, 0.9, 0)
    _coin(d, cx, h * 0.5, r, 1.0, 0, q=True)


def m_curve(d, rnd, w, h):
    left, right, top, bot = w * 0.08, w * 0.92, h * 0.12, h * 0.86
    for i in range(1, 6):                                                              # faint grid
        y = bot - (bot - top) * i / 5
        d.line([(left, y), (right, y)], fill=(40, 36, 24), width=3)
    k = rnd.uniform(3.2, 4.6)
    pts = []
    for i in range(61):
        t = i / 60
        pts.append((left + (right - left) * t, bot - (bot - top) * ((math.exp(k * t) - 1) / (math.exp(k) - 1)) ** 1.0))
    flat = [(left + (right - left) * i / 60, bot - (bot - top) * 0.22 * (i / 60)) for i in range(61)]   # the "no growth" line
    _gold_line(d, flat, 5, (110, 96, 60))
    d.polygon(pts + [(right, bot), (left, bot)], fill=(48, 40, 14))
    _gold_line(d, pts, 11)
    ex, ey = pts[-1]
    _coin(d, ex, ey, h * 0.075, 1.0, 0)


def m_bars(d, rnd, w, h):
    n = rnd.randint(7, 11)
    left, right, bot = w * 0.1, w * 0.9, h * 0.86
    gap = (right - left) / n
    grow = rnd.uniform(1.12, 1.3)
    for i in range(n):
        bh = h * 0.1 * (grow ** i) * rnd.uniform(0.9, 1.05)
        bh = min(bh, h * 0.72)
        x0 = left + gap * i + gap * 0.14
        x1 = left + gap * (i + 1) - gap * 0.14
        for y in range(int(bot - bh), int(bot)):
            t = (y - (bot - bh)) / max(1, bh)
            d.line([(x0, y), (x1, y)], fill=_lerp(GOLD, (110, 84, 14), t))
    d.line([(left - 10, bot + 6), (right + 10, bot + 6)], fill=DEEP, width=5)


def m_ring(d, rnd, w, h):
    cx, cy, r = w * rnd.uniform(0.42, 0.58), h * 0.5, h * 0.38
    parts = rnd.choice(((0.5, 0.3, 0.2), (0.5, 0.3, 0.2), (0.6, 0.25, 0.15), (0.7, 0.2, 0.1)))
    cols = (GOLD, DEEP, (120, 98, 30))
    a = -90.0
    for frac, col in zip(parts, cols):
        d.pieslice([cx - r, cy - r, cx + r, cy + r], a, a + 360 * frac - 1.6, fill=col)
        a += 360 * frac
    d.ellipse([cx - r * 0.58, cy - r * 0.58, cx + r * 0.58, cy + r * 0.58], fill=(16, 15, 12))
    _coin(d, cx, cy, r * 0.34, 1.0, 0, q=True)


def m_scale(d, rnd, w, h):
    cx, top, base = w * 0.5, h * 0.2, h * 0.88
    d.rectangle([cx - 8, top, cx + 8, base], fill=DEEP)
    d.rounded_rectangle([cx - w * 0.1, base - 6, cx + w * 0.1, base + 14], radius=8, fill=DEEP)
    tilt = rnd.uniform(-0.12, 0.12)
    half = w * 0.3
    ly, ry = top + h * tilt * 0.5, top - h * tilt * 0.5
    d.line([(cx - half, ly), (cx + half, ry)], fill=GOLD, width=10)
    for sx, sy, heavy in ((cx - half, ly, tilt < 0), (cx + half, ry, tilt >= 0)):
        d.line([(sx, sy), (sx - w * 0.07, sy + h * 0.32)], fill=DEEP, width=4)
        d.line([(sx, sy), (sx + w * 0.07, sy + h * 0.32)], fill=DEEP, width=4)
        d.chord([sx - w * 0.1, sy + h * 0.24, sx + w * 0.1, sy + h * 0.46], 0, 180, fill=GOLD)
        for k in range(4 if heavy else 2):
            _coin(d, sx + (k - 1.5) * h * 0.02, sy + h * 0.25 - k * h * 0.035, h * 0.06, 0.34, 0.2)


def m_rain(d, rnd, w, h):
    coins = [(rnd.uniform(0.04, 0.96) * w, rnd.uniform(0.05, 0.95) * h, rnd.uniform(0.04, 0.12) * h, rnd.uniform(0.35, 1.0)) for _ in range(rnd.randint(16, 24))]
    for x, y, r, sq in sorted(coins, key=lambda c: c[2]):
        _coin(d, x, y, r, sq, 0.1 if sq < 0.8 else 0)


def m_steps(d, rnd, w, h):
    n = rnd.randint(5, 8)
    left, right, bot = w * 0.12, w * 0.88, h * 0.86
    sw = (right - left) / n
    for i in range(n):
        sh = h * (0.12 + 0.62 * (i + 1) / n)
        t = i / max(1, n - 1)
        d.rectangle([left + sw * i, bot - sh, left + sw * (i + 1) - 6, bot], fill=_lerp((120, 94, 16), GOLD, t))
    _coin(d, left + sw * (n - 0.5), bot - h * (0.12 + 0.62) - h * 0.09, h * 0.08, 1.0, 0)


def m_gauge(d, rnd, w, h):
    cx, cy, r = w * 0.5, h * 0.82, h * 0.7
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=(34, 31, 22))
    segs = 18
    val = rnd.uniform(0.2, 0.85)
    for i in range(segs):
        a0 = 180 + 180 * i / segs
        col = _lerp(DEEP, GOLD, i / segs) if i / segs <= val else (52, 47, 30)
        d.pieslice([cx - r, cy - r, cx + r, cy + r], a0 + 1, a0 + 180 / segs - 1, fill=col)
    d.pieslice([cx - r * 0.74, cy - r * 0.74, cx + r * 0.74, cy + r * 0.74], 175, 365, fill=(16, 15, 12))
    ang = math.radians(180 + 180 * val)
    d.line([(cx, cy), (cx + math.cos(ang) * r * 0.82, cy + math.sin(ang) * r * 0.82)], fill=CREAM, width=9)
    d.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=GOLD)


def m_tree(d, rnd, w, h):
    def branch(x, y, ang, ln, depth, wd):
        if depth == 0 or ln < 6:
            if depth == 0:
                d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=GOLD)
            return
        x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        d.line([(x, y), (x2, y2)], fill=_lerp(GOLD, DEEP, depth / 9), width=max(2, int(wd)))
        sp = rnd.uniform(0.35, 0.55)
        branch(x2, y2, ang - sp, ln * rnd.uniform(0.74, 0.82), depth - 1, wd * 0.72)
        branch(x2, y2, ang + sp, ln * rnd.uniform(0.74, 0.82), depth - 1, wd * 0.72)
    branch(w * rnd.uniform(0.45, 0.55), h * 0.97, -math.pi / 2, h * 0.24, 9, 22)


def m_road(d, rnd, w, h):
    hz = h * 0.46
    sun_x = w * rnd.uniform(0.4, 0.6)
    d.ellipse([sun_x - h * 0.2, hz - h * 0.2, sun_x + h * 0.2, hz + h * 0.2], fill=GOLD)
    d.rectangle([0, hz, w, h], fill=(18, 17, 14))
    d.polygon([(sun_x - w * 0.02, hz), (sun_x + w * 0.02, hz), (w * 0.82, h), (w * 0.18, h)], fill=(30, 28, 20))
    for i in range(7):
        t0, t1 = (i / 7) ** 1.8, (i / 7 + 0.07) ** 1.8
        y0, y1 = hz + (h - hz) * t0, hz + (h - hz) * t1
        d.polygon([(sun_x - 2 - 10 * t0, y0), (sun_x + 2 + 10 * t0, y0), (sun_x + 2 + 10 * t1, y1), (sun_x - 2 - 10 * t1, y1)], fill=GOLD)


def m_shield(d, rnd, w, h):
    cx, top = w * 0.5, h * 0.1
    sw, sh = h * 0.36, h * 0.8
    pts = [(cx - sw, top + sh * 0.12), (cx, top), (cx + sw, top + sh * 0.12), (cx + sw * 0.92, top + sh * 0.6), (cx, top + sh), (cx - sw * 0.92, top + sh * 0.6)]
    d.polygon(pts, fill=(34, 30, 18), outline=GOLD, width=10)
    _coin(d, cx, top + sh * 0.46, h * 0.2, 1.0, 0, q=True)


def m_grid(d, rnd, w, h):
    cols, rows = 30, 12
    gx, gy = w * 0.08, h * 0.12
    cw, ch = (w * 0.84) / cols, (h * 0.76) / rows
    lit = int(cols * rows * rnd.uniform(0.25, 0.9))
    for i in range(cols * rows):
        x, y = gx + (i % cols) * cw + cw / 2, gy + (i // cols) * ch + ch / 2
        r = min(cw, ch) * 0.28
        d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD if i < lit else (46, 42, 28))


def m_pair(d, rnd, w, h):
    r = h * 0.2
    base = h * 0.82
    for k in range(rnd.randint(2, 3)):
        _coin(d, w * 0.27, base - k * r * 0.2, r, 0.34, 0.2)
    for k in range(rnd.randint(7, 9)):
        _coin(d, w * 0.72, base - k * r * 0.2, r, 0.34, 0.2)
    d.line([(w * 0.5, h * 0.2), (w * 0.5, base + 10)], fill=(60, 54, 34), width=4)


DRAW = {k: globals()[f"m_{k}"] for k in MOTIFS}


# ---------------------------------------------------------------- public

def render_motif(motif: str, seed: int) -> Image.Image:
    """The drawn picture for one motif and seed, W x H RGB."""
    if motif not in DRAW:
        raise ValueError(f"unknown motif {motif!r}; known: {', '.join(MOTIFS)}")
    rnd = random.Random(seed * 7919 + MOTIFS.index(motif))
    bg = _ground(seed)
    layer = Image.new("RGB", bg.size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    DRAW[motif](d, rnd, *bg.size)
    mask = ImageChops.lighter(layer.convert("L").point(lambda v: 255 if v > 0 else 0), Image.new("L", bg.size, 0))
    shadow = mask.filter(ImageFilter.GaussianBlur(22 * SS)).point(lambda v: int(v * 0.5))
    im = Image.composite(Image.new("RGB", bg.size, (0, 0, 0)), bg, shadow)           # soft contact shadow under everything drawn
    im.paste(layer, mask=mask)
    im = _glow(im, layer.point(lambda v: int(v * 0.75)), 26 * SS, 0.22)                # a faint gold bloom, never clipping the metal
    return im.resize((W, H), Image.LANCZOS)


def owner_image(day: int) -> Path | None:
    """The owner's picture for this day, cleaned copy first, if there is one."""
    for folder in (CLEAN, SOURCE):
        for ext in EXTS:
            p = folder / f"day-{day:03d}{ext}"
            if p.exists():
                return p
    return None


def fit_frame(src: Image.Image) -> Image.Image:
    """Put any picture into the W x H frame: crop when the shape is close, otherwise keep the whole picture over its own blurred, darkened copy."""
    src = src.convert("RGB")
    ratio, target = src.width / src.height, W / H
    if 0.8 * target <= ratio <= 1.25 * target:
        sw, sh = (src.width, int(src.width / target)) if ratio < target else (int(src.height * target), src.height)
        l, t = (src.width - sw) // 2, (src.height - sh) // 2
        return src.crop((l, t, l + sw, t + sh)).resize((W, H), Image.LANCZOS)
    bg = src.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.35))
    s = min(W / src.width, H / src.height)
    fg = src.resize((max(1, int(src.width * s)), max(1, int(src.height * s))), Image.LANCZOS)
    bg.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
    return bg


def day_art(day: int, motif: str, variant: int = 0) -> tuple[Image.Image, str]:
    """(picture, source) where source is 'owner' or 'drawn'. Same inputs, same picture."""
    own = owner_image(day)
    if own:
        return fit_frame(Image.open(own)), "owner"
    return render_motif(motif, day * 31 + variant), "drawn"


def save_day(day: int, motif: str, variant: int = 0, quality: int = 76) -> Path:
    GENERATED.mkdir(parents=True, exist_ok=True)
    im, _src = day_art(day, motif, variant)
    out = GENERATED / f"day-{day:03d}.jpg"
    im.save(out, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=0 if quality > 85 else 2)
    return out
