"""Front covers for the Quiet Money products: the silent salesperson, drawn in code, checked the way a buyer's eye will meet it.

The design follows the corrected edition of the owner's cover research (skill `faceless-cover-science`): look like the category first and be
distinctive inside it; ONE focal symbol, ONE primary colour and ONE accent; the title is the picture (it takes most of the cover); built for
the 100-200 px phone thumbnail first; a moderate curiosity gap rather than a full explanation. Every cover is 1600x2560 (the 1.6:1 ebook
ratio), RGB JPEG, with a thin grey border when the ground is light so it does not vanish on a white page. Type is set in code with the brand
fonts (never AI-made letters). No price, discount or promise is ever drawn on a cover, so one file serves Gumroad, Etsy and the site.

Each product gets its own colour and symbol, in one family (brand strip on top, tagline and tier pips at the foot):
  money-reset-printables  Starter   emerald, a reset ring around the brand coin
  money-reset-kit         Complete  navy and gold, three rising steps and the coin on top (the tier ladder as a picture)
  debt-payoff-planner     free gift black and crimson, a chain link breaking
  rat-race-escape-planner           brand yellow and black, a doorway of light and a small silhouette walking to it
The Daily Planner keeps its own Quinton cover (`planner_cover.py`, the Core tier).

`python -m faceless frontcover build|check|sheet`. Output goes to `channel/shop/<id>/front/` (cover.jpg, thumb.jpg, wide.jpg) and
`channel/shop/front-covers-sheet.png` (the whole series at full size, 400 px and 120 px: the squint and grid tests).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from faceless import brand, mockup
from faceless.config import Paths

W, H = 1600, 2560
OUT = Paths.root / "channel" / "shop"
ANTON, BLACK, XBOLD, BODY = "Anton-Regular.ttf", "Montserrat-Black.ttf", "Montserrat-ExtraBold.ttf", "Carlito-Regular.ttf"
CREAM, GOLD, INK = (245, 241, 230), (255, 210, 63), (14, 14, 16)
CRIMSON = (246, 54, 70)
SPECS: dict[str, dict] = {
    "money-reset-printables": {
        "tier": 1, "label": "STARTER", "symbol": "reset", "ink": CREAM,
        "ground": ((4, 70, 52), (2, 26, 20)), "glow": (24, 190, 130),
        "title": [("MONEY RESET", ANTON, 250, CREAM), ("PRINTABLES", ANTON, 420, GOLD)],
        "tag": "Six pages. One honest look at your money."},
    "money-reset-kit": {
        "tier": 3, "label": "COMPLETE", "symbol": "steps", "ink": CREAM,
        "ground": ((10, 20, 58), (3, 6, 24)), "glow": (46, 84, 214),
        "title": [("MONEY RESET", ANTON, 250, CREAM), ("KIT", ANTON, 800, GOLD)],
        "tag": "Two planners. Six pages. One weekend."},
    "debt-payoff-planner": {
        "tier": 0, "label": "FREE GIFT", "symbol": "chain", "ink": CREAM,
        "ground": ((22, 12, 14), (3, 2, 3)), "glow": (170, 22, 44),
        "title": [("DEBT", ANTON, 700, CRIMSON), ("PAYOFF PLANNER", ANTON, 250, CREAM)],
        "tag": "Your payoff date and the interest it costs, from your own numbers."},
    "rat-race-escape-planner": {
        "tier": 0, "label": "", "symbol": "door", "ink": INK,
        "ground": ((255, 218, 70), (236, 172, 22)), "glow": (255, 247, 205),
        "title": [("RAT RACE", ANTON, 300, INK), ("ESCAPE", ANTON, 560, INK), ("PLANNER", ANTON, 190, INK)],
        "tag": "Your freedom number and the year it arrives."},
}
SERIES_LINE = "THE MONEY RULES NOBODY TAUGHT YOU."


# ---------------------------------------------------------------- drawing helpers

def _gradient(size: tuple[int, int], top, bottom) -> Image.Image:
    mask = Image.linear_gradient("L").resize(size)
    return Image.composite(Image.new("RGB", size, bottom), Image.new("RGB", size, top), mask)


def _glow(base: Image.Image, center: tuple[int, int], radius: int, color, strength: float = 0.55) -> None:
    m = Image.new("L", base.size, 0)
    ImageDraw.Draw(m).ellipse([center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius], fill=int(255 * strength))
    m = m.filter(ImageFilter.GaussianBlur(radius // 2))
    base.paste(Image.new("RGB", base.size, color), (0, 0), m)


def _fit(d: ImageDraw.ImageDraw, text: str, name: str, max_w: int, size: int, floor: int = 60):
    while size > floor and d.textlength(text, font=brand.font(name, size)) > max_w:
        size -= 4
    return brand.font(name, size)


def _tracked(d, cx: int, y: int, text: str, font, fill, spacing: int) -> None:
    total = sum(d.textlength(c, font=font) for c in text) + spacing * (len(text) - 1)
    x = cx - total / 2
    for c in text:
        d.text((x, y), c, font=font, fill=fill, anchor="ls")
        x += d.textlength(c, font=font) + spacing


def _title(img: Image.Image, spec: dict, top: int) -> int:
    """The title block, centred; returns the y where it ends. Each line is as big as the width allows (up to its size), which is what makes
    the title the picture: it carries the cover at 120 px."""
    d = ImageDraw.Draw(img)
    y = top
    for text, name, size, color in spec["title"]:
        f = _fit(d, text, name, W - 190, size)
        l, t, r, b = d.textbbox((0, 0), text, font=f, anchor="ls")
        base = y - t
        d.text((W // 2 + 8, base + 8), text, font=f, fill=tuple(int(c * 0.28) for c in spec["ground"][1]) if spec["ink"] != INK else (0, 0, 0, 0), anchor="ms")
        d.text((W // 2, base), text, font=f, fill=color, anchor="ms")
        y = base + int(f.size * 0.07) + 26
    return y


def _frame(img: Image.Image, spec: dict) -> None:
    d = ImageDraw.Draw(img)
    c = brand.coin(84).convert("RGBA")
    ink = spec["ink"]
    f = brand.font(XBOLD, 40)
    label = "QUIET MONEY"
    tw = sum(d.textlength(ch, font=f) for ch in label) + 12 * (len(label) - 1)
    x0 = (W - (84 + 30 + tw)) / 2
    img.paste(c, (int(x0), 92), c)
    _tracked(d, int(x0 + 84 + 30 + tw / 2), 148, label, f, ink, 12)


def _foot(img: Image.Image, spec: dict) -> None:
    d = ImageDraw.Draw(img)
    ink, acc = spec["ink"], (INK if spec["ink"] == INK else GOLD)
    tag = spec["tag"]
    f = _fit(d, tag, XBOLD, W - 260, 56, 38)
    d.text((W // 2, 2300), tag, font=f, fill=ink, anchor="ms")
    y = 2392
    if spec["tier"]:
        r, gap = 22, 78
        x0 = W // 2 - gap - 190
        d.text((W // 2 - 120, y + 16), f"TIER {spec['tier']}", font=brand.font(XBOLD, 40), fill=ink, anchor="rs")
        for i in range(3):
            cx = W // 2 - 80 + i * 70
            if i < spec["tier"]:
                d.ellipse([cx - r, y - r + 2, cx + r, y + r + 2], fill=acc)
            else:
                d.ellipse([cx - r, y - r + 2, cx + r, y + r + 2], outline=acc, width=5)
        d.text((W // 2 + 150, y + 16), spec["label"], font=brand.font(XBOLD, 40), fill=ink, anchor="ls")
    elif spec["label"]:
        pill = brand.font(BLACK, 44)
        tw = d.textlength(spec["label"], font=pill) + 90
        d.rounded_rectangle([W // 2 - tw / 2, y - 44, W // 2 + tw / 2, y + 44], radius=44, outline=GOLD, width=6)
        d.text((W // 2, y + 16), spec["label"], font=pill, fill=GOLD, anchor="ms")
    d.text((W // 2, 2490), SERIES_LINE, font=brand.font(XBOLD, 30), fill=ink, anchor="ms") if False else _tracked(d, W // 2, 2490, SERIES_LINE, brand.font(XBOLD, 30), ink, 5)


# ---------------------------------------------------------------- the four symbols (each drawn at 2x, one focal object)

def _arc_arrow(layer: Image.Image, center, radius: int, width: int, color, start: float, end: float) -> None:
    d = ImageDraw.Draw(layer)
    box = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
    d.arc(box, start, end, fill=color, width=width)
    for ang in (start, end):                                                  # round both ends
        x, y = center[0] + radius * math.cos(math.radians(ang)), center[1] + radius * math.sin(math.radians(ang))
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=color)
    t = math.radians(end)
    px, py = center[0] + radius * math.cos(t), center[1] + radius * math.sin(t)
    tx, ty = -math.sin(t), math.cos(t)                                         # clockwise tangent in screen coordinates
    nx, ny = math.cos(t), math.sin(t)
    L, Wd = width * 1.9, width * 1.55
    d.polygon([(px + tx * L, py + ty * L), (px + nx * Wd, py + ny * Wd), (px - nx * Wd, py - ny * Wd)], fill=color)


def _sym_reset(size: int) -> Image.Image:
    s = size * 2
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c = s // 2
    coin = brand.coin(int(s * 0.52)).convert("RGBA")
    layer.paste(coin, (c - coin.width // 2, c - coin.height // 2), coin)
    _arc_arrow(layer, (c, c), int(s * 0.40), int(s * 0.082), CREAM, 52, 346)
    return layer.resize((size, size), Image.LANCZOS)


def _sym_steps(size: int) -> Image.Image:
    s = size * 2
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bw, gap, base = int(s * 0.27), int(s * 0.03), int(s * 0.96)
    heights = [int(s * 0.28), int(s * 0.46), int(s * 0.64)]
    x = (s - (3 * bw + 2 * gap)) // 2
    top_coin = None
    for i, h in enumerate(heights):
        step = Image.new("RGBA", (bw, h), (0, 0, 0, 0))
        grad = _gradient((bw, h), (255, 224, 110), (190, 146, 30)).convert("RGBA")
        mask = Image.new("L", (bw, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, h + 40], radius=int(bw * 0.12), fill=255)
        step.paste(grad, (0, 0), mask)
        layer.paste(step, (x, base - h), step)
        d.text((x + bw // 2, base - h + int(bw * 0.58)), str(i + 1), font=brand.font(ANTON, int(bw * 0.62)), fill=(14, 22, 58), anchor="mm")
        if i == 2:
            top_coin = (x + bw // 2, base - h)
        x += bw + gap
    coin = brand.coin(int(s * 0.25)).convert("RGBA")
    layer.paste(coin, (top_coin[0] - coin.width // 2, top_coin[1] - coin.height - 6), coin)
    return layer.resize((size, size), Image.LANCZOS)


def _ring(w: int, h: int, stroke: int, color) -> Image.Image:
    r = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(r)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=color)
    d.rounded_rectangle([stroke, stroke, w - 1 - stroke, h - 1 - stroke], radius=max(2, h // 2 - stroke), fill=(0, 0, 0, 0))
    return r


def _sym_chain(size: int) -> Image.Image:
    """Two interlocked links; the right one has snapped. A cream link, intact, and a crimson link with a missing segment: the end cap has broken
    off and is flying away. The links pass over and under each other at their two crossings, so it reads as a chain, not two shapes."""
    s = size * 2
    ang = 24
    lw, lh, st = int(s * 0.46), int(s * 0.27), int(s * 0.07)
    D = int(s * 0.35)
    ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))                  # the chain runs down and to the right
    mid = (s * 0.42, s * 0.55)
    ca = (mid[0] - ux * D / 2, mid[1] - uy * D / 2)
    cb = (mid[0] + ux * D / 2, mid[1] + uy * D / 2)

    def put(ring: Image.Image, center) -> Image.Image:
        rot = ring.rotate(-ang, expand=True, resample=Image.BICUBIC)
        out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        out.paste(rot, (int(center[0] - rot.width / 2), int(center[1] - rot.height / 2)), rot)
        return out

    A = put(_ring(lw, lh, st, CREAM), ca)
    full_b = _ring(lw, lh, st, CRIMSON)
    main_b, cap_b = full_b.copy(), full_b.copy()
    cut_l, cut_r = int(lw * 0.70), int(lw * 0.77)                                        # the break: a slab removed near the right end
    ImageDraw.Draw(main_b).rectangle([cut_l, 0, lw, lh], fill=(0, 0, 0, 0))
    ImageDraw.Draw(cap_b).rectangle([0, 0, cut_r, lh], fill=(0, 0, 0, 0))
    B = put(main_b, cb)
    # over/under: at the two crossings, the cream link wins on one side of the chain's axis and the crimson on the other
    a_alpha, b_alpha = np.asarray(A.split()[3]) > 0, np.asarray(B.split()[3]) > 0
    yy, xx = np.mgrid[0:s, 0:s]
    side = (xx - mid[0]) * (-uy) + (yy - mid[1]) * ux
    b_wins = a_alpha & b_alpha & (side > 0)
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    layer.alpha_composite(B)
    layer.alpha_composite(A)
    layer.alpha_composite(Image.composite(B, Image.new("RGBA", (s, s), (0, 0, 0, 0)), Image.fromarray((b_wins * 255).astype("uint8"))))
    cap = cap_b.crop(cap_b.getbbox()).rotate(-ang + 34, expand=True, resample=Image.BICUBIC)   # the broken-off end, alone, tilted, flung out and up
    cx, cy = cb[0] + ux * (lw * 0.50 + s * 0.105), cb[1] + uy * (lw * 0.50 + s * 0.105) - s * 0.13
    layer.alpha_composite(cap, (int(cx - cap.width / 2), int(cy - cap.height / 2)))
    return layer.resize((size, size), Image.LANCZOS)


def _sym_door(size: int) -> Image.Image:
    s = size * 2
    layer = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    dw, dh = int(s * 0.46), int(s * 0.80)
    x0, y0 = (s - dw) // 2, int(s * 0.02)
    frame = int(s * 0.045)
    arch = dw // 2
    d.rounded_rectangle([x0, y0, x0 + dw, y0 + dh], radius=arch, fill=INK)                     # the doorway: black arch
    d.rectangle([x0, y0 + dh - arch, x0 + dw, y0 + dh], fill=INK)
    inner = [x0 + frame, y0 + frame, x0 + dw - frame, y0 + dh - 2]
    light = _gradient((inner[2] - inner[0], inner[3] - inner[1]), (255, 255, 250), (255, 232, 140)).convert("RGBA")
    m = Image.new("L", light.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, light.width - 1, light.height + arch], radius=arch - frame, fill=255)
    layer.paste(light, (inner[0], inner[1]), m)
    beam = Image.new("RGBA", layer.size, (0, 0, 0, 0))                                           # light spilling onto the floor
    ImageDraw.Draw(beam).polygon([(inner[0], y0 + dh - 2), (inner[2], y0 + dh - 2), (x0 + dw + int(s * 0.20), s - 30), (x0 - int(s * 0.20), s - 30)], fill=(255, 250, 225, 235))
    layer.alpha_composite(beam)
    fx, fb = s // 2 + int(s * 0.03), s - int(s * 0.07)                                          # a small silhouette walking toward it (seen from behind)
    fh = int(s * 0.17)
    d = ImageDraw.Draw(layer)
    d.ellipse([fx - fh * 0.13, fb - fh, fx + fh * 0.13, fb - fh * 0.74], fill=INK)
    d.polygon([(fx - fh * 0.19, fb - fh * 0.70), (fx + fh * 0.19, fb - fh * 0.70), (fx + fh * 0.15, fb - fh * 0.30), (fx - fh * 0.15, fb - fh * 0.30)], fill=INK)
    d.polygon([(fx - fh * 0.15, fb - fh * 0.32), (fx - fh * 0.02, fb - fh * 0.32), (fx - fh * 0.08, fb), (fx - fh * 0.20, fb)], fill=INK)
    d.polygon([(fx + fh * 0.02, fb - fh * 0.32), (fx + fh * 0.15, fb - fh * 0.32), (fx + fh * 0.22, fb - fh * 0.04), (fx + fh * 0.10, fb - fh * 0.02)], fill=INK)
    return layer.resize((size, size), Image.LANCZOS)


SYMBOLS = {"reset": _sym_reset, "steps": _sym_steps, "chain": _sym_chain, "door": _sym_door}
SYMBOL_BOX = {"reset": (1180, 1180), "steps": (1200, 1200), "chain": (1260, 1260), "door": (1160, 1160)}


# ---------------------------------------------------------------- the covers

def render(pid: str) -> Image.Image:
    spec = SPECS[pid]
    img = _gradient((W, H), *spec["ground"])
    probe = Image.new("RGB", (W, H))
    end = _title(probe, spec, 250)                                           # measure the title first, so the symbol takes exactly the room left
    bottom = 2215
    size = int(min(SYMBOL_BOX[spec["symbol"]][0], bottom - (end + 20)))
    top = end + 20 + max(0, (bottom - (end + 20) - size) // 2)
    _glow(img, (W // 2, top + size // 2), 760, spec["glow"], 0.5 if spec["ink"] != INK else 0.7)
    _frame(img, spec)
    _title(img, spec, 250)
    sym = SYMBOLS[spec["symbol"]](size)
    img.paste(sym, ((W - sym.width) // 2, top), sym)
    _foot(img, spec)
    light = np.asarray(img.convert("L"), dtype=np.float32)[:, :30].mean() > 190
    if light:                                                                # a thin grey border keeps a light cover from vanishing on a white page
        ImageDraw.Draw(img).rectangle([0, 0, W - 1, H - 1], outline=(120, 120, 120), width=4)
    return img


def thumb(cover: Image.Image, size: int = 1200) -> Image.Image:
    """Gumroad's square card: the cover as a book on its own ground."""
    g = _gradient((size, size), tuple(int(c * 0.9) for c in cover.getpixel((40, 40))), tuple(int(c * 0.5) for c in cover.getpixel((40, size))))
    h = int(size * 0.88)
    c = cover.resize((int(h * cover.width / cover.height), h), Image.LANCZOS)
    box = ((size - c.width) // 2, (size - h) // 2, (size + c.width) // 2, (size + h) // 2)
    mockup.drop_shadow(g, box, blur=40, offset=22, alpha=150, radius=6)
    g.paste(c, box[:2])
    return g


def scene(cover: Image.Image, shot: Image.Image | None, chips: list[str], size: tuple[int, int], *, spreadsheet: bool, tabs: tuple = (), file_name: str = "") -> Image.Image:
    """The cover as a product shot: the book on the left, a real page or sheet on the right and chips under it, on the cover's own colour.
    Used for the Gumroad 16:9 cover and the Etsy first image (which must be landscape and not dark, so it carries a white page)."""
    w, h = size
    a, b = cover.getpixel((40, 40)), cover.getpixel((40, 2400))
    if _lum(a) < 0.06:      # a dark cover on a dark table disappears (and Etsy ranks dark main images lower): put it on warm paper
        g = _gradient(size, (238, 232, 220), (205, 196, 180))
    else:
        g = _gradient(size, tuple(int(c * 0.85) for c in a), tuple(int(c * 0.55) for c in b))
    ch = int(h * 0.86)
    c = cover.resize((int(ch * cover.width / cover.height), ch), Image.LANCZOS)
    cx0 = int(w * 0.09)
    top = (h - ch) // 2
    mockup.drop_shadow(g, (cx0, top, cx0 + c.width, top + ch), blur=50, offset=30, alpha=170, radius=6)
    g.paste(c, (cx0, top))
    if shot is not None:
        avail_w, avail_h = int(w * 0.52), int(h * 0.62)
        dev = mockup.fit_window(shot, avail_w, avail_h, title=file_name, tabs=tabs, active=1 if tabs else 0) if spreadsheet else mockup.paper(shot, int(avail_h * shot.width / shot.height * 0.98))
        rcx = cx0 + c.width + (w - cx0 - c.width) // 2
        mockup.place(g, dev, rcx, int(h * 0.14))
    if chips:
        fs, gap = int(h * 0.026), int(w * 0.012)
        x, y = cx0 + c.width + int(w * 0.04), int(h * 0.88)
        d = ImageDraw.Draw(g)
        f = mockup.font(mockup.XBOLD, fs)
        for t in chips[:3]:
            width = int(d.textlength(t, font=f)) + 2 * int(fs * 0.8)
            ink = (14, 14, 16) if _lum(a) < 0.06 else mockup.CREAM
            mockup.chip(g, x + width // 2, y, t, size=fs, color=ink, fill=(255, 255, 255) if _lum(a) < 0.06 else None)
            x += width + gap
    return g


# ---------------------------------------------------------------- the checks a buyer's eye would apply

def _lum(c) -> float:
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def gates(pid: str, cover: Image.Image) -> list[tuple[str, bool, str]]:
    """The research's tests as numbers. Hard gates must pass before a cover is used."""
    spec = SPECS[pid]
    out = []
    out.append(("size", cover.size == (W, H), f"{cover.size[0]}x{cover.size[1]} (ebook ratio 1.6:1, 1600x2560)"))
    title_colors = {c for _, _, _, c in spec["title"]}
    worst = min(contrast(c, spec["ground"][0]) for c in title_colors)
    out.append(("title_contrast", worst >= 4.5, f"lowest title-to-ground contrast {worst:.1f}:1 (4.5 or more)"))
    # the squint test: at 120 px wide the title band must still stand out from the ground
    small = np.asarray(cover.convert("L").resize((120, 192), Image.LANCZOS), dtype=np.float32)
    band = small[int(192 * 0.10):int(192 * 0.47)]
    out.append(("thumbnail_title_visible", float(band.std()) >= 32, f"luminance spread of the title band at 120 px: {band.std():.0f} (32 or more)"))
    # palette discipline (rule of one): the coloured pixels fall in at most two hue families, one ground and one accent
    hsv = np.asarray(cover.convert("RGB").resize((200, 320)).convert("HSV"), dtype=np.float32)
    chroma = (hsv[..., 1] > 64) & (hsv[..., 2] > 64)
    hist = np.bincount((hsv[..., 0][chroma] * 36 / 256).astype(int) % 36, minlength=36).astype(float)
    total = hist.sum() or 1.0
    kept = 0.0
    for _ in range(2):
        win = [sum(hist[(i + k) % 36] for k in range(-2, 3)) for i in range(36)]
        best = int(np.argmax(win))
        kept += win[best]
        for k in range(-2, 3):
            hist[(best + k) % 36] = 0
    out.append(("palette_discipline", kept / total >= 0.93, f"{kept / total:.0%} of the coloured pixels sit in two hue families (93% or more: one ground, one accent)"))
    # one focal point: the symbol's region carries the detail, not the whole cover
    a = np.asarray(cover.convert("L").resize((200, 320)), dtype=np.float32)
    gy, gx = np.gradient(a)
    energy = np.hypot(gx, gy)
    focal = float(energy[int(320 * 0.40):int(320 * 0.90)].sum() / (energy.sum() + 1e-6))
    out.append(("one_focal_zone", 0.30 <= focal <= 0.75, f"{focal:.0%} of the edge detail sits in the symbol zone (30-75%)"))
    return out


def series_gates(covers: dict[str, Image.Image]) -> list[tuple[str, bool, str]]:
    """The grid test: side by side at 120 px the covers must be told apart at a glance (hue, or how light the ground is) yet read as one family."""
    def ground(im: Image.Image):
        px = np.asarray(im.resize((60, 96)).convert("HSV"), dtype=np.float32)[:6, :, :].reshape(-1, 3).mean(0)
        return px[0] * 360 / 256, px[1] / 255, px[2] / 255
    g = {k: ground(v) for k, v in covers.items()}
    ids, worst, low = list(g), 1e9, []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            dh = min(abs(g[a][0] - g[b][0]), 360 - abs(g[a][0] - g[b][0]))
            chroma = min(g[a][1], g[b][1])
            d = max(dh if chroma > 0.3 else 0, abs(g[a][2] - g[b][2]) * 140)
            worst = min(worst, d)
            if d < 40:
                low.append(f"{a}/{b} {d:.0f}")
    return [("distinguishable_in_a_grid", not low, f"closest pair {worst:.0f} degrees of hue (or lightness equivalent), 40 or more needed; too alike: {low or 'none'}")]


def build(only: str | None = None) -> dict[str, dict]:
    ids = [only] if only and only != "all" else list(SPECS)
    out, made = {}, {}
    for pid in ids:
        cover = render(pid)
        folder = OUT / pid / "front"
        folder.mkdir(parents=True, exist_ok=True)
        cover.save(folder / "cover.jpg", "JPEG", quality=92, optimize=True, progressive=True)
        thumb(cover).save(folder / "thumb.jpg", "JPEG", quality=90, optimize=True)
        made[pid] = cover
        out[pid] = {"gates": gates(pid, cover), "folder": str(folder)}
    if len(ids) > 1:
        sg = series_gates(made)
        for pid in ids:
            out[pid]["gates"] += sg
        sheet(made)
    return out


def sheet(covers: dict[str, Image.Image] | None = None) -> Path:
    """The whole series at three sizes: full, 400 px (a phone feed) and 120 px (a search grid), so the squint test is one look."""
    covers = covers or {pid: render(pid) for pid in SPECS}
    n = len(covers)
    pad = 40
    big_h, mid_h, small_h = 760, 400, 192
    width = pad + n * (int(big_h / 1.6) + pad)
    height = pad + big_h + pad + mid_h + pad + small_h + pad
    sh = Image.new("RGB", (width, height), (236, 234, 228))
    x = pad
    for cover in covers.values():
        bw = int(big_h / 1.6)
        sh.paste(cover.resize((bw, big_h), Image.LANCZOS), (x, pad))
        sh.paste(cover.resize((int(mid_h / 1.6), mid_h), Image.LANCZOS), (x, pad + big_h + pad))
        sh.paste(cover.resize((int(small_h / 1.6), small_h), Image.LANCZOS), (x + int(mid_h / 1.6) + 30, pad + big_h + pad))
        x += bw + pad
    path = OUT / "front-covers-sheet.png"
    sh.save(path)
    return path
