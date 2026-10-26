"""Fiverr gig gallery images (skill faceless-gig-gallery): 1280x769 hero, what-you-get and proof images for the brand-kit and studio gigs.

Pictures come from real engine output (brand kits) and Flow concept art kept in channel/services/studio/gallery-src/ (no lettering in the art);
every word on an image is drawn here so the type is crisp. Samples are fictional brands and are labelled as such.

    python -m faceless gigart          # rebuilds channel/services/brand-kit/gallery/ and channel/services/studio/gallery/
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from faceless import brand
from faceless.config import Paths

W, H = 1280, 769
INK, GOLD, CREAM, MUTED = brand.INK, brand.GOLD, brand.CREAM, brand.MUTED
SVC = Paths.root / "channel" / "services"
KITS = Path("/tmp/kits")        # sample kits are rebuilt by `faceless brandkit --out` before this runs


def _canvas(bg=INK) -> Image.Image:
    im = Image.new("RGB", (W, H), bg)
    return im


def _glow(im: Image.Image, cx: int, cy: int, r: int, color, alpha: int = 90) -> None:
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(r // 2))
    im.paste(layer, (0, 0), layer)


def _round(img: Image.Image, radius: int) -> Image.Image:
    img = img.convert("RGBA")
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius, fill=255)
    img.putalpha(m)
    return img


def _card(im: Image.Image, art: Image.Image, box: tuple[int, int, int, int], radius: int = 22, shadow: int = 26) -> None:
    x0, y0, x1, y1 = box
    art = _round(art.resize((x1 - x0, y1 - y0), Image.LANCZOS), radius)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 4, y0 + 14, x1 + 4, y1 + 14], radius, fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(shadow))
    im.paste(sh, (0, 0), sh)
    im.paste(art, (x0, y0), art)


def _text(d: ImageDraw.ImageDraw, xy, text, size, fill=CREAM, font="Anton-Regular.ttf", anchor="la", spacing=6) -> None:
    d.multiline_text(xy, text, font=brand.font(font, size), fill=fill, anchor=anchor, spacing=spacing)


def _size_for(text: str, max_w: int, start: int, font: str = "Anton-Regular.ttf", floor: int = 30) -> int:
    """Largest font size (<= start) at which the widest line of `text` fits max_w."""
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    size = start
    while size > floor and max(probe.textlength(line, font=brand.font(font, size)) for line in text.split("\n")) > max_w:
        size -= 2
    return size


def _chip(d: ImageDraw.ImageDraw, x: int, y: int, text: str, size: int = 24, fg=INK, bg=GOLD) -> int:
    f = brand.font("Montserrat-ExtraBold.ttf", size)
    w = int(d.textlength(text, font=f))
    d.rounded_rectangle([x, y, x + w + 36, y + size + 22], 999, fill=bg)
    d.text((x + 18, y + 10), text, font=f, fill=fg)
    return w + 36


def _fit(img: Image.Image, w: int, h: int) -> Image.Image:
    """Cover-crop to w x h."""
    r = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def _sample_label(d: ImageDraw.ImageDraw, x: int, y: int, text: str = "SAMPLE PROJECT: FICTIONAL BRAND") -> None:
    _text(d, (x, y), text, 18, fill=MUTED, font="Montserrat-ExtraBold.ttf")


# ------------------------------------------------------------------ brand-kit gig

def kit_hero() -> Image.Image:
    kit = KITS / "night-ledger"
    im = _canvas()
    _glow(im, 980, 330, 330, GOLD, 70)
    d = ImageDraw.Draw(im)
    head = "YOUR CHANNEL'S\nWHOLE IDENTITY.\nONE DELIVERY."
    hs = _size_for(head, 500, 92)
    _text(d, (70, 110), head, hs, fill=CREAM, spacing=2)
    d.rectangle([70, 430, 190, 438], fill=GOLD)
    sub = "Avatar + banner + logo + brand sheet"
    _text(d, (70, 462), sub, _size_for(sub, 500, 28, "Montserrat-ExtraBold.ttf", 18), fill=CREAM, font="Montserrat-ExtraBold.ttf")
    sub2 = "for faceless YouTube and TikTok channels"
    _text(d, (70, 508), sub2, _size_for(sub2, 500, 24, "Montserrat-ExtraBold.ttf", 16), fill=MUTED, font="Montserrat-ExtraBold.ttf")
    x = 70
    for t in ("Ready to upload", "Mobile-safe banner"):
        x += _chip(d, x, 600, t, 20) + 12
    # a channel-page mockup: banner on top, avatar overlapping it
    ban = Image.open(kit / "banner-youtube.png").convert("RGB")
    _card(im, _fit(ban, 620, 349), (620, 150, 1240, 499), 20)
    av = Image.open(kit / "avatar.png").convert("RGB").resize((200, 200), Image.LANCZOS)
    m = Image.new("L", (200, 200), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 199, 199], fill=255)
    ring = Image.new("RGB", (216, 216), INK)
    rm = Image.new("L", (216, 216), 0)
    ImageDraw.Draw(rm).ellipse([0, 0, 215, 215], fill=255)
    im.paste(ring, (660, 450), rm)
    im.paste(av, (668, 458), m)
    d = ImageDraw.Draw(im)
    _text(d, (900, 545), "Night Ledger", 38, fill=CREAM, font="Montserrat-ExtraBold.ttf")
    _text(d, (900, 592), "Money stories after dark", 24, fill=MUTED, font="Montserrat-ExtraBold.ttf")
    _sample_label(d, 620, 712)
    return im


def kit_contents() -> Image.Image:
    kit = KITS / "night-ledger"
    im = _canvas((20, 20, 24))
    d = ImageDraw.Draw(im)
    _text(d, (70, 52), "WHAT'S IN YOUR KIT", 64, fill=CREAM)
    d.rectangle([70, 128, 170, 134], fill=GOLD)
    tiles = [("avatar.png", "Avatar", "800 px, circle-safe"), ("banner-youtube.png", "YouTube banner", "2560 x 1440, mobile-safe"),
             ("og-image.png", "Share image", "1200 x 630"), ("watermark.png", "Watermark", "for the video player"),
             ("favicon-512.png", "Favicons", "32 / 180 / 512 px"), ("palette.png", "Colour sheet", "exact hex values")]
    cw, ch, gx, gy = 380, 175, 35, 30
    for i, (fn, title, sub) in enumerate(tiles):
        col, row = i % 3, i // 3
        x0 = 70 + col * (cw + gx)
        y0 = 160 + row * (ch + gy + 70)
        art = Image.open(kit / fn).convert("RGB")
        bg = Image.new("RGB", (cw, ch), (12, 12, 15))
        scale = min((cw - 30) / art.width, (ch - 30) / art.height)
        art = art.resize((max(1, int(art.width * scale)), max(1, int(art.height * scale))), Image.LANCZOS)
        bg.paste(art, ((cw - art.width) // 2, (ch - art.height) // 2))
        _card(im, bg, (x0, y0, x0 + cw, y0 + ch), 18, 16)
        d = ImageDraw.Draw(im)
        _text(d, (x0 + 4, y0 + ch + 12), title, 30, fill=GOLD, font="Montserrat-ExtraBold.ttf")
        _text(d, (x0 + 4, y0 + ch + 48), sub, 21, fill=MUTED, font="Montserrat-ExtraBold.ttf")
    d = ImageDraw.Draw(im)
    _text(d, (70, 722), "+ vector logo (SVG)  +  one-page brand sheet", 22, fill=CREAM, font="Montserrat-ExtraBold.ttf")
    return im


def kit_proof() -> Image.Image:
    im = _canvas()
    d = ImageDraw.Draw(im)
    _text(d, (70, 48), "ONE LOOK. EVERY PLATFORM.", 64, fill=CREAM)
    _text(d, (70, 136), "Four sample channels, each kit built the same way", 26, fill=MUTED, font="Montserrat-ExtraBold.ttf")
    names = ["calm-orbit", "iron-fork", "pixel-harbor", "night-ledger"]
    cw, ch = 560, 230
    for i, n in enumerate(names):
        col, row = i % 2, i // 2
        x0, y0 = 70 + col * (cw + 20), 195 + row * (ch + 34)
        ban = _fit(Image.open(KITS / n / "banner-youtube.png").convert("RGB"), cw, ch)
        _card(im, ban, (x0, y0, x0 + cw, y0 + ch), 18, 14)
        av = Image.open(KITS / n / "avatar.png").convert("RGB").resize((110, 110), Image.LANCZOS)
        m = Image.new("L", (110, 110), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 109, 109], fill=255)
        im.paste(av, (x0 + 18, y0 + ch - 62), m)
    d = ImageDraw.Draw(im)
    _sample_label(d, 70, 738)
    return im


# ------------------------------------------------------------------ studio (concept directions) gig

def _concepts(a: int, b: int) -> list[Image.Image]:
    src = SVC / "studio" / "gallery-src"
    return [Image.open(src / f"concept{n:02d}.jpg").convert("RGB") for n in range(a, b + 1)]


def studio_hero() -> Image.Image:
    cons = _concepts(1, 12)
    im = _canvas((245, 241, 230))
    d = ImageDraw.Draw(im)
    head = "6 TO 12 LOGO\n& MASCOT\nDIRECTIONS"
    hs = _size_for(head, 520, 96)
    _text(d, (70, 90), head, hs, fill=INK, spacing=0)
    d.rectangle([70, 430, 190, 438], fill=INK)
    _text(d, (70, 464), "See your options in one sheet.", 30, fill=INK, font="Montserrat-ExtraBold.ttf")
    _text(d, (70, 510), "Pick one. It's refined by hand.", 26, fill=(90, 86, 78), font="Montserrat-ExtraBold.ttf")
    _chip(d, 70, 580, "First concepts in 24 hours", 22, fg=CREAM, bg=INK)
    # three overlapping cards on the right
    spec = [(cons[0], (640, 110, 910, 380), 0), (cons[3], (770, 330, 1070, 630), 0), (cons[8], (960, 90, 1230, 360), 0)]
    for art, box, _ in spec:
        _card(im, art, box, 24, 22)
    d = ImageDraw.Draw(im)
    _sample_label(d, 70, 712, "SAMPLE CONCEPTS: FICTIONAL BRANDS")
    return im


def studio_process() -> Image.Image:
    cons = _concepts(1, 12)
    im = _canvas((20, 20, 24))
    d = ImageDraw.Draw(im)
    _text(d, (70, 52), "HOW IT WORKS", 64, fill=CREAM)
    d.rectangle([70, 128, 170, 134], fill=GOLD)
    steps = [("1", "Send a short brief", "What it is for, who it is for, the feeling you want.", cons[6]),
             ("2", "Get a sheet of options", "6 to 12 different angles, each with a name, an idea and a 3-colour palette.", cons[2]),
             ("3", "Pick one, I refine it", "Your pick is cleaned up by hand. Revisions included in higher tiers.", cons[10])]
    cw, gap = 370, 45
    for i, (n, title, sub, art) in enumerate(steps):
        x0 = 70 + i * (cw + gap)
        _card(im, art, (x0, 170, x0 + cw, 170 + 300), 22, 18)
        d = ImageDraw.Draw(im)
        d.ellipse([x0 + 16, 186, x0 + 70, 240], fill=GOLD)
        _text(d, (x0 + 43, 214), n, 40, fill=INK, anchor="mm")
        _text(d, (x0 + 4, 492), title, _size_for(title, cw - 8, 30, "Montserrat-ExtraBold.ttf", 18), fill=GOLD, font="Montserrat-ExtraBold.ttf")
        words, line, lines = sub.split(), "", []
        f = brand.font("Montserrat-ExtraBold.ttf", 22)
        for w in words:
            if d.textlength((line + " " + w).strip(), font=f) > cw:
                lines.append(line); line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        _text(d, (x0 + 4, 542), "\n".join(lines), 22, fill=CREAM, font="Montserrat-ExtraBold.ttf", spacing=8)
    d = ImageDraw.Draw(im)
    _text(d, (70, 722), "No copying of living artists or existing brands.", 22, fill=MUTED, font="Montserrat-ExtraBold.ttf")
    return im


def studio_proof() -> Image.Image:
    cons = _concepts(1, 12)
    im = _canvas((245, 241, 230))
    d = ImageDraw.Draw(im)
    _text(d, (70, 40), "ONE BRIEF, SIX DIRECTIONS", 60, fill=INK)
    _text(d, (70, 124), "Sample sheet for a fictional kids' space-learning channel", 24, fill=(90, 86, 78), font="Montserrat-ExtraBold.ttf")
    names = ["A  Fox Astronaut", "B  Little Robot", "C  Moon Cadet", "D  Owl Pilot", "E  Rocket Badge", "F  Comet Grin"]
    cw, ch = 360, 205
    for i in range(6):
        col, row = i % 3, i // 3
        x0, y0 = 70 + col * (cw + 35), 170 + row * (ch + 68)
        art = _fit(cons[i], cw, ch)
        _card(im, art, (x0, y0, x0 + cw, y0 + ch), 18, 12)
        d = ImageDraw.Draw(im)
        _text(d, (x0 + 4, y0 + ch + 14), names[i], 26, fill=INK, font="Montserrat-ExtraBold.ttf")
    d = ImageDraw.Draw(im)
    _sample_label(d, 70, 736, "SAMPLE PROJECT: FICTIONAL BRAND")
    return im


def build() -> list[Path]:
    out = []
    for gig, makers in (("brand-kit", [kit_hero, kit_contents, kit_proof]), ("studio", [studio_hero, studio_process, studio_proof])):
        folder = SVC / gig / "gallery"
        folder.mkdir(parents=True, exist_ok=True)
        for n, fn in enumerate(makers, 1):
            p = folder / f"{n}-{fn.__name__.split('_', 1)[1]}.jpg"
            fn().convert("RGB").save(p, quality=92, optimize=True)
            out.append(p)
    return out


if __name__ == "__main__":
    for p in build():
        print(p)
