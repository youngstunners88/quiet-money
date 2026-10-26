"""Fiverr gig gallery images v2 (skill faceless-gig-gallery): six 1280x769 images with a cinematic look, drawn entirely in code.

The look: near-black ground, volumetric light rays, bokeh, glowing glass cards in perspective, bloom. The pictures inside the cards are real
engine output (brand kits built by `faceless brandkit`) and the clean mascot/emblem concepts kept in channel/services/studio/gallery-src/
(no lettering in the art). Every word is drawn here so type is crisp. Samples are fictional brands and are labelled as such.

    python -m faceless gigart     # rebuilds channel/services/brand-kit/gallery/ and channel/services/studio/gallery/
"""

from __future__ import annotations

import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from faceless import brand
from faceless.config import Paths

W, H = 1280, 769
SVC = Paths.root / "channel" / "services"
KITS = Path("/tmp/kits")
VIOLET, GOLD, CREAM = (150, 105, 255), (255, 210, 63), (245, 241, 230)
SAMPLES = [("Calm Orbit", "Slow living for fast minds", "mint", "mindfulness", "Calm,Focus,Sleep", "calm-orbit"),
           ("Iron Fork", "Cook it right, once", "coral", "cooking", "Recipes,Technique,Gear", "iron-fork"),
           ("Pixel Harbor", "Game news, minus the noise", "sky", "gaming", "News,Reviews,Deals", "pixel-harbor"),
           ("Night Ledger", "Money stories after dark", "violet", "finance", "Stories,Math,Rules", "night-ledger")]


def ensure_kits() -> None:
    for n, t, p, nz, pills, d in SAMPLES:
        if not (KITS / d / "avatar.png").exists():
            (KITS / d).mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "faceless", "brandkit", n, "--tagline", t, "--palette", p, "--niche", nz, "--pills", pills,
                            "--out", str(KITS / d)], check=True, capture_output=True, timeout=300)


# ------------------------------------------------------------------ light and glass primitives

def backdrop(top=(20, 16, 40), mid=(8, 8, 16), bot=(2, 2, 6), glow=(110, 70, 220), gx=0.78, gy=0.35, seed=1) -> Image.Image:
    """Dark vertical gradient + a soft coloured glow + faint grain."""
    y = np.linspace(0, 1, H)[:, None, None]
    t, m, b = (np.array(c, float)[None, None, :] for c in (top, mid, bot))
    base = np.where(y < 0.55, t + (m - t) * (y / 0.55), m + (b - m) * ((y - 0.55) / 0.45))
    base = np.broadcast_to(base, (H, W, 3)).copy()
    xx, yy = np.meshgrid(np.linspace(0, 1, W), np.linspace(0, 1, H))
    d = np.sqrt(((xx - gx) * 1.4) ** 2 + (yy - gy) ** 2)
    g = np.exp(-(d / 0.34) ** 2)[..., None] * np.array(glow, float)[None, None, :] * 0.55
    rng = np.random.default_rng(seed)
    out = np.clip(base + g + rng.normal(0, 1.6, (H, W, 1)), 0, 255)
    return Image.fromarray(out.astype("uint8"), "RGB")


def rays(im: Image.Image, ox: float, oy: float, color=(255, 214, 120), strength=0.22, n=16, spread=1.5, seed=3) -> Image.Image:
    """Volumetric light shafts fanning out from (ox, oy) in fractions of the canvas."""
    rnd = random.Random(seed)
    layer = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(layer)
    cx, cy = ox * W, oy * H
    for _ in range(n):
        a = rnd.uniform(math.pi * 0.55, math.pi * 0.55 + spread)
        width = rnd.uniform(0.02, 0.09)
        L = 1700
        d.polygon([(cx, cy), (cx + math.cos(a - width) * L, cy + math.sin(a - width) * L), (cx + math.cos(a + width) * L, cy + math.sin(a + width) * L)],
                  fill=int(rnd.uniform(40, 120)))
    layer = layer.filter(ImageFilter.GaussianBlur(26))
    tint = Image.new("RGB", (W, H), color)
    return Image.composite(Image.blend(im, tint, min(1.0, strength * 1.8)), im, layer.point(lambda v: int(v * strength * 2.2)))


def bokeh(im: Image.Image, n=26, palette=((150, 105, 255), (255, 210, 63), (120, 190, 255)), seed=7, zone=(0, 0, 1, 1)) -> Image.Image:
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        r = rnd.randint(8, 46)
        x = rnd.uniform(zone[0], zone[2]) * W
        y = rnd.uniform(zone[1], zone[3]) * H
        c = rnd.choice(palette)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*c, rnd.randint(14, 46)), outline=(*c, rnd.randint(30, 80)), width=2)
    layer = layer.filter(ImageFilter.GaussianBlur(2.2))
    out = im.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def bloom(im: Image.Image, thresh=222, radius=20, gain=0.5) -> Image.Image:
    bright = im.point(lambda v: max(0, v - thresh) * 4)
    glow = bright.filter(ImageFilter.GaussianBlur(radius))
    return ImageChops.screen(im, glow.point(lambda v: int(v * gain)))


def vignette(im: Image.Image, strength=0.55) -> Image.Image:
    xx, yy = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    v = 1 - strength * np.clip(np.sqrt(xx ** 2 * 0.8 + yy ** 2) - 0.45, 0, 1) ** 1.6
    return Image.fromarray((np.asarray(im, float) * v[..., None]).clip(0, 255).astype("uint8"))


def _persp_coeffs(src, dst):
    a = []
    for (x, y), (u, v) in zip(dst, src):
        a += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
    A = np.array(a, float)
    b = np.array([c for p in src for c in p], float)
    return np.linalg.solve(A, b)


def _overlay(out: Image.Image, layer: Image.Image, x0: int, y0: int) -> None:
    """alpha_composite that tolerates a layer hanging off the canvas."""
    sx, sy = max(-x0, 0), max(-y0, 0)
    dx, dy = max(x0, 0), max(y0, 0)
    w = min(layer.width - sx, out.width - dx)
    h = min(layer.height - sy, out.height - dy)
    if w > 0 and h > 0:
        out.alpha_composite(layer.crop((sx, sy, sx + w, sy + h)), (dx, dy))


def glass_card(base: Image.Image, art: Image.Image, center, size, yaw=0.0, glow=VIOLET, radius=18, alpha=1.0) -> Image.Image:
    """Paste `art` as a glowing rounded card turned by `yaw` (-1..1, 3-D left/right), with edge light, sheen and a soft shadow."""
    w, h = size
    art = art.convert("RGB").resize((w, h), Image.LANCZOS)
    card = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    card.paste(art, (4, 4), m)
    ImageDraw.Draw(card).rounded_rectangle([3, 3, w + 4, h + 4], radius, outline=(*glow, 235), width=3)
    sheen = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(sheen).polygon([(0, 0), (w * 0.55, 0), (w * 0.15, h), (0, h)], fill=(255, 255, 255, 24))
    sheen.putalpha(ImageChops.multiply(sheen.getchannel("A"), card.getchannel("A")))
    card.alpha_composite(sheen)
    cw, ch = card.size
    pad = 90
    big = Image.new("RGBA", (cw + pad * 2, ch + pad * 2), (0, 0, 0, 0))
    big.paste(card, (pad, pad))
    sq = ch * 0.12 * yaw                      # the nearer edge is taller: yaw>0 makes the right edge nearer
    src = [(pad, pad), (pad + cw, pad), (pad + cw, pad + ch), (pad, pad + ch)]
    dst = [(pad, pad + sq), (pad + cw, pad - sq), (pad + cw, pad + ch + sq), (pad, pad + ch - sq)]
    warped = big.transform(big.size, Image.PERSPECTIVE, _persp_coeffs(src, dst), Image.BICUBIC)
    x0, y0 = int(center[0] - warped.width / 2), int(center[1] - warped.height / 2)
    out = base.convert("RGBA")
    a = warped.getchannel("A")
    shadow = Image.new("RGBA", warped.size, (0, 0, 0, 0))
    shadow.putalpha(a.filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * 0.75)))
    _overlay(out, shadow, x0 + 10, y0 + 36)
    gl = Image.new("RGBA", warped.size, (*glow, 0))
    gl.putalpha(a.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.45)))
    _overlay(out, gl, x0, y0)
    if alpha < 1:
        warped.putalpha(a.point(lambda v: int(v * alpha)))
    _overlay(out, warped, x0, y0)
    return out.convert("RGB")


def _font(name, size):
    return brand.font(name, size)


def text_glow(im: Image.Image, xy, text, size, fill=CREAM, glow=None, font="Anton-Regular.ttf", anchor="la", spacing=2, blur=14) -> Image.Image:
    f = _font(font, size)
    if glow:
        layer = Image.new("RGB", im.size, (0, 0, 0))
        ImageDraw.Draw(layer).multiline_text(xy, text, font=f, fill=glow, anchor=anchor, spacing=spacing, align="center" if anchor[0] == "m" else "left")
        im = ImageChops.screen(im, layer.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(im).multiline_text(xy, text, font=f, fill=fill, anchor=anchor, spacing=spacing, align="center" if anchor[0] == "m" else "left")
    return im


def fit_size(text, max_w, start, font="Anton-Regular.ttf", floor=28):
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    s = start
    while s > floor and max(probe.textlength(l, font=_font(font, s)) for l in text.split("\n")) > max_w:
        s -= 2
    return s


def chip(im: Image.Image, x, y, text, size=22, fg=(14, 14, 16), bg=GOLD) -> tuple[Image.Image, int]:
    d = ImageDraw.Draw(im)
    f = _font("Montserrat-ExtraBold.ttf", size)
    w = int(d.textlength(text, font=f))
    d.rounded_rectangle([x, y, x + w + 34, y + size + 20], 999, fill=bg)
    d.text((x + 17, y + 9), text, font=f, fill=fg)
    return im, w + 34


def label(im: Image.Image, x, y, text="SAMPLE PROJECT: FICTIONAL BRAND", color=(150, 146, 136)):
    ImageDraw.Draw(im).text((x, y), text, font=_font("Montserrat-ExtraBold.ttf", 17), fill=color)


def finish(im: Image.Image, v=0.5) -> Image.Image:
    return vignette(bloom(im), v)


def disc(art: Image.Image, d: int) -> Image.Image:
    art = art.convert("RGB").resize((d, d), Image.LANCZOS)
    m = Image.new("L", (d, d), 0)
    ImageDraw.Draw(m).ellipse([0, 0, d - 1, d - 1], fill=255)
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    out.paste(art, (0, 0), m)
    return out


def paste_disc(im: Image.Image, art: Image.Image, cx, cy, d, glow=VIOLET) -> Image.Image:
    layer = Image.new("RGB", im.size, (0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - d // 2 - 10, cy - d // 2 - 10, cx + d // 2 + 10, cy + d // 2 + 10], fill=glow)
    im = ImageChops.screen(im, layer.filter(ImageFilter.GaussianBlur(34)).point(lambda v: int(v * 0.7)))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([cx - d // 2 + 6, cy - d // 2 + 22, cx + d // 2 + 6, cy + d // 2 + 22], fill=(0, 0, 0, 170))
    out = im.convert("RGBA")
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    _overlay(out, disc(art, d), cx - d // 2, cy - d // 2)
    ImageDraw.Draw(out).ellipse([cx - d // 2, cy - d // 2, cx + d // 2, cy + d // 2], outline=(*CREAM, 130), width=3)
    return out.convert("RGB")


def square_tile(art: Image.Image, side: int, bg=(12, 12, 18), inner=0.72) -> Image.Image:
    tile = Image.new("RGB", (side, side), bg)
    a = art.convert("RGBA")
    k = int(side * inner)
    a = a.resize((k, k), Image.LANCZOS)
    tile.paste(a, ((side - k) // 2, (side - k) // 2), a)
    return tile


# ------------------------------------------------------------------ brand-kit gig

def kit_hero() -> Image.Image:
    ensure_kits()
    kit = KITS / "night-ledger"
    im = backdrop(glow=(120, 70, 230), gx=0.8, gy=0.4)
    im = rays(im, 0.88, -0.05, (200, 160, 255), 0.17, 18)
    im = bokeh(im, 30, seed=11, zone=(0.4, 0.0, 1.0, 0.9))
    im = glass_card(im, Image.open(kit / "og-image.png"), (1135, 185), (300, 158), yaw=-0.5, glow=(120, 90, 255), alpha=0.92)
    im = glass_card(im, Image.open(kit / "banner-youtube.png"), (885, 352), (560, 315), yaw=0.5, glow=VIOLET)
    im = paste_disc(im, Image.open(kit / "avatar.png"), 770, 545, 210)
    im = glass_card(im, Image.open(kit / "palette.png"), (1090, 590), (330, 82), yaw=-0.45, glow=GOLD, alpha=0.96)
    head = "YOUR CHANNEL\nLOOKS LIKE A\nREAL BRAND."
    im = text_glow(im, (66, 96), head, fit_size(head, 470, 100), CREAM, glow=(120, 80, 255), spacing=0, blur=18)
    ImageDraw.Draw(im).rectangle([68, 432, 190, 438], fill=GOLD)
    im = text_glow(im, (68, 462), "Avatar. Banner. Logo. Brand sheet.", 28, CREAM, font="Montserrat-ExtraBold.ttf", blur=6)
    im = text_glow(im, (68, 508), "One consistent kit for faceless channels.", 22, (170, 166, 180), font="Montserrat-ExtraBold.ttf", blur=3)
    im, w = chip(im, 68, 590, "Ready to upload", 21)
    im, _ = chip(im, 68 + w + 12, 590, "Mobile-safe banner", 21)
    label(im, 68, 730)
    return finish(im, 0.5)


def kit_contents() -> Image.Image:
    ensure_kits()
    kit = KITS / "night-ledger"
    im = backdrop(top=(18, 14, 34), glow=(90, 60, 200), gx=0.5, gy=0.5)
    im = rays(im, 0.5, -0.1, (190, 150, 255), 0.12, 14, 1.7, 5)
    im = bokeh(im, 22, seed=5)
    c = (640, 395)
    nodes = [("banner-youtube.png", "YouTube banner", "2560 x 1440, mobile-safe", (250, 255), (340, 191), 0.4),
             ("og-image.png", "Share image", "1200 x 630", (1030, 255), (310, 163), -0.4),
             ("watermark.png", "Video watermark", "150 px", (230, 545), (150, 150), 0.3),
             ("favicon-512.png", "Favicons", "32 / 180 / 512 px", (1050, 545), (150, 150), -0.3),
             ("palette.png", "Colour sheet", "exact hex values", (640, 612), (330, 82), 0.0)]
    d = ImageDraw.Draw(im)
    for _, _, _, (x, y), _, _ in nodes:
        d.line([c, (x, y)], fill=(255, 210, 63), width=2)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(255, 210, 63))
    for fn, t, s, (x, y), sz, yaw in nodes:
        art = Image.open(kit / fn)
        if fn.startswith(("watermark", "favicon")):
            art = square_tile(art, 240)
        im = glass_card(im, art, (x, y), sz, yaw=yaw, glow=GOLD if fn == "palette.png" else VIOLET)
    im = paste_disc(im, Image.open(kit / "avatar.png"), c[0], c[1], 220, VIOLET)
    ImageDraw.Draw(im).ellipse([c[0] - 124, c[1] - 124, c[0] + 124, c[1] + 124], outline=GOLD, width=3)
    t = "EVERYTHING YOUR CHANNEL NEEDS"
    im = text_glow(im, (640, 68), t, fit_size(t, 1120, 66), CREAM, glow=(120, 80, 255), anchor="mm", blur=16)
    for fn, tt, s, (x, y), sz, yaw in nodes:
        ty = y + sz[1] // 2 + 24
        if fn == "palette.png":
            ty = y + sz[1] // 2 + 22
        im = text_glow(im, (x, ty), tt, 24, GOLD, font="Montserrat-ExtraBold.ttf", anchor="mm", blur=6)
        ImageDraw.Draw(im).text((x, ty + 27), s, font=_font("Montserrat-ExtraBold.ttf", 17), fill=(165, 160, 176), anchor="mm")
    im = text_glow(im, (640, 748), "+ vector logo (SVG)    +    one-page brand sheet", 20, CREAM, font="Montserrat-ExtraBold.ttf", anchor="mm", blur=5)
    return finish(im, 0.45)


def kit_proof() -> Image.Image:
    ensure_kits()
    im = backdrop(top=(16, 12, 30), glow=(70, 60, 190), gx=0.5, gy=0.55)
    im = rays(im, 0.5, 1.1, (120, 170, 255), 0.1, 14, 1.4, 9)
    im = bokeh(im, 20, seed=3)
    glows = {"calm-orbit": (60, 230, 160), "iron-fork": (255, 110, 90), "pixel-harbor": (90, 170, 255), "night-ledger": VIOLET}
    layout = [("calm-orbit", 180, 380, 0.5, (310, 174)), ("night-ledger", 1100, 380, -0.5, (310, 174)),
              ("iron-fork", 470, 350, 0.28, (340, 191)), ("pixel-harbor", 810, 350, -0.28, (340, 191))]
    for n, x, y, yaw, sz in layout:
        im = glass_card(im, Image.open(KITS / n / "banner-youtube.png"), (x, y), sz, yaw=yaw, glow=glows[n])
    for n, x, y, yaw, sz in layout:
        im = paste_disc(im, Image.open(KITS / n / "avatar.png"), x, y + 175, 100 if abs(yaw) < 0.4 else 90, glows[n])
    im = text_glow(im, (640, 64), "ONE LOOK. EVERY PLATFORM.", 76, CREAM, glow=(110, 90, 255), anchor="mm", blur=16)
    im = text_glow(im, (640, 122), "Four sample channels. Every kit is built the same way.", 24, (170, 166, 184), font="Montserrat-ExtraBold.ttf", anchor="mm", blur=4)
    label(im, 440, 738)
    return finish(im, 0.45)


# ------------------------------------------------------------------ studio (concept directions) gig

def concepts() -> list[Image.Image]:
    src = SVC / "studio" / "gallery-src"
    return [Image.open(src / f"concept{n:02d}.jpg").convert("RGB") for n in range(1, 13)]


def studio_hero() -> Image.Image:
    cons = concepts()
    im = backdrop(top=(10, 22, 40), mid=(6, 10, 22), glow=(255, 150, 60), gx=0.72, gy=0.5)
    im = rays(im, 0.78, -0.1, (255, 190, 110), 0.2, 16, 1.5, 4)
    im = bokeh(im, 28, palette=((255, 150, 60), (60, 200, 220), (240, 80, 160)), seed=21, zone=(0.4, 0, 1, 1))
    for art, ctr, sz, yaw in [(cons[5], (705, 205), 220, 0.5), (cons[1], (1175, 215), 220, -0.5), (cons[8], (845, 520), 240, 0.3), (cons[6], (1085, 535), 240, -0.3),
                              (cons[3], (960, 350), 320, 0.0)]:
        im = glass_card(im, art, ctr, (sz, sz), yaw=yaw, glow=(255, 160, 80), radius=24)
    head = "6 TO 12 LOGO\nAND MASCOT\nCONCEPTS."
    im = text_glow(im, (66, 96), head, fit_size(head, 470, 104), CREAM, glow=(255, 130, 60), spacing=0, blur=18)
    ImageDraw.Draw(im).rectangle([68, 440, 190, 446], fill=(255, 160, 80))
    im = text_glow(im, (68, 470), "See your options. Pick your favourite.", 27, CREAM, font="Montserrat-ExtraBold.ttf", blur=6)
    im = text_glow(im, (68, 514), "Your pick is refined by hand.", 22, (180, 176, 190), font="Montserrat-ExtraBold.ttf", blur=3)
    im, _ = chip(im, 68, 590, "First concepts in 24 hours", 21)
    label(im, 68, 730, "SAMPLE CONCEPTS: FICTIONAL BRANDS")
    return finish(im, 0.5)


def studio_process() -> Image.Image:
    cons = concepts()
    im = backdrop(top=(10, 18, 36), mid=(6, 8, 18), glow=(60, 160, 200), gx=0.5, gy=0.4)
    im = rays(im, 0.5, -0.12, (140, 220, 255), 0.11, 14, 1.7, 8)
    im = bokeh(im, 20, palette=((60, 200, 220), (255, 150, 60), (240, 80, 160)), seed=2)
    ImageDraw.Draw(im).line([(215, 285), (1065, 285)], fill=(255, 190, 110), width=3)
    steps = [("1", "SEND A BRIEF", "What it is for, who it is for, the feeling you want.", cons[6], -0.32),
             ("2", "GET YOUR OPTIONS", "6 to 12 different angles, each with a name, an idea and a palette.", cons[2], 0.0),
             ("3", "PICK ONE", "I refine your favourite by hand. Revisions in higher tiers.", cons[10], 0.32)]
    for i, (n, t, s, art, yaw) in enumerate(steps):
        im = glass_card(im, art, (215 + i * 425, 285), (260, 260), yaw=yaw, glow=(255, 160, 80), radius=26)
    d = ImageDraw.Draw(im)
    for i, (n, t, s_, art, yaw) in enumerate(steps):
        cx = 215 + i * 425
        d.ellipse([cx - 34, 56, cx + 34, 124], fill=(255, 190, 90))
        d.text((cx, 92), n, font=_font("Anton-Regular.ttf", 54), fill=(14, 14, 16), anchor="mm")
    f = _font("Montserrat-ExtraBold.ttf", 21)
    for i, (n, t, s_, art, yaw) in enumerate(steps):
        cx = 215 + i * 425
        im = text_glow(im, (cx, 455), t, fit_size(t, 340, 40), CREAM, glow=(255, 150, 60), anchor="mm", blur=10)
        words, line, lines = s_.split(), "", []
        for w in words:
            if ImageDraw.Draw(im).textlength((line + " " + w).strip(), font=f) > 330:
                lines.append(line); line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        ImageDraw.Draw(im).multiline_text((cx, 500), "\n".join(lines), font=f, fill=(190, 186, 200), anchor="ma", align="center", spacing=8)
    im = text_glow(im, (640, 712), "No copying of living artists or existing brands.", 21, (150, 146, 160), font="Montserrat-ExtraBold.ttf", anchor="mm", blur=4)
    return finish(im, 0.45)


def studio_proof() -> Image.Image:
    cons = concepts()
    im = backdrop(top=(10, 16, 34), mid=(6, 8, 18), glow=(230, 120, 70), gx=0.5, gy=0.6)
    im = rays(im, 0.5, 1.15, (255, 180, 110), 0.1, 16, 1.5, 6)
    im = bokeh(im, 20, palette=((255, 150, 60), (60, 200, 220), (240, 80, 160)), seed=13)
    names = ["A  Fox Astronaut", "B  Little Robot", "C  Moon Cadet", "D  Owl Pilot", "E  Rocket Badge", "F  Comet Grin"]
    cw = 235
    pos = [(235 + (i % 3) * 300, 215 + (i // 3) * 290) for i in range(6)]
    for i in range(6):
        im = glass_card(im, cons[i], pos[i], (cw, cw), yaw=((i % 3) - 1) * 0.2, glow=(255, 160, 80), radius=22)
    d = ImageDraw.Draw(im)
    for i in range(6):
        d.text((pos[i][0], pos[i][1] + cw // 2 + 26), names[i], font=_font("Montserrat-ExtraBold.ttf", 22), fill=CREAM, anchor="mm")
    im = text_glow(im, (1115, 190), "ONE BRIEF.\nSIX\nDIRECTIONS.", fit_size("ONE BRIEF.\nSIX\nDIRECTIONS.", 300, 76), CREAM, glow=(255, 130, 60), anchor="mm", spacing=0, blur=14)
    im = text_glow(im, (1115, 410), "Sample sheet for a\nfictional kids' space\nlearning channel.", 20, (180, 176, 190), font="Montserrat-ExtraBold.ttf", anchor="mm", spacing=6, blur=3)
    label(im, 68, 738, "SAMPLE PROJECT: FICTIONAL BRAND")
    return finish(im, 0.45)


def build() -> list[Path]:
    ensure_kits()
    out = []
    for gig, makers in (("brand-kit", [kit_hero, kit_contents, kit_proof]), ("studio", [studio_hero, studio_process, studio_proof])):
        folder = SVC / gig / "gallery"
        folder.mkdir(parents=True, exist_ok=True)
        for n, fn in enumerate(makers, 1):
            p = folder / f"{n}-{fn.__name__.split('_', 1)[1]}.jpg"
            fn().convert("RGB").save(p, quality=93, optimize=True)
            out.append(p)
    return out


if __name__ == "__main__":
    for p in build():
        print(p)
