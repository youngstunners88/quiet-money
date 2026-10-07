"""Brand kit service: the engine behind the Fiverr gig "faceless channel brand kit".

Given a channel name, tagline and palette, build the full set a new faceless channel needs, reproducibly and in seconds:
avatar, YouTube banner (text kept inside the mobile-safe area), watermark, share image, favicons, vector logo, palette
swatches, and a short BRAND.md (colors, fonts, voice). `python -m faceless brandkit "Calm Orbit" --palette mint`.
Fonts are the OFL-licensed ones shipped in assets/fonts (free for commercial use). The look is clean typography and a
monogram mark, not custom illustration; the gig listing says exactly that. Our own brand kit stays in faceless/brand.py.
"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from faceless import brand
from faceless.config import Paths

OUT = Paths.root / "channel" / "services" / "brand-kit"
PALETTES = {   # name: (ink, accent, cream, muted)
    "gold": ("#0E0E10", "#FFD23F", "#F5F1E6", "#96928A"),
    "mint": ("#0B1613", "#35E0A1", "#EAF7F1", "#7E9A90"),
    "coral": ("#171112", "#FF6F5E", "#FCEFEA", "#A08B87"),
    "sky": ("#0C1420", "#5BB6FF", "#EAF3FC", "#7F93A8"),
    "violet": ("#120D1C", "#B58CFF", "#F2EBFC", "#9488A8"),
    "lime": ("#11140C", "#B7F33C", "#F3F8E4", "#919A7C"),
}
SAFE_W, SAFE_H = 1546, 423          # YouTube's mobile-safe area, centered on the 2560x1440 banner
NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &'.-]{0,23}$")


def clean(name: str) -> str:
    name = " ".join(name.split())
    if not NAME_OK.match(name):
        raise ValueError("channel name: 1-24 characters, letters, numbers, spaces and & ' . - only")
    return name


def rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def monogram(name: str) -> str:
    words = [w for w in re.split(r"[\s&.-]+", name) if w]
    return (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper()[:2] if len(words) > 1 else words[0][0].upper()


def mark(size: int, name: str, pal: tuple) -> Image.Image:
    """A round monogram badge: accent disc, inner ring, ink letters. Supersampled for clean edges."""
    ink, accent = rgb(pal[0]), rgb(pal[1])
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=accent)
    ring = int(s * 0.055)
    d.ellipse([ring, ring, s - 1 - ring, s - 1 - ring], outline=tuple(int(c * 0.78) for c in accent), width=max(2, int(s * 0.018)))
    letters = monogram(name)
    f = brand.font("Montserrat-Black.ttf", int(s * (0.5 if len(letters) > 1 else 0.62)))
    bb = d.textbbox((0, 0), letters, font=f)
    d.text(((s - (bb[2] - bb[0])) / 2 - bb[0], (s - (bb[3] - bb[1])) / 2 - bb[1] - s * 0.01), letters, font=f, fill=ink)
    return im.resize((size, size), Image.LANCZOS)


def backdrop(w: int, h: int, pal: tuple) -> Image.Image:
    ink, accent = rgb(pal[0]), rgb(pal[1])
    glow = Image.new("RGB", (w, h), ink)
    ImageDraw.Draw(glow).ellipse([w * 0.25, h * 0.15, w * 0.75, h * 0.85], fill=tuple(int(i + (a - i) * 0.2) for i, a in zip(ink, accent)))
    return Image.blend(Image.new("RGB", (w, h), ink), glow.filter(ImageFilter.GaussianBlur(w // 10)), 0.9)


def _fit(draw: ImageDraw.ImageDraw, text: str, fontfile: str, size: int, width: int, spacing: int) -> tuple:
    while size > 24:
        f = brand.font(fontfile, size)
        if brand._spaced_width(draw, text, f, spacing) <= width:
            return f, size
        size -= 4
    return brand.font(fontfile, 24), 24


def avatar(name: str, pal: tuple, size: int = 800) -> Image.Image:
    im = backdrop(size, size, pal)
    m = mark(int(size * 0.7), name, pal)
    im.paste(m, ((size - m.width) // 2, (size - m.height) // 2), m)
    return im


def banner_parts(name: str, tagline: str, pills: list[str], pal: tuple) -> tuple[Image.Image, tuple]:
    """(banner, bbox of all text and mark). The bbox must sit inside the mobile-safe area; tests enforce it."""
    W, H = 2560, 1440
    base = backdrop(W, H, pal)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    accent, cream, muted = rgb(pal[1]), rgb(pal[2]), rgb(pal[3])
    cx, cy = W // 2, H // 2
    m = mark(230, name, pal)
    title = name.upper()
    room = SAFE_W - m.width - 60 - 40
    tf, _ = _fit(d, title, "Montserrat-Black.ttf", 132, room, 8)
    tw = brand._spaced_width(d, title, tf, 8)
    tag_f, _ = _fit(d, tagline, "Montserrat-ExtraBold.ttf", 48, room, 0)
    total = int(m.width + 50 + max(tw, d.textlength(tagline, font=tag_f)))
    x0 = int(cx - total // 2)
    layer.paste(m, (x0, cy - 170), m)
    brand._spaced(d, (x0 + m.width + 50, cy - 150), title, tf, accent, 8)
    d.text((x0 + m.width + 54, cy - 10), tagline, font=tag_f, fill=cream)
    if pills:
        line = "   ·   ".join(p.upper() for p in pills[:4])
        pf, _ = _fit(d, line, "Montserrat-ExtraBold.ttf", 34, SAFE_W - 80, 0)
        lw = d.textlength(line, font=pf)
        d.text((int(cx - lw / 2), cy + 110), line, font=pf, fill=muted)
    box = layer.getbbox()
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB"), box


def og_image(name: str, tagline: str, pal: tuple) -> Image.Image:
    W, H = 1200, 630
    im = backdrop(W, H, pal)
    d = ImageDraw.Draw(im)
    m = mark(170, name, pal)
    im.paste(m, (90, (H - 170) // 2 - 20), m)
    tf, _ = _fit(d, name.upper(), "Montserrat-Black.ttf", 82, W - 300 - 60, 5)
    brand._spaced(d, (300, 215), name.upper(), tf, rgb(pal[1]), 5)
    tag_f, _ = _fit(d, tagline, "Montserrat-ExtraBold.ttf", 36, W - 300 - 60, 0)
    d.text((304, 325), tagline, font=tag_f, fill=rgb(pal[2]))
    d.rectangle([0, H - 14, W, H], fill=rgb(pal[1]))
    return im


def logo_svg(name: str, pal: tuple) -> str:
    n, letters = html.escape(name, quote=True), html.escape(monogram(name))
    size = 340 if len(letters) == 1 else 250
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="{n}">
  <circle cx="256" cy="256" r="256" fill="{pal[1]}"/>
  <circle cx="256" cy="256" r="228" fill="none" stroke="{pal[0]}" stroke-opacity="0.35" stroke-width="9"/>
  <text x="256" y="262" text-anchor="middle" dominant-baseline="central"
        font-family="Montserrat, Arial Black, sans-serif" font-weight="900" font-size="{size}" fill="{pal[0]}">{letters}</text>
</svg>
"""


def swatches(pal: tuple) -> Image.Image:
    im = Image.new("RGB", (1200, 300), rgb(pal[0]))
    d = ImageDraw.Draw(im)
    f = brand.font("Montserrat-ExtraBold.ttf", 28)
    for i, (label, hexv) in enumerate(zip(("Ink", "Accent", "Cream", "Muted"), pal)):
        x = 30 + i * 285
        d.rounded_rectangle([x, 30, x + 255, 200], radius=18, fill=rgb(hexv), outline=rgb(pal[3]), width=2)
        d.text((x, 215), f"{label}  {hexv.upper()}", font=f, fill=rgb(pal[2]))
    return im


def brand_md(name: str, tagline: str, palette: str, pal: tuple, niche: str) -> str:
    return f"""# {name}: brand sheet

**Tagline:** {tagline}
{f'**Niche:** {niche}' + chr(10) if niche else ''}
## Colors
| role | hex |
|---|---|
| Ink (backgrounds) | `{pal[0].upper()}` |
| Accent (titles, highlights) | `{pal[1].upper()}` |
| Cream (body text) | `{pal[2].upper()}` |
| Muted (secondary text) | `{pal[3].upper()}` |

## Fonts (free for commercial use, SIL Open Font License)
Montserrat Black for titles, Montserrat ExtraBold for subtitles and captions, Anton or Bebas Neue for big numbers.

## Using the files
- `avatar.png` (800 x 800): profile picture for YouTube, TikTok and Instagram; it survives the circle crop.
- `banner-youtube.png` (2560 x 1440): upload as is; all text sits inside the 1546 x 423 mobile-safe area.
- `watermark.png` (150 x 150): YouTube branding watermark (Studio > Customization > Branding).
- `og-image.png` (1200 x 630): link-preview image for a website or newsletter.
- `favicon-*.png` and `logo.svg`: website icons and the vector mark.

## Voice (fill in with your own words)
- Say it in plain words a friend would use. Short sentences. One idea per video.
- Never promise results. Never copy another creator's wording.
- Always disclose AI-assisted visuals or voice where the platform asks.

*Generated with the Quiet Money brand kit service. Palette: {palette}.*
"""


def build(name: str, tagline: str = "", palette: str = "gold", niche: str = "", pills: list[str] | None = None, out: Path | None = None,
          zip_it: bool = True) -> dict:
    name = clean(name)
    tagline = " ".join((tagline or "").split())[:60]
    if palette not in PALETTES:
        raise ValueError(f"palette must be one of {', '.join(PALETTES)}")
    pal = PALETTES[palette]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    dest = Path(out) if out else OUT / "samples" / slug
    dest.mkdir(parents=True, exist_ok=True)
    avatar(name, pal).save(dest / "avatar.png", optimize=True)
    ban, box = banner_parts(name, tagline, pills or [], pal)
    ban.save(dest / "banner-youtube.png", optimize=True)
    mark(150, name, pal).save(dest / "watermark.png", optimize=True)
    og_image(name, tagline, pal).save(dest / "og-image.png", optimize=True)
    for s in (512, 180, 32):
        avatar(name, pal, s).save(dest / f"favicon-{s}.png", optimize=True)
    (dest / "logo.svg").write_text(logo_svg(name, pal), encoding="utf-8")
    swatches(pal).save(dest / "palette.png", optimize=True)
    (dest / "BRAND.md").write_text(brand_md(name, tagline, palette, pal, niche), encoding="utf-8")
    sheet = Image.new("RGB", (1800, 1100), rgb(pal[0]))
    b = ban.resize((1740, 979))
    sheet.paste(b.crop((0, 300, 1740, 760)).resize((1740, 460)), (30, 30))
    av = avatar(name, pal, 420)
    sheet.paste(av, (30, 520))
    sheet.paste(og_image(name, tagline, pal).resize((840, 441)), (480, 520))
    sheet.paste(swatches(pal).resize((420, 105)), (1350, 520))
    sheet.save(dest / "preview.png", optimize=True)
    bundle = None
    if zip_it:
        bundle = dest.parent / f"{slug}-brand-kit.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(dest.iterdir()):
                if p.name != "preview.png":
                    z.write(p, f"{slug}/{p.name}")
    return {"dir": str(dest), "zip": str(bundle) if bundle else None, "text_box": box, "files": sorted(p.name for p in dest.iterdir())}


def samples() -> list[dict]:
    """Gig gallery samples for made-up brands, clearly labeled as samples in the listing (never passed off as client work)."""
    specs = [("Calm Orbit", "Slow living for fast minds", "mint", "mindfulness", ["Calm", "Focus", "Sleep"]),
             ("Iron Fork", "Cook it right, once", "coral", "cooking", ["Recipes", "Technique", "Gear"]),
             ("Pixel Harbor", "Game news, minus the noise", "sky", "gaming", ["News", "Reviews", "Deals"]),
             ("Night Ledger", "Money stories after dark", "violet", "finance", ["Stories", "Math", "Rules"])]
    return [build(n, t, p, nz, pills) for n, t, p, nz, pills in specs]


GIG = """# Gig: Faceless channel brand kit (Fiverr)

The owner creates the listing, sets the prices and handles messages. Nothing here is posted for them.

## Title
I will design a clean brand kit for your faceless YouTube or TikTok channel

## What the buyer gets (be exact; promise only this)
| tier | price to test | includes |
|---|---|---|
| Starter | $15 | profile avatar (800 px), YouTube banner with mobile-safe text, watermark, 1 revision |
| Standard | $35 | Starter + share image, favicons, vector logo, color swatches, BRAND.md sheet, 2 revisions |
| Full | $75 | Standard + 3 alternative palettes of the same kit, 10 channel-name ideas, 30 video title templates for your niche, 3 revisions |
Prices are guesses to test (assumed); raise them as soon as orders arrive faster than you can fill them.

## Description (paste)
Starting a faceless channel? Get the whole identity in one delivery: a monogram avatar that survives the circle crop, a banner whose
text stays inside YouTube's mobile-safe area, a watermark, a link-preview image, favicons, a vector logo and a one-page brand sheet
with exact colors and fonts. Clean typography and a monogram mark, not custom illustration: it is meant for new channels that need to
look consistent and finished today. Fonts are free for commercial use.
AI disclosure: layouts are generated with code and AI-assisted tooling and checked by a person before delivery. Files are original to your channel name.

## What not to promise
No growth, views, subscribers or income. No copying another channel's identity. No trademarked names or logos. Turnaround "same day" only if you will actually do it.

## Gallery
Use `samples/*/preview.png` (made-up brands: Calm Orbit, Iron Fork, Pixel Harbor, Night Ledger). Label them "sample" in the gallery.
Check Fiverr's current rules on AI-assisted work and disclosure before publishing the gig.

## Fulfilment (agent, per order, about 2 minutes)
`python -m faceless brandkit "<Channel Name>" --tagline "<tagline>" --palette <gold|mint|coral|sky|violet|lime> --niche "<niche>" --pills "A,B,C"`
then review the preview, send `<slug>-brand-kit.zip`. Revisions: change inputs and rebuild.
"""


def write_gig() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "GIG.md"
    p.write_text(GIG, encoding="utf-8")
    return p
