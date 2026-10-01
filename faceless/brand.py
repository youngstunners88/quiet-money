"""Brand kit generator: every platform asset from one palette, reproducible with `python -m faceless brand`.

Outputs to channel/brand-kit/:
  avatar.png (800)          YouTube / TikTok / Instagram profile picture (circle-safe)
  banner-youtube.png        2560x1440, all text inside the 1546x423 mobile-safe area
  watermark.png (150)       YouTube "branding watermark"
  og-image.png              1200x630 social / website share card
  favicon-*.png             site icons
  logo.svg                  vector mark for anything else
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from faceless import config
from faceless.config import Paths

INK = (14, 14, 16)
GOLD = (255, 210, 63)
DEEP_GOLD = (201, 162, 39)
CREAM = (245, 241, 230)
MUTED = (150, 146, 136)
KIT = Paths.root / "channel" / "brand-kit"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Paths.fonts / name), size)


def coin(size: int) -> Image.Image:
    """The mark: a gold coin with a negative-space Q. Supersampled for clean edges."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=GOLD)
    ring = int(s * 0.055)
    d.ellipse([ring, ring, s - 1 - ring, s - 1 - ring], outline=DEEP_GOLD, width=max(2, int(s * 0.018)))
    # subtle top-left sheen
    sheen = Image.new("L", (s, s), 0)
    ImageDraw.Draw(sheen).ellipse([int(s * 0.12), int(s * 0.08), int(s * 0.7), int(s * 0.55)], fill=60)
    sheen = sheen.filter(ImageFilter.GaussianBlur(s // 14))
    im = Image.composite(Image.new("RGBA", (s, s), (255, 255, 255, 255)), im, sheen.point(lambda v: v * 0.5))
    im.putalpha(Image.new("L", (s, s), 0))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
    im.putalpha(mask)
    d = ImageDraw.Draw(im)
    f = font("Montserrat-Black.ttf", int(s * 0.66))
    bbox = d.textbbox((0, 0), "Q", font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((s - tw) / 2 - bbox[0], (s - th) / 2 - bbox[1] - s * 0.01), "Q", font=f, fill=INK)
    return im.resize((size, size), Image.LANCZOS)


def avatar(size: int = 800) -> Image.Image:
    im = Image.new("RGB", (size, size), INK)
    glow = Image.new("RGB", (size, size), INK)
    ImageDraw.Draw(glow).ellipse([size * 0.1, size * 0.1, size * 0.9, size * 0.9], fill=(70, 55, 12))
    im = Image.blend(im, glow.filter(ImageFilter.GaussianBlur(size // 8)), 0.8)
    c = coin(int(size * 0.68))
    im.paste(c, ((size - c.width) // 2, (size - c.height) // 2), c)
    return im


def _spaced(draw, xy, text, f, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + spacing
    return x


def _spaced_width(draw, text, f, spacing):
    return sum(draw.textlength(ch, font=f) for ch in text) + spacing * (len(text) - 1)


def backdrop(w: int, h: int, source: str | None) -> Image.Image:
    """Dark cinematic backdrop: generated coin macro if available, else a gold-to-ink glow."""
    if source and Path(source).exists():
        bg = Image.open(source).convert("RGB")
        sc = max(w / bg.width, h / bg.height)
        bg = bg.resize((math.ceil(bg.width * sc), math.ceil(bg.height * sc)), Image.LANCZOS)
        left, top = (bg.width - w) // 2, (bg.height - h) // 2
        bg = bg.crop((left, top, left + w, top + h)).filter(ImageFilter.GaussianBlur(w // 320))
        return Image.blend(Image.new("RGB", (w, h), INK), bg, 0.42)
    bg = Image.new("RGB", (w, h), INK)
    glow = Image.new("RGB", (w, h), INK)
    ImageDraw.Draw(glow).ellipse([w * 0.25, h * 0.15, w * 0.75, h * 0.85], fill=(60, 46, 10))
    return Image.blend(bg, glow.filter(ImageFilter.GaussianBlur(w // 10)), 0.9)


def banner(source: str | None = None) -> Image.Image:
    W, H = 2560, 1440
    ch = config.load()["channel"]
    im = backdrop(W, H, source)
    d = ImageDraw.Draw(im)
    # mobile-safe area is the central 1546x423; everything readable lives inside it
    cx, cy = W // 2, H // 2
    mark = coin(250)
    title_f = font("Montserrat-Black.ttf", 132)
    tw = _spaced_width(d, "QUIET MONEY", title_f, 10)
    total = int(mark.width + 46 + tw)
    x0 = int(cx - total // 2)
    im.paste(mark, (x0, cy - 185), mark)
    _spaced(d, (x0 + mark.width + 46, cy - 160), "QUIET MONEY", title_f, GOLD, 10)
    tag_f = font("Montserrat-ExtraBold.ttf", 52)
    tag = ch["tagline"]
    d.text((x0 + mark.width + 50, cy - 10), tag, font=tag_f, fill=CREAM)
    pill_f = font("Montserrat-ExtraBold.ttf", 34)
    lead = "NEW SHORTS DAILY"
    rest = "   ·   STORIES  ·  MATH  ·  PSYCHOLOGY  ·  MYTHS  ·  PLAYBOOKS"
    lead_f = font("Montserrat-Black.ttf", 34)
    lw, rw = d.textlength(lead, font=lead_f), d.textlength(rest, font=pill_f)
    px = int(cx - (lw + rw) / 2)
    d.text((px, cy + 120), lead, font=lead_f, fill=GOLD)       # inside the 1546x423 mobile-safe area
    d.text((px + lw, cy + 120), rest, font=pill_f, fill=MUTED)
    return im


def og_image(source: str | None = None) -> Image.Image:
    W, H = 1200, 630
    ch = config.load()["channel"]
    im = backdrop(W, H, source)
    d = ImageDraw.Draw(im)
    mark = coin(170)
    im.paste(mark, (90, (H - 170) // 2 - 40), mark)
    _spaced(d, (300, 190), "QUIET MONEY", font("Montserrat-Black.ttf", 82), GOLD, 5)
    d.text((304, 300), ch["tagline"], font=font("Montserrat-ExtraBold.ttf", 36), fill=CREAM)
    d.text((304, 360), "Real numbers. Real stories. 60 seconds a day.", font=font("Montserrat-ExtraBold.ttf", 28), fill=MUTED)
    d.rectangle([0, H - 14, W, H], fill=GOLD)
    return im


def logo_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Quiet Money">
  <circle cx="256" cy="256" r="256" fill="#FFD23F"/>
  <circle cx="256" cy="256" r="228" fill="none" stroke="#C9A227" stroke-width="9"/>
  <text x="256" y="262" text-anchor="middle" dominant-baseline="central"
        font-family="Montserrat, Arial Black, sans-serif" font-weight="900" font-size="340" fill="#0E0E10">Q</text>
</svg>
"""


def build(background: str | None = None) -> dict:
    KIT.mkdir(parents=True, exist_ok=True)
    out = {}
    av = avatar(800)
    av.save(KIT / "avatar.png", optimize=True)
    out["avatar"] = KIT / "avatar.png"
    banner(background).save(KIT / "banner-youtube.png", optimize=True)
    out["banner"] = KIT / "banner-youtube.png"
    coin(150).save(KIT / "watermark.png", optimize=True)
    og_image(background).save(KIT / "og-image.png", optimize=True)
    for s in (512, 180, 32):
        avatar(s).save(KIT / f"favicon-{s}.png", optimize=True)
    (KIT / "logo.svg").write_text(logo_svg(), encoding="utf-8")
    return {k: str(v) for k, v in out.items()}


def generate_background() -> str | None:
    """One cinematic coin-macro backdrop from the image chain (cached; ~156 free neurons)."""
    from faceless.providers import images
    prompt = ("macro photograph of a few stacked antique gold coins in near darkness, single warm rim light from the "
              "left, deep black negative space on both sides, shallow depth of field, cinematic, minimal, no text")
    cache = Paths.cache / "brand-bg.jpg"
    if cache.exists():
        return str(cache)
    cache.parent.mkdir(parents=True, exist_ok=True)
    for name in ("cloudflare", "pollinations"):
        try:
            images.PROVIDERS[name](prompt, 1536, 864, 4242, cache)
            return str(cache)
        except Exception:  # noqa: BLE001 - the kit still renders with the procedural glow
            continue
    return None
