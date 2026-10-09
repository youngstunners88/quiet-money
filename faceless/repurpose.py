"""Repurposing kit: one finished video becomes a dozen native assets, with no extra model calls.

Per video (written next to the posting pack, in `<pack>/kit/`):
  thread.txt      X/Threads thread          linkedin.txt   LinkedIn post         newsletter.md  one newsletter item
  pin.png/.txt    Pinterest pin (1000x1500) carousel/NN.png  Instagram/LinkedIn carousel (1080x1350)
  audio.mp3       the audio edition (podcast clip), extracted from the video     KIT.md  where each file goes
`weekly_issue()` compiles the week's newsletter items into one issue. Everything is derived from the script JSON, so it
is deterministic, free and reproducible: `python -m faceless kit [day|job]`. Each file keeps the AI/education disclosure.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from faceless import brand, config
from faceless.config import Paths
from faceless.state import all_jobs

DISCLOSE = "Educational content, not financial advice. Narration and visuals are AI-assisted."
CAROUSEL = (1080, 1350)
PIN = (1000, 1500)
ACTION = re.compile(r"\b(this week|today|tonight|right now|tomorrow|open |set up|pick |list |call |cancel|check |write |turn on)", re.I)


def sentences(text: str) -> list[str]:
    """Whole sentences only: a trailing '...' is a spoken teaser or loop-back and reads as a fragment in text."""
    parts = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]
    return [s for s in parts if not s.endswith(("...", "…"))]


def is_cta(say: str) -> bool:
    return say.lower().startswith(("follow", "subscribe", "like and"))


def facts(script: dict) -> list[dict]:
    """The body beats in order: no hook beat, no follow-CTA. Each keeps its callout (the number worth a slide)."""
    return [b for b in script["beats"][1:] if b.get("say") and not is_cta(b["say"])]


def action_beat(script: dict) -> str:
    """The sentence that tells the viewer what to do; falls back to the last whole sentence of the body."""
    every = [s for b in facts(script) for s in sentences(b["say"])]
    for s in reversed(every):
        if ACTION.search(s):
            return s
    return every[-1] if every else ""


def the_number(script: dict) -> str:
    """The most striking number in the script: the largest numeric callout, with the sentence it sits in."""
    best, top = "", -1.0
    for b in facts(script):
        m = re.search(r"\d[\d,]*\.?\d*", b.get("callout", ""))
        if m:
            v = float(m.group().replace(",", "").rstrip(".") or 0)
            if v > top and (s := sentences(b["say"])):
                best, top = f"{b['callout'].title()}: {s[0]}", v
    return best


def paragraphs(script: dict, per: int = 2, limit: int = 4) -> list[str]:
    every = [s for b in facts(script) for s in sentences(b["say"])]
    return [" ".join(every[i:i + per]) for i in range(0, len(every), per)][:limit + 1]


def link(vid: str = "", source: str = "", medium: str = "", slug: str = "checklist") -> str:
    """The link in a repurposed asset. Where a link is tappable (a thread, a post, a pin, a newsletter) it is the hub page tagged with the
    asset and the video, so a click can be traced to this post; without those it is the plain bio link."""
    plain = config.load()["channel"].get("link_in_bio", "")
    if not (vid and source):
        return plain
    from faceless import offer
    return offer.tracked(offer.hub_url(), source, medium or "post", slug, content=vid, focus=slug) or plain


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def thread(script: dict, vid: str = "", slug: str = "checklist") -> str:
    """Tweet 1 is the hook; the body beats are packed two sentences at a time; the last tweet carries the link."""
    lines = [s for b in facts(script) for s in sentences(b["say"])]
    chunks, cur = [], ""
    for s in lines:
        if cur and len(cur) + len(s) + 1 > 250:
            chunks.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        chunks.append(cur)
    chunks = chunks[:6]
    n = len(chunks) + 2
    out = [f"1/{n} {_clip(script['title'], 120)}\n\n{_clip(script['hook_text'].capitalize(), 140)}"]
    out += [f"{i}/{n} {_clip(c, 270)}" for i, c in enumerate(chunks, 2)]
    out.append(f"{n}/{n} Free 7-day Money Reset (checklist + calculators): {link(vid, 'x', 'thread', slug)}\n\n{DISCLOSE}")
    return "\n\n---\n\n".join(out) + "\n"


def linkedin(script: dict, vid: str = "", slug: str = "checklist") -> str:
    post = [script["title"], "", script["hook_text"].capitalize() + ".", ""]
    for para in paragraphs(script):
        post += [para, ""]
    post += ["Try this: " + action_beat(script), "", script.get("first_comment") or "What would you change first?", "",
             f"Free checklist and calculators: {link(vid, 'linkedin', 'post', slug)}", "", DISCLOSE, "", " ".join(script.get("hashtags", [])[:3])]
    return _clip("\n".join(post), 2900) + "\n"


def newsletter_item(script: dict, meta: dict, vid: str = "", slug: str = "checklist") -> str:
    out = [f"### {script['title']}", "", script.get("description") or sentences(facts(script)[0]["say"])[0], ""]
    if num := the_number(script):
        out += [f"**The number** — {num}", ""]
    out += [f"**Try this:** {action_beat(script)}", "", f"*{meta.get('pillar', '')} series* · [Free 7-day Money Reset]({link(vid, 'newsletter', 'email', slug)})", ""]
    return "\n".join(out)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if cur and draw.textlength(t, font=font) > width:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + [cur] if cur else lines


def _backdrop(cover: Path | None, size: tuple[int, int], dim: float) -> Image.Image:
    if cover and cover.exists():
        im = Image.open(cover).convert("RGB")
        im = im.crop((0, int(im.height * 0.42), im.width, im.height))   # the cover's own title sits in the top part
        scale = max(size[0] / im.width, size[1] / im.height)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        left, top = (im.width - size[0]) // 2, (im.height - size[1]) // 2
        im = im.crop((left, top, left + size[0], top + size[1])).filter(ImageFilter.GaussianBlur(8))
        return ImageEnhance.Brightness(im).enhance(dim)
    return Image.new("RGB", size, brand.INK)


def _footer(d: ImageDraw.ImageDraw, size: tuple[int, int], left: str, right: str = "") -> None:
    f = brand.font("Montserrat-ExtraBold.ttf", 30)
    d.text((64, size[1] - 84), left, font=f, fill=brand.GOLD)
    if right:
        d.text((size[0] - 64 - d.textlength(right, font=f), size[1] - 84), right, font=f, fill=brand.MUTED)


def _slide(size, cover, big: str, small: str, tag: str, page: str, dim: float = 0.5) -> Image.Image:
    im = _backdrop(cover, size, dim)
    d = ImageDraw.Draw(im)
    bigf = brand.font("Anton-Regular.ttf", 150 if len(big) < 18 else 104)
    y = size[1] * 0.2
    for ln in _wrap(d, big.upper(), bigf, size[0] - 160)[:5]:
        d.text((80, y), ln, font=bigf, fill=brand.GOLD)
        y += bigf.size * 1.08
    if small:
        smf = brand.font("Montserrat-ExtraBold.ttf", 46)
        y += 40
        for ln in _wrap(d, small, smf, size[0] - 160)[:8]:
            d.text((80, y), ln, font=smf, fill=brand.CREAM)
            y += 66
    _footer(d, size, tag, page)
    return im


def carousel(script: dict, cover: Path | None, out: Path) -> int:
    """Hook slide, up to five body slides (numbers first, then the sequence), one CTA slide."""
    out.mkdir(parents=True, exist_ok=True)
    body = facts(script)
    keep = sorted(sorted(range(len(body)), key=lambda i: (not body[i].get("callout"), i))[:5])
    total = len(keep) + 2
    handle = config.load()["channel"]["handle"]
    slides = [_slide(CAROUSEL, cover, script["hook_text"], "", handle, f"1/{total}", 0.65)]
    for n, i in enumerate(keep, 2):
        b = body[i]
        slides.append(_slide(CAROUSEL, cover, b.get("callout") or sentences(b["say"])[0], b["say"] if b.get("callout") else "",
                             handle, f"{n}/{total}"))
    slides.append(_slide(CAROUSEL, None, "Do this week", action_beat(script), handle, f"{total}/{total}"))
    for n, im in enumerate(slides, 1):
        d = ImageDraw.Draw(im)
        if n == len(slides):
            small = brand.font("Montserrat-ExtraBold.ttf", 26)
            for k, ln in enumerate(_wrap(d, DISCLOSE, small, CAROUSEL[0] - 160)):
                d.text((80, CAROUSEL[1] - 190 + k * 36), ln, font=small, fill=brand.MUTED)
        im.save(out / f"{n:02d}.png", optimize=True)
    return len(slides)


def pin(script: dict, meta: dict, cover: Path | None, out: Path, vid: str = "", slug: str = "checklist") -> None:
    im = _slide(PIN, cover, script["hook_text"], "", config.load()["channel"]["handle"], "money rules", 0.65)
    im.save(out / "pin.png", optimize=True)
    (out / "pin.txt").write_text(
        f"Title: {_clip(script['title'], 100)}\nLink: {link(vid, 'pinterest', 'pin', slug)}\n\n{_clip(meta.get('description', '').split(chr(10) + chr(10))[0], 480)}\n\n"
        f"{DISCLOSE}\n", encoding="utf-8")


def audio(video: Path, out: Path) -> bool:
    """The audio edition: voice + bed at the video's loudness, mono 64 kbps (podcast-ready). False if ffmpeg or the video is missing."""
    if not video.exists() or not shutil.which("ffmpeg"):
        return False
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k",
                        str(out)], capture_output=True, timeout=120, check=False)
    return r.returncode == 0 and out.exists()


GUIDE = """# Repurposing kit
Everything here comes from the same script as the video. Post natively; do not cross-post the raw file.

| file | where | note |
|---|---|---|
| thread.txt | X / Threads | tweets separated by `---`; post as a reply chain |
| linkedin.txt | LinkedIn | text post; attach carousel/ as a document if you want swipe format |
| carousel/NN.png | Instagram / LinkedIn / TikTok photo mode | 4:5, upload in order, caption = POST.md caption |
| pin.png + pin.txt | Pinterest | link goes to the free Money Reset page |
| newsletter.md | newsletter | the weekly issue compiles these (`python -m faceless kit --issue`) |
| audio.mp3 | podcast host (audio edition) | 60-second clip; the weekly episode stitches the week |

Turn each platform's AI-generated-content label on. Every file carries the education/AI disclosure.
"""


def build_pack(job, folder: Path) -> dict:
    """Write the kit for one job into `folder/kit`. Returns what was made."""
    scr_path = Paths.final / f"{job.id}.json"
    script = json.loads(scr_path.read_text(encoding="utf-8"))
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
    kit = folder / "kit"
    kit.mkdir(parents=True, exist_ok=True)
    cover = folder / "cover.jpg"
    made = {}
    slug = (meta.get("offer") or {}).get("slug", "checklist")
    (kit / "thread.txt").write_text(thread(script, job.id, slug), encoding="utf-8")
    (kit / "linkedin.txt").write_text(linkedin(script, job.id, slug), encoding="utf-8")
    (kit / "newsletter.md").write_text(newsletter_item(script, meta, job.id, slug), encoding="utf-8")
    pin(script, meta, cover, kit, job.id, slug)
    made["carousel"] = carousel(script, cover, kit / "carousel")
    made["audio"] = audio(folder / "video.mp4", kit / "audio.mp3")
    (kit / "KIT.md").write_text(GUIDE, encoding="utf-8")
    made["files"] = sorted(p.name for p in kit.iterdir())
    return made


def build(selector: str | None = None) -> list[dict]:
    """Kits for every packaged/published job matching a day (YYYY-MM-DD, by post day) or a job id; default: today's queue."""
    want = selector or config.today_utc().isoformat()
    out = []
    for j in all_jobs():
        local = (j.artifacts.get("publish") or {}).get("local") or {}
        folder = Path(local["folder"]) if local.get("folder") else None
        if j.status not in ("packaged", "published") or not folder or not folder.exists():
            continue
        if want not in (j.id, folder.parent.name, j.day):
            continue
        try:
            out.append({"job": j.id, "folder": str(folder), **build_pack(j, folder)})
        except (OSError, KeyError, json.JSONDecodeError, IndexError) as e:
            out.append({"job": j.id, "error": f"{type(e).__name__}: {e}"})
    return out


def weekly_issue(end: str | None = None, days: int = 7) -> Path | None:
    """Compile the newsletter items of the last `days` post days into one issue under channel/newsletter/."""
    last = date.fromisoformat(end) if end else config.today_utc()
    first = last - timedelta(days=days - 1)
    items = []
    for folder in sorted(Paths.queue.glob("*/slot*/kit/newsletter.md")):
        day = folder.parents[2].name
        try:
            if first <= date.fromisoformat(day) <= last:
                items.append(folder.read_text(encoding="utf-8"))
        except ValueError:
            continue
    if not items:
        return None
    cfg = config.load().get("newsletter", {})
    addr = cfg.get("postal_address", "")
    head = [f"# Quiet Money Weekly: {first:%b %d} to {last:%b %d}", "", "Seven days of money rules, in one read. One number and one action per item.", ""]
    foot = ["---", DISCLOSE, ""]
    if addr:
        foot.append(f"You are getting this because you joined the free Money Reset. {addr}. Unsubscribe: {{{{unsubscribe_url}}}}")
    else:
        foot.append("> NOT SENDABLE YET: set `[newsletter] postal_address` in studio.toml and send through a service that adds the "
                    "unsubscribe link (the law requires both).")
    out = Paths.root / "channel" / "newsletter" / f"{last.isocalendar().year}-W{last.isocalendar().week:02d}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(head + items + foot), encoding="utf-8")
    return out
