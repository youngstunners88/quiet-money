"""Music library: real instrumental beds per series, generated once, reused for every video.

Why: the procedural bed made every video sound alike, and YouTube's monetization policy asks for content that is not
interchangeable video to video. A handful of distinct tracks per series fixes that for cents, once.
`python -m faceless music --build` generates the missing tracks (Lyria RealTime, free tier; needs `pip install google-genai`),
`python -m faceless music` lists the library. Videos pick a track by series and job seed (`pick`); no track means the procedural bed, so nothing can break.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

from faceless import config
from faceless.config import Paths

DIR = Paths.root / "assets" / "music"
MANIFEST = DIR / "manifest.json"
BASE = ("Instrumental background music bed under a voice-over for an educational video: steady energy, plenty of space in the "
        "mid frequencies for a voice, no sudden drops, gentle intro. ")
SECONDS = 80
MOODS = {   # series -> distinct musical directions: (prompt, bpm, scale, brightness, density); one track each
    "story": [("warm nostalgic felt piano with soft strings, slow and reflective", 78, "MAJOR", 0.45, 0.35),
              ("gentle acoustic guitar with light brushed percussion and a hint of cello, storytelling mood", 84, "MAJOR", 0.5, 0.4)],
    "math": [("minimal glassy marimba and soft pulses, precise and curious, slowly building", 96, "PENTATONIC", 0.6, 0.4),
             ("clean electric piano arpeggios over a quiet synth pad, analytical and calm", 100, "MAJOR", 0.55, 0.4)],
    "psychology": [("introspective soft pads with a subtle heartbeat-like pulse and distant piano, thoughtful", 70, "MINOR", 0.35, 0.3),
                   ("dreamy lo-fi keys with warm tape texture and muted drums, contemplative", 76, "MAJOR", 0.4, 0.35)],
    "myth": [("tense low cello drone with dry clicky percussion, skeptical and investigative", 92, "MINOR", 0.3, 0.45),
             ("dark minimal electronic pulse with plucked strings, myth-busting edge", 98, "MINOR", 0.35, 0.5)],
    "playbook": [("upbeat light groove with plucked bass, bright keys and finger snaps, practical and motivating", 104, "MAJOR", 0.7, 0.5),
                 ("friendly clean funk guitar with soft drums, can-do energy", 108, "MAJOR", 0.7, 0.5)],
    "escape": [("cinematic rising strings and hopeful piano with a restrained driving pulse, escape and freedom", 90, "MAJOR", 0.6, 0.5),
               ("quiet orchestral build with warm brass swells, ambitious and determined", 94, "MAJOR", 0.6, 0.5)],
}
TARGET_LUFS = -17.5     # the level of the procedural bed (measured), so production.music_volume keeps meaning the same thing


def load() -> dict:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"tracks": []}


def tracks(pillar: str | None = None) -> list[dict]:
    out = [t for t in load()["tracks"] if (DIR / t["file"]).exists()]
    return [t for t in out if not pillar or t["pillar"] == pillar]


def pick(pillar: str, seed: int) -> Path | None:
    """The track for this video: the series' own tracks first, rotating by seed; any track if the series has none."""
    pool = tracks(pillar) or tracks()
    if not pool:
        return None
    return DIR / pool[seed % len(pool)]["file"]


def _duration(path: Path) -> float:
    if not shutil.which("ffprobe"):
        return 0.0
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, timeout=30, check=False)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def plan() -> list[tuple[str, int, tuple]]:
    have = {t["file"] for t in tracks()}
    per = int(config.load().get("music", {}).get("tracks_per_series", 2))
    return [(p, k, moods[k]) for p, moods in MOODS.items() for k in range(min(per, len(moods))) if f"{p}-{k + 1}.mp3" not in have]


def finish(wav: Path, out: Path) -> bool:
    """48 kHz stereo WAV -> mono 80 kbps MP3 at the procedural bed's loudness, with a fade in and out. True when ffmpeg succeeded."""
    secs = _duration(wav)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "1", "-ar", "44100",
                        "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=7,afade=t=in:d=1.2,afade=t=out:st={max(0, secs - 2.5):.2f}:d=2.5",
                        "-c:a", "libmp3lame", "-b:a", "80k", str(out)], capture_output=True, timeout=120, check=False)
    return r.returncode == 0 and out.exists() and out.stat().st_size > 50_000


def build(limit: int | None = None) -> list[dict]:
    """Generate the missing tracks (a few minutes each of real time). Each result is checked before it is kept."""
    from faceless.providers import ProviderUnavailable
    from faceless.providers import music as provider
    DIR.mkdir(parents=True, exist_ok=True)
    man = load()
    done = []
    for pillar, k, (mood, bpm, scale, bright, dens) in plan()[:limit]:
        name = f"{pillar}-{k + 1}.mp3"
        wav, tmp = DIR / f".{name}.wav", DIR / f".{name}.part.mp3"
        try:
            provider.generate(BASE + mood, wav, seconds=SECONDS, bpm=bpm, scale=scale, brightness=bright, density=dens)
        except ProviderUnavailable as e:
            done.append({"file": name, "skipped": str(e)})
            break
        except Exception as e:  # noqa: BLE001 - one failed track must not stop the rest
            done.append({"file": name, "failed": f"{type(e).__name__}: {str(e)[:160]}"})
            continue
        ok = finish(wav, tmp)
        wav.unlink(missing_ok=True)
        secs = _duration(tmp) if ok else 0.0
        if not ok or secs < 60:
            tmp.unlink(missing_ok=True)
            done.append({"file": name, "failed": f"encode/length check failed ({secs:.0f}s)"})
            continue
        tmp.replace(DIR / name)
        row = {"file": name, "pillar": pillar, "mood": mood, "bpm": bpm, "scale": scale, "model": "lyria-realtime-exp", "seconds": round(secs, 1),
               "sha256": hashlib.sha256((DIR / name).read_bytes()).hexdigest()[:16], "made": date.today().isoformat(),
               "note": "AI-generated instrumental (Google Lyria RealTime via the Gemini API); output carries Google's SynthID watermark"}
        man["tracks"] = [t for t in man["tracks"] if t["file"] != name] + [row]
        MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")
        done.append(row)
    return done
