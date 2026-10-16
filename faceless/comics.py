"""Stick-figure comic posts: the secondary series for the image-post feeds (YouTube Community tab, Instagram and Facebook posts, X), five a day.

One Claude Opus 5.5 call (OpenRouter) draws a batch of comics as SVG and writes each one's caption; our code adds the brand frame and renders to PNG with the
Chromium already installed. Drawing in SVG means every word on the picture is spelled right (image models misspell), and the look is one hand-drawn marker style.
The first comic of a run can be a recreation of a reference picture the owner supplies: Opus looks at it (multimodal) and redraws the gag in our frame.
Layout: wordmark header, the comic, the handle footer. The caption is written to be read AFTER the picture: it must not repeat the picture's words.
Posting: the YouTube API has no Community-post call, so packs are delivered to the owner (and to any image-post connector that exists later).
Skill: .claude/skills/faceless-comics.
"""

from __future__ import annotations

import base64
import glob
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from faceless import config, ledger, safety
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic
from faceless.providers import ProviderError, ProviderUnavailable, http

MODEL = "anthropic/claude-opus-5.5"
CAP_USD = 1.00
W, H, ART_H = 1080, 1350, 1100
LEDGER = Paths.state / "comics.jsonl"
OUT = Paths.root / "distribution" / "comics"
GOLD = "#FFD23F"
TAGS = {"g", "path", "line", "circle", "ellipse", "rect", "polygon", "polyline", "text", "tspan"}
ATTRS = {"d", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "width", "height", "points", "fill", "stroke", "stroke-width", "stroke-linecap",
         "stroke-linejoin", "transform", "font-size", "text-anchor", "dy", "dx", "opacity", "font-weight", "letter-spacing", "fill-opacity"}

SYSTEM = f"""You are the cartoonist for Quiet Money, a channel about money psychology and personal finance for 18-40 year olds who feel behind with money.
You draw funny black-and-white stick-figure comics in ONE hand-drawn marker style and write each comic's post caption. Return ONLY JSON: {{"comics": [ ... ]}} where each comic is
{{"slug": "kebab-case", "title": "short", "joke": "one line: the gag in plain words", "svg": "...", "caption": "...", "alt": "one sentence describing the picture", "hashtags": ["#a", ...]}}.

SVG rules (the "svg" value is the INNER markup only, no <svg> tag): the canvas is {W} x {ART_H}, transparent, drawn on white. Use only g, path, line, circle, ellipse, rect, polygon,
polyline, text, tspan. Colours: black strokes (stroke-width 5-7, round caps and joins), white fills, and the brand gold {GOLD} ONLY as a highlight rectangle behind the punchline words.
Stick figures: round head, line body, line limbs, simple props (helmet, hat, briefcase, coin, bench, sign, laptop). Give them faces with two dots and a mouth line; show feeling with the
mouth, brows and a "?" or "!". Text: UPPERCASE, font-size 46-58, text-anchor middle, at most 4 lines per block, wrap by hand with tspans (dy 62), every word spelled correctly, no word
cut by the edge: keep all text inside x 60..1020. Signs are a rect with white fill and a black border; speech bubbles are a rounded path with a tail. Leave breathing room; nothing outside the canvas.
Each comic: ONE scene, two characters at most, a visible visual gag, and a short punchline in a sign, a speech bubble or both.

Humour: dry, observational, kind; the joke lands on a money habit or a money myth (saving, spending, debt, compounding, subscriptions, budgets, "I'll start next month"), or on a pun.
Never mock people for being poor; never give advice to buy or invest; no promised returns; no real person named except a hedged "attributed to" quote the owner supplied.

Caption (the reader reads it AFTER the picture, so do NOT repeat the picture's words): 2-4 short lines, max 260 characters. Line 1 a curious or funny reaction that makes them look back at the picture;
then a one-line true money insight that explains why the joke works; end with a question that invites a comment. No links, no hashtags inside the caption, no income claims. Hashtags: 4 to 6, relevant.
Every comic in a batch must be a different scene and a different joke from the others and from the ALREADY MADE list."""


def made() -> list[str]:
    return [r.get("joke", r.get("title", "")) for r in read_jsonl(LEDGER)][-120:]


def clean_svg(markup: str) -> str:
    """Only drawing elements and attributes survive: nothing from the model reaches the page as script, link, image or style (rule 14)."""
    try:
        root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{markup}</svg>')
    except ET.ParseError as e:
        raise ValueError(f"svg does not parse: {e}")
    out = []

    def walk(el):
        tag = el.tag.split("}")[-1]
        if tag not in TAGS:
            raise ValueError(f"svg element not allowed: {tag}")
        attrs = {k: v for k, v in el.attrib.items() if k in ATTRS}
        for k, v in attrs.items():
            if re.search(r"url\(|javascript|<|&", v, re.I):
                raise ValueError(f"svg attribute not allowed: {k}")
        a = "".join(f' {k}="{v}"' for k, v in attrs.items())
        text = (el.text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out.append(f"<{tag}{a}>{text}")
        for c in el:
            walk(c)
            tail = (c.tail or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            out.append(tail)
        out.append(f"</{tag}>")

    for child in root:
        walk(child)
        out.append((child.tail or "").strip())
    return "".join(out)


def frame_html(svg_inner: str) -> str:
    fonts = Paths.fonts
    return f"""<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Bebas;src:url('file://{fonts}/BebasNeue-Regular.ttf')}}
@font-face{{font-family:Mont;src:url('file://{fonts}/Montserrat-ExtraBold.ttf')}}
html,body{{margin:0;background:#fff}} .page{{width:{W}px;height:{H}px;position:relative;background:#fff;overflow:hidden}}
.head{{height:96px;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.wm{{font:800 34px Mont;letter-spacing:11px;color:#111}} .rule{{width:140px;height:5px;background:{GOLD};margin-top:12px}}
svg{{display:block}} svg text{{font-family:Bebas,Impact,sans-serif;font-weight:400;fill:#111;stroke:none}}
.foot{{position:absolute;left:0;right:0;bottom:0;height:150px;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.h{{font:800 30px Mont;letter-spacing:5px;color:#111}} .s{{font:800 20px Mont;letter-spacing:3px;color:#777;margin-top:8px}}
</style><div class="page"><div class="head"><div class="wm">QUIET MONEY</div><div class="rule"></div></div>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{ART_H}" viewBox="0 0 {W} {ART_H}">
<defs><filter id="w" x="-2%" y="-2%" width="104%" height="104%"><feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="6"/></filter></defs>
<g filter="url(#w)">{svg_inner}</g></svg>
<div class="foot"><div class="h">@QUIETMONEYRULE</div><div class="s">MONEY RULES, DRAWN BADLY ON PURPOSE</div></div></div>"""


def chrome() -> str:
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    if not found:
        raise ProviderUnavailable("no Chromium found for rendering")
    return found[-1]


def render(svg_inner: str, out_png: Path) -> Path:
    out_png = Path(out_png).resolve()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    html = out_png.with_suffix(".html")
    write_atomic(html, frame_html(clean_svg(svg_inner)))
    subprocess.run([chrome(), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{H+150}", "--force-device-scale-factor=1",
                    "--virtual-time-budget=4000", f"--screenshot={out_png}", f"file://{html}"], capture_output=True, timeout=90, check=True)
    html.unlink(missing_ok=True)
    from PIL import Image
    with Image.open(out_png) as im:                      # headless chrome's viewport is shorter than the window: render tall, crop to the page
        im.crop((0, 0, W, H)).save(out_png)
    return out_png


def ask(n: int, reference: Path | None = None, theme: str = "") -> tuple[list[dict], float]:
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    safety.guard("comics batch", 0.4)
    if not ledger.allow("comics", "usd", 0.4, CAP_USD):
        raise ProviderUnavailable(f"comics daily cap ${CAP_USD:.2f} reached")
    text = (f"Draw {n} comics. ALREADY MADE (never repeat any of these jokes or scenes):\n" + "\n".join(f"- {j}" for j in made()) + "\n"
            + (f"Theme for this batch: {theme}\n" if theme else ""))
    content: list = [{"type": "text", "text": text}]
    if reference:
        from PIL import Image
        import io
        im = Image.open(reference).convert("RGB")
        im.thumbnail((900, 1600))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        content[0]["text"] += ("Comic 1 MUST recreate the gag of the attached reference picture in our style and frame: same joke, same two-character setup, redrawn as clean SVG stick figures "
                               "(the reference's sign text and speech-bubble text stay as in the picture, spelled exactly). Comics 2 onward are NEW money jokes.\n")
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}})
    body = {"model": MODEL, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}], "response_format": {"type": "json_object"},
            "max_tokens": 20000, "usage": {"include": True}, "reasoning": {"effort": "low"}}
    r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=420, headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        raise ProviderError(f"openrouter {r.status_code}")
    d = r.json()
    cost = float((d.get("usage") or {}).get("cost") or 0)
    ledger.spend("comics", "usd", cost, usd=cost)
    from faceless.providers.llm import _extract_json
    data = _extract_json(d["choices"][0]["message"]["content"])
    return (data.get("comics") if isinstance(data, dict) else data) or [], cost


def caption_problems(c: dict) -> list[str]:
    from faceless import offer
    cap = str(c.get("caption", ""))
    out = []
    if not 40 <= len(cap) <= 300:
        out.append(f"caption is {len(cap)} characters")
    if re.search(r"https?://|www\.", cap):
        out.append("link in the caption")
    out += [f"claim: {v}" for v in offer.violations(cap)]
    return out


def build(day: str | None = None, n: int = 5, reference: Path | None = None, theme: str = "") -> dict:
    """Draw, check and render a day's comics into distribution/comics/<day>/NN-slug/ (picture.png, POST.md, comic.json) and log them."""
    day = day or config.today_utc().isoformat()
    comics, cost = ask(n, reference, theme)
    folder = OUT / day
    start = len([p for p in folder.glob("*/comic.json")]) if folder.exists() else 0
    made_now, problems = [], []
    for c in comics[:n]:
        slug = re.sub(r"[^a-z0-9]+", "-", str(c.get("slug") or c.get("title", "comic")).lower()).strip("-")[:40] or "comic"
        d = folder / f"{start + len(made_now) + 1:02d}-{slug}"
        bad = caption_problems(c)
        try:
            render(str(c.get("svg", "")), d / "picture.png")
        except (ValueError, subprocess.SubprocessError, OSError) as e:
            bad.append(f"render: {str(e)[:120]}")
        if bad:
            problems.append(f"{slug}: {'; '.join(bad)}")
            continue
        tags = " ".join(t if t.startswith("#") else f"#{t}" for t in (c.get("hashtags") or [])[:6])
        post = (f"{c['caption'].strip()}\n\n{tags}\n\nIllustrated with AI. Education and humour, not financial advice.")
        write_atomic(d / "POST.md", f"# {c.get('title', slug)}\n\n## Caption (paste with the picture)\n```\n{post}\n```\n\n## Alt text\n{c.get('alt', '')}\n\n## The joke\n{c.get('joke', '')}\n")
        write_atomic(d / "comic.json", json.dumps({k: v for k, v in c.items() if k != "svg"} | {"post": post, "day": day}, indent=1, ensure_ascii=False))
        write_atomic(d / "comic.svg.txt", str(c["svg"]))
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": day, "slug": slug, "title": c.get("title", ""), "joke": c.get("joke", "")}, ensure_ascii=False) + "\n")
        made_now.append(str(d))
    return {"day": day, "made": len(made_now), "wanted": n, "folders": made_now, "problems": problems, "usd": round(cost, 4)}
