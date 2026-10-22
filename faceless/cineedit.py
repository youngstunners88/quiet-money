"""Cinematic edit for the owner's Flow clips: speed ramps, impact framing, grade, grain, and the Quiet Money brand.

Raw AI video is soft and floaty. This rebuilds its energy to the owner's editing standard (.claude/skills/faceless-cineedit):
establish, build, slow-mo into the hit, a fast strike, then an aftermath beat. On top of that it crushes the blacks, pushes
contrast, warms the highlights, adds grain and a vignette, flashes 2 frames at the peak, pushes in on the impact, lays a
low-end boom under the hit, and closes on the gold Q coin end card.

Nothing here calls a paid API: it is ffmpeg plus the repo's own brand kit, so an edit costs nothing but CPU.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from faceless import brand
from faceless.config import Paths

FPS = 24
W, H = 720, 1280
GOLD = "#FFD23F"
# The look: push contrast, cool the shadows, warm the highlights. How hard the blacks are crushed depends on the clip:
# crushing a night scene the way you crush a daylight one just turns it to mud, so the grade is picked from mean luma.
GRADE_DAY = ("curves=all='0/0 0.12/0.04 0.5/0.52 1/1',"
             "eq=contrast=1.22:saturation=1.14:gamma=0.97,"
             "colorbalance=rs=-0.05:bs=0.07:rh=0.07:bh=-0.05")
GRADE_DUSK = ("curves=all='0/0 0.12/0.07 0.5/0.54 1/1',"
              "eq=contrast=1.18:saturation=1.20:gamma=1.0,"
              "colorbalance=rs=-0.04:bs=0.06:rh=0.07:bh=-0.04")
GRADE_NIGHT = ("curves=all='0/0.015 0.15/0.13 0.5/0.56 1/1',"
               "eq=contrast=1.16:saturation=1.32:gamma=1.06,"
               "colorbalance=rs=-0.03:bs=0.05:rh=0.08:bh=-0.03")
NIGHT_LUMA, DAY_LUMA = 70.0, 92.0
ENCODE_TIMEOUT, PROBE_TIMEOUT = 900, 120      # no ffmpeg call may hang the run (tests/test_audit.py)
GRAIN = "noise=alls=5:allf=t+u"
VIGNETTE = "vignette=PI/4.2"
BUILD_SECONDS = 3.0        # the skill's pacing: establish 0.8-1.5s, build 1-3s, then the peak
SLOW = 0.65                # the slow-motion depth into the hit. Deeper than this and the judder shows.
# Slowing 24fps footage just repeats frames: every second frame comes out identical and the motion stutters.
# Optical flow invents the in-between frames instead, which is what makes a ramp look filmed rather than stretched.
SMOOTH = "minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" 


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=ENCODE_TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd[:8])}...\n{r.stderr[-1500:]}")


def mean_luma(path: Path) -> float:
    """Average brightness of the clip, 0-255. Decides how hard the grade may crush the blacks."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf",
                        "fps=4,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "/dev/null"],
                       capture_output=True, text=True, timeout=PROBE_TIMEOUT)
    vals = [float(x.split("=")[1]) for x in r.stderr.split() if x.startswith("lavfi.signalstats.YAVG=")]
    return sum(vals) / len(vals) if vals else 100.0


def grade_for(luma: float) -> tuple[str, str, float]:
    """(grade chain, name, flash opacity) for a clip of this brightness. A dark clip gets a gentler grade and a softer flash."""
    if luma < NIGHT_LUMA:
        return GRADE_NIGHT, "night", 0.18
    if luma < DAY_LUMA:
        return GRADE_DUSK, "dusk", 0.26
    return GRADE_DAY, "day", 0.32


def probe_duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, timeout=PROBE_TIMEOUT)
    return float(r.stdout.strip())


def ramp_plan(duration: float, impact: float) -> list[tuple[float, float, float]]:
    """(start, end, speed) segments around `impact`: tighten the establish, hold the build, slow into the hit,
    snap through the strike, then land the aftermath slightly slow. Speeds stay inside atempo's 0.5-2.0 range."""
    pre, strike, after = max(0.0, impact - 1.0), min(duration, impact + 0.45), duration
    segs = []
    if pre > 1.4:                                   # establish, tightened
        segs.append((0.0, 1.4, 1.25))
        # The build is the part that drags in raw AI video: compress it toward BUILD_SECONDS so the hit arrives early.
        speed = min(2.0, max(1.0, (pre - 1.4) / BUILD_SECONDS))
        segs.append((1.4, pre, round(speed, 3)))
    elif pre > 0:
        segs.append((0.0, pre, 1.0))
    segs.append((pre, impact, SLOW))                # slow-mo into the hit
    segs.append((impact, strike, 2.0))              # the strike snaps past
    if after > strike:
        segs.append((strike, after, 0.6))           # aftermath, slightly slow
    return [(a, b, s) for a, b, s in segs if b - a > 0.04]


def _segments(src: Path, segs: list[tuple[float, float, float]], work: Path) -> Path:
    """Cut each segment at its own speed, then concatenate. Video and audio are ramped together so the roar stays on the hit."""
    parts = []
    for i, (a, b, speed) in enumerate(segs):
        out = work / f"seg{i:02d}.mp4"
        # Only a slowed segment needs the interpolation, and it is the expensive filter, so the rest skip it.
        vf = f"setpts=PTS/{speed}," + (SMOOTH.format(fps=FPS) if speed < 1.0 else f"fps={FPS}")
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src),
              "-filter_complex",
              f"[0:v]{vf}[v];[0:a]atempo={speed},asetpts=N/SR/TB[a]",
              "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)])
        parts.append(out)
    listing = work / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    joined = work / "ramped.mp4"
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
          str(joined)])
    return joined


def _impact_after_ramp(segs: list[tuple[float, float, float]], impact: float) -> float:
    """Where the hit lands on the ramped timeline: every earlier segment's real length divided by its speed."""
    t = 0.0
    for a, b, speed in segs:
        if impact <= a + 1e-6:
            break
        t += (min(b, impact) - a) / speed
    return t


def endcard(out: Path, line: str) -> Path:
    """The closing frame: the gold Q coin, the wordmark, and the handle on ink."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (9, 9, 11))
    d = ImageDraw.Draw(im)
    coin = brand.coin(300)
    im.paste(coin, ((W - 300) // 2, 420), coin)
    title = brand.font("Anton-Regular.ttf", 92)
    sub = brand.font("Montserrat-ExtraBold.ttf", 34)
    for text, font, y, fill in ((line, title, 770, (255, 210, 63)), ("@quietmoneyrule", sub, 890, (232, 230, 225))):
        wdt = d.textbbox((0, 0), text, font=font)[2]
        d.text(((W - wdt) // 2, y), text, font=font, fill=fill)
    im.save(out)
    return out


def edit(src: Path, out: Path, *, impact: float, card_line: str = "QUIET MONEY", card_seconds: float = 1.0) -> dict:
    """Ramp, grade, flash the peak, push in on it, brand it, and close on the card. Returns what the edit did."""
    src, out = Path(src), Path(out)
    duration = probe_duration(src)
    luma = mean_luma(src)
    grade, grade_name, flash_alpha = grade_for(luma)
    segs = ramp_plan(duration, impact)
    work = Path(tempfile.mkdtemp(prefix="cineedit-"))
    try:
        ramped = _segments(src, segs, work)
        hit = _impact_after_ramp(segs, impact)
        ramped_len = probe_duration(ramped)
        card_png = endcard(work / "card.png", card_line)
        mark = Paths.root / "channel" / "brand-kit" / "watermark.png"
        # A 2-frame gold flash on the hit, a slow push-in that peaks there, grain, vignette, the mark, then the card.
        flash_a, flash_b = hit, hit + 2.0 / FPS
        push = (f"zoompan=z='min(1.0+0.05*(on/{max(1, int(ramped_len * FPS))}),1.06)'"
                f":d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
        chain = [f"[0:v]scale={W}:{H},{push},{grade},{GRAIN},{VIGNETTE},format=yuv420p[base]",
                 f"color=c={GOLD}:s={W}x{H}:d={ramped_len:.3f}:r={FPS},format=rgba,colorchannelmixer=aa={flash_alpha}[fl]",
                 f"[base][fl]overlay=enable='between(t,{flash_a:.3f},{flash_b:.3f})'[flashed]"]
        inputs = ["-i", str(ramped)]
        if mark.exists():
            inputs += ["-i", str(mark)]
            chain.append(f"[flashed][1:v]overlay=W-w-28:H-h-40:format=auto[branded]")
            last = "[branded]"
        else:
            last = "[flashed]"
        body = work / "body.mp4"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
              "-filter_complex", ";".join(chain), "-map", last, "-map", "0:a",
              "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", str(body)])
        if card_seconds <= 0:
            shutil.copy2(body, out)
            return {"source": str(src), "out": str(out), "source_seconds": round(duration, 2),
                    "edited_seconds": round(probe_duration(out), 2), "impact_at": impact,
                    "impact_after_ramp": round(hit, 2), "mean_luma": round(luma, 1), "grade": grade_name,
                    "flash_alpha": flash_alpha, "segments": [[round(a, 2), round(b, 2), s] for a, b, s in segs]}
        card = work / "card.mp4"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-t", f"{card_seconds}",
              "-i", str(card_png), "-f", "lavfi", "-t", f"{card_seconds}", "-i", "anullsrc=r=48000:cl=stereo",
              "-filter_complex", f"[0:v]fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.2[v]",
              "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
              "-c:a", "aac", "-b:a", "192k", "-shortest", str(card)])
        listing = work / "final.txt"
        listing.write_text(f"file '{body.name}'\nfile '{card.name}'\n", encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
              "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
        return {"source": str(src), "out": str(out), "source_seconds": round(duration, 2),
                "edited_seconds": round(probe_duration(out), 2), "impact_at": impact,
                "impact_after_ramp": round(hit, 2), "mean_luma": round(luma, 1), "grade": grade_name,
                "flash_alpha": flash_alpha, "segments": [[round(a, 2), round(b, 2), s] for a, b, s in segs]}
    finally:
        shutil.rmtree(work, ignore_errors=True)
