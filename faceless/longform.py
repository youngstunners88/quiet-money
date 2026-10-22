"""The weekly long-form (C3): "Money Rules Weekly", the week's best Shorts re-cut into one 16:9 episode with chapters.

Shorts earn little and do not count toward the Partner Program's watch hours; a landscape episode does. The stories are the
week's passed Shorts, ranked by the views they measured (`analytics/metrics.jsonl`, latest reading per platform, summed), up
to seven. Renders are not kept between sessions, so each story is voiced fresh from its committed final script through the
same voice chain as the podcast (one call per story; the voice's word timings put each card on screen while its line is spoken), and
drawn as brand cards in code: an intro, a chapter card per story, one card per beat with its callout, and an outro with the
disclaimer and the AI disclosure (rules 2 and 4). No generated pictures, so no image spend.

Beside `episode.mp4` it writes `thumbnail.jpg` (1280x720), `EPISODE.md` (title, description with the chapters and the one
tracked hub link, rule 13) and `episode.json`. Uploading is the owner's step until they say yes (rule 9 covers Shorts only).

`python -m faceless longform build [--week YYYY-MM-DD] [--max 7]`, `longform status`.
"""

from __future__ import annotations

import json
import re
import tempfile
import textwrap
from datetime import timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from faceless import config
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic

OUT = Paths.root / "distribution" / "longform"
SIZE = (1920, 1080)
FPS = 30
MAX_STORIES = 7
MIN_STORIES = 3                   # YouTube shows chapters only with at least three
GAPS = {"intro": 0.9, "chapter": 0.5, "beat": 0.3, "last": 0.9, "outro": 1.5}
SHOW = "Money Rules Weekly"


# ---------------------------------------------------------------- which stories

def views() -> dict[str, int]:
    """Views per job: the latest reading of each platform, summed."""
    latest: dict[tuple[str, str], dict] = {}
    for r in read_jsonl(Paths.root / "analytics" / "metrics.jsonl"):
        key = (str(r.get("job", "")), str(r.get("platform", "")))
        if key[0] and str(r.get("date", "")) >= str(latest.get(key, {}).get("date", "")):
            latest[key] = r
    out: dict[str, int] = {}
    for (job, _), r in latest.items():
        try:
            out[job] = out.get(job, 0) + int(r.get("views") or 0)
        except (TypeError, ValueError):
            continue
    return out


def stories(end: str, most: int = MAX_STORIES) -> list[dict]:
    """The week's passed Shorts with a final script, most viewed first (oldest first on a tie): {job, day, title, views, beats}."""
    from faceless import podcast
    seen = views()
    out = []
    for it in podcast.week_items(end):
        try:
            s = json.loads((Paths.final / f"{it['job']}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        beats = [{"say": str(b.get("say", "")).strip(), "callout": str(b.get("callout") or "").strip()}
                 for b in s.get("beats") or [] if isinstance(b, dict) and str(b.get("say", "")).strip()]
        if beats:
            out.append({**{k: it[k] for k in ("job", "day", "title")}, "views": seen.get(it["job"], 0), "beats": beats})
    out.sort(key=lambda x: -x["views"])                # stable: equal views keep the oldest first
    return out[:most]


def segments(items: list[dict], end: str) -> list[dict]:
    """What is spoken and shown, in order: {kind, text, chapter (1-based or 0), callout}."""
    from faceless import podcast
    first = podcast.week_days(end)[0]
    out = [{"kind": "intro", "chapter": 0, "text": f"This is {SHOW} from Quiet Money. The {len(items)} money rules that landed hardest "
            f"this week, from {podcast._spoken(first)} to {podcast._spoken(end)}. Let's go."}]
    for n, it in enumerate(items, 1):
        out.append({"kind": "chapter", "chapter": n, "text": f"Number {n}. {it['title']}.", "job": it["job"], "title": it["title"]})
        for i, b in enumerate(it["beats"]):
            out.append({"kind": "last" if i == len(it["beats"]) - 1 else "beat", "chapter": n, "text": b["say"], "callout": b["callout"]})
    out.append({"kind": "outro", "chapter": 0, "text": f"That's the week. One new money rule every day on Quiet Money. Subscribe so "
                f"next week's episode finds you. {podcast.DISCLAIMER} {podcast.AI_NOTE}"})
    return out


# ---------------------------------------------------------------- cards

def _fit(d: ImageDraw.ImageDraw, text: str, name: str, size: int, width: int, lines: int):
    """The largest font (down from `size`) at which `text` wraps into at most `lines` lines no wider than `width`."""
    from faceless import brand
    while True:
        f = brand.font(name, size)
        per = max(8, int(width / (f.getlength("n") or 1)))
        wrapped = textwrap.wrap(text, per)
        while wrapped and max(d.textlength(w, font=f) for w in wrapped) > width and per > 8:
            per -= 1
            wrapped = textwrap.wrap(text, per)
        if len(wrapped) <= lines or size <= 36:
            return f, wrapped
        size -= 6


def _centered(d, lines: list[str], f, cy: float, fill, lead: float = 1.18) -> None:
    h = f.size * lead
    y = cy - h * len(lines) / 2
    for ln in lines:
        d.text((SIZE[0] / 2, y + h / 2), ln, font=f, fill=fill, anchor="mm")
        y += h


def _base(chapter: int, total: int) -> Image.Image:
    """Ink with a soft light from above, the mark and show name, and chapter progress along the bottom."""
    from faceless import brand
    w, h = SIZE
    im = Image.new("RGB", SIZE, brand.INK)
    glow = Image.new("L", (w // 8, h // 8), 0)
    ImageDraw.Draw(glow).ellipse([w // 8 * 0.15, -h // 8 * 0.6, w // 8 * 0.85, h // 8 * 0.7], fill=46)
    from PIL import ImageFilter
    glow = glow.filter(ImageFilter.GaussianBlur(9)).resize(SIZE, Image.BICUBIC)
    im = Image.composite(Image.new("RGB", SIZE, (40, 36, 26)), im, glow)
    im.paste(c := brand.coin(64), (72, 56), c)
    d = ImageDraw.Draw(im)
    d.text((152, 88), "QUIET MONEY  ·  " + SHOW.upper(), font=brand.font("Montserrat-ExtraBold.ttf", 26), fill=brand.MUTED, anchor="lm")
    if chapter:
        d.text((w - 72, 88), f"{chapter:02d} / {total:02d}", font=brand.font("Montserrat-ExtraBold.ttf", 30), fill=brand.GOLD, anchor="rm")
    if total:
        gap, left, right, y = 10, 72, w - 72, h - 52
        seg = (right - left - gap * (total - 1)) / total
        for i in range(total):
            x = left + i * (seg + gap)
            d.rounded_rectangle([x, y, x + seg, y + 8], radius=4, fill=brand.GOLD if i < chapter else (52, 50, 46))
    return im


def card(seg: dict, total: int, items: list[dict], end: str) -> Image.Image:
    from faceless import brand, podcast
    im = _base(seg["chapter"], total)
    d = ImageDraw.Draw(im)
    w, h = SIZE
    kind = seg["kind"]
    if kind == "intro":
        mark = brand.coin(220)
        im.paste(mark, ((w - 220) // 2, 230), mark)
        f, lines = _fit(d, SHOW.upper(), "Anton-Regular.ttf", 150, 1600, 1)
        _centered(d, lines, f, 590, brand.CREAM)
        sub = f"The week's {len(items)} best money rules  ·  {podcast._spoken(podcast.week_days(end)[0])} to {podcast._spoken(end)}"
        d.text((w / 2, 720), sub, font=brand.font("Montserrat-ExtraBold.ttf", 40), fill=brand.GOLD, anchor="mm")
    elif kind == "chapter":
        d.text((w / 2, 340), f"{seg['chapter']:02d}", font=brand.font("Anton-Regular.ttf", 280), fill=brand.GOLD, anchor="mm")
        f, lines = _fit(d, seg["title"], "Montserrat-Black.ttf", 96, 1560, 3)
        _centered(d, lines, f, 660, brand.CREAM)
    elif kind == "outro":
        f, lines = _fit(d, "One new money rule every day.", "Anton-Regular.ttf", 130, 1600, 1)
        _centered(d, lines, f, 400, brand.CREAM)
        d.text((w / 2, 560), "Subscribe so next week's episode finds you.", font=brand.font("Montserrat-ExtraBold.ttf", 44), fill=brand.GOLD, anchor="mm")
        small = brand.font("Carlito-Regular.ttf", 34)
        d.text((w / 2, 820), podcast.DISCLAIMER, font=small, fill=brand.MUTED, anchor="mm")
        d.text((w / 2, 870), podcast.AI_NOTE, font=small, fill=brand.MUTED, anchor="mm")
    else:
        top = 540
        if seg.get("callout"):
            fc, cl = _fit(d, seg["callout"].upper(), "Anton-Regular.ttf", 170, 1600, 1)
            _centered(d, cl, fc, 330, brand.GOLD)
            top = 640
        f, lines = _fit(d, seg["text"], "Montserrat-ExtraBold.ttf", 76 if seg.get("callout") else 84, 1560, 4 if seg.get("callout") else 6)
        _centered(d, lines, f, top, brand.CREAM, lead=1.24)
    return im


def thumbnail(items: list[dict]) -> Image.Image:
    """1280x720: the count big, the top story's title under it."""
    from faceless import brand
    im = _base(0, 0).resize((1280, 720), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.text((640, 250), f"{len(items)} MONEY RULES", font=brand.font("Anton-Regular.ttf", 150), fill=brand.GOLD, anchor="mm")
    f, lines = _fit(d, items[0]["title"], "Montserrat-Black.ttf", 64, 1100, 2)
    h = f.size * 1.15
    y = 470 - h * len(lines) / 2
    for ln in lines:
        d.text((640, y + h / 2), ln, font=f, fill=brand.CREAM, anchor="mm")
        y += h
    return im


# ---------------------------------------------------------------- build

def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def units(segs: list[dict]) -> list[list[dict]]:
    """The voice calls: the intro, one per story (its chapter line and every beat in one breath), the outro. Few long calls,
    because the free voice drops about one short call in nine under load."""
    out: list[list[dict]] = []
    for seg in segs:
        if seg["kind"] in ("beat", "last"):
            out[-1].append(seg)
        else:
            out.append([seg])
    return out


def cue_times(cards: list[dict], words: list[dict], seconds: float) -> list[float]:
    """When each card's line starts inside one voiced unit. The voice's word timings are matched to the text in order (a word
    spoken differently from how it is written, like a number, is skipped); without timings, time follows the characters."""
    joined, starts = "", []
    for c in cards:
        starts.append(len(joined))
        joined += _norm(c["text"])
    marks, cursor = [], 0                                     # (character offset, time) of each word found in the text
    for w in words or []:
        token = _norm(str(w.get("w", "")))
        at = joined.find(token, cursor) if token else -1
        if at >= 0 and at - cursor < 40:
            marks.append((at, float(w.get("start", 0))))
            cursor = at + len(token)
    out = []
    for off in starts:
        hit = next((t for at, t in marks if at >= off), None)
        out.append(hit if hit is not None and off else seconds * off / max(1, len(joined)))
    out[0] = 0.0
    for i in range(1, len(out)):                              # never backwards, and every card stays up a moment
        out[i] = min(max(out[i], out[i - 1] + 0.4), seconds)
    return out


def build(end: str | None = None, *, most: int = MAX_STORIES, music: bool = True, synth=None) -> dict:
    """Voice, draw, cut and encode the episode. `synth(text, wav_path)` is the voice chain; a test passes its own."""
    from faceless import podcast
    from faceless.providers import tts
    end = end or (config.today_utc() - timedelta(days=1)).isoformat()
    items = stories(end, most)
    if len(items) < MIN_STORIES:
        return {"week": end, "items": len(items), "file": None, "reason": f"{len(items)} passed Shorts with a script that week; chapters need {MIN_STORIES}"}
    synth = synth or (lambda text, wav: tts.synthesize(text, wav, job=f"longform-{end}"))
    folder = OUT / end
    folder.mkdir(parents=True, exist_ok=True)
    segs = segments(items, end)
    groups = units(segs)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        words: dict[int, list] = {}
        wavs = podcast.voice_all([" ".join(c["text"] for c in g) for g in groups], tmp, synth, words)
        audio_parts, frames, at = [], [], 0.0
        for gi, (group, wav) in enumerate(zip(groups, wavs)):
            spoken = tts.duration(wav)
            pause = GAPS[group[-1]["kind"]]
            gap = tmp / f"gap{gi}.wav"
            podcast._ff("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(pause), "-ar", "24000", "-ac", "1", str(gap))
            audio_parts += [wav, gap]
            cues = cue_times(group, words.get(gi, []), spoken) + [spoken + pause]
            for ci, seg in enumerate(group):
                seg["start"] = at + cues[ci]
                png = tmp / f"c{gi:02d}-{ci:02d}.png"
                card(seg, len(items), items, end).save(png)
                frames.append((png, cues[ci + 1] - cues[ci]))
            at += spoken + pause
        (tmp / "a.txt").write_text("".join(f"file '{p}'\n" for p in audio_parts), encoding="utf-8")
        voice = tmp / "voice.wav"
        podcast._ff("-f", "concat", "-safe", "0", "-i", str(tmp / "a.txt"), "-c", "copy", str(voice))
        (tmp / "v.txt").write_text("".join(f"file '{p}'\nduration {s:.3f}\n" for p, s in frames) + f"file '{frames[-1][0]}'\n", encoding="utf-8")
        bed = podcast._bed(end) if music else None
        mp4 = folder / "episode.mp4"
        mix = "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[m]"
        inputs = ["-f", "concat", "-safe", "0", "-i", str(tmp / "v.txt"), "-i", str(voice)]
        if bed:
            vol = float(config.load()["production"].get("music_volume", 0.25)) * 0.6
            inputs += ["-stream_loop", "-1", "-i", str(bed)]
            mix = (f"[2:a]volume={vol},aformat=channel_layouts=mono[b];[1:a][b]amix=inputs=2:duration=first:dropout_transition=0,"
                   "loudnorm=I=-14:TP=-1.5:LRA=11[m]")
        podcast._ff(*inputs, "-filter_complex", f"[0:v]fps={FPS},format=yuv420p[v];{mix}", "-map", "[v]", "-map", "[m]",
                    "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "20", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-t", f"{at:.3f}", str(mp4))
        length = tts.duration(mp4)
    thumbnail(items).save(folder / "thumbnail.jpg", quality=90)
    chapters = [{"title": "Intro", "start": 0.0}] + [{"title": s["title"], "start": round(s["start"], 1), "job": s["job"]} for s in segs if s["kind"] == "chapter"]
    chapters.append({"title": "Outro", "start": round(segs[-1]["start"], 1)})
    write_atomic(folder / "EPISODE.md", episode_md(end, items, chapters, length))
    write_atomic(folder / "episode.json", json.dumps({"week": end, "seconds": round(length, 1), "chapters": chapters,
                                                      "stories": [{"job": i["job"], "views": i["views"]} for i in items]}, indent=1))
    return {"week": end, "items": len(items), "file": str(mp4), "seconds": round(length, 1), "notes": str(folder / "EPISODE.md")}


def episode_md(end: str, items: list[dict], chapters: list[dict], seconds: float) -> str:
    from faceless import offer, podcast
    title = f"{len(items)} Money Rules Nobody Taught You: {items[0]['title']} | {SHOW}"
    if len(title) > 100:                               # YouTube's title limit
        title = f"{len(items)} Money Rules Nobody Taught You | {SHOW} ({end})"
    link = offer.tracked(offer.hub_url(), "youtube", "longform", f"weekly-{end}")
    lines = [f"# {title}", "", f"Week ending {end} · {podcast._clock(seconds)} · 1920x1080 · {len(items)} stories ranked by views", "",
             "## Description (paste)", "",
             f"The {len(items)} money rules that landed hardest on Quiet Money this week, in one sitting.", ""]
    lines += [f"{podcast._clock(c['start'])} {c['title']}" for c in chapters]
    lines += [""] + ([f"Free 7-day Money Reset checklist and every link: {link}", ""] if link else [])
    lines += [podcast.DISCLAIMER, podcast.AI_NOTE, "", "## Upload", "",
              "Upload `episode.mp4` as a normal (not Shorts) video with `thumbnail.jpg`, the title and the description above.",
              "Turn on \"altered or synthetic content\" (rule 4). The chapters come from the timestamps in the description."]
    return "\n".join(lines) + "\n"
