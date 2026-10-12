"""Song video: one picture and one song become a music video, in code, with no paid service.

Landscape 1920x1080 (16:9) is the default, because the pictures are 16:9 and a full song belongs on YouTube as a normal video; `portrait=True` gives
1080x1920 for Shorts and Reels. The picture is graded, given a bloom and a vignette, then a slow camera drifts across it while warm particles float up,
film grain moves, and a thin gold waveform follows the song. Only two things are written on the picture: the QUIET MONEY wordmark at the top, as on every
Quiet Money video, and the song title low. The AI label is the platform's own toggle, not on-screen text. Two passes, as the motion-reel study
recommended: a small DRAFT to look at frames, then the DELIVERY render. The final mix is normalised to -14 LUFS so loudness does not change from song to
song. Every frame is a function of time (the drift and breathing use `t`), so the same input gives the same video.
Skill: .claude/skills/faceless-motion-stack, methods taken from the 2026-10-12 intake.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from faceless.config import Paths
from faceless.fsutil import write_atomic

LANDSCAPE, PORTRAIT = (1920, 1080), (1080, 1920)
FPS = 30
ZOOM = 1.10                  # the picture is drawn this much larger than the frame so the camera can drift
LOOP_S = 10                  # the particle clip loops every 10 seconds, seamlessly
GOLD = (255, 210, 63)
GRADES = {                   # contrast, colour, bloom strength: tuned per mood
    "dusk": (1.12, 1.20, 0.40),
    "warm": (1.08, 1.12, 0.45),
    "deep": (1.14, 1.15, 0.35),
}
FFMPEG_TIMEOUT = 3600


def frame_size(portrait: bool, sc: float) -> tuple[int, int]:
    w, h = PORTRAIT if portrait else LANDSCAPE
    return round(w * sc / 2) * 2, round(h * sc / 2) * 2


def drift_x(dur: float, fw: int, start: float = 0.0, end: float = 1.0) -> str:
    """ffmpeg expression for the crop's x: an ease-in-out glide from `start` to `end` (fractions of the free width) over the song."""
    return f"(iw-{fw})*({start}+({end}-{start})*(0.5-0.5*cos(PI*min(t/{dur:.3f},1))))"


def title_lines(title: str, width: int = 24) -> list[str]:
    words, lines, cur = title.upper().split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + ([cur] if cur else [])


def _font(name: str, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Paths.fonts / name), max(8, round(size)))


def _spaced(d: ImageDraw.ImageDraw, cx: float, y: float, text: str, font, fill, spacing: float) -> None:
    widths = [d.textlength(c, font=font) for c in text]
    x = cx - (sum(widths) + spacing * (len(text) - 1)) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=font, fill=fill)
        x += w + spacing


def enhance(src: Path, grade: str, size: tuple[int, int]) -> Image.Image:
    """The picture, a little larger than the frame, graded, with bloom: the 'cooler' part. The whole picture stays in view as the camera drifts."""
    contrast, colour, bloom = GRADES[grade]
    fw, fh = size
    img = Image.open(src).convert("RGB")
    scale = max(fw * ZOOM / img.width, fh * ZOOM / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(colour)
    a = np.asarray(img).astype(np.float32) / 255
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    hi = (a * np.clip((lum - 0.62) / 0.38, 0, 1)[..., None] * 255).astype(np.uint8)
    glow = np.asarray(Image.fromarray(hi).filter(ImageFilter.GaussianBlur(max(2, fh * 0.02)))).astype(np.float32) / 255
    out = 1 - (1 - a) * (1 - glow * bloom)             # screen blend: highlights bloom softly
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def overlay(title: str, size: tuple[int, int]) -> Image.Image:
    """Static layer: vignette, top and bottom shade, the wordmark and the title. Nothing else is written on the picture."""
    w, h = size
    portrait = h > w
    u = w / 1080 if portrait else h / 1080               # one design unit: 1/1080 of the short side
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w * 0.75)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2)
    alpha = np.clip((r - 0.55) * 0.9, 0, 0.55)
    top = (330 if portrait else 200) * u
    alpha = np.maximum(alpha, np.clip(1 - yy / top, 0, 1) * 0.55)                              # shade behind the wordmark
    low = (1150 if portrait else 640) * u
    alpha = np.maximum(alpha, np.clip((yy - low) / (h - low), 0, 1) * 0.62)                    # shade behind the title
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.putalpha(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8), "L"))
    d = ImageDraw.Draw(im)
    wm_y = (70 if portrait else 44) * u
    _spaced(d, w / 2, wm_y, "QUIET MONEY", _font("Montserrat-ExtraBold.ttf", 34 * u), (255, 255, 255, 235), 9 * u)
    line_y = wm_y + 54 * u
    d.line([(60 * u, line_y), (w - 60 * u, line_y)], fill=(255, 255, 255, 70), width=max(1, round(2 * u)))
    d.line([(w / 2 - 36 * u, line_y), (w / 2 + 36 * u, line_y)], fill=GOLD + (255,), width=max(1, round(3 * u)))
    big = _font("Montserrat-Black.ttf", 70 * u)
    lines = title_lines(title, 16 if portrait else 28)
    y = ((1290 if len(lines) == 1 else 1250) if portrait else 872) * u
    for line in lines:
        tw = d.textlength(line, font=big)
        d.text(((w - tw) / 2 + 3 * u, y + 3 * u), line, font=big, fill=(0, 0, 0, 170))
        d.text(((w - tw) / 2, y), line, font=big, fill=(255, 255, 255, 255))
        y += 84 * u
    return im


def particles(path: Path, size: tuple[int, int]) -> None:
    """A seamless 10-second loop of drifting warm particles, drawn with numpy and piped to ffmpeg."""
    w, h = size
    u = min(w, h) / 1080
    rng = np.random.default_rng(7)
    n = 150
    px, py = rng.uniform(0, w, n), rng.uniform(0, h, n)
    laps = rng.integers(1, 4, n)                       # whole laps per loop: the clip ends where it began
    sway, phase = rng.uniform(4, 22, n) * u, rng.uniform(0, 6.283, n)
    rad, lum = rng.uniform(1.0, 3.2, n) * u, rng.uniform(0.35, 1.0, n)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
           "-t", str(LOOP_S), "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "16", str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(LOOP_S * FPS):
            p = f / (LOOP_S * FPS)
            frame = Image.new("RGB", (w, h), (0, 0, 0))
            d = ImageDraw.Draw(frame)
            for i in range(n):
                y = (py[i] - laps[i] * h * p) % h
                x = (px[i] + sway[i] * np.sin(6.283 * p * laps[i] + phase[i])) % w
                c = tuple(int(v * lum[i]) for v in (255, 226, 160))
                d.ellipse([x - rad[i], y - rad[i], x + rad[i], y + rad[i]], fill=c)
            proc.stdin.write(frame.filter(ImageFilter.GaussianBlur(max(0.6, 1.1 * u))).tobytes())
        proc.stdin.close()
        proc.wait(timeout=FFMPEG_TIMEOUT)
    finally:
        if proc.poll() is None:
            proc.kill()


def probe_seconds(audio: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
                         capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    return float(out)


def make(image: Path, audio: Path, title: str, out: Path, *, grade: str = "deep", draft: bool = False, portrait: bool = False,
         pan: tuple[float, float] = (0.0, 1.0), seconds: float | None = None) -> dict:
    """Render the song video. `draft` is a small, fast pass for looking at frames; the delivery pass is the real file."""
    image, audio, out = Path(image), Path(audio), Path(out)
    sc = 0.5 if draft and not portrait else (1 / 3 if draft else 1.0)
    fps = 10 if draft else FPS
    dur = seconds or probe_seconds(audio)
    w, h = frame_size(portrait, sc)
    work = Paths.cache / "songvideo" / out.stem
    work.mkdir(parents=True, exist_ok=True)
    big, ov, pt = work / "picture.png", work / "overlay.png", work / "particles.mp4"
    enhance(image, grade, (w, h)).save(big)
    overlay(title, (w, h)).save(ov)
    particles(pt, (w, h))
    x = drift_x(dur, w, *pan)
    u = w / 1080 if portrait else h / 1080
    wave_w, wave_h = round((760 if portrait else 720) * u), round((84 if portrait else 64) * u)
    wave_y = round((1405 if portrait else 990) * u)
    fc = (
        f"[0:v]crop=w={w}:h={h}:x='{x}':y='(ih-{h})/2+{round(30 * u)}*sin(t/7)',eq=brightness='0.014*sin(2*PI*t/6)':eval=frame,format=gbrp[bg];"
        f"[1:v]scale={w}:{h}:flags=bicubic,format=gbrp[pt];"
        f"[bg][pt]blend=all_mode=screen:all_opacity=0.75[b2];"
        f"[2:v]format=rgba,fade=t=in:st=0.6:d=1.6:alpha=1[ov];"
        f"[b2]format=rgba[b3];[b3][ov]overlay=0:0,noise=alls=7:allf=t,format=yuv420p[b4];"
        f"[3:a]asplit[wa][ma];"
        f"[wa]showwaves=s={wave_w}x{wave_h}:mode=cline:rate={fps}:colors=0xFFD23F@0.9:scale=sqrt,format=rgba,fade=t=in:st=1.2:d=1.6:alpha=1[wv];"
        f"[b4][wv]overlay=x=(W-w)/2:y={wave_y}:format=auto,format=yuv420p[v];"
        f"[ma]afade=t=in:d=0.6,afade=t=out:st={max(0, dur - 3):.2f}:d=3,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-loop", "1", "-framerate", str(fps), "-i", str(big),
           "-stream_loop", "-1", "-i", str(pt),
           "-loop", "1", "-framerate", str(fps), "-i", str(ov),
           "-i", str(audio),
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}", "-r", str(fps),
           "-c:v", "libx264", "-preset", "ultrafast" if draft else "medium", "-crf", "30" if draft else "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, timeout=FFMPEG_TIMEOUT)
    info = {"video": str(out), "seconds": round(dur, 2), "size": f"{w}x{h}", "draft": draft, "grade": grade, "title": title}
    write_atomic(out.with_suffix(".json"), json.dumps(info, indent=1))
    return info


def poster(image: Path, title: str, out: Path, *, grade: str = "deep", portrait: bool = False, focus: float = 0.5) -> Path:
    """A still cover (1920x1080, or 1080x1920 with portrait): the graded picture with the wordmark and the title."""
    w, h = frame_size(portrait, 1.0)
    big = enhance(image, grade, (w, h))
    left = round((big.width - w) * focus)
    top = (big.height - h) // 2
    frame = big.crop((left, top, left + w, top + h)).convert("RGBA")
    frame.alpha_composite(overlay(title, (w, h)))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.convert("RGB").save(out, "JPEG", quality=93)
    return out
