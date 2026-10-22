"""The weekly audio edition (C4): one podcast episode a week, rebuilt from the week's scripts that passed the gauntlet.

Renders are not kept between sessions, but every final script is committed, so the episode is voiced fresh from
`script-lab/final/<job_id>.json` through the same voice chain as the Shorts (free voices first). It is an intro, each
story with its title as a chapter, and an outro carrying the disclaimer and the AI disclosure (rules 2 and 4), over a low
music bed, encoded mono 64 kbps for a podcast host. `EPISODE.md` beside it holds the title, the description and the
chapter timestamps to paste.

`python -m faceless podcast build [--week YYYY-MM-DD]` builds the week ending on that day (default: yesterday). Uploading is
the owner's step: a free podcast host account (empire gate `podcast`). Nothing here posts anything.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

from faceless import config
from faceless.config import Paths
from faceless.fsutil import write_atomic

OUT = Paths.root / "distribution" / "podcast"
GAP_S = 0.8
DISCLAIMER = "Quiet Money is education, not financial advice. Do your own research before any money decision."
AI_NOTE = "This episode is narrated with an AI voice and made with AI tools."


def week_days(end: str) -> list[str]:
    e = date.fromisoformat(end)
    return [(e - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]


def week_items(end: str) -> list[dict]:
    """The week's passed Shorts that have a committed final script, oldest first: {job, day, title, text}."""
    from faceless.state import all_jobs
    days = set(week_days(end))
    items = []
    for j in sorted((j for j in all_jobs() if j.day in days and j.status == "published" and not j.id.startswith("host-")),
                    key=lambda j: (j.day, j.slot)):
        path = Paths.final / f"{j.id}.json"
        try:
            s = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        text = " ".join(str(b.get("say", "")).strip() for b in s.get("beats") or [] if isinstance(b, dict)).strip()
        if text:
            items.append({"job": j.id, "day": j.day, "title": str(s.get("title") or j.topic).strip(), "text": text})
    return items


def segments(items: list[dict], end: str) -> list[dict]:
    """What is spoken, in order. Each segment becomes one chapter."""
    name = config.load()["channel"]["name"]
    first, last = week_days(end)[0], end
    intro = (f"This is {name}, the money rules nobody taught you. Here are this week's {len(items)} stories, "
             f"from {_spoken(first)} to {_spoken(last)}.")
    out = [{"title": "Intro", "text": intro}]
    for n, it in enumerate(items, 1):
        out.append({"title": it["title"], "text": f"Number {n}. {it['title']}. {it['text']}", "job": it["job"]})
    out.append({"title": "Outro", "text": f"That's the week. New money rules every day on {name}. {DISCLAIMER} {AI_NOTE}"})
    return out


def _spoken(day: str) -> str:
    d = date.fromisoformat(day)
    return f"{d.strftime('%B')} {d.day}"


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True, timeout=600)


def _clock(s: float) -> str:
    s = int(round(s))
    return f"{s // 3600:d}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:d}:{s % 60:02d}"


def build(end: str | None = None, *, music: bool = True, synth=None) -> dict:
    """Voice, join and encode the episode. `synth(text, wav_path)` is the voice chain; a test passes its own."""
    from faceless.providers import tts
    end = end or (config.today_utc() - timedelta(days=1)).isoformat()
    items = week_items(end)
    if not items:
        return {"week": end, "items": 0, "file": None, "reason": "no passed Shorts with a final script that week"}
    synth = synth or (lambda text, wav: tts.synthesize(text, wav, job=f"podcast-{end}"))
    folder = OUT / end
    folder.mkdir(parents=True, exist_ok=True)
    segs = segments(items, end)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gap = tmp / "gap.wav"
        _ff("-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono", "-t", str(GAP_S), "-ar", "24000", "-ac", "1", str(gap))
        parts, at = [], 0.0
        for i, seg in enumerate(segs):
            raw, wav = tmp / f"s{i}.raw.wav", tmp / f"s{i}.wav"
            synth(seg["text"], raw)
            _ff("-i", str(raw), "-ar", "24000", "-ac", "1", str(wav))          # one format, so the concat is clean
            seg["start"] = at
            at += tts.duration(wav) + GAP_S
            parts += [wav, gap]
        listing = tmp / "list.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        voice = tmp / "voice.wav"
        _ff("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(voice))
        bed = _bed(end) if music else None
        mp3 = folder / "episode.mp3"
        if bed:
            vol = float(config.load()["production"].get("music_volume", 0.25)) * 0.6       # quieter than a Short: it runs for minutes
            _ff("-i", str(voice), "-stream_loop", "-1", "-i", str(bed), "-filter_complex",
                f"[1:a]volume={vol},aformat=channel_layouts=mono[b];[0:a][b]amix=inputs=2:duration=first:dropout_transition=0[m];"
                "[m]loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k", str(mp3))
        else:
            _ff("-i", str(voice), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k", str(mp3))
        length = tts.duration(mp3)
    notes = episode_md(end, segs, length)
    write_atomic(folder / "EPISODE.md", notes)
    write_atomic(folder / "episode.json", json.dumps({"week": end, "seconds": round(length, 1), "items": [s.get("job") for s in segs if s.get("job")],
                                                      "chapters": [{"title": s["title"], "start": round(s["start"], 1)} for s in segs]}, indent=1))
    return {"week": end, "items": len(items), "file": str(mp3), "seconds": round(length, 1), "notes": str(folder / "EPISODE.md")}


def _bed(end: str) -> Path | None:
    try:
        from faceless import musiclib
        return musiclib.pick("story", seed=int(end.replace("-", "")))
    except Exception:  # noqa: BLE001 - no bed is a quieter episode, never a failed one
        return None


def episode_md(end: str, segs: list[dict], seconds: float) -> str:
    name = config.load()["channel"]["name"]
    first = week_days(end)[0]
    stories = [s for s in segs if s.get("job")]
    title = f"{name} Weekly: {stories[0]['title']} and {len(stories) - 1} more" if len(stories) > 1 else f"{name} Weekly: {stories[0]['title']}"
    lines = [f"# {title}", "", f"Week {first} to {end} · {_clock(seconds)} · mono 64 kbps", "",
             "## Description (paste)", "",
             f"This week's money rules from {name}, in one listen: " + "; ".join(s["title"] for s in stories) + ".", "",
             DISCLAIMER, AI_NOTE, "", "## Chapters (paste)", ""]
    lines += [f"{_clock(s['start'])} {s['title']}" for s in segs]
    lines += ["", "## Upload", "", "The owner's step: upload `episode.mp3` to the podcast host with the title, description and chapters above.",
              "Mark it as AI-generated where the host asks."]
    return "\n".join(lines) + "\n"
