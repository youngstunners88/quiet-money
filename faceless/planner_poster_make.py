"""Typeset wellness posters for weeks 41 to 52, in the look of the owner's "DID YOU KNOW" posters.

The owner made 44 posters; 4 repeat another, which fills weeks 1 to 40. Weeks 41 to 52 need twelve more. They are made here, never as AI-drawn lettering (image models misspell):
  - the scene (white framed poster on the colour-block wall, no text) and the twelve illustrations come from Muapi, once, and are kept in assets/planner/wellness/made/;
  - the owner's own light bulb is lifted from poster 1;
  - every letter is typeset in code (Montserrat Black, Anton, Carlito), so the words are exactly the words written below.

    python -m faceless planner posters-make        # rebuild assets/planner/wellness/cropped/wellness-045..056.jpg

The facts are hedged on purpose ("can", "tends to") and make no clinical or quantified claim; the planner page adds the not-medical-advice note (planner_wellness.NOT_MEDICAL).
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from faceless import brand, planner_posters
from faceless.config import STUDIO

MADE = STUDIO / "assets" / "planner" / "wellness" / "made"
# the white frame's inside, as fractions of the scene (left, top, right, bottom)
FRAME = (0.075, 0.100, 0.925, 0.915)

# position -> (bold title, plain fact). Positions 45 to 56 are weeks 41 to 52.
TEXT: dict[int, tuple[str, str]] = {
    45: ("A SHORT NIGHT CAN MAKE IMPULSE BUYS HARDER TO RESIST!",
         "When you are short of sleep, self-control and judgment tend to slip. Tired people often find it harder to say no to a quick treat."),
    46: ("SHOPPING HUNGRY MAY LEAD TO A BIGGER BASKET!",
         "Studies of shoppers suggest that going to the shops hungry can lead people to buy more than they planned. Eat first, then shop with a list."),
    47: ("NAMING WHAT YOU ARE GRATEFUL FOR CAN LIFT YOUR MOOD!",
         "Writing down a few things that went well, even small ones, is a simple habit that many people find helps them feel more settled."),
    48: ("COMPARING YOURSELF TO OTHERS CAN MAKE YOU FEEL BEHIND!",
         "Online, people mostly show their best moments. Comparing your real life with their highlights can nudge you to spend just to keep up."),
    49: ("AN HOUR WITHOUT NOTIFICATIONS CAN HELP YOU FOCUS!",
         "Phone alerts pull your attention away from what you are doing. A quiet hour gives your mind room to think things through."),
    50: ("SHORT STRETCH BREAKS CAN HELP YOU FEEL LESS STIFF!",
         "Standing up and moving for a few minutes after a long time sitting is a free way to feel better and clear your head."),
    51: ("PLANNING MEALS CAN HELP YOU WASTE LESS FOOD!",
         "Knowing what you will eat this week makes it easier to shop with a list and to use up what you already have at home."),
    52: ("WALKING WITH A FRIEND CAN MAKE MOVING MORE ENJOYABLE!",
         "Company can make exercise feel easier, and a walk is a free way to catch up. Time with people you like costs very little."),
    53: ("WRITING YOUR WORRIES DOWN CAN HELP YOU SORT THEM OUT!",
         "Putting a worry on paper can make it feel more manageable. It is a good first step before you look at the numbers."),
    54: ("A PAUSE BEFORE A PURCHASE GIVES YOU TIME TO THINK!",
         "Waiting a day before buying something unplanned lets the urge fade. If you still want it tomorrow, you can decide calmly."),
    55: ("GIVING TO OTHERS CAN FEEL SURPRISINGLY GOOD!",
         "Some research suggests that spending a little on other people can feel more rewarding than spending on yourself. Generosity can fit any budget."),
    56: ("REST IS PART OF THE PLAN!",
         "Taking time to rest helps you think clearly and avoid burnout. A calm mind tends to make better money decisions than a rushed one."),
}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(brand.Paths.fonts / name), size)


def _wrap(d: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if cur and d.textlength(t, font=font) > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + [cur] if cur else lines


def _fit(d, text: str, name: str, width: int, start: int, floor: int, max_lines: int):
    for size in range(start, floor - 1, -2):
        f = _font(name, size)
        lines = _wrap(d, text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    raise ValueError(f"text does not fit in {max_lines} lines at {floor}px: {text[:40]}")


def _crop_to_content(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("L"))
    ys, xs = np.nonzero(a < 200)
    if not len(ys):
        return im
    pad = 6
    return im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + pad), min(im.height, ys.max() + pad)))


def _white_ground(im: Image.Image, start: float = 222.0) -> Image.Image:
    """Push the near-white ground of an illustration to pure white so it multiplies away on the poster."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    lift = np.clip((a.min(axis=2, keepdims=True) - start) / 16.0, 0, 1)          # only pixels that are nearly white on every channel
    return Image.fromarray((a + (255.0 - a) * lift).astype(np.uint8))


def _multiply(base: Image.Image, top: Image.Image, xy: tuple[int, int]) -> None:
    box = (xy[0], xy[1], xy[0] + top.width, xy[1] + top.height)
    region = np.asarray(base.crop(box)).astype(np.float32)
    layer = np.asarray(top.convert("RGB")).astype(np.float32)
    base.paste(Image.fromarray((region * layer / 255.0).astype(np.uint8)), box[:2])


def compose(pos: int) -> Image.Image:
    title, fact = TEXT[pos]
    scene = Image.open(MADE / "scene.jpg").convert("RGB")
    W, H = scene.size
    x0, y0, x1, y1 = (int(FRAME[0] * W), int(FRAME[1] * H), int(FRAME[2] * W), int(FRAME[3] * H))
    cx, inner = (x0 + x1) // 2, (x1 - x0) - 60
    d = ImageDraw.Draw(scene)
    ink = (14, 14, 14)

    hf = _font("Montserrat-Black.ttf", 64)
    while d.textlength("DID YOU KNOW:", font=hf) > inner and hf.size > 30:
        hf = _font("Montserrat-Black.ttf", hf.size - 2)
    y = y0 + 38
    d.text((cx, y), "DID YOU KNOW:", font=hf, fill=ink, anchor="ma")
    y += int(hf.size * 1.25)

    bulb = _white_ground(Image.open(MADE / "bulb.png").convert("RGB"), 205.0)
    bh = int(H * 0.15)
    bulb = bulb.resize((int(bulb.width * bh / bulb.height), bh), Image.LANCZOS)
    _multiply(scene, bulb, (cx - bulb.width // 2, y))
    y += bh + 14

    tf, tl = _fit(d, title, "Anton-Regular.ttf", inner, 50, 30, 3)
    for ln in tl:
        d.text((cx, y), ln, font=tf, fill=ink, anchor="ma")
        y += int(tf.size * 1.12)
    y += 10
    bf, bl = _fit(d, fact, "Carlito-Regular.ttf", inner, 33, 22, 6)
    for ln in bl:
        d.text((cx, y), ln, font=bf, fill=ink, anchor="ma")
        y += int(bf.size * 1.18)

    ill = _crop_to_content(_white_ground(Image.open(MADE / "illustrations" / f"{pos}.jpg")))
    room = y1 - 24 - (y + 14)
    if room < 120:
        raise ValueError(f"poster {pos}: no room left for the picture ({room}px)")
    s = min(room / ill.height, inner * 0.85 / ill.width, 1.6)
    ill = ill.resize((int(ill.width * s), int(ill.height * s)), Image.LANCZOS)
    _multiply(scene, ill, (cx - ill.width // 2, y1 - 24 - ill.height))
    return scene


def make(positions: list[int] | None = None) -> list[int]:
    done = []
    for pos in positions or sorted(TEXT):
        buf = io.BytesIO()
        compose(pos).save(buf, "JPEG", quality=90, optimize=True)
        planner_posters._write(planner_posters.CROPPED / f"wellness-{pos:03d}.jpg", buf.getvalue())
        done.append(pos)
    return done
