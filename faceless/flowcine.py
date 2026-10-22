"""Cinematic Flow lane: three 10-second, captionless, high-energy AI clips a day for the owner's Google Flow session.

Why a lane: Flow gives free daily credits and 10-second clips, and the owner makes the clips by hand (the same rule as
faceless/flow.py: no scripted Google login). The engine writes the day's three prompts, the owner generates and saves
the clips into channel/flow/cinematic/inbox/, and the engine adds the Quiet Money branding later. No captions here by design.

Every prompt must earn its ten seconds: a hook in the first second, one big reveal or transformation in the middle, and
a strong last frame. Scenes are rotated so no scene repeats within four days.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from faceless.config import Paths

DIR = Paths.root / "channel" / "flow" / "cinematic"
SHOTLISTS, INBOX, USED = DIR / "shotlists", DIR / "inbox", DIR / "used"
RULES = ("vertical 9:16, 10 seconds, cinematic 4K, IMAX scale, no text, no letters, no numbers, no logos, no brands, "
         "no human faces, no dialogue, no music")
SCENES = [
    "hyper-speed dive through a wormhole of gold and violet light; at second six the tunnel snaps open onto a planet-sized "
    "golden coin hanging in black space, starlight rippling across its face, then a slow push-in and a hard cut to black",
    "a supermassive black hole swallows a glowing bank vault in slow motion; the vault door peels open and a river of gold "
    "light pours out in a spiral, extreme low angle",
    "a spacecraft rockets straight up out of a glowing ringed planet, leaving a blazing trail that splits the sky into two "
    "suns; the camera whip-pans to follow, sparks and anamorphic lens flare",
    "crash zoom from a city's night lights into a tiny glowing dot in the void; the dot ignites into a comet that streaks "
    "away across the frame, kinetic handheld, then freezes on a single bright pixel of light",
    "a crystal moon cracks in slow motion and bursts into thousands of silver shards that re-form in zero gravity into a "
    "single golden hourglass, spinning slowly, ending on the sand starting to fall",
    "an aurora storm over a frozen alien ocean: a towering wave of light rises and freezes mid-crest, then a gold mega-structure "
    "rises out of the ice in one fluid crane shot, ending on a wide reveal",
    "macro of a single gold coin spinning on a black mirror surface in slow motion; each spin sends concentric shockwaves "
    "of starlight across a galaxy reflected below, ending with the coin landing upright in perfect silence",
    "a rocket launches from a cliff under two suns, the camera racing alongside at ground level, then the frame rolls ninety "
    "degrees as the rocket punches through the clouds into a sea of stars",
    "a nebula collapses in time-lapse into a glowing sphere that unfolds into a city of floating towers at dawn; the camera "
    "drifts through a gap between towers and out over the clouds",
    "a violet tidal wave of light rolls across an endless silver desert; a lone glowing door stands in its path, the wave parts "
    "around it, and the door swings open onto sunrise, slow motion",
    "a golden meteor streaks across a midnight sky, slows to a crawl as it nears a lone cabin on a frozen moon, then bursts "
    "into a shower of gold sparks that trace one perfect circle in the air",
    "gravity inversion: a glowing train of carriages races through an asteroid belt, the camera rolls upside down as the track "
    "curls into a loop around a ringed planet, ending with the train vanishing into light",
]


def pick(day: date, n: int = 3) -> list[str]:
    """Three scenes for `day`: consecutive slots in the rotation, so a scene comes back only after every other scene has run."""
    start = day.toordinal() * n
    return [f"{SCENES[(start + k) % len(SCENES)]}. {RULES}." for k in range(n)]


def shotlist(day: date | None = None) -> Path:
    """Writes channel/flow/cinematic/shotlists/<day>.md: the day's three prompts, ready to paste into Flow."""
    day = day or date.today()
    prompts = pick(day)
    lines = [f"# Cinematic Flow shot list {day.isoformat()}", "",
             "Paste each prompt into Google Flow (10-second clip, vertical). Save each clip into `channel/flow/cinematic/inbox/` as",
             "`<NN>-<anything>.mp4`, where NN is the number below. No captions: the engine adds the branding later.", ""]
    for k, p in enumerate(prompts, 1):
        lines += [f"## {k:02d}", "", p, ""]
    SHOTLISTS.mkdir(parents=True, exist_ok=True)
    path = SHOTLISTS / f"{day.isoformat()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def status() -> dict:
    inbox = sorted(p.name for p in INBOX.glob("*.mp4")) if INBOX.exists() else []
    return {"inbox": inbox, "waiting": len(inbox), "shotlists": sorted(p.stem for p in SHOTLISTS.glob("*.md")) if SHOTLISTS.exists() else []}
