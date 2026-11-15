"""Text-to-speech providers.

Every provider returns (wav_path, words) where words = [{"w": str, "start": s, "end": s}].
Word timings drive caption sync and scene cuts, so providers without native timings
(Gemini) get an estimated alignment that is snapped to detected pauses.
"""

from __future__ import annotations

import asyncio
import base64
import re
import ssl
import subprocess
import time
import wave
from pathlib import Path

import requests

from faceless import config, ledger
from faceless.providers import ProviderError, ProviderUnavailable, http, run_chain


def rate_to_speed(rate: str | None) -> float:
    """Edge-style rate string ("+6%", "-4%") to a speed multiplier (1.06, 0.96)."""
    if not rate:
        return 1.0
    return 1 + float(rate.strip().rstrip("%")) / 100


def speed_to_rate(speed: float) -> str:
    pct = round((speed - 1) * 100)
    return f"{pct:+d}%"


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True, timeout=300)


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True, timeout=60).stdout.strip()
    return float(out)


def _to_wav(src: Path, dst: Path) -> None:
    # light broadcast chain: rumble cut, gentle compression, presence lift
    _ffmpeg("-i", str(src), "-af",
            "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=90,"
            "equalizer=f=3200:t=q:w=1.2:g=2", "-ar", "48000", "-ac", "1", str(dst))


# ---------------------------------------------------------------- edge (free)

def _edge_ssl_patch() -> None:
    bundle = config.ca_bundle()
    if not bundle:
        return
    import certifi
    import edge_tts.communicate as comm
    certifi.where = lambda: bundle
    comm._SSL_CTX = ssl.create_default_context(cafile=bundle)


EDGE_ATTEMPTS = 5
EDGE_TIMEOUT_S = 180
EDGE_BACKOFF_S = 4


def _nudged(rate: str, attempt: int) -> str:
    """The configured speed on the first try, then one point off in alternating directions (+14% -> +13%, +15%, +12%, +16%)."""
    m = re.fullmatch(r"([+-])(\d+)%", rate.strip())
    if not attempt or not m:
        return rate
    delta = (attempt + 1) // 2 * (-1 if attempt % 2 else 1)
    val = int(m.group(2)) * (1 if m.group(1) == "+" else -1) + delta
    return f"{val:+d}%"


def edge(text: str, out: Path, *, rate: str | None = None) -> list[dict]:
    try:
        import edge_tts
    except ImportError as e:
        raise ProviderUnavailable("edge-tts not installed") from e
    _edge_ssl_patch()
    cfg = config.load()["voice"]
    mp3 = out.with_suffix(".edge.mp3")
    words: list[dict] = []

    base_rate = rate or cfg["edge_rate"]

    async def go(use_rate: str):
        c = edge_tts.Communicate(text, cfg["edge_voice"], rate=use_rate, boundary="WordBoundary")
        with open(mp3, "wb") as f:
            async for ch in c.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    s = ch["offset"] / 1e7
                    words.append({"w": ch["text"], "start": round(s, 3), "end": round(s + ch["duration"] / 1e7, 3)})

    # Edge's service answers "no audio received" to some (text, speed) pairs and renders the same text at a neighbouring speed (2026-11-15: the
    # same line failed at +14% and +13% and worked at +15%, every time). So a retry changes the speed by a point, not the voice: the sound of the
    # channel stays the same, and a repeat of the identical request would only fail the same way.
    last = None
    for attempt in range(EDGE_ATTEMPTS):
        words.clear()
        try:
            asyncio.run(asyncio.wait_for(go(_nudged(base_rate, attempt)), timeout=EDGE_TIMEOUT_S))
            if words and mp3.stat().st_size >= 2000:
                last = None
                break
            last = ProviderError("edge returned no audio")
        except (Exception, asyncio.TimeoutError) as e:   # noqa: BLE001 - NoAudioReceived, a dropped socket and a hang all get the same retry
            last = e
        if attempt + 1 < EDGE_ATTEMPTS:
            time.sleep(EDGE_BACKOFF_S * (attempt + 1))
    if last is not None:
        raise last if isinstance(last, ProviderError) else ProviderError(f"edge: {type(last).__name__}: {last}"[:300])
    _to_wav(mp3, out)
    mp3.unlink(missing_ok=True)
    ledger.spend("edge", "chars", len(text))
    return words


# ---------------------------------------------------------------- elevenlabs (premium)

def elevenlabs(text: str, out: Path, *, rate: str | None = None) -> list[dict]:
    key = config.env("ELEVENLABS_API_KEY", "ELEVENLABS_API", "ELEVENLABS_api_KEY2")
    if not key:
        raise ProviderUnavailable("ELEVENLABS_API_KEY not set")
    cfg = config.load()["voice"]
    speed = max(0.85, min(1.15, rate_to_speed(rate)))
    r = http().post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{cfg['elevenlabs_voice']}/with-timestamps",
        headers={"xi-api-key": key},
        json={"text": text, "model_id": cfg["elevenlabs_model"],
              "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.25, "speed": speed}},
        timeout=240)
    if r.status_code != 200:
        raise ProviderError(f"elevenlabs {r.status_code}: {r.text[:200]}")
    d = r.json()
    mp3 = out.with_suffix(".el.mp3")
    mp3.write_bytes(base64.b64decode(d["audio_base64"]))
    _to_wav(mp3, out)
    mp3.unlink(missing_ok=True)
    al = d.get("alignment") or d.get("normalized_alignment") or {}
    words, cur, start, end = [], "", None, 0.0
    for ch, s, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                        al.get("character_end_times_seconds", [])):
        if ch.isspace():
            if cur:
                words.append({"w": cur, "start": round(start, 3), "end": round(end, 3)})
            cur, start = "", None
            continue
        if start is None:
            start = s
        cur += ch
        end = e
    if cur:
        words.append({"w": cur, "start": round(start, 3), "end": round(end, 3)})
    ledger.spend("elevenlabs", "chars", len(text))
    return [w for w in words if re.search(r"\w", w["w"])]


# ---------------------------------------------------------------- gemini (free tier, no timings)

def gemini(text: str, out: Path, *, rate: str | None = None) -> list[dict]:
    key = config.env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if not key:
        raise ProviderUnavailable("GEMINI_API_KEY not set")
    cfg = config.load()["voice"]
    pace = "briskly" if rate and not rate.startswith("-") else "at a steady pace"
    body = {"contents": [{"parts": [{"text": f"Read this {pace}, like a calm, confident documentary narrator:\n\n{text}"}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": cfg["gemini_voice"]}}}}}
    try:   # key in a header: urllib3 error messages echo the URL, and errors land in the committed journal
        r = http().post(f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['gemini_model']}:generateContent",
                        headers={"x-goog-api-key": key}, json=body, timeout=300)
    except requests.RequestException as e:
        raise ProviderError(f"gemini-tts {type(e).__name__}") from e
    if r.status_code != 200:
        raise ProviderError(f"gemini-tts {r.status_code}: {r.text[:200]}")
    part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
    pcm = base64.b64decode(part["data"])
    raw = out.with_suffix(".gem.wav")
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    _to_wav(raw, out)
    raw.unlink(missing_ok=True)
    ledger.spend("gemini-tts", "chars", len(text))
    return estimate_timings(text, out)


def _silences(path: Path, noise_db: int = -35, min_d: float = 0.18) -> list[tuple[float, float]]:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_d}", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=120)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    return list(zip(starts, ends))


def estimate_timings(text: str, wav: Path) -> list[dict]:
    """Distribute words over speech time by character weight, then snap sentence ends to pauses."""
    total = duration(wav)
    sil = _silences(wav)
    lead = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    tail = sil[-1][0] if sil and sil[-1][1] >= total - 0.05 else total
    tokens = text.split()
    weights = [len(re.sub(r"\W", "", t)) + 1.6 + (2.5 if t[-1] in ".!?" else 1.2 if t[-1] in ",;:" else 0)
               for t in tokens]
    scale = (tail - lead) / sum(weights)
    words, t = [], lead
    for tok, wgt in zip(tokens, weights):
        d = wgt * scale
        words.append({"w": tok, "start": round(t, 3), "end": round(t + d * 0.85, 3)})
        t += d
    # snap: the word after each long pause starts at that pause's end
    for s0, s1 in sil:
        if s0 <= lead or s1 >= tail:
            continue
        nxt = min(range(len(words)), key=lambda i: abs(words[i]["start"] - s1))
        shift = s1 - words[nxt]["start"]
        if abs(shift) < 0.6:
            for w in words[nxt:]:
                w["start"] = round(w["start"] + shift, 3)
                w["end"] = round(w["end"] + shift, 3)
    return words


PROVIDERS = {"edge": edge, "elevenlabs": elevenlabs, "gemini": gemini}


def synthesize(text: str, out: Path, *, rate: str | None = None, prefer: str | None = None,
               job: str | None = None) -> tuple[str, list[dict]]:
    chain = list(config.load()["voice"]["chain"])
    if prefer and prefer in PROVIDERS:
        chain = [prefer] + [c for c in chain if c != prefer]
    return run_chain("tts", [(n, (lambda f=PROVIDERS[n]: f(text, out, rate=rate))) for n in chain if n in PROVIDERS],
                     job=job)
