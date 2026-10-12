"""Song video: one picture and one song become a 1080x1920 music video, in code, with no paid service.

The picture is graded, given a bloom and a vignette, then a slow camera pans across the whole of it while warm particles drift up, film grain moves, and
a thin gold waveform follows the song. The QUIET MONEY wordmark sits at the top as on every Quiet Money video; the song title sits low,
above the platforms' bottom interface zone. Two passes, as the motion-reel study recommended: a small DRAFT to look at frames, then the DELIVERY render.
The final mix is normalised to -14 LUFS so loudness does not change from song to song. Every frame is a function of time (the pan and breathing use `t`),
so the same input gives the same video. Skill: .claude/skills/faceless-motion-stack, methods taken from the 2026-10-12 intake.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from faceless import config
from faceless.config import Paths
from faceless.fsutil import write_atomic

W, H, FPS = 1080, 1920, 30
ZOOM = 1.12                  # the picture is drawn this much larger than the frame so the camera can drift
LOOP_S = 10                  # the particle clip loops every 10 seconds, seamlessly
GOLD = (255, 210, 63)
GRADES = {                   # contrast, colour, bloom strength: tuned per mood
    "dusk": (1.12, 1.20, 0.40),
    "warm": (1.08, 1.12, 0.45),
    "deep": (1.14, 1.15, 0.35),
}
FFMPEG_TIMEOUT = 1800


def pan_x(dur: float, start: float = 0.0, end: float = 1.0, fw: int = W) -> str:
    """ffmpeg expression for the crop's x: an ease-in-out glide from `start` to `end` (fractions of the free width) over the song."""
    return f"(iw-{fw})*({start}+({end}-{start})*(0.5-0.5*cos(PI*min(t/{dur:.3f},1))))"


def title_lines(title: str, width: int = 16) -> list[str]:
    words, lines, cur = title.upper().split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return lines + ([cur] if cur else [])


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(Paths.fonts / name), max(8, round(size)))


def _spaced(d: ImageDraw.ImageDraw, cx: float, y: float, text: str, font, fill, spacing: float) -> None:
    widths = [d.textlength(c, font=font) for c in text]
    x = cx - (sum(widths) + spacing * (len(text) - 1)) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=font, fill=fill)
        x += w + spacing


def enhance(src: Path, grade: str, sc: float) -> Image.Image:
    """The picture, larger than the frame, graded, with bloom: the 'cooler' part."""
    contrast, colour, bloom = GRADES[grade]
    img = Image.open(src).convert("RGB")
    ph = round(H * ZOOM * sc)
    img = img.resize((round(img.width * ph / img.height), ph), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(colour)
    a = np.asarray(img).astype(np.float32) / 255
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    hi = (a * np.clip((lum - 0.62) / 0.38, 0, 1)[..., None] * 255).astype(np.uint8)
    glow = np.asarray(Image.fromarray(hi).filter(ImageFilter.GaussianBlur(max(2, 38 * sc)))).astype(np.float32) / 255
    out = 1 - (1 - a) * (1 - glow * bloom)             # screen blend: highlights bloom softly
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def overlay(title: str, sc: float) -> Image.Image:
    """Static layer: vignette, top and bottom shade, the wordmark and the title. Nothing else is written on the picture; the AI label is the platform's own toggle."""
    w, h = round(W * sc), round(H * sc)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w * 0.75)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2)
    alpha = np.clip((r - 0.55) * 0.9, 0, 0.55)
    alpha = np.maximum(alpha, np.clip(1 - yy / (330 * sc), 0, 1) * 0.55)                 # top shade behind the wordmark
    alpha = np.maximum(alpha, np.clip((yy - 1150 * sc) / (500 * sc), 0, 1) * 0.62)        # bottom shade behind the title
    layer = Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8), "L")
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.putalpha(layer)
    d = ImageDraw.Draw(im)
    _spaced(d, w / 2, 70 * sc, "QUIET MONEY", _font("Montserrat-ExtraBold.ttf", 34 * sc), (255, 255, 255, 235), 9 * sc)
    d.line([(60 * sc, 124 * sc), (w - 60 * sc, 124 * sc)], fill=(255, 255, 255, 70), width=max(1, round(2 * sc)))
    d.line([(w / 2 - 36 * sc, 124 * sc), (w / 2 + 36 * sc, 124 * sc)], fill=GOLD + (255,), width=max(1, round(3 * sc)))
    big = _font("Montserrat-Black.ttf", 70 * sc)
    lines = title_lines(title)
    y = 1290 * sc if len(lines) == 1 else 1250 * sc
    for line in lines:
        tw = d.textlength(line, font=big)
        d.text(((w - tw) / 2 + 3 * sc, y + 3 * sc), line, font=big, fill=(0, 0, 0, 170))
        d.text(((w - tw) / 2, y), line, font=big, fill=(255, 255, 255, 255))
        y += 84 * sc
    return im


def particles(path: Path, sc: float) -> None:
    """A seamless 10-second loop of drifting warm particles, drawn with numpy and piped to ffmpeg."""
    w, h = round(W * sc / 2) * 2, round(H * sc / 2) * 2
    rng = np.random.default_rng(7)
    n = 150
    px, py = rng.uniform(0, w, n), rng.uniform(0, h, n)
    laps = rng.integers(1, 4, n)                       # whole laps per loop: the clip ends where it began
    sway, phase = rng.uniform(4, 22, n) * sc, rng.uniform(0, 6.283, n)
    rad, lum = rng.uniform(1.0, 3.2, n) * sc, rng.uniform(0.35, 1.0, n)
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
            proc.stdin.write(frame.filter(ImageFilter.GaussianBlur(max(0.6, 1.1 * sc))).tobytes())
        proc.stdin.close()
        proc.wait(timeout=FFMPEG_TIMEOUT)
    finally:
        if proc.poll() is None:
            proc.kill()


def probe_seconds(audio: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
                         capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    return float(out)


def make(image: Path, audio: Path, title: str, out: Path, *, grade: str = "deep", draft: bool = False,
         pan: tuple[float, float] = (0.0, 1.0), seconds: float | None = None) -> dict:
    """Render the song video. `draft` is a small, fast pass for looking at frames; the delivery pass is the real file."""
    image, audio, out = Path(image), Path(audio), Path(out)
    sc = 1 / 3 if draft else 1.0
    fps = 10 if draft else FPS
    dur = seconds or probe_seconds(audio)
    w, h = round(W * sc / 2) * 2, round(H * sc / 2) * 2
    work = Paths.cache / "songvideo" / out.stem
    work.mkdir(parents=True, exist_ok=True)
    big, ov, pt = work / "picture.png", work / "overlay.png", work / "particles.mp4"
    enhance(image, grade, sc).save(big)
    overlay(title, sc).save(ov)
    particles(pt, sc)
    x = pan_x(dur, *pan, fw=w)
    wave_w, wave_h = round(760 * sc), round(84 * sc)
    fc = (
        f"[0:v]crop=w={w}:h={h}:x='{x}':y='(ih-{h})/2+{round(40 * sc)}*sin(t/7)',eq=brightness='0.014*sin(2*PI*t/6)':eval=frame,format=gbrp[bg];"
        f"[1:v]scale={w}:{h}:flags=bicubic,format=gbrp[pt];"
        f"[bg][pt]blend=all_mode=screen:all_opacity=0.75[b2];"
        f"[2:v]format=rgba,fade=t=in:st=0.6:d=1.6:alpha=1[ov];"
        f"[b2]format=rgba[b3];[b3][ov]overlay=0:0,noise=alls=7:allf=t,format=yuv420p[b4];"
        f"[3:a]asplit[wa][ma];"
        f"[wa]showwaves=s={wave_w}x{wave_h}:mode=cline:rate={fps}:colors=0xFFD23F@0.9:scale=sqrt,format=rgba,fade=t=in:st=1.2:d=1.6:alpha=1[wv];"
        f"[b4][wv]overlay=x=(W-w)/2:y={round(1405 * sc)}:format=auto,format=yuv420p[v];"
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


def poster(image: Path, title: str, out: Path, *, grade: str = "deep", focus: float = 0.5) -> Path:
    """A 1080x1920 still (cover): the graded picture cropped around `focus` (0 left, 1 right), with the wordmark and the title."""
    big = enhance(image, grade, 1.0)
    left = round((big.width - W) * focus)
    top = (big.height - H) // 2
    frame = big.crop((left, top, left + W, top + H)).convert("RGBA")
    frame.alpha_composite(overlay(title, 1.0))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.convert("RGB").save(out, "JPEG", quality=93)
    return out
