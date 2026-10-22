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
RULES = ("vertical 9:16, 10 seconds, slow cinematic camera, no people's faces, no text or numbers anywhere, no logos or brands, "
         "no dialogue or music")
SUBJECTS = {   # per series: 10-second scenes with a hook in the first second and a reveal by the last; rotated by date
    "story": ["a dusty leather wallet bursts open and a river of gold coins spills across a black desk in slow motion, the camera racing alongside",
              "a vintage car crashes through a garage wall and rockets into a sky full of falling gold coins, low angle, wind and dust",
              "a pocket watch shatters into a swarm of glowing gears that reassemble into a golden hourglass floating in a dark void",
              "a lunch box cracks open and a bright sunrise erupts out of it, flooding a workshop with light, push-in"],
    "math": ["a stack of gold coins grows into a skyscraper of coins in one fast crane up, each coin clicking into place, dark studio",
             "a single seed explodes into a giant golden tree in time-lapse, roots tearing through the floor, fast push-in",
             "a line of dominoes topples at lightning speed, the last domino becomes a glowing gold staircase climbing into the clouds",
             "a snowball the size of a planet rolls down a mountain, growing with every turn, the camera racing ahead of it"],
    "psychology": ["a glowing phone screen shatters and a shopping cart rockets out of the shards down a neon aisle, fast whip pan",
                   "a candy jar bursts open, candy freezes mid-air and turns into golden coins, slow motion, sharp backlight",
                   "a savings jar and a bank vault face off, the vault splits open and a golden tidal wave of coins rushes the camera",
                   "a cosmic crossroad splits the sky in two, one path erupting in fire, the other in gold light, the camera spins between them"],
    "myth": ["a cracked glass sphere explodes outward in slow motion, golden light bursting through every shard, extreme close-up",
             "a rusty padlock snaps open with a shock wave that ripples through a dark sea, fast push-in, sparks flying",
             "a chalk drawing on a blackboard comes to life, the chalk lines tear off the board and swirl into a golden tornado",
             "a house of cards stands in a storm, a single card flips and the whole tower erupts into a flock of golden birds"],
    "playbook": ["piles of receipts fly up and form a neat golden staircase, camera tilts up as the last receipt snaps into place",
                 "a calendar's pages flip at high speed, one date blazes gold and lifts off the page toward the camera",
                 "a notebook page tears itself out and transforms into a golden map, pen strokes racing across it, overhead",
                 "a piggy bank cracks open and a sunrise launches out of it into a dark sky, fast push-in"],
    "escape": ["a massive steel door blasts open in slow motion, a tidal wave of golden daylight pours through, camera pulled back by the blast",
               "a commuter train bursts off its rails into the sky and flies over a glowing city at dawn, low angle, speed lines",
               "a hamster wheel spins faster and faster until it tears free and rolls out the door into a golden sunrise",
               "a rope bridge snaps and a rocket launches from the canyon below, racing up through clouds into the stars"],
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
