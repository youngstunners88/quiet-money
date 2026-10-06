"""Render stage: stills -> moving shots -> graded, captioned, mixed 1080x1920 MP4.

1. Plan shots from beat timings (long beats split into a wide shot + a punch-in).
2. Render each shot in parallel: sub-pixel Ken Burns via PIL affine transforms piped to x264.
3. Concat shots losslessly, then one final pass: grade, grain, progress bar, ASS captions,
   voice + ducked music + SFX, loudness-normalized to -14 LUFS (platform standard).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from faceless import config, events
from faceless.config import Paths
from faceless.pipeline import captions, cards, music

GRADES = {
    "warm": "colorbalance=rs=0.05:gs=0.01:bs=-0.06:rm=0.03:bm=-0.04,eq=contrast=1.06:saturation=1.04",
    "gold": "colorbalance=rs=0.04:gs=0.02:bs=-0.07,eq=contrast=1.12:brightness=-0.015",
    "cool": "colorbalance=rs=-0.04:bs=0.05:rm=-0.02:bm=0.04,eq=contrast=1.08:saturation=0.86",
    "contrast": "eq=contrast=1.16:saturation=1.08:brightness=-0.02",
    "clean": "eq=contrast=1.03:saturation=1.07:brightness=0.015",
    "night": "colorbalance=rs=-0.03:bs=0.06:rh=0.06:gh=0.01:bh=-0.05,eq=contrast=1.12:saturation=1.06:brightness=-0.01",
}

# (z0, z1, (cx0, cy0), (cx1, cy1)); centers are fractions of the free pan range
MOTIONS = {
    "push_in": (1.00, 1.13, (0.5, 0.42), (0.5, 0.40)),
    "pull_out": (1.15, 1.02, (0.5, 0.44), (0.5, 0.50)),
    "pan_left": (1.13, 1.15, (0.80, 0.45), (0.20, 0.45)),
    "pan_right": (1.13, 1.15, (0.20, 0.45), (0.80, 0.45)),
    "pan_up": (1.13, 1.15, (0.5, 0.78), (0.5, 0.25)),
    "pan_down": (1.13, 1.15, (0.5, 0.25), (0.5, 0.72)),
}
HOOK = (1.00, 1.20, (0.5, 0.45), (0.5, 0.40))


def _ease(p: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * p)


def plan_shots(beats: list[tuple[float, float]], images: list[dict], fps: int, max_shot: float, seed: str) -> list[dict]:
    rnd = random.Random(seed)
    cycle = list(MOTIONS)
    rnd.shuffle(cycle)
    shots, mi = [], 0
    for i, ((s, e), img) in enumerate(zip(beats, images)):
        spans = [(s, e)]
        if e - s > max_shot and e - s >= 2.4:
            mid = s + (e - s) * 0.55
            spans = [(s, mid), (mid, e)]
        for k, (a, b) in enumerate(spans):
            if i == 0 and k == 0:
                motion = HOOK
            elif k == 1:  # punch-in: tighter frame on a different focal point of the same image
                fx, fy = rnd.uniform(0.3, 0.7), rnd.uniform(0.3, 0.6)
                motion = (1.30, 1.38, (fx, fy), (fx + rnd.uniform(-0.08, 0.08), fy + rnd.uniform(-0.05, 0.05)))
            else:
                motion = MOTIONS[cycle[mi % len(cycle)]]
                mi += 1
            f0, f1 = round(a * fps), round(b * fps)
            if f1 > f0:
                shots.append({"image": img["path"], "frames": f1 - f0, "start": a, "motion": motion, "beat": i,
                              "card": img.get("card")})
    return shots


def _prepare(image_path: str, W: int, H: int, over: float):
    """Scale the still so it covers the frame with `over` headroom, sharpened once."""
    im = Image.open(image_path).convert("RGB")
    sw, sh = im.size
    base = max(W / sw, H / sh) * over
    im = im.resize((round(sw * base), round(sh * base)), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))


def render_shot(args) -> str:
    image_path, out_path, frames, motion, W, H, fps, look = args
    over = 1.3
    im = _prepare(image_path, W, H, over)
    SW, SH = im.size
    try:  # OpenCV's SIMD warp is ~9x faster than PIL's transform; PIL stays as the fallback
        import cv2
        import numpy as np
        cv2.setNumThreads(1)  # parallelism comes from the process pool
        src = np.asarray(im)

        def warp(s, x0, y0):
            m = np.float32([[s, 0, x0], [0, s, y0]])
            return cv2.warpAffine(src, m, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                                  borderMode=cv2.BORDER_REFLECT).tobytes()
    except ImportError:
        def warp(s, x0, y0):
            return im.transform((W, H), Image.AFFINE, (s, 0, x0, 0, s, y0), resample=Image.BICUBIC).tobytes()
    z0, z1, (cx0, cy0), (cx1, cy1) = motion
    proc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-vf", look, "-c:v", "libx264", "-preset", "ultrafast",
         "-crf", "13", "-pix_fmt", "yuv420p", "-r", str(fps), str(out_path)], stdin=subprocess.PIPE)
    for i in range(frames):
        p = _ease(i / max(1, frames - 1))
        z = z0 + (z1 - z0) * p
        s = over / z                      # source pixels per output pixel
        ww, hh = W * s, H * s             # visible window in source pixels
        ncx = min(1.0, max(0.0, cx0 + (cx1 - cx0) * p))
        ncy = min(1.0, max(0.0, cy0 + (cy1 - cy0) * p))
        proc.stdin.write(warp(s, (SW - ww) * ncx, (SH - hh) * ncy))
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"shot encode failed: {out_path}")
    return str(out_path)


def card_shot(args) -> str:
    """Cut one shot out of the HyperFrames card reel, encoded like every other shot so the concat can copy."""
    reel, out_path, offset, frames, fps = args
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{offset:.3f}", "-i", str(reel),
          "-frames:v", str(frames), "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "13",
          "-pix_fmt", "yuv420p", "-r", str(fps), str(out_path)])
    return str(out_path)


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {p.stderr[-1500:]}")


def cover_image(first_image: str, hook: str, out: Path, accent: str) -> None:
    W, H = 1080, 1920
    im = Image.open(first_image).convert("RGB")
    sw, sh = im.size
    sc = max(W / sw, H / sh)
    im = im.resize((round(sw * sc), round(sh * sc)), Image.LANCZOS)
    left, top = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((left, top, left + W, top + H))
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(Paths.fonts / "Montserrat-Black.ttf"), 92)
    lines = captions.wrap_hook(hook, 14)
    y = 360
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (W - tw) // 2
        d.rectangle([x - 28, y - 18, x + tw + 28, y + th + 34], fill=accent)
        d.text((x, y - bbox[1]), line, font=font, fill="#101010")
        y += th + 64
    im.save(out, "JPEG", quality=92)


def run(job, script: dict, voice: dict, imgs: list[dict]) -> dict:
    cfg = config.load()["production"]
    pillar = config.pillar(job.pillar)
    W, H, fps = cfg["width"], cfg["height"], cfg["fps"]
    total = voice["duration"]
    work = job.dir / "shots"
    work.mkdir(exist_ok=True)

    shots = plan_shots(voice["beats"], imgs, fps, cfg["shot_max_seconds"], job.id)
    expected = round(total * fps)
    have = sum(s["frames"] for s in shots)
    if have != expected and shots:          # absorb rounding so video length == audio length
        shots[-1]["frames"] += expected - have
    grade = GRADES.get(pillar.grade, GRADES["warm"])
    vig = "PI/7" if pillar.grade == "clean" else "PI/4.6"
    look = f"{grade},vignette={vig},noise=alls=3:allf=t+u,format=yuv420p"
    card_specs = {r["beat"]: r["card"] for r in imgs if r.get("card")}
    reel = cards.render_reel(job, card_specs, {i: tuple(b) for i, b in enumerate(voice["beats"])}, job.pillar,
                             cfg["accent"], fps) if card_specs else None
    tasks, card_tasks = [], []
    for i, s in enumerate(shots):
        out_i = work / f"shot{i:03d}.mp4"
        if s.get("card") and reel:       # card beat: offset inside its card's slot in the reel
            beat_start = voice["beats"][s["beat"]][0]
            card_tasks.append((reel[0], out_i, reel[1][s["beat"]] + max(0.0, s["start"] - beat_start), s["frames"], fps))
        else:
            if s["image"] is None:       # card beat whose reel failed: fall back to generated placeholder art
                from faceless.providers import images as image_providers
                s["image"] = str(Paths.cache / f"{job.id}-fallback{s['beat']}.jpg")
                image_providers.procedural("abstract", 864, 1536, s["beat"], s["image"])
            tasks.append((s["image"], out_i, s["frames"], s["motion"], W, H, fps, look))
    with ProcessPoolExecutor(max_workers=4) as ex:
        list(ex.map(render_shot, tasks))
        list(ex.map(card_shot, card_tasks))
    tasks += [(None, t[1]) for t in card_tasks]
    tasks.sort(key=lambda t: t[1].name)
    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{t[1].name}'\n" for t in tasks), encoding="utf-8")
    raw = job.dir / "raw.mp4"
    _run(["ffmpeg", "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(raw)])

    # audio beds
    seed = int(hashlib.sha1(job.id.encode()).hexdigest()[:8], 16)
    cut_times = [s["start"] for s in shots[1:]]
    music_wav, sfx_wav = job.dir / "music.wav", job.dir / "sfx.wav"
    mode = cfg.get("music", "procedural")
    if mode == "procedural":
        music.write_wav(music_wav, music.ambient_bed(total + 0.5, pillar.music_key, 84 + seed % 12, seed))
    elif mode != "none" and Path(mode).exists():
        _run(["ffmpeg", "-hide_banner", "-y", "-stream_loop", "-1", "-i", mode, "-t", f"{total + 0.5:.2f}",
              "-ac", "1", "-ar", "44100", str(music_wav)])
    else:
        music.write_wav(music_wav, music.ambient_bed(total + 0.5) * 0)
    music.write_wav(sfx_wav, music.sfx_track(total + 0.5, cut_times, seed))

    ass = job.dir / "captions.ass"
    covered = captions.build(script, voice, ass, skip_callouts={i for i in card_specs if reel})

    accent = cfg["accent"].lstrip("#")
    fonts = str(Paths.fonts)
    vf = (f"color=c=0x{accent}:s={W}x10:r={fps}[bar];"
          f"[0:v][bar]overlay=x='-w+W*t/{total:.3f}':y=0:shortest=1[p];"
          f"[p]ass=filename='{ass}':fontsdir='{fonts}'[v]")
    af = (f"[1:a]aresample=48000,asplit=2[vo1][vo2];"
          f"[2:a]aresample=48000,volume={cfg['music_volume']}[mu];"
          f"[mu][vo1]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[duck];"
          f"[3:a]aresample=48000,volume={cfg['sfx_volume']}[fx];"
          f"[vo2][duck][fx]amix=inputs=3:duration=first:normalize=0,"
          f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    out = job.dir / "final.mp4"
    _run(["ffmpeg", "-hide_banner", "-y", "-i", str(raw), "-i", str(job.dir / "voice.wav"), "-i", str(music_wav),
          "-i", str(sfx_wav), "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "6M", "-bufsize", "12M",
          "-profile:v", "high", "-pix_fmt", "yuv420p",
          "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-t", f"{total:.3f}",
          "-movflags", "+faststart", str(out)])
    cover = job.dir / "cover.jpg"
    cover_image(imgs[0]["path"], script.get("hook_text") or script["title"], cover, cfg["accent"])
    for t in tasks:  # shots are reproducible from cache; keep the job folder light
        Path(t[1]).unlink(missing_ok=True)
    raw.unlink(missing_ok=True)
    if reel:      # the reel is large and reproducible; keep the small index.html as the record of what was drawn
        Path(reel[0]).unlink(missing_ok=True)
        for f in (job.dir / "cards" / "assets").glob("*.ttf"):
            f.unlink(missing_ok=True)
    info = {"video": str(out), "cover": str(cover), "shots": len(shots), "captioned_words": covered,
            "avg_shot": round(total / max(1, len(shots)), 2),
            "cards": len(card_specs) if reel else 0}
    (job.dir / "render.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    events.emit("RENDERED", job=job.id, **info)
    return info
