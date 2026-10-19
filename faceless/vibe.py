"""Vibe: one full song becomes a long-form 16:9 music video (the "twice a week" format with a female vocalist).

The song is used whole: the video is exactly as long as the audio and the audio is encoded untouched (no trim, no fade, no loudness change).
Pipeline: LISTEN (Gemini hears the file: vocalist, lyrics, mood) -> PLAN (Claude Opus 5.5 on OpenRouter writes a shot list that follows the song's arc, one
impossible-but-beautiful scene per shot) -> STILLS (a premium image model through Muapi, never the free fallback) -> CLIPS (a few real image-to-video moments
at the strongest sections, optional and capped) -> RENDER (every frame computed in code: smooth sub-pixel camera moves, cuts on the beat grid, bloom and zoom
that breathe with the bass, particles, grain, the gold waveform, wordmark and title) -> PACK (cover, post copy via songpost).
Only the brand wordmark and the song title are written on the picture (the AI label is the platform toggle, not on-screen text).
Skill: .claude/skills/faceless-vibe.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from faceless import config, ledger, muapi, safety, songvideo
from faceless.config import Paths
from faceless.fsutil import write_atomic
from faceless.providers import ProviderError, ProviderUnavailable, http

MODEL = "anthropic/claude-opus-5.5"
LISTEN_MODEL = "gemini-flash-latest"
STILL_MODEL = "bytedance-seedream-5.0-pro"
CLIP_MODEL = "wan2.7-image-to-video"
CAP_USD = 1.50                                    # per day for the planning call; image spend is capped by the Muapi desk
FPS = 30
XFADE = 1.6                                       # seconds of overlap between two shots
ZOOM_SRC = 1.30                                   # the picture is kept this much larger than the frame so the camera can move
STATE = Paths.state / "vibe"
FFMPEG_TIMEOUT = 7200
MOTIONS = ("push", "pull", "left", "right", "rise", "fall")
BANNED = ("kitchen table in a flood; lantern in a black-glass desert; broken chain at dawn; a runner on a frozen highway; a mountain staircase in clouds; "
          "a rain street with a split skyscraper; a floorboard Penrose loop; a gravity-flipped city under a sea; a salt plain of mirror shards with a swing; "
          "a folding city; a pocket watch of gears; a bathtub of stars; a blue whale carrying a city; a glass hand holding a sea; a recursive painting")
TAIL = "No text, no letters, no logos, no visible faces."


def slug_of(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


# ---------------------------------------------------------------- LISTEN

def listen(audio: Path, work: Path) -> dict:
    """Gemini hears the whole file. Returns vocalist, lyrics (word for word), mood, summary. Cached beside the work files."""
    cache = work / "listen.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    key = config.env("GEMINI_API_KEY")
    if not key:
        raise ProviderUnavailable("GEMINI_API_KEY not set")
    safety.guard("vibe listen", 0.02)
    prompt = ('Listen carefully to the whole song. Reply with JSON only: {"vocalist": "gender and vocal character", "has_lyrics": true or false (true only if clearly intelligible sung words exist), '
              '"lyrics": "ONLY words you are certain of, with [Section] tags; empty string if the voice is wordless vocalise. Never invent lyrics", "genre": "...", "mood": "...", '
              '"instrumentation": "...", "summary": "two sentences on the feeling and arc of the piece", "seo_topic": "a 2-4 word subject a person would search for, e.g. Calm Focus Music"}')
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/mpeg", "data": base64.b64encode(audio.read_bytes()).decode()}}, {"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}}
    for attempt in range(4):                       # the audio model answers 503 when busy: wait and ask again
        r = http().post(f"https://generativelanguage.googleapis.com/v1beta/models/{LISTEN_MODEL}:generateContent", json=body, timeout=240, headers={"x-goog-api-key": key})
        if r.status_code == 200:
            break
        time.sleep(15 * (attempt + 1))
    if r.status_code != 200:
        raise ProviderError(f"gemini listen {r.status_code}")
    data = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    write_atomic(cache, json.dumps(data, indent=1, ensure_ascii=False))
    return data


# ---------------------------------------------------------------- AUDIO ANALYSIS

def analyse(audio: Path, fps: int = FPS) -> dict:
    """Beat grid and a per-frame energy envelope (bass and overall), computed from the file itself."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "22050", "-f", "s16le", "-"], capture_output=True, timeout=300, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    sr, hop = 22050, 512
    n = (len(x) - 1024) // hop
    win = np.hanning(1024).astype(np.float32)
    spec = np.stack([np.abs(np.fft.rfft(x[i * hop:i * hop + 1024] * win)) for i in range(n)])
    flux = np.maximum(0, np.diff(np.log1p(spec * 20), axis=0)).sum(axis=1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fr = sr / hop
    lo, hi = int(fr * 60 / 180), int(fr * 60 / 70)
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    lag = lo + int(np.argmax(ac[lo:hi]))
    bpm = 60 * fr / lag
    while bpm < 90:
        bpm *= 2
    while bpm > 150:
        bpm /= 2
    beat = 60 / bpm
    best, phase = -1.0, 0.0
    for p in np.arange(0, beat, 0.01):
        idx = np.round((np.arange(p, len(flux) / fr, beat)) * fr).astype(int)
        idx = idx[idx < len(flux)]
        s = flux[idx].sum()
        if s > best:
            best, phase = s, float(p)
    bass = spec[:, 1:12].mean(axis=1)
    full = spec.mean(axis=1)
    t = np.arange(int(len(x) / sr * fps)) / fps
    ix = np.minimum((t * fr).astype(int), len(bass) - 1)

    def norm(v):
        v = v[ix]
        k = int(fps * 0.25)
        v = np.convolve(v, np.ones(k) / k, "same")
        return np.clip((v - np.percentile(v, 5)) / (np.percentile(v, 98) - np.percentile(v, 5) + 1e-9), 0, 1)
    return {"bpm": round(float(bpm), 2), "beat": float(beat), "phase": phase, "bass": norm(bass), "energy": norm(full), "seconds": len(x) / sr}


def sections(ana: dict, fps: int = FPS) -> list[tuple[float, float, str]]:
    """The song's own structure from its energy: boundaries where the loudness steps up or down, snapped to bar lines. Returns (start, end, feel)."""
    e, dur, bar = ana["energy"], ana["seconds"], ana["beat"] * 4
    sec = lambda a, b: float(e[int(max(0, a) * fps):int(min(dur, b) * fps)].mean()) if b > a else 0.0
    step = bar
    grid = np.arange(0, dur, step)
    nov = np.array([abs(sec(t, t + 8) - sec(t - 8, t)) for t in grid])
    picks: list[float] = []
    for i in np.argsort(-nov):
        t = float(grid[i])
        if nov[i] < 0.10 or t < 12 or t > dur - 10:
            continue
        if all(abs(t - q) >= 12 for q in picks):
            picks.append(t)
    bounds = [0.0] + sorted(picks) + [dur]
    out = []
    for a, b in zip(bounds, bounds[1:]):
        m = sec(a, b)
        feel = "near silence" if m < 0.12 else "calm, sparse" if m < 0.30 else "building, groove" if m < 0.55 else "driving, full" if m < 0.75 else "peak, soaring"
        out.append((round(a, 3), round(b, 3), feel))
    return out


def shot_ranges(ana: dict, target: float = 15.0) -> list[tuple[float, float, str]]:
    """Shot start and end times: each section is split into shots near `target` seconds long, every cut on a bar line."""
    bar = ana["beat"] * 4
    out = []
    for a, b, feel in sections(ana):
        n = max(1, round((b - a) / target))
        for k in range(n):
            lo = a if k == 0 else round(a + round((b - a) * k / n / bar) * bar, 3)
            hi = b if k == n - 1 else round(a + round((b - a) * (k + 1) / n / bar) * bar, 3)
            out.append((lo, hi, feel))
    return out


# ---------------------------------------------------------------- PLAN

SYSTEM = f"""You are the creative director of Quiet Money's long-form music visuals: slow, hypnotic, cinematic films for a full song, for people who put it on and stay.
You get the song's lyrics, mood, summary and the number of shots. Return JSON only: {{"shots":[{{"prompt":"...","motion":"push|pull|left|right|rise|fall","clip_prompt":"..."}}]}}
Rules for every shot:
- It is a still frame of a film, 16:9, exceptionally beautiful and unmistakably NOT stock: one impossible or surreal image drawn from the feeling of that moment of the song
  (scale, nesting, gravity, time, reflection, loops), with two or three small specific true details, a named light source, two or three named colours, and a named lens and angle.
- One consistent world across the film (the song's mood and palette) and one quiet thread that returns: a lone woman seen only from behind or as a small silhouette.
  Vary subject, scale and camera distance between shots (wide, macro, low, high). No two shots alike.
- The shots follow the shot list in order and the song's real arc.
- Never repeat these used motifs: {BANNED}.
- Premium, painterly-photographic, rich detail, deep contrast, volumetric light. Never cartoon, never clip-art, never generic neon-grid synthwave cliche, never a stock photo.
- End every prompt with: {TAIL}
- "clip_prompt" describes only the slow camera and element motion of that image (one sentence), for the moments that get a few seconds of real video.
- Let the picture match the music: sparse and near-silent passages are still, vast and intimate; building passages gather light and movement; peaks are luminous and soaring.
- "motion" is the camera move across the still; alternate them so neighbours differ."""


def plan(info: dict, ranges: list[tuple[float, float, str]], title: str, work: Path) -> list[dict]:
    cache = work / "plan.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    safety.guard("vibe plan", 0.3)
    if not ledger.allow("vibe", "usd", 0.3, CAP_USD):
        raise ProviderUnavailable(f"vibe daily cap ${CAP_USD:.2f} reached")
    n = len(ranges)
    lines = "\n".join(f"{i + 1}. {a:.0f}s to {b:.0f}s ({b - a:.0f}s): the music is {feel}" for i, (a, b, feel) in enumerate(ranges))
    user = (f"Song title: {title}\nVocalist: {info.get('vocalist')} (the voice is {'sung words' if info.get('has_lyrics') else 'wordless vocalise: the title and the feeling are the only story'})\n"
            f"Genre: {info.get('genre')}\nMood: {info.get('mood')}\nInstrumentation: {info.get('instrumentation')}\nSummary: {info.get('summary')}\n"
            + (f"Lyrics:\n{info.get('lyrics')}\n" if info.get('has_lyrics') else "") + f"\nThe shot list, in order, with what the music does in each:\n{lines}\n\nWrite exactly {n} shots, one per line above.")
    body = {"model": MODEL, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], "response_format": {"type": "json_object"},
            "max_tokens": 9000, "usage": {"include": True}, "reasoning": {"effort": "low"}}
    r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=420, headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        raise ProviderError(f"openrouter {r.status_code}")
    d = r.json()
    ledger.spend("vibe", "usd", float((d.get("usage") or {}).get("cost") or 0), usd=float((d.get("usage") or {}).get("cost") or 0))
    from faceless.providers.llm import _extract_json
    data = _extract_json(d["choices"][0]["message"]["content"])
    shots = (data.get("shots") if isinstance(data, dict) else data) or []
    shots = shots[:n]
    for i, s in enumerate(shots):
        s["prompt"] = str(s.get("prompt", "")).strip()
        if TAIL not in s["prompt"]:
            s["prompt"] = s["prompt"].rstrip(". ") + ". " + TAIL
        if s.get("motion") not in MOTIONS:
            s["motion"] = MOTIONS[i % len(MOTIONS)]
    if len(shots) < n:
        raise ProviderError(f"the plan has {len(shots)} shots, wanted {n}")
    write_atomic(cache, json.dumps(shots, indent=1, ensure_ascii=False))
    return shots


# ---------------------------------------------------------------- STILLS AND CLIPS

def stills(shots: list[dict], work: Path) -> list[Path]:
    out = []
    for i, s in enumerate(shots):
        dest = work / f"shot{i + 1:02d}.png"
        if not dest.is_file():
            res = muapi.run(STILL_MODEL, {"prompt": s["prompt"], "aspect_ratio": "16:9", "resolution": "2K"}, work / "dl", job=f"vibe-{work.name}-{i + 1}")
            files = res.get("files") or []
            if not files:
                raise ProviderError(f"no image for shot {i + 1}")
            Image.open(files[0]).convert("RGB").save(dest)
        out.append(dest)
    return out


def clips(shots: list[dict], images: list[Path], work: Path) -> dict[int, Path]:
    got = {}
    for i, s in enumerate(shots):
        if not s.get("clip"):
            continue
        dest = work / f"clip{i + 1:02d}.mp4"
        if not dest.is_file():
            try:
                url = muapi.upload(images[i])
                res = muapi.run(CLIP_MODEL, {"prompt": s.get("clip_prompt") or "slow cinematic camera drift, light shimmering", "image_url": url, "resolution": "1080p", "duration": 5},
                                work / "dl", job=f"vibe-{work.name}-clip{i + 1}")
                f = (res.get("files") or [None])[0]
                if not f:
                    continue
                Path(f).replace(dest)
            except (ProviderError, ProviderUnavailable) as e:
                print(f"clip {i + 1} skipped: {e}")
                continue
        got[i] = dest
    return got


# ---------------------------------------------------------------- VOICEOVER

VO_VOICE = "pFZP5JQG7iQjIQuC4Bku"                 # Lily: velvety, warm, human (ElevenLabs premium voice, not the free robotic fallback)
VO_MODEL = "eleven_multilingual_v2"
VO_SETTINGS = {"stability": 0.38, "similarity_boost": 0.82, "style": 0.42, "use_speaker_boost": True}   # looser stability = more natural variation


def voiceover(lines: list[tuple[str, float]], work: Path) -> list[tuple[Path, float]]:
    """A short spoken welcome in the quiet opening and a short invitation in the quiet ending, by a premium female voice. Returns (file, start seconds)."""
    key = config.env("ELEVENLABS_API_KEY")
    if not key:
        raise ProviderUnavailable("ELEVENLABS_API_KEY not set")
    out = []
    for i, (text, start) in enumerate(lines):
        dest = work / f"vo{i + 1}.mp3"
        if not dest.is_file():
            safety.guard("vibe voiceover", 0.05)
            r = http().post(f"https://api.elevenlabs.io/v1/text-to-speech/{VO_VOICE}?output_format=mp3_44100_128", timeout=120,
                            headers={"xi-api-key": key}, json={"text": text, "model_id": VO_MODEL, "voice_settings": VO_SETTINGS})
            if r.status_code != 200:
                raise ProviderError(f"elevenlabs {r.status_code}")
            dest.write_bytes(r.content)
            ledger.spend("elevenlabs", "chars", len(text))
        out.append((dest, start))
    return out


# ---------------------------------------------------------------- RENDER

def ease(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def camera(motion: str, u: float, bass: float) -> tuple[float, float, float]:
    """Zoom and centre offset (fractions of the spare room) for a move at progress u in 0..1."""
    e = ease(u)
    zoom = 1.0 + 0.020 * bass                       # the picture breathes with the bass
    cx = cy = 0.5
    if motion == "push":
        zoom *= 1.0 + 0.12 * e
    elif motion == "pull":
        zoom *= 1.12 - 0.12 * e
    elif motion == "left":
        cx = 0.62 - 0.24 * e
        zoom *= 1.06
    elif motion == "right":
        cx = 0.38 + 0.24 * e
        zoom *= 1.06
    elif motion == "rise":
        cy = 0.62 - 0.24 * e
        zoom *= 1.06
    elif motion == "fall":
        cy = 0.38 + 0.24 * e
        zoom *= 1.06
    return zoom, cx, cy


class ClipReader:
    """Plays a short clip as the shot's moving picture: forward then backward (no seam) for as long as the shot needs."""

    def __init__(self, path: Path, size: tuple[int, int]):
        self.w, self.h = size
        pp = path.with_name(path.stem + "-pp.mp4")
        if not pp.is_file():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-filter_complex",
                            f"[0:v]scale={self.w}:{self.h}:flags=lanczos,fps={FPS},split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-an",
                            "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", str(pp)], check=True, timeout=600)
        self.pp = pp
        self.p = None
        self.k = -1
        self.cur = None
        self.first = None
        self._open()

    def _open(self):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(self.pp), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.k = -1

    def _next(self):
        buf = self.p.stdout.read(self.w * self.h * 3)
        if len(buf) < self.w * self.h * 3:
            self.p.kill()
            self._open()
            buf = self.p.stdout.read(self.w * self.h * 3)
        self.k += 1
        self.cur = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
        if self.first is None:
            self.first = self.cur
        return self.cur

    def frame(self, k: int) -> np.ndarray:
        if k <= 0:
            return self.first if self.first is not None else self._next()
        if self.first is None:
            self._next()
        while self.k < k:
            self._next()
        return self.cur

    def close(self):
        if self.p:
            self.p.kill()


def render(images: list[Path], shots: list[dict], ranges: list[tuple[float, float, str]], clip_files: dict[int, Path], audio: Path, title: str, out: Path, *, draft: bool = False,
           seconds: float | None = None, vo: list[tuple[Path, float]] | None = None) -> dict:
    out = Path(out)
    dur = seconds or songvideo.probe_seconds(audio)
    sc = 0.5 if draft else 1.0
    fps = 12 if draft else FPS
    w, h = round(1920 * sc), round(1080 * sc)
    work = Paths.cache / "vibe" / out.stem
    work.mkdir(parents=True, exist_ok=True)
    ana = analyse(audio, fps)
    n = len(images)
    starts = [r[0] for r in ranges]
    big = [songvideo.enhance(p, "deep", (round(w * ZOOM_SRC / songvideo.ZOOM), round(h * ZOOM_SRC / songvideo.ZOOM))) for p in images]
    readers = {i: ClipReader(p, (w, h)) for i, p in clip_files.items()} if clip_files else {}
    ov, pt = work / "overlay.png", work / "particles.mp4"
    songvideo.overlay(title, (w, h)).save(ov)
    songvideo.particles(pt, (w, h))
    u = h / 1080
    wave_w, wave_h, wave_y = round(720 * u), round(64 * u), round(990 * u)
    vo = vo or []
    if vo:
        legs = "".join(f"[{4 + k}:a]aresample=48000,volume=1.35,adelay={round(st * 1000)}|{round(st * 1000)}[vo{k}];" for k, (_, st) in enumerate(vo))
        ins = "".join(f"[vo{k}]" for k in range(len(vo)))
        audio_mix = f"{legs}[ma]{ins}amix=inputs={1 + len(vo)}:normalize=0:duration=first,alimiter=limit=0.97[a]"
    else:
        audio_mix = "[ma]anull[a]"
    fc = (f"[0:v]format=gbrp[bg];[1:v]scale={w}:{h}:flags=bicubic,format=gbrp[pt];[bg][pt]blend=all_mode=screen:all_opacity=0.55[b2];"
          f"[2:v]format=rgba,fade=t=in:st=0.6:d=1.6:alpha=1[ov];[b2]format=rgba[b3];[b3][ov]overlay=0:0,noise=alls=5:allf=t,format=gbrp[b4];"
          f"[3:a]asplit[wa][ma];[wa]aformat=channel_layouts=mono,showwaves=s={wave_w}x{wave_h}:mode=cline:rate={fps}:colors=white:scale=sqrt,format=gray[wm];"
          f"color=c=0xFFD23F:s={wave_w}x{wave_h}:r={fps},format=rgba[gold];[gold][wm]alphamerge,colorchannelmixer=aa=0.85,fade=t=in:st=1.2:d=1.6:alpha=1[wv];"
          f"[b4][wv]overlay=x=(W-w)/2:y={wave_y}:format=gbrp,format=yuv420p[v];{audio_mix}")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-stream_loop", "-1", "-i", str(pt), "-loop", "1", "-framerate", str(fps), "-i", str(ov), "-i", str(audio),
           *[x for f, _ in vo for x in ("-i", str(f))],
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-r", str(fps), "-c:v", "libx264", "-preset", "ultrafast" if draft else "medium",
           "-crf", "30" if draft else "19", *([] if draft else ["-maxrate", "18M", "-bufsize", "36M"]), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-t", f"{dur:.3f}", str(out)]
    out.parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    vignette = np.asarray(Image.radial_gradient("L").resize((w, h)), dtype=np.float32) / 255
    vignette = (1 - 0.38 * vignette)[..., None]
    total = int(np.ceil(dur * fps))
    half = XFADE / 2
    try:
        for f in range(total):
            t = f / fps
            idx = [i for i in range(n) if starts[i] - (half if i else 0) <= t < (starts[i + 1] + half if i + 1 < n else 1e9)]
            bass = float(ana["bass"][min(f if not draft else int(t * FPS), len(ana["bass"]) - 1)])
            energy = float(ana["energy"][min(f if not draft else int(t * FPS), len(ana["energy"]) - 1)])
            layers = []
            for i in idx:
                begin = starts[i] - (half if i else 0)
                end = (starts[i + 1] + half) if i + 1 < n else ana["seconds"]
                local = t - begin
                if i in readers:
                    fr = readers[i].frame(int(round(local * fps)))
                    im = fr.astype(np.float32)
                else:
                    zoom, cx, cy = camera(shots[i]["motion"], local / max(end - begin, 1e-6), bass)
                    src = big[i]
                    vw, vh = w * ZOOM_SRC / zoom, h * ZOOM_SRC / zoom
                    vw, vh = min(vw, src.width), min(vh, src.height)
                    left = (src.width - vw) * cx
                    top = (src.height - vh) * cy
                    im = np.asarray(src.transform((w, h), Image.EXTENT, (left, top, left + vw, top + vh), Image.BICUBIC), dtype=np.float32)
                alpha = 1.0
                if len(idx) == 2:
                    k = ease((t - (starts[idx[1]] - half)) / XFADE)
                    alpha = k if i == idx[1] else 1 - k
                layers.append((im, alpha))
            frame = sum(im * a for im, a in layers) if len(layers) > 1 else layers[0][0]
            fade_mid = 4 * (alpha_mid := (ease((t - (starts[idx[1]] - half)) / XFADE) if len(idx) == 2 else 0.0)) * (1 - alpha_mid)
            pil = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
            glow = pil.resize((max(2, w // 8), max(2, h // 8)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((w, h), Image.BICUBIC)
            gain = 0.16 + 0.30 * energy + 0.35 * bass + 0.30 * fade_mid
            out_f = np.asarray(pil, dtype=np.float32) / 255
            g = np.asarray(glow, dtype=np.float32) / 255
            out_f = 1 - (1 - out_f) * (1 - np.clip(g * gain, 0, 0.9))
            out_f = out_f * vignette * (1.0 + 0.05 * bass)
            enc.stdin.write((np.clip(out_f, 0, 1) * 255).astype(np.uint8).tobytes())
        enc.stdin.close()
        if enc.wait(timeout=FFMPEG_TIMEOUT) != 0:
            raise ProviderError("ffmpeg failed")
    finally:
        for r in readers.values():
            r.close()
        if enc.poll() is None:
            enc.kill()
    info = {"video": str(out), "seconds": round(dur, 2), "size": f"{w}x{h}", "fps": fps, "bpm": ana["bpm"], "shots": n, "clips": sorted(clip_files), "title": title, "draft": draft}
    write_atomic(out.with_suffix(".json"), json.dumps(info, indent=1))
    return info


# ---------------------------------------------------------------- ORCHESTRATION

def pick_clip_shots(ana: dict, ranges: list[tuple[float, float, str]], k: int) -> list[int]:
    """The k most energetic shots, spread apart (never neighbours), get a few seconds of real video."""
    e = ana["energy"]
    score = [(float(e[int(a * FPS):int(b * FPS)].mean()), i) for i, (a, b, _) in enumerate(ranges)]
    chosen: list[int] = []
    for _, i in sorted(score, reverse=True):
        if all(abs(i - j) > 1 for j in chosen):
            chosen.append(i)
        if len(chosen) == k:
            break
    return sorted(chosen)


def make(audio: Path, title: str, day: str | None = None, *, clip_n: int = 3, draft: bool = False, seconds: float | None = None, out_dir: Path | None = None,
         vo_lines: list[tuple[str, float]] | None = None) -> dict:
    """Listen, plan, make the pictures, render. Everything before the render is cached, so a re-run only pays for what is missing."""
    audio = Path(audio)
    day = day or config.today_utc().isoformat()
    slug = slug_of(title)
    work = Paths.cache / "vibe" / f"{day}-{slug}"
    work.mkdir(parents=True, exist_ok=True)
    info = listen(audio, work)
    ana = analyse(audio)
    ranges = shot_ranges(ana)
    shots = plan(info, ranges, title, work)
    for i in pick_clip_shots(ana, ranges, clip_n):
        shots[i]["clip"] = True
    images = stills(shots, work)
    clip_files = clips(shots, images, work) if clip_n else {}
    out = (out_dir or Paths.root / "music" / "videos" / day) / f"vibe-{slug}{'-draft' if draft else ''}.mp4"
    vo = voiceover(vo_lines, work) if vo_lines else []
    res = render(images, shots, ranges, clip_files, audio, title, out, draft=draft, seconds=seconds, vo=vo)
    res["listen"] = {k: info.get(k) for k in ("vocalist", "genre", "mood", "summary", "seo_topic", "has_lyrics")}
    STATE.mkdir(parents=True, exist_ok=True)
    write_atomic(STATE / f"{day}-{slug}.json", json.dumps({"title": title, "audio": audio.name, "video": str(out), "shots": len(shots), "clips": res["clips"], **res["listen"]}, indent=1, ensure_ascii=False))
    return res
