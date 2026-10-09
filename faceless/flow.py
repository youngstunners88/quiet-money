"""Flow lane: the owner's daily Google Flow routine, wired into the factory without any unofficial automation.

Why a lane and not a bot: Flow runs on the owner's Google login and free daily credits. Scripting that login (a saved
session, a reverse-engineered client) breaks Google's terms and risks the account, so the agent never touches it.
The agent does the rest of the work around the ten minutes only a person should spend:

  1. `python -m faceless flow`            writes channel/flow/shotlists/<day>.md: three ready-to-paste prompts (one per series)
  2. the owner pastes them into Flow and saves the clips into channel/flow/inbox/ as <pillar>-<anything>.mp4
  3. the next video of that series claims a clip: it becomes the hook shot (beat 0) instead of a still, so it saves an
     image and gives the opening real motion; the clip is moved to channel/flow/used/ and copied into the job folder.
An empty inbox changes nothing: the pipeline falls back to the generated still. Clips are AI output and the video's
AI disclosure already covers them.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

from faceless import analytics, config
from faceless.config import Paths

DIR = Paths.root / "channel" / "flow"
INBOX, USED, LISTS = DIR / "inbox", DIR / "used", DIR / "shotlists"
RULES = ("vertical 9:16, 8 seconds, slow cinematic camera, no people's faces, no text or numbers anywhere, no logos or brands, "
         "no dialogue or music")
SUBJECTS = {   # per series: scenes that read as the idea without a face or a word; rotated by date so no two days repeat
    "story": ["a worn leather wallet and one old coin on a dark wooden desk, dust drifting through a window beam",
              "a vintage car parked alone in a quiet garage, one bulb overhead",
              "an old pocket watch ticking beside a stack of faded letters",
              "an empty lunch box and a thermos on a workbench at dawn"],
    "math": ["gold coins stacking one at a time on a dark surface, macro, warm rim light",
             "a single seed sprouting into a small tree in time-lapse on dark soil, soft side light",
             "dominoes toppling in a long curve, shallow depth of field, dark studio",
             "a snowball rolling down a slope and growing, wide, blue hour"],
    "psychology": ["a hand hesitating over a glowing phone on a nightstand, screen unreadable, dim room",
                   "a shopping cart rolling slowly down an empty aisle under cold light",
                   "a candy jar and a savings jar side by side on a kitchen counter, light shifting between them",
                   "a person's silhouette at a crossroads of two glowing paths, fog, wide"],
    "myth": ["a cracked glass sphere slowly filling with golden light in a dark studio",
             "a rusty padlock opening itself, macro, dramatic side light",
             "a chalk drawing on a blackboard being wiped away by a hand, slow",
             "a house of cards in warm light, one card sliding out slowly"],
    "playbook": ["hands sorting receipts into neat stacks on a clean desk, overhead, soft morning light",
                 "a calendar page turning to a highlighted date, close, shallow focus",
                 "a notebook with a pen checking off a list, overhead, warm lamp",
                 "a piggy bank on a windowsill as morning light slowly rises"],
    "escape": ["a heavy steel door swinging open to bright daylight, dust in the light beam, slow push-in",
               "a commuter train leaving an empty platform at dawn, wide, cold tones",
               "a hamster wheel slowing to a stop in a dim room, macro",
               "a rope bridge over a misty canyon, a gate opening at the far end"],
}
CAMERAS = ["slow push-in", "slow dolly left to right", "slow orbit", "slow crane up", "static with subtle handheld drift"]


def enabled() -> bool:
    return bool(config.load()["production"].get("flow", {}).get("enabled", False))


def shotlist(day: str | None = None, n: int = 3) -> Path:
    """Three prompts for the day: the series with the biggest weight first, subjects rotated by date. Deterministic."""
    day = day or config.today_utc().isoformat()
    ordinal = date.fromisoformat(day).toordinal()
    weights = analytics.pillar_weights()
    order = sorted(weights, key=lambda k: (-weights[k], (list(weights).index(k) - ordinal) % len(weights)))
    rows = []
    for k, pillar in enumerate(order[:n]):
        pool = SUBJECTS.get(pillar)
        if not pool:
            continue
        subject = pool[(ordinal + k) % len(pool)]
        camera = CAMERAS[(ordinal + 2 * k) % len(CAMERAS)]
        rows.append((pillar, f"{subject[0].upper()}{subject[1:]}. {camera}. {RULES}.", f"{pillar}-{day.replace('-', '')}-{k + 1}.mp4"))
    LISTS.mkdir(parents=True, exist_ok=True)
    out = LISTS / f"{day}.md"
    L = [f"# Flow shot list for {day}", "",
         f"About 10 minutes. Paste each prompt into Flow, generate, download, and save the clip into `channel/flow/inbox/` under the file name shown. "
         f"Inbox now holds {len(list(INBOX.glob('*.mp4'))) if INBOX.exists() else 0} clip(s).", "",
         "Use your own Google account in your own browser; nothing here logs in for you. Check Flow's current terms allow commercial use "
         "of what you generate before relying on a clip.", ""]
    for pillar, prompt, name in rows:
        L += [f"## {pillar} -> `{name}`", "", f"> {prompt}", ""]
    out.write_text("\n".join(L), encoding="utf-8")
    return out


def probe(path: Path) -> dict | None:
    """Duration/size of a clip, or None when it is not a usable video."""
    if not shutil.which("ffprobe"):
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, timeout=30, check=False)
    try:
        d = json.loads(r.stdout)
        return {"duration": float(d["format"]["duration"]), "width": d["streams"][0]["width"], "height": d["streams"][0]["height"]}
    except (ValueError, KeyError, IndexError):
        return None


def waiting(pillar: str | None = None) -> list[Path]:
    """Inbox clips, the series' own first."""
    if not INBOX.exists():
        return []
    clips = sorted(INBOX.glob("*.mp4"))
    return sorted(clips, key=lambda p: (not (pillar and p.name.startswith(pillar + "-")), p.name))


def claim(job, need: float) -> dict | None:
    """Take the best waiting clip for this job's hook: its series first, then any. The clip must run at least `need` seconds
    and be at least 480 px wide; it is moved to used/ and copied into the job folder, so a re-run never depends on the inbox."""
    if not enabled():
        return None
    for clip in waiting(job.pillar):
        info = probe(clip)
        if not info or info["duration"] < need or info["width"] < 480:
            continue
        USED.mkdir(parents=True, exist_ok=True)
        dest = job.dir / "hook-clip.mp4"
        job.dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(clip, dest)
        frame = job.dir / "hook-clip.jpg"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "0.5", "-i", str(dest), "-frames:v", "1",
                        "-q:v", "2", str(frame)], capture_output=True, timeout=60, check=False)
        if not frame.exists():
            dest.unlink(missing_ok=True)
            continue
        shutil.move(str(clip), str(USED / f"{job.id}-{clip.name}"))
        return {"clip": str(dest), "frame": str(frame), "source": clip.name, **info}
    return None


def status() -> dict:
    return {"inbox": len(waiting()), "used": len(list(USED.glob("*.mp4"))) if USED.exists() else 0,
            "latest_list": max((p.name for p in LISTS.glob("*.md")), default=None) if LISTS.exists() else None}
