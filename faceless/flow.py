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
RULES = ("vertical 9:16, 10 seconds, cinematic 4K, photoreal, expressive human faces welcome, no text or numbers anywhere, "
         "no logos or brands, no dialogue, no music")
SUBJECTS = {   # per series: one self-contained prompt per scene, with timed beats (0-3s, 3-7s, 7-10s), a named subject, an action, a payoff
    "story": [
        "A rusted pocket watch on a frozen lake at dusk. 0-3s: a crack runs across the ice beneath it and it sinks into a black hole. 3-7s: the camera drops under the ice as the watch hands spin backward and a shaft of gold light climbs up through the crack. 7-10s: the shaft widens into a golden door that swings open onto a sunrise, and the camera passes through it. Locked-off low angle, then a fast push-in.",
        "A vintage pickup truck bursts out of a dusty barn at dawn, driven by a silhouetted figure in a leather jacket and a worn helmet. 0-3s: it smashes through a barbed-wire fence. 3-7s: it races along a canyon road toward a giant golden toll barrier. 7-10s: it hits the barrier at full speed, the barrier shatters into gold coins that rain over the truck, and it leaps into open sky. Chase camera from behind, then a wide aerial.",
        "A wooden lunch box on a workbench in a dark garage. 0-3s: the lid pops open and a bright sunrise erupts out of it, flooding the room with light. 3-7s: tools lift off the bench and spin in orbit around the sunlight as it grows into a hot golden disc. 7-10s: the disc tears free and rolls across the garage floor toward the camera like a wheel of fire, sparks flying. Low dolly push-in, then handheld shake on impact.",
    ],
    "math": [
        "A single gold seed in cracked dry earth at night. 0-3s: the seed splits with a flash and a golden root shoots down into the soil. 3-7s: time-lapse as the root spreads through the ground, lifting stones, and a trunk bursts up and grows into a giant golden tree in seconds, its branches blooming into coins. 7-10s: the camera rises above the canopy as the roots glow through the desert floor like a city grid. Crane up under moonlight.",
        "A line of three hundred black dominoes on a black glass floor in a huge empty hall. 0-3s: the first domino tips and sparks race down the line. 3-7s: the dominoes topple in a curve, each one turning gold as it falls and the whole line arcing toward the camera. 7-10s: the last domino lands and the gold line rises into a glowing staircase climbing into the clouds. Overhead tracking shot, then a low angle on the staircase.",
        "A snowball the size of a mountain starts rolling down a steep alpine slope under a blue dusk sky. 0-3s: it breaks loose with a crack and the camera races ahead of it. 3-7s: it picks up trees, boulders and a frozen lake, growing bigger with every turn. 7-10s: it crests a ridge and blasts into a valley of glowing gold snow, filling the whole frame. Fast drone shot that pulls back wide.",
    ],
    "psychology": [
        "A glass phone screen glowing in a dark bedroom, with a shopping cart on the other side of the glass. 0-3s: the screen cracks and the cart bursts out and rolls down a neon aisle toward the camera. 3-7s: its wheels spark as it races past endless shelves, the price tags melting into fire. 7-10s: the cart tips over a cliff edge into a silent void, and a single gold coin floats in its place. Fast whip pan, then a slow push-in onto the coin.",
        "A candy jar and a steel savings vault stand on a kitchen counter at night. 0-3s: the candy jar cracks open and candy flies into the air, freezing mid-flight in slow motion. 3-7s: each candy turns into a gold coin and the coins fly into the open vault. 7-10s: the vault door slams shut and a golden tidal wave of coins rushes out from under it toward the camera. Slow motion with a sharp backlight, then a fast dolly back.",
        "A stone crossroad at the edge of a foggy canyon at dusk, with two glowing paths ahead. 0-3s: the left path erupts in orange fire. 3-7s: the right path ignites in gold light, and a silhouetted figure stands between them with its arms spread. 7-10s: the fire and the gold merge into one white beam that shoots up through the clouds. Overhead orbit around the figure, then a crane up.",
    ],
    "myth": [
        "A cracked glass sphere on a black pedestal in a dark studio. 0-3s: the sphere splits from the inside and gold light pours through every crack. 3-7s: the shards lift off the pedestal and orbit the camera, each reflecting a different city at night. 7-10s: the shards snap back together into one perfect golden sphere that rises out of frame. Extreme close-up in slow motion, then a fast crane up.",
        "A rusty padlock on a steel vault door at the end of a dark tunnel. 0-3s: a golden wire spider the size of a hand crawls down the door toward the lock. 3-7s: it reaches the shackle and snaps it open in a burst of sparks. 7-10s: the vault door swings out and a river of gold coins rolls toward the camera. Locked-off wide shot, then a fast push-in onto the coins.",
        "A chalk drawing of a mountain on a blackboard in an empty classroom at night. 0-3s: a single chalk line starts to move on its own across the board. 3-7s: the lines tear off the board and spin into a golden tornado that fills the room and lifts the desks. 7-10s: the tornado collapses into a sunrise drawn in light on the back wall. Dolly through the room, then a locked-off wide.",
    ],
    "playbook": [
        "A stack of paper receipts on a clean desk in a bright office at dawn. 0-3s: the receipts lift off and fly into a neat formation. 3-7s: they stack into a golden staircase, each step snapping into place with a sharp sound. 7-10s: the top receipt flips to reveal a single gold line leading up into the light. Overhead shot, then a slow crane up along the staircase.",
        "A paper calendar on a wall in a dark room. 0-3s: its pages flip at high speed and one date blazes gold. 3-7s: the gold date peels off the wall and flies toward the camera, leaving a trail of light. 7-10s: it lands on a wooden desk and opens like a map that spreads to fill the frame. Close push-in, then an overhead view.",
        "A ceramic piggy bank on a windowsill in a dark bedroom at night. 0-3s: the piggy bank cracks open along its seam with a bright flash. 3-7s: a sunrise erupts out of it and climbs over the windowsill, turning the room gold. 7-10s: the sun rolls out of the window and across the rooftops of a sleeping city. Locked-off wide, then a fast push-out through the window.",
    ],
    "escape": [
        "A massive steel door at the end of a dark tunnel, sealed with heavy chains. 0-3s: the chains snap in a blast of white light. 3-7s: the door bursts open and a tidal wave of golden daylight pours down the tunnel toward the camera, dragging dust and paper in its path. 7-10s: the light fills the frame and a silhouetted figure steps out into an endless sunrise. Camera pulled back by the blast, then a slow push-in onto the figure.",
        "A commuter train speeds along a rail line over a dark glowing city at night. 0-3s: the train jumps its rails in a shower of sparks. 3-7s: it flies up into the sky above the skyline, speed lines streaking past its windows. 7-10s: it curves upward through the clouds toward a full moon. Low-angle chase, then a wide aerial as it climbs.",
        "A rocket on a cliff launch pad under a red sky, with a visored astronaut silhouette at the foot of the ladder. 0-3s: the astronaut climbs the ladder two rungs at a time. 3-7s: the countdown lights flicker on in sequence and the engines ignite in a roaring white flame. 7-10s: the rocket lifts off and its flame stretches across the frame into a sky full of stars. Tracking shot from ground level, then a crane up.",
    ],
}


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
        rows.append((pillar, f"{subject} {RULES}.", f"{pillar}-{day.replace('-', '')}-{k + 1}.mp4"))
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
