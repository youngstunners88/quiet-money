"""Three Flow clips compiled into one video: a voiceover threads them and lands a call to action.

The day's three clips are not three posts. They are three acts of one story, so the prompts are written as a set
(.claude/skills/faceless-flow) and this compiles them: each clip is edited by faceless/cineedit, joined with a short dip
through black, and carried by one quiet narration line per act over a music bed, ending on the CTA card.

The voice stays under the action on purpose: it is the thread, not the show. Clip sound keeps the hits; the bed fills
the gaps; the narration ducks everything else only while it speaks.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from faceless import brand, cineedit
from faceless.config import Paths

W, H, FPS = cineedit.W, cineedit.H, cineedit.FPS
DIP = 0.18                   # seconds of dip-to-black between acts: a breath, not a transition anyone notices
VO_DELAY = 0.45              # the line starts just after the cut, never on it
VO_GAIN, CLIP_GAIN, BED_GAIN = 1.0, 0.5, 0.17
# The platform standard the rest of the channel is mastered to (faceless/pipeline/render.py). Without this the reel
# came out at -21 LUFS and would play noticeably quieter than every other Quiet Money post in the same feed.
LOUDNESS = "loudnorm=I=-14:TP=-1.5:LRA=11"
DUCK = 0.35                  # what the clip sound and bed drop to while the voice speaks


def _run(cmd: list[str]) -> None:
    cineedit._run(cmd)


def cta_card(out: Path, headline: str, sub: str) -> Path:
    """The closing frame: the gold coin, the one line that asks for the follow, and the handle."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (9, 9, 11))
    d = ImageDraw.Draw(im)
    coin = brand.coin(300)
    im.paste(coin, ((W - 300) // 2, 360), coin)
    rows = [(headline, brand.font("Anton-Regular.ttf", 76), 730, (255, 210, 63)),
            (sub, brand.font("Montserrat-ExtraBold.ttf", 34), 840, (232, 230, 225)),
            ("@quietmoneyrule", brand.font("Montserrat-Black.ttf", 40), 930, (255, 210, 63))]
    for text, font, y, fill in rows:
        wdt = d.textbbox((0, 0), text, font=font)[2]
        d.text(((W - wdt) // 2, y), text, font=font, fill=fill)
    im.save(out)
    return out


def _voice(text: str, out: Path) -> float:
    """One narration line. Returns its length so the next act can be timed against it."""
    from faceless.providers import tts
    tts.synthesize(text, out)
    return tts.duration(out)


def _dip(src: Path, out: Path, seconds: float = DIP) -> None:
    """Fade the tail of an act to black so the cut lands as a beat rather than a jolt."""
    dur = cineedit.probe_duration(src)
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
          "-vf", f"fade=t=out:st={max(0.0, dur - seconds):.3f}:d={seconds}",
          "-af", f"afade=t=out:st={max(0.0, dur - seconds):.3f}:d={seconds}",
          "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", str(out)])


def build(acts: list[dict], out: Path, *, cta_line: str, cta_headline: str = "ONE MONEY RULE A DAY",
          cta_sub: str = "Real numbers. No hype.", bed: Path | None = None, cta_seconds: float = 3.2) -> dict:
    """acts: [{"src": clip, "impact": seconds, "line": narration}]. Returns what was built."""
    out = Path(out)
    work = Path(tempfile.mkdtemp(prefix="reel-"))
    try:
        bodies, starts, t = [], [], 0.0
        for i, act in enumerate(acts):
            body = work / f"act{i}.mp4"
            cineedit.edit(Path(act["src"]), body, impact=float(act["impact"]), card_seconds=0)
            dipped = work / f"act{i}d.mp4"
            _dip(body, dipped)
            starts.append(t)
            t += cineedit.probe_duration(dipped)
            bodies.append(dipped)

        card_png = cta_card(work / "cta.png", cta_headline, cta_sub)
        card = work / "cta.mp4"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-t", f"{cta_seconds}",
              "-i", str(card_png), "-f", "lavfi", "-t", f"{cta_seconds}", "-i", "anullsrc=r=48000:cl=stereo",
              "-filter_complex", f"[0:v]fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.25[v]",
              "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
              "-c:a", "aac", "-b:a", "192k", "-shortest", str(card)])
        card_start = t
        bodies.append(card)

        listing = work / "acts.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in bodies), encoding="utf-8")
        joined = work / "joined.mp4"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
              "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", str(joined)])
        total = cineedit.probe_duration(joined)

        # One narration line per act, placed just after each cut, plus the CTA line over the card.
        lines = [(starts[i] + VO_DELAY, a["line"]) for i, a in enumerate(acts) if a.get("line")]
        lines.append((card_start + 0.3, cta_line))
        vo_files, spoken = [], []
        for i, (at, text) in enumerate(lines):
            wav = work / f"vo{i}.wav"
            length = _voice(text, wav)
            vo_files.append((at, wav))
            spoken.append({"at": round(at, 2), "seconds": round(length, 2), "line": text})

        inputs, chain, vo_labels = ["-i", str(joined)], [], []
        for n, (at, wav) in enumerate(vo_files, start=1):
            inputs += ["-i", str(wav)]
            chain.append(f"[{n}:a]adelay={int(at * 1000)}|{int(at * 1000)},apad[vo{n}]")
            vo_labels.append(f"[vo{n}]")
        chain.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:normalize=0,volume={VO_GAIN}[vo]")
        chain.append("[vo]asplit=2[vomix][vokey]")
        if bed and Path(bed).exists():
            inputs += ["-stream_loop", "-1", "-i", str(bed)]
            bed_idx = len(vo_files) + 1
            chain.append(f"[0:a]volume={CLIP_GAIN}[clip]")
            chain.append(f"[{bed_idx}:a]volume={BED_GAIN},atrim=0:{total:.3f},asetpts=N/SR/TB[bed]")
            chain.append("[clip][bed]amix=inputs=2:normalize=0[under]")
        else:
            chain.append(f"[0:a]volume={CLIP_GAIN}[under]")
        # Duck everything under the narration only while it speaks, so the voice reads without flattening the hits.
        chain.append(f"[under][vokey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400:makeup=1[ducked]")
        chain.append(f"[ducked][vomix]amix=inputs=2:normalize=0,{LOUDNESS},"
                     f"atrim=0:{total:.3f},asetpts=N/SR/TB,aresample=48000[mix]")
        out.parent.mkdir(parents=True, exist_ok=True)
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
              "-filter_complex", ";".join(chain), "-map", "0:v", "-map", "[mix]",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
        return {"out": str(out), "seconds": round(cineedit.probe_duration(out), 2), "acts": len(acts),
                "loudness_target": LOUDNESS,
                "act_starts": [round(s, 2) for s in starts], "cta_at": round(card_start, 2),
                "bed": str(bed) if bed else None, "narration": spoken}
    finally:
        shutil.rmtree(work, ignore_errors=True)
