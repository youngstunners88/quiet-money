"""Listing visuals drawn in code: device mockups, hero and feature images, a listing video. No AI image is involved, so every word is spelled
right, every screenshot is the real product, and the same input always gives the same picture.

Layout rule from Etsy's own image guide: the first photo may be cropped to square, portrait or landscape thumbnails, so everything that
matters sits inside the centre 3:4 of a 4:3 canvas (x between 15% and 85%). A main image must not be a collage and must not be dark or
blurry, so the hero is one device and one headline on a bright-on-dark ground.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from faceless.brand import CREAM, GOLD, INK, MUTED, coin
from faceless.config import Paths

W, H = 2400, 1800                      # Etsy: 4:3, both sides above the 2000 px the help center asks for
SAFE_L, SAFE_R = int(W * 0.15), int(W * 0.85)
WHITE = (255, 255, 255)
PANEL = (28, 28, 33)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Paths.fonts / name), size)


ANTON, BEBAS, BLACK, XBOLD = "Anton-Regular.ttf", "BebasNeue-Regular.ttf", "Montserrat-Black.ttf", "Montserrat-ExtraBold.ttf"


# ---------------------------------------------------------------- primitives

def ground(w: int = W, h: int = H, glow_at: tuple[float, float] = (0.5, 0.58)) -> Image.Image:
    """Near-black ground with a soft gold glow where the product sits and a faint vertical vignette."""
    base = Image.new("RGB", (w, h), INK)
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    cx, cy = int(w * glow_at[0]), int(h * glow_at[1])
    r = int(min(w, h) * 0.62)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(70, 56, 12))
    glow = glow.filter(ImageFilter.GaussianBlur(r // 2))
    out = ImageChops.add(base, glow)
    vig = Image.new("L", (w, h), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle([0, 0, w, h], fill=0)
    vd.ellipse([-w * 0.15, -h * 0.15, w * 1.15, h * 1.15], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(w // 8))
    return Image.composite(out, Image.new("RGB", (w, h), (6, 6, 8)), vig)


def tracked(d: ImageDraw.ImageDraw, xy, text: str, fnt, fill, spacing: int = 6, anchor: str = "l") -> int:
    """Text with letter spacing; returns its width. anchor 'l' (x is the left edge) or 'm' (x is the centre)."""
    widths = [d.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor == "m":
        x -= total / 2
    for ch, wch in zip(text, widths):
        d.text((x, y), ch, font=fnt, fill=fill)
        x += wch + spacing
    return int(total)


def wrap(d: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


def centered(d, y: int, text: str, fnt, fill, width: int = SAFE_R - SAFE_L, line_gap: float = 0.2, cx: int = W // 2) -> int:
    """Wrapped, centre-aligned text starting at y; returns the y below the last line (measured from the real glyphs, so tall display
    fonts like Anton never run into what comes next)."""
    for line in wrap(d, text, fnt, width):
        d.text((cx, y), line, font=fnt, fill=fill, anchor="ma")
        y = d.textbbox((cx, y), line, font=fnt, anchor="ma")[3] + int(fnt.size * line_gap)
    return y


def headline(d, y: int, text: str, size: int, width: int, max_lines: int = 2, floor: int = 100, accent=GOLD, fill=WHITE) -> int:
    """A display headline that shrinks until it fits `max_lines`, with its last word in the accent colour. Returns the y below it."""
    fnt = font(ANTON, size)
    lines = wrap(d, text.upper(), fnt, width)
    while len(lines) > max_lines and size > floor:
        size -= 8
        fnt = font(ANTON, size)
        lines = wrap(d, text.upper(), fnt, width)
    for i, line in enumerate(lines):
        words = line.split(" ")
        last = i == len(lines) - 1
        widths = [d.textlength(w, font=fnt) for w in words]
        space = d.textlength(" ", font=fnt)
        x = W / 2 - (sum(widths) + space * (len(words) - 1)) / 2
        for j, (w, wd) in enumerate(zip(words, widths)):
            d.text((x, y), w, font=fnt, fill=accent if last and j == len(words) - 1 else fill, anchor="la")
            x += wd + space
        y = d.textbbox((W // 2, y), line, font=fnt, anchor="ma")[3] + int(size * 0.16)
    return y


def chip(img: Image.Image, cx: int, cy: int, text: str, size: int = 44, fill=None, outline=GOLD, color=CREAM) -> int:
    """A pill with gold outline, centred on (cx, cy); returns its width."""
    d = ImageDraw.Draw(img)
    f = font(XBOLD, size)
    tw = int(d.textlength(text, font=f))
    pad_x, pad_y = int(size * 0.8), int(size * 0.42)
    w, h = tw + 2 * pad_x, size + 2 * pad_y
    x0, y0 = cx - w // 2, cy - h // 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h // 2, fill=fill, outline=outline, width=4)
    d.text((cx, cy), text, font=f, fill=color, anchor="mm")
    return w


def check(d: ImageDraw.ImageDraw, x: int, y: int, size: int = 54, color=GOLD) -> None:
    d.ellipse([x, y, x + size, y + size], fill=color)
    k = size / 54
    d.line([(x + 14 * k, y + 28 * k), (x + 24 * k, y + 38 * k), (x + 41 * k, y + 17 * k)], fill=INK, width=max(4, int(7 * k)), joint="curve")


def drop_shadow(canvas: Image.Image, box: tuple[int, int, int, int], blur: int = 60, offset: int = 40, alpha: int = 170, radius: int = 40) -> None:
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0 + 10, y0 + offset, x1 - 10, y1 + offset], radius=radius, fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste(sh, (0, 0), sh)


def fit_inside(im: Image.Image, w: int, h: int, bg=WHITE) -> Image.Image:
    """The picture scaled to fit w x h, centred on `bg` (a screenshot keeps its real proportions)."""
    s = min(w / im.width, h / im.height)
    r = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    out = Image.new("RGB", (w, h), bg)
    out.paste(r, ((w - r.width) // 2, (h - r.height) // 2))
    return out


def autocrop(im: Image.Image, pad: int = 28, bg=WHITE, tol: int = 12) -> Image.Image:
    """Trim the page margins off a rendered page, keeping `pad` px of air."""
    rgb = im.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, bg)).convert("L").point(lambda v: 255 if v > tol else 0)
    box = diff.getbbox()
    if not box:
        return rgb
    x0, y0, x1, y1 = box
    return rgb.crop((max(0, x0 - pad), max(0, y0 - pad), min(rgb.width, x1 + pad), min(rgb.height, y1 + pad)))


# ---------------------------------------------------------------- window

GREY_BAR, GREY_TAB, GREEN = (236, 238, 241), (226, 229, 233), (24, 128, 74)


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    big = Image.new("L", (size[0] * 3, size[1] * 3), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, size[0] * 3 - 1, size[1] * 3 - 1], radius=radius * 3, fill=255)
    return big.resize(size, Image.LANCZOS)


def window(shot: Image.Image, width: int, title: str = "", tabs: tuple[str, ...] = (), active: int = 0) -> Image.Image:
    """An app window around the real page: title bar, the page at its own proportions, the real sheet tabs underneath. RGBA with rounded corners."""
    shot = shot.convert("RGB")
    body = shot.resize((width, max(1, int(shot.height * width / shot.width))), Image.LANCZOS)
    bar_h = max(48, int(width * 0.030))
    tab_h = max(44, int(width * 0.028)) if tabs else 0
    img = Image.new("RGBA", (width, bar_h + body.height + tab_h), GREY_BAR + (255,))
    d = ImageDraw.Draw(img)
    r = bar_h // 5
    for k in range(3):
        cx = bar_h // 2 + k * int(r * 3.1)
        d.ellipse([cx - r, bar_h // 2 - r, cx + r, bar_h // 2 + r], fill=(184, 188, 194))
    if title:
        d.text((width // 2, bar_h // 2), title, font=font(XBOLD, int(bar_h * 0.40)), fill=(96, 100, 108), anchor="mm")
    img.paste(body, (0, bar_h))
    if tabs:
        y0 = bar_h + body.height
        d.rectangle([0, y0, width, y0 + tab_h], fill=GREY_TAB)
        f = font(XBOLD, int(tab_h * 0.46))
        x = int(tab_h * 0.5)
        for i, name in enumerate(tabs):
            tw = int(d.textlength(name, font=f)) + int(tab_h * 0.9)
            if x + tw > width - 10:
                break
            if i == active:
                d.rectangle([x, y0, x + tw, y0 + tab_h], fill=WHITE)
                d.rectangle([x, y0, x + tw, y0 + 5], fill=GREEN)
            d.text((x + tw // 2, y0 + tab_h // 2 + 2), name, font=f, fill=(34, 98, 62) if i == active else (92, 96, 104), anchor="mm")
            x += tw + 4
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), _rounded_mask(img.size, max(14, int(width * 0.011))))
    return out


def place(canvas: Image.Image, dev: Image.Image, cx: int, top: int, shadow: bool = True) -> tuple[int, int, int, int]:
    x = cx - dev.width // 2
    if shadow:
        drop_shadow(canvas, (x, top, x + dev.width, top + dev.height), blur=int(dev.width * 0.03), offset=int(dev.width * 0.022), alpha=200, radius=22)
    canvas.paste(dev, (x, top), dev)
    return x, top, x + dev.width, top + dev.height


def fit_window(shot: Image.Image, max_w: int, max_h: int, **kw) -> Image.Image:
    """The largest window for `shot` that fits max_w x max_h."""
    w = max_w
    for _ in range(12):
        win = window(shot, w, **kw)
        if win.height <= max_h:
            return win
        w = int(w * max_h / win.height) - 2
    return window(shot, max(200, w), **kw)


# ---------------------------------------------------------------- brand strip

def brand_strip(img: Image.Image, y: int = 84, label: str = "QUIET MONEY") -> None:
    d = ImageDraw.Draw(img)
    c = coin(96).convert("RGBA")
    f = font(XBOLD, 40)
    tw = sum(d.textlength(ch, font=f) + 8 for ch in label) - 8
    total = c.width + 26 + tw
    x = (W - total) // 2
    img.paste(c, (int(x), y), c)
    tracked(d, (int(x) + c.width + 26, y + 26), label, f, CREAM, spacing=8)


# ---------------------------------------------------------------- the images of a listing

def hero(title: str, subtitle: str, shot: Image.Image, chips: list[str], tabs: tuple[str, ...] = (), active: int = 0, file_name: str = "") -> Image.Image:
    """Main image: brand, headline, subtitle, one real page in a window, three promises. Not a collage."""
    img = ground()
    brand_strip(img, y=64)
    d = ImageDraw.Draw(img)
    y = headline(d, 205, title, 176, SAFE_R - SAFE_L + 200)
    y = centered(d, y + 12, subtitle, font(XBOLD, 54), CREAM, width=SAFE_R - SAFE_L + 160)
    chips_y = H - 100
    top = y + 34
    win = fit_window(shot, 1760, chips_y - 62 - top, title=file_name, tabs=tabs, active=active)
    place(img, win, W // 2, top + max(0, (chips_y - 62 - top - win.height) // 2))
    widths = [d.textlength(t.upper(), font=font(XBOLD, 40)) + 2 * 32 + 30 for t in chips]
    x = W // 2 - int(sum(widths) / 2) - 24 * (len(chips) - 1) // 2
    for t, w in zip(chips, widths):
        chip(img, int(x + w / 2), chips_y, t.upper(), size=40)
        x += w + 24
    return img


def feature(headline_text_: str, bullets: list[str], shot: Image.Image, index: int, total: int, tabs: tuple[str, ...] = (), active: int = 0, file_name: str = "") -> Image.Image:
    """One tab close-up: headline, the real page, up to three ticked benefits."""
    img = ground(glow_at=(0.5, 0.5))
    d = ImageDraw.Draw(img)
    y = headline(d, 90, headline_text_, 118, SAFE_R - SAFE_L + 300, floor=84)
    f = font(XBOLD, 46)
    rows = [wrap(d, b, f, SAFE_R - SAFE_L - 220) for b in bullets[:3]]
    bullets_h = sum(len(r) * 62 + 20 for r in rows)
    top = y + 24
    win = fit_window(shot, 2000, H - top - bullets_h - 150, title=file_name, tabs=tabs, active=active)
    box = place(img, win, W // 2, top)
    by = box[3] + 62
    for lines in rows:
        check(d, SAFE_L + 40, by + 2, 52)
        for ln in lines:
            d.text((SAFE_L + 120, by), ln, font=f, fill=CREAM)
            by += 62
        by += 20
    tracked(d, (W // 2, H - 56), f"{index} / {total}", font(XBOLD, 28), MUTED, spacing=6, anchor="m")
    return img


def inside_grid(title: str, shots: list[tuple[str, Image.Image]], sub: str = "", footer: str = "") -> Image.Image:
    """'What's inside': every tab as a labelled tile (a content image, never the main one)."""
    img = ground(glow_at=(0.5, 0.5))
    d = ImageDraw.Draw(img)
    y = headline(d, 100, title, 124, SAFE_R - SAFE_L + 300, floor=90)
    if sub:
        y = centered(d, y + 6, sub, font(XBOLD, 48), CREAM, width=SAFE_R - SAFE_L + 200)
    n = len(shots)
    cols = 3 if n > 4 else 2
    rows = math.ceil(n / cols)
    gap = 56
    tw = int((W - 2 * 150 - gap * (cols - 1)) / cols)
    th = int(tw * 0.74)
    grid_w = cols * tw + (cols - 1) * gap
    x0 = (W - grid_w) // 2
    area_top, area_bot = y + 50, H - (170 if footer else 70)
    row_h = th + 96
    y0 = area_top + max(0, (area_bot - area_top - rows * row_h) // 2)
    f = font(XBOLD, 40)
    for i, (label, sh) in enumerate(shots):
        r, c = divmod(i, cols)
        x, yy = x0 + c * (tw + gap), y0 + r * row_h
        tile = fit_inside(sh.convert("RGB"), tw, th)
        drop_shadow(img, (x, yy, x + tw, yy + th), blur=24, offset=14, alpha=170, radius=18)
        img.paste(tile, (x, yy), _rounded_mask(tile.size, 18))
        d.text((x + tw // 2, yy + th + 22), label.upper(), font=f, fill=GOLD, anchor="ma")
    if footer:
        centered(d, H - 150, footer, font(XBOLD, 40), MUTED, width=SAFE_R - SAFE_L + 300)
    return img


def steps_image(title: str, steps: list[tuple[str, str]]) -> Image.Image:
    """'How it works': numbered steps down the middle."""
    img = ground(glow_at=(0.5, 0.5))
    d = ImageDraw.Draw(img)
    y = headline(d, 140, title, 140, SAFE_R - SAFE_L + 300)
    step_h = 300
    y += max(60, (H - y - len(steps) * step_h - 120) // 2)
    head_f, sub_f = font(ANTON, 92), font(XBOLD, 50)
    for i, (head, sub) in enumerate(steps, 1):
        x = SAFE_L + 10
        d.ellipse([x, y, x + 200, y + 200], fill=GOLD)
        d.text((x + 100, y + 104), str(i), font=font(ANTON, 140), fill=INK, anchor="mm")
        d.text((x + 270, y + 6), head.upper(), font=head_f, fill=WHITE, anchor="la")
        sy = d.textbbox((x + 270, y + 6), head.upper(), font=head_f, anchor="la")[3] + 14
        for ln in wrap(d, sub, sub_f, SAFE_R - x - 300):
            d.text((x + 272, sy), ln, font=sub_f, fill=CREAM)
            sy += 64
        y += max(step_h, sy - y + 40)
    return img


def notes_image(title: str, points: list[str], footer: str = "") -> Image.Image:
    """'Honest notes' and 'works with': plain statements on the ground."""
    img = ground(glow_at=(0.5, 0.5))
    d = ImageDraw.Draw(img)
    y = headline(d, 150, title, 150, SAFE_R - SAFE_L + 300)
    f = font(XBOLD, 54)
    block = sum(len(wrap(d, p_, f, SAFE_R - SAFE_L - 200)) * 72 + 44 for p_ in points)
    y += max(60, (H - y - block - (260 if footer else 120)) // 2)
    for p_ in points:
        lines = wrap(d, p_, f, SAFE_R - SAFE_L - 200)
        check(d, SAFE_L + 20, y + 4, 62)
        for ln in lines:
            d.text((SAFE_L + 130, y), ln, font=f, fill=CREAM)
            y += 72
        y += 44
    if footer:
        centered(d, H - 200, footer, font(XBOLD, 36), MUTED, width=SAFE_R - SAFE_L + 200)
    return img


def deliver(im: Image.Image, size: tuple[int, int] = (2800, 2100)) -> Image.Image:
    """The finished 2400x1800 design at Etsy's recommended size (2000 px or more on both sides), with a touch of sharpening for the resize."""
    return im.convert("RGB").resize(size, Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=2))


def cover_16x9(hero_img: Image.Image, w: int = 1280, h: int = 720) -> Image.Image:
    """Gumroad cover: the hero re-composed for 16:9 (the central band of the 4:3 hero, scaled)."""
    band_h = int(hero_img.width * h / w)
    top = max(0, (hero_img.height - band_h) // 2 - 40)
    return hero_img.crop((0, top, hero_img.width, top + band_h)).resize((w, h), Image.LANCZOS)


def square_thumb(shot: Image.Image, title: str, size: int = 1200) -> Image.Image:
    """Gumroad card thumbnail: square, coin, name, the real page."""
    img = ground(W, W, glow_at=(0.5, 0.64))
    d = ImageDraw.Draw(img)
    c = coin(150).convert("RGBA")
    img.paste(c, (W // 2 - 75, 100), c)
    big = font(ANTON, 210)
    y = 300
    for i, ln in enumerate(wrap(d, title.upper(), big, W - 420)[:3]):
        d.text((W // 2, y), ln, font=big, fill=WHITE, anchor="ma")
        y += 214
    win = fit_window(shot, 1900, W - y - 120)
    place(img, win, W // 2, y + 20)
    return img.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- video

def video(frames: list[Path], out: Path, seconds_each: float = 2.4, size: tuple[int, int] = (1920, 1080), fps: int = 30) -> bool:
    """A short silent listing video: each image eased in with a slow push, cross-faded. Etsy takes 3 to 15 seconds, no audio kept."""
    if not shutil.which("ffmpeg") or not frames:
        return False
    fade = 0.5
    w, h = size
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for f in frames:
        cmd += ["-i", str(f)]                                     # one frame per image: zoompan turns it into d frames
    parts = []
    for i in range(len(frames)):
        d = int((seconds_each + fade) * fps)
        parts.append(f"[{i}:v]scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                     f"zoompan=z='1+0.0007*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={d}:s={w}x{h}:fps={fps},setsar=1,format=yuv420p[v{i}]")
    chain, last = ";".join(parts), "v0"
    for i in range(1, len(frames)):
        off = i * seconds_each
        chain += f";[{last}][v{i}]xfade=transition=fade:duration={fade}:offset={off:.2f}[x{i}]"
        last = f"x{i}"
    cmd += ["-filter_complex", chain, "-map", f"[{last}]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
    return r.returncode == 0 and out.exists()


def render_pages(xlsx: Path, dpi: int = 230, first: int = 1, last: int = 8, workdir: Path | None = None) -> list[Image.Image]:
    """The product's own pages, rendered by LibreOffice from the shipped file at `dpi` and trimmed to their content."""
    office, ppm = shutil.which("soffice") or shutil.which("libreoffice"), shutil.which("pdftoppm")
    if not office or not ppm:
        return []
    tmp = workdir or Path(tempfile.mkdtemp(prefix="mock-"))
    subprocess.run([office, "--headless", "--norestore", f"-env:UserInstallation=file://{tmp}/profile", "--convert-to", "pdf", "--outdir", str(tmp), str(xlsx)],
                   capture_output=True, timeout=240, check=False)
    pdf = tmp / (xlsx.stem + ".pdf")
    if not pdf.exists():
        return []
    subprocess.run([ppm, "-png", "-r", str(dpi), "-f", str(first), "-l", str(last), str(pdf), str(tmp / "pg")], capture_output=True, timeout=300, check=False)
    return [autocrop(Image.open(p)) for p in sorted(tmp.glob("pg-*.png"))]


# ---------------------------------------------------------------- 16:9 cover, paper pages

def cover_wide(title: str, subtitle: str, shot: Image.Image, chips: list[str], tabs: tuple[str, ...] = (), active: int = 0, file_name: str = "",
               size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    """Gumroad cover, composed natively for 16:9: words on the left, the real page on the right."""
    w, h = size
    s = w / 1920
    img = ground(w, h, glow_at=(0.68, 0.5))
    d = ImageDraw.Draw(img)
    c = coin(int(88 * s)).convert("RGBA")
    img.paste(c, (int(90 * s), int(72 * s)), c)
    tracked(d, (int(90 * s) + c.width + int(22 * s), int(72 * s) + int(24 * s)), "QUIET MONEY", font(XBOLD, int(34 * s)), CREAM, spacing=int(7 * s))
    fnt = font(ANTON, int(132 * s))
    lines = wrap(d, title.upper(), fnt, int(780 * s))
    while len(lines) > 3 and fnt.size > 80:
        fnt = font(ANTON, fnt.size - 8)
        lines = wrap(d, title.upper(), fnt, int(780 * s))
    y = int(215 * s)
    for i, ln in enumerate(lines):
        d.text((int(90 * s), y), ln, font=fnt, fill=GOLD if i == len(lines) - 1 else WHITE, anchor="la")
        y = d.textbbox((int(90 * s), y), ln, font=fnt, anchor="la")[3] + int(fnt.size * 0.14)
    sub_f = font(XBOLD, int(38 * s))
    for ln in wrap(d, subtitle, sub_f, int(740 * s)):
        d.text((int(90 * s), y + int(14 * s)), ln, font=sub_f, fill=CREAM)
        y += int(52 * s)
    cy = h - int(120 * s)
    x = int(90 * s)
    for t_ in chips:
        fch = font(XBOLD, int(26 * s))
        wch = int(d.textlength(t_.upper(), font=fch) + 2 * 0.8 * 26 * s)
        chip(img, x + wch // 2, cy, t_.upper(), size=int(26 * s))
        x += wch + int(16 * s)
        if x > int(840 * s):
            x, cy = int(90 * s), cy + int(78 * s)
    win = fit_window(shot, int(1020 * s), int(900 * s), title=file_name, tabs=tabs, active=active)
    place(img, win, int(1330 * s), (h - win.height) // 2)
    return img


def paper(page: Image.Image, width: int) -> Image.Image:
    """One printed page: white, thin edge, soft corners (RGBA)."""
    pg = page.convert("RGB")
    pg = pg.resize((width, int(pg.height * width / pg.width)), Image.LANCZOS)
    out = Image.new("RGBA", pg.size, (0, 0, 0, 0))
    out.paste(pg, (0, 0), _rounded_mask(pg.size, 8))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, pg.width - 1, pg.height - 1], radius=8, outline=(205, 205, 205, 255), width=2)
    return out


def paper_fan(pages: list[Image.Image], width: int = 860) -> Image.Image:
    """Three pages fanned on a transparent layer (RGBA), the middle one in front."""
    angles, shifts = (-9, 9, 0), (int(-width * 0.49), int(width * 0.49), 0)
    order = [0, 1, 2]
    layer = Image.new("RGBA", (int(width * 4.2), int(width * 2.3)), (0, 0, 0, 0))
    for k in order:
        pg = paper(pages[k % len(pages)], width)
        sh = Image.new("RGBA", pg.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([0, 0, pg.width, pg.height], radius=10, fill=(0, 0, 0, 210))
        sh = sh.filter(ImageFilter.GaussianBlur(28))
        r_sh, r_pg = sh.rotate(angles[k], expand=True, resample=Image.BICUBIC), pg.rotate(angles[k], expand=True, resample=Image.BICUBIC)
        cx, cy = layer.width // 2 + shifts[k], layer.height // 2 + (30 if k < 2 else 0)
        layer.paste(r_sh, (cx - r_sh.width // 2 + 14, cy - r_sh.height // 2 + 34), r_sh)
        layer.paste(r_pg, (cx - r_pg.width // 2, cy - r_pg.height // 2), r_pg)
    return layer.crop(layer.getbbox())


def hero_pages(title: str, subtitle: str, pages: list[Image.Image], chips: list[str]) -> Image.Image:
    """Main image for a printable pack: brand, headline, a fan of the real pages, promises."""
    img = ground()
    brand_strip(img, y=64)
    d = ImageDraw.Draw(img)
    y = headline(d, 205, title, 176, SAFE_R - SAFE_L + 200)
    y = centered(d, y + 12, subtitle, font(XBOLD, 54), CREAM, width=SAFE_R - SAFE_L + 160)
    chips_y = H - 100
    fan = paper_fan(pages)
    avail_h, avail_w = chips_y - 70 - (y + 30), 1900
    s = min(avail_w / fan.width, avail_h / fan.height, 1.0)
    fan = fan.resize((int(fan.width * s), int(fan.height * s)), Image.LANCZOS)
    img.paste(fan, ((W - fan.width) // 2, y + 30 + (avail_h - fan.height) // 2), fan)
    widths = [d.textlength(t.upper(), font=font(XBOLD, 40)) + 2 * 32 + 30 for t in chips]
    x = W // 2 - int(sum(widths) / 2) - 24 * (len(chips) - 1) // 2
    for t_, w_ in zip(chips, widths):
        chip(img, int(x + w_ / 2), chips_y, t_.upper(), size=40)
        x += w_ + 24
    return img


def feature_page(headline_text_: str, bullets: list[str], page: Image.Image, index: int, total: int) -> Image.Image:
    """One printed page large on the left, the benefits on the right."""
    img = ground(glow_at=(0.35, 0.5))
    d = ImageDraw.Draw(img)
    pg = paper(page, 1000)
    max_h = H - 2 * 130
    if pg.height > max_h:
        pg = pg.resize((int(pg.width * max_h / pg.height), max_h), Image.LANCZOS)
    x0 = 200
    drop_shadow(img, (x0, (H - pg.height) // 2, x0 + pg.width, (H + pg.height) // 2), blur=40, offset=26, alpha=200, radius=10)
    img.paste(pg, (x0, (H - pg.height) // 2), pg)
    tx = x0 + pg.width + 130
    fnt = font(ANTON, 104)
    y = 330
    lines = wrap(d, headline_text_.upper(), fnt, W - tx - 150)
    for i, ln in enumerate(lines):
        d.text((tx, y), ln, font=fnt, fill=GOLD if i == len(lines) - 1 else WHITE, anchor="la")
        y = d.textbbox((tx, y), ln, font=fnt, anchor="la")[3] + 16
    y += 50
    f = font(XBOLD, 46)
    for b in bullets[:3]:
        check(d, tx, y + 2, 52)
        for ln in wrap(d, b, f, W - tx - 150 - 80):
            d.text((tx + 80, y), ln, font=f, fill=CREAM)
            y += 62
        y += 24
    tracked(d, (W // 2, H - 56), f"{index} / {total}", font(XBOLD, 28), MUTED, spacing=6, anchor="m")
    return img


def render_pdf(pdf: Path, dpi: int = 110, first: int = 1, last: int = 6) -> list[Image.Image]:
    """Pages of a PDF as images (pdftoppm), margins kept: paper looks like paper."""
    ppm = shutil.which("pdftoppm")
    if not ppm or not pdf.exists():
        return []
    tmp = Path(tempfile.mkdtemp(prefix="pdfpg-"))
    subprocess.run([ppm, "-png", "-r", str(dpi), "-f", str(first), "-l", str(last), str(pdf), str(tmp / "p")], capture_output=True, timeout=300, check=False)
    return [Image.open(p).convert("RGB") for p in sorted(tmp.glob("p-*.png"))]


# ---------------------------------------------------------------- bundle and printable variants

def paper_grid(title: str, shots: list[tuple[str, Image.Image]], sub: str = "", footer: str = "") -> Image.Image:
    """'What's inside' for printable pages: portrait tiles, three across."""
    img = ground(glow_at=(0.5, 0.5))
    d = ImageDraw.Draw(img)
    y = headline(d, 100, title, 124, SAFE_R - SAFE_L + 300, floor=90)
    if sub:
        y = centered(d, y + 6, sub, font(XBOLD, 48), CREAM, width=SAFE_R - SAFE_L + 200)
    cols = 3
    rows = math.ceil(len(shots) / cols)
    area_top, area_bot = y + 40, H - (150 if footer else 60)
    label_h, gap_x = 84, 90
    th = int((area_bot - area_top - rows * label_h - (rows - 1) * 30) / rows)
    tw = int(th * 0.773)                                   # US Letter proportions
    x0 = (W - (cols * tw + (cols - 1) * gap_x)) // 2
    f = font(XBOLD, 38)
    for i, (label, pg) in enumerate(shots):
        r, c = divmod(i, cols)
        x, yy = x0 + c * (tw + gap_x), area_top + r * (th + label_h + 30)
        tile = paper(pg, tw)
        if tile.height > th:
            tile = tile.resize((int(tile.width * th / tile.height), th), Image.LANCZOS)
        drop_shadow(img, (x, yy, x + tile.width, yy + tile.height), blur=22, offset=14, alpha=190, radius=8)
        img.paste(tile, (x + (tw - tile.width) // 2, yy), tile)
        d.text((x + tw // 2, yy + th + 22), label.upper(), font=f, fill=GOLD, anchor="ma")
    if footer:
        centered(d, H - 130, footer, font(XBOLD, 40), MUTED, width=SAFE_R - SAFE_L + 300)
    return img


def cover_pages(title: str, subtitle: str, pages: list[Image.Image], chips: list[str], size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    """Gumroad cover for a printable pack: words on the left, a fan of the real pages on the right."""
    w, h = size
    s = w / 1920
    img = ground(w, h, glow_at=(0.68, 0.5))
    d = ImageDraw.Draw(img)
    c = coin(int(88 * s)).convert("RGBA")
    img.paste(c, (int(90 * s), int(72 * s)), c)
    tracked(d, (int(90 * s) + c.width + int(22 * s), int(72 * s) + int(24 * s)), "QUIET MONEY", font(XBOLD, int(34 * s)), CREAM, spacing=int(7 * s))
    fnt = font(ANTON, int(132 * s))
    lines = wrap(d, title.upper(), fnt, int(780 * s))
    while len(lines) > 3 and fnt.size > 80:
        fnt = font(ANTON, fnt.size - 8)
        lines = wrap(d, title.upper(), fnt, int(780 * s))
    y = int(215 * s)
    for i, ln in enumerate(lines):
        d.text((int(90 * s), y), ln, font=fnt, fill=GOLD if i == len(lines) - 1 else WHITE, anchor="la")
        y = d.textbbox((int(90 * s), y), ln, font=fnt, anchor="la")[3] + int(fnt.size * 0.14)
    sub_f = font(XBOLD, int(38 * s))
    for ln in wrap(d, subtitle, sub_f, int(740 * s)):
        d.text((int(90 * s), y + int(14 * s)), ln, font=sub_f, fill=CREAM)
        y += int(52 * s)
    cy, x = h - int(120 * s), int(90 * s)
    fch = font(XBOLD, int(26 * s))
    for t_ in chips:
        wch = int(d.textlength(t_.upper(), font=fch) + 2 * 0.8 * 26 * s)
        chip(img, x + wch // 2, cy, t_.upper(), size=int(26 * s))
        x += wch + int(16 * s)
        if x > int(840 * s):
            x, cy = int(90 * s), cy + int(78 * s)
    fan = paper_fan(pages, width=int(520 * s))
    k = min(int(1000 * s) / fan.width, int(930 * s) / fan.height, 1.0)
    fan = fan.resize((int(fan.width * k), int(fan.height * k)), Image.LANCZOS)
    img.paste(fan, (int(1330 * s) - fan.width // 2, (h - fan.height) // 2), fan)
    return img


def hero_bundle(title: str, subtitle: str, shot_a: Image.Image, shot_b: Image.Image, pages: list[Image.Image], chips: list[str]) -> Image.Image:
    """Main image for the kit: two real spreadsheet windows overlapping, a fan of printed pages tucked under them."""
    img = ground()
    brand_strip(img, y=64)
    d = ImageDraw.Draw(img)
    y = headline(d, 205, title, 176, SAFE_R - SAFE_L + 200)
    y = centered(d, y + 12, subtitle, font(XBOLD, 54), CREAM, width=SAFE_R - SAFE_L + 160)
    chips_y = H - 100
    top, bottom = y + 40, chips_y - 80
    avail = bottom - top
    win_h = int(avail * 0.56)
    a, b = fit_window(shot_a, 1120, win_h), fit_window(shot_b, 1120, win_h)
    place(img, a, W // 2 - 320, top)
    place(img, b, W // 2 + 320, top + int(avail * 0.07))
    fan = paper_fan(pages, width=400)
    k = min(1.0, avail * 0.52 / fan.height, 1500 / fan.width)
    fan = fan.resize((int(fan.width * k), int(fan.height * k)), Image.LANCZOS)
    img.paste(fan, (W // 2 - fan.width // 2, bottom - fan.height), fan)
    widths = [d.textlength(t_.upper(), font=font(XBOLD, 40)) + 2 * 32 + 30 for t_ in chips]
    x = W // 2 - int(sum(widths) / 2) - 24 * (len(chips) - 1) // 2
    for t_, w_ in zip(chips, widths):
        chip(img, int(x + w_ / 2), chips_y, t_.upper(), size=40)
        x += w_ + 24
    return img


def bundle_inside(title: str, items: list[tuple[str, list[str], Image.Image, bool]], sub: str = "") -> Image.Image:
    """'What is in the kit': three tiles (two spreadsheet windows, one printed page), each named and described in three short lines."""
    img = ground(glow_at=(0.5, 0.5))
    d = ImageDraw.Draw(img)
    y = headline(d, 100, title, 130, SAFE_R - SAFE_L + 300, floor=90)
    if sub:
        y = centered(d, y + 6, sub, font(XBOLD, 48), CREAM, width=SAFE_R - SAFE_L + 200)
    gap = 50
    tw = int((W - 2 * 130 - gap * 2) / 3)
    top = y + 90
    tile_h = int(tw * 0.78)
    for i, (lab, lines, shot, is_paper) in enumerate(items):
        x = 130 + i * (tw + gap)
        card_h = tile_h + 70
        d.rounded_rectangle([x, top - 35, x + tw, top - 35 + card_h], radius=28, fill=(22, 20, 14), outline=(92, 78, 28), width=3)
        if is_paper:
            tile = paper(shot, int(tile_h * 0.74))
            tx, ty = x + (tw - tile.width) // 2, top - 35 + (card_h - tile.height) // 2
            drop_shadow(img, (tx, ty, tx + tile.width, ty + tile.height), blur=22, offset=14, alpha=190, radius=8)
            img.paste(tile, (tx, ty), tile)
        else:
            win = fit_window(shot, tw - 60, tile_h)
            wx, wy = x + (tw - win.width) // 2, top - 35 + (card_h - win.height) // 2
            drop_shadow(img, (wx, wy, wx + win.width, wy + win.height), blur=22, offset=14, alpha=190, radius=18)
            img.paste(win, (wx, wy), win)
        by = top + tile_h + 70
        nf = font(ANTON, 66)
        for ln in wrap(d, lab.upper(), nf, tw):
            d.text((x + tw // 2, by), ln, font=nf, fill=GOLD, anchor="ma")
            by = d.textbbox((x + tw // 2, by), ln, font=nf, anchor="ma")[3] + 8
        by += 22
        lf = font(XBOLD, 40)
        for line in lines:
            for ln in wrap(d, line, lf, tw - 20):
                d.text((x + tw // 2, by), ln, font=lf, fill=CREAM, anchor="ma")
                by += 54
            by += 14
    return img
