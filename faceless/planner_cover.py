"""Cover and listing pictures for the Quiet Money Daily Planner.

The cover is drawn from the brand's own coin (faceless/brand.py), the brand fonts and the planner's style lock: near-black ground, one warm light, gold
metal, no people. Nothing here calls a paid service. `cover(w, h)` returns the print cover at any page size; `listing_images()` writes the Etsy and
Gumroad pictures (hero, what is inside, sample pages, the year at a glance) from the real PDF pages.
"""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from faceless import brand, planner_art
from faceless.config import Paths

INK, GOLD, DEEP, CREAM, MUTED = brand.INK, brand.GOLD, brand.DEEP_GOLD, brand.CREAM, brand.MUTED
TITLE_1, TITLE_2 = "THE QUIET MONEY", "DAILY PLANNER"
SUB = "365 days of basic money lessons.\nOne picture. One lesson. One small action."
CHIPS = ("365 PAGES", "LETTER + A4", "UNDATED")
TAGLINE = "The money rules nobody taught you."


def _ground(w: int, h: int, cx: float, cy: float, strength: float = 1.0) -> Image.Image:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - cx * w) / w) ** 2 + ((yy - cy * h) / h) ** 2)
    glow = np.clip(1.0 - d * 1.9, 0, 1) ** 2.0
    vig = np.clip(1.0 - (((xx / w - 0.5) * 1.1) ** 2 + ((yy / h - 0.5) * 1.1) ** 2), 0.3, 1)
    base = np.array(INK, np.float32)
    warm = np.array((104, 78, 16), np.float32) * strength
    rgb = (base + warm * glow[..., None]) * vig[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def _fit(draw: ImageDraw.ImageDraw, text: str, font_name: str, width: int, start: int, spacing: int = 0) -> tuple:
    size = start
    while size > 10:
        f = brand.font(font_name, size)
        tw = draw.textlength(text, font=f) + spacing * (len(text) - 1)
        if tw <= width:
            return f, tw
        size -= 2
    f = brand.font(font_name, 10)
    return f, draw.textlength(text, font=f)


def _spaced(draw: ImageDraw.ImageDraw, xy: tuple, text: str, font, fill, spacing: int) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def _dust(im: Image.Image, seed: int, n: int = 140) -> Image.Image:
    rnd = random.Random(seed)
    layer = Image.new("RGB", im.size, (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x, y = rnd.uniform(0, im.width), rnd.uniform(0, im.height)
        r = rnd.choice((1, 1, 2, 2, 3, 4)) * max(1, im.width // 1700)
        a = rnd.randint(50, 200)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(a, int(a * 0.8), int(a * 0.22)))
    return ImageChops.add(im, layer.filter(ImageFilter.GaussianBlur(max(1, im.width // 1100))))


def _stacks(w: int, h: int, seed: int) -> Image.Image:
    """Three lit coin stacks along the bottom edge, drawn with the same coin as the daily pictures (RGBA, on transparent)."""
    ss = 2
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    rnd = random.Random(seed)
    r = h * ss * 0.2
    for cx, n in ((0.16, rnd.randint(3, 4)), (0.5, rnd.randint(6, 8)), (0.84, rnd.randint(4, 5))):
        for k in range(n):
            planner_art._coin(d, w * ss * cx, h * ss * 0.8 - k * r * 0.2, r, 0.34, 0.2)
    return big.resize((w, h), Image.LANCZOS)


def cover(w: int = 1700, h: int = 2200, seed: int = 11) -> Image.Image:
    """The print cover at any size (w x h pixels). All positions are fractions, so it holds from Letter to A4 to a square crop."""
    im = _ground(w, h, 0.5, 0.26)
    im = _dust(im, seed)
    d = ImageDraw.Draw(im)
    # wordmark
    f = brand.font("Montserrat-ExtraBold.ttf", int(w * 0.026))
    word, sp = "QUIET MONEY", int(w * 0.012)
    tw = sum(d.textlength(ch, font=f) + sp for ch in word) - sp
    _spaced(d, ((w - tw) / 2, h * 0.055), word, f, CREAM, sp)
    d.rectangle([w / 2 - w * 0.03, h * 0.055 + w * 0.045, w / 2 + w * 0.03, h * 0.055 + w * 0.049], fill=GOLD)
    # the coin: brand mark, with a warm halo and a long soft shadow
    cd = int(w * 0.36)
    cx, cy = w // 2, int(h * 0.245)
    halo = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(halo).ellipse([cx - cd * 0.62, cy - cd * 0.62, cx + cd * 0.62, cy + cd * 0.62], fill=(120, 90, 18))
    im = ImageChops.add(im, halo.filter(ImageFilter.GaussianBlur(cd // 3)))
    side = brand.coin(int(cd * 0.42))
    for sx, sy, a in ((-0.78, 0.22, 0.5), (0.8, 0.24, 0.4)):                              # two smaller coins behind, for depth
        dim = side.copy()
        dim.putalpha(dim.getchannel("A").point(lambda v, a=a: int(v * a)))
        im.paste(dim, (int(cx + sx * cd - side.width / 2), int(cy + sy * cd - side.height / 2)), dim)
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([cx - cd * 0.5, cy - cd * 0.5 + cd * 0.06, cx + cd * 0.5, cy + cd * 0.5 + cd * 0.06], fill=(0, 0, 0, 170))
    shadow = shadow.filter(ImageFilter.GaussianBlur(cd // 14))
    im.paste(shadow, (0, 0), shadow)
    coin = brand.coin(cd)
    im.paste(coin, (cx - cd // 2, cy - cd // 2), coin)
    d = ImageDraw.Draw(im)
    # title
    width = int(w * 0.84)
    f1, tw1 = _fit(d, TITLE_1, "Anton-Regular.ttf", width, int(w * 0.1))
    y = int(h * 0.455)
    d.text(((w - tw1) / 2, y), TITLE_1, font=f1, fill=CREAM)
    f2, tw2 = _fit(d, TITLE_2, "Anton-Regular.ttf", width, int(w * 0.165))
    y2 = y + int(f1.size * 1.25)
    d.text(((w - tw2) / 2, y2), TITLE_2, font=f2, fill=GOLD)
    y3 = y2 + int(f2.size * 1.28)
    d.rectangle([w / 2 - w * 0.07, y3, w / 2 + w * 0.07, y3 + max(4, int(w * 0.006))], fill=GOLD)
    # subtitle
    fs = brand.font("Montserrat-ExtraBold.ttf", int(w * 0.028))
    ys = y3 + int(w * 0.04)
    for line in SUB.split("\n"):
        lw = d.textlength(line, font=fs)
        d.text(((w - lw) / 2, ys), line, font=fs, fill=(218, 212, 196))
        ys += int(fs.size * 1.55)
    # chips
    fc = brand.font("Montserrat-ExtraBold.ttf", int(w * 0.021))
    pads = int(w * 0.022)
    widths = [d.textlength(c, font=fc) + pads * 2 for c in CHIPS]
    gap = int(w * 0.02)
    x = (w - (sum(widths) + gap * (len(CHIPS) - 1))) / 2
    ych = ys + int(w * 0.012)
    chip_h = int(fc.size * 2.2)
    for c, cw in zip(CHIPS, widths):
        d.rounded_rectangle([x, ych, x + cw, ych + chip_h], radius=chip_h // 2, outline=GOLD, width=max(2, int(w * 0.002)))
        d.text((x + pads, ych + (chip_h - fc.size) / 2 - fc.size * 0.08), c, font=fc, fill=GOLD)
        x += cw + gap
    # lit coin stacks and the footer line
    st = _stacks(w, int(h * 0.17), seed)
    top = h - st.height
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    glow.paste(st.convert("RGB"), (0, top), st.getchannel("A"))
    im = ImageChops.add(im, glow.filter(ImageFilter.GaussianBlur(w // 60)).point(lambda v: int(v * 0.25)))
    im.paste(st, (0, top), st)
    d = ImageDraw.Draw(im)
    ft = brand.font("Montserrat-ExtraBold.ttf", int(w * 0.02))
    tl = d.textlength(TAGLINE.upper(), font=ft) + int(w * 0.006) * (len(TAGLINE) - 1)
    _spaced(d, ((w - tl) / 2, ych + chip_h + h * 0.028), TAGLINE.upper(), ft, (240, 214, 120), int(w * 0.006))
    return im


def thumbnail(size: int = 1200) -> Image.Image:
    """Square Gumroad thumbnail: the real cover, large, on the brand ground with a soft shadow."""
    ss = size * 2
    img = _ground(ss, ss, 0.5, 0.45, 0.8)
    h = int(ss * 0.9)
    cov = cover(1700, 2200).resize((int(h * 1700 / 2200), h), Image.LANCZOS)
    x, y = (ss - cov.width) // 2, (ss - h) // 2
    shadow = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([x + 16, y + 30, x + cov.width + 16, y + h + 30], fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(ss // 40))
    img.paste(shadow, (0, 0), shadow)
    img.paste(cov, (x, y))
    ImageDraw.Draw(img).rectangle([x, y, x + cov.width, y + h], outline=GOLD, width=max(3, ss // 400))
    return img.resize((size, size), Image.LANCZOS)
