"""The host: Quiet Money's recurring front man. One face, one voice, once a week.

Consistency is a procedure, not luck, so every generation goes through the same four locks:
  1. FACE   the owner's reference photograph (channel/host/reference.png) is passed as @image1 to every image-to-video model; a Gemini Omni
            *character* is made from it once and its id reused where that model family is used.
  2. VOICE  a custom voice profile made with `gemini-omni-audio` (a base voice reshaped by a written description; free; nobody has heard it), and a
            *voice anchor*: the 10-15 s of the first intro's own audio, passed as a reference audio to later clips so the timbre carries over.
  3. LOOK   one wardrobe and one room (BIBLE.md): black blazer, charcoal roll-neck, the small gold Q pin on the left lapel, warm bokeh lounge.
  4. SEED   a fixed seed where the model takes one.
The files that hold the locks live in channel/host/ (host.json, BIBLE.md, reference.png, voice-anchor.wav). Nothing here posts anything;
the clip is packaged as a job and goes out through the normal publisher once the owner has approved it. Generating a clip spends money: the
desk estimates first, shows the price, and runs only with apply=True.
"""

from __future__ import annotations

import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from faceless import config, decide, events, muapi
from faceless.config import STUDIO
from faceless.fsutil import write_atomic
from faceless.providers import ProviderError, ProviderUnavailable

def _today() -> date:
    return datetime.now(timezone.utc).date()          # dates come from UTC, never from the machine's zone


DIR = STUDIO / "channel" / "host"
STATE = DIR / "host.json"
REFERENCE = DIR / "reference.png"
ANCHOR = DIR / "voice-anchor.wav"

NAME = "Quinton"       # the owner named him (2026-10-12)
VOICE_BASE = "orus"
VOICE_NAME = "Quiet Money Host v1"
VOICE_DESCRIPTION = ("A one-of-a-kind male voice in his early thirties: low, warm baritone with a faint natural rasp, relaxed and unhurried, the calm "
                     "confidence of someone who has already done the thing he is explaining. Slightly smiling delivery, intimate like talking to one "
                     "person across a table, short pauses before the key number, never salesy, never shouting. Neutral international English with a "
                     "hint of soft transatlantic polish. Emotion: encouraging, grounded, quietly determined.")
VOICE_SAMPLE = "Welcome to Quiet Money. Stay with me, and we will build this together."

LOOK = ("a man in his early thirties, short dark swept-up hair, light stubble, calm direct eyes, black tailored blazer over a charcoal roll-neck sweater, "
        "a small round gold enamel pin with a black letter Q on the left lapel, a plain wedding ring, in a warm dimly lit hotel lounge with soft golden bokeh lights")

INTRO_CANDIDATES = {
    "a": "I'm your host here at Quiet Money. One money rule a day, one community, one goal: escape the rat race. Stay with us.",
    "b": "Welcome to Quiet Money. Learn how money really works, practice it together, and build a life you never need to escape from.",
    "c": "I'm glad you're here. Quiet Money is a community: one small money rule a day, until the rat race is behind us. Subscribe.",
    "d": "Welcome to Quiet Money. No hype. One money rule a day, and a community working toward escaping the rat race. I'm in. Are you?",
    "e": "Welcome to Quiet Money, where ordinary people quietly build freedom. Subscribe, and let's escape the rat race together.",
    "f": "Welcome to Quiet Money. I'm Quinton. No hype, one money rule a day, and a community escaping the rat race together. Are you in?",
}
MAX_WORDS = 26          # about ten seconds at a natural, unhurried pace (2.5 words a second)


# ------------------------------------------------------------------ state
def state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(data: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    write_atomic(STATE, json.dumps(data, indent=1))


def status() -> dict:
    s = state()
    return {"reference_photo": REFERENCE.exists(), "voice_profile": (s.get("voice") or {}).get("audio_id"), "character": (s.get("character") or {}).get("character_id"),
            "voice_anchor": ANCHOR.exists(), "videos": len(s.get("videos", []))}


def _output(res: dict, *keys: str) -> str | None:
    """A field out of a Muapi result however it came back (instant models answer in `data`)."""
    for d in res.get("data") or []:
        if isinstance(d, dict):
            for k in keys:
                if d.get(k):
                    return str(d[k])
    return None


# ------------------------------------------------------------------ the voice (free)
def design_voice(force: bool = False) -> str:
    """Make the host's custom voice profile once (a base voice reshaped by VOICE_DESCRIPTION). Free; returns the profile id."""
    s = state()
    have = (s.get("voice") or {}).get("audio_id")
    if have and not force:
        return have
    res = muapi.run("gemini-omni-audio", {"audio_id": VOICE_BASE, "name": VOICE_NAME, "voice_description": VOICE_DESCRIPTION, "example_dialogue": VOICE_SAMPLE},
                    DIR / "tmp", max_usd=0.05, label="host-voice")
    vid = _output(res, "audio_id")
    if not vid:
        raise ProviderError("the voice profile endpoint returned no audio_id")
    s["voice"] = {"model": "gemini-omni-audio", "base_voice": VOICE_BASE, "name": VOICE_NAME, "audio_id": vid, "created": _today().isoformat()}
    save(s)
    events.emit("HOST_VOICE_CREATED", audio_id=vid)
    return vid


# ------------------------------------------------------------------ the face
def create_character(image: Path = REFERENCE) -> str:
    """A reusable Gemini Omni character from the reference photograph (free), carrying the voice profile. Returns its id."""
    if not Path(image).exists():
        raise ProviderUnavailable(f"no reference photograph at {image}: put the host's picture there first")
    s = state()
    voice = design_voice()
    url = muapi.upload(image)
    res = muapi.run("gemini-omni-character", {"descriptions": f"{NAME}, Quiet Money's host: {LOOK}. Warm, grounded, quietly confident.", "images_list": [url],
                                              "character_name": NAME, "audio_ids": [voice]}, DIR / "tmp", max_usd=0.05, label="host-character")
    cid = _output(res, "character_id", "id")
    if not cid:
        raise ProviderError("the character endpoint returned no id")
    s["character"] = {"model": "gemini-omni-character", "character_id": cid, "created": _today().isoformat()}
    save(s)
    events.emit("HOST_CHARACTER_CREATED", character_id=cid)
    return cid


# ------------------------------------------------------------------ the words (Jev chooses, the code checks)
def check_line(text: str) -> list[str]:
    """What is wrong with a candidate line (empty list = fine)."""
    bad = []
    words = text.split()
    if len(words) > MAX_WORDS:
        bad.append(f"{len(words)} words; more than fits in ten seconds ({MAX_WORDS})")
    if not text.rstrip().endswith((".", "!", "?")) or text.rstrip().endswith("..."):
        bad.append("must end on a complete sentence")
    from faceless.gauntlet import COMPLIANCE_BANNED
    hits = [p for p in COMPLIANCE_BANNED if p in text.lower()]
    if hits:
        bad.append(f"advice or promise language: {hits}")
    return bad


def choose_line(candidates: dict[str, str] | None = None) -> tuple[str, str, str]:
    """Ask the decision layer (Jev when TYPESAFE_API_KEY is set, otherwise the open backend, otherwise the heuristic) which candidate is the best
    welcome. Returns (key, text, backend). Candidates that break a rule are removed first: the host validates every choice."""
    cands = {k: v for k, v in (candidates or INTRO_CANDIDATES).items() if not check_line(v)}
    if not cands:
        raise ProviderError("no candidate line passes the checks")
    q = decide.Q(kind="choice", fallback=min(cands, key=lambda k: abs(len(cands[k].split()) - 24)),
                 instructions=("Pick the best ten-second welcome for the first video of a personal-finance channel's new recurring host. It must (1) make a stranger "
                               "feel welcome and part of a community, (2) name the shared goal, escaping the rat race, without promising income, (3) sound like a calm, "
                               "grounded person rather than a salesman, (4) end with a clear next step, and (5) be spoken comfortably in ten seconds."),
                 options=cands)
    d = decide.ask({"intro_line": q}, {"series": "Quiet Money", "purpose": "channel introduction"})["intro_line"]
    key = d.value if d.value in cands else q.fallback
    return key, cands[key], d.backend


# ------------------------------------------------------------------ the clip
def shot_prompt(line: str, seconds: int = 10) -> str:
    """The Seedance 2 prompt: the reference photo is the host (@image1); native speech and lip-sync say `line` in the host's voice."""
    return (f"Vertical 9:16, {seconds} seconds. {NAME}, the man in @image1, exactly as pictured ({LOOK}), stands in the same warm lounge and speaks straight to camera in a "
            f"slow, steady medium close-up with a very gentle push-in. Natural, accurate lip-sync. He is relaxed and quietly smiling; one small open-hand gesture on the "
            f"key words; the gold Q pin on his lapel stays visible and unchanged. His voice: {VOICE_DESCRIPTION} He says, in one take: \"{line}\" "
            f"Soft room tone only, no music, no subtitles, no text on screen, no cuts.")


def estimate(model: str, seconds: int, resolution: str = "720p") -> float:
    est = muapi.estimate(model, {"prompt": "x", "images_list": ["x"], "duration": seconds, "resolution": resolution})
    return float(est if est is not None else 0.0)


def make_clip(line: str, *, model: str = "seedance-2-i2v", seconds: int = 10, resolution: str = "720p", apply: bool = False, max_usd: float = 2.5) -> dict:
    """Generate the host clip. Without apply=True it only prices it. With the voice anchor present, the model that takes reference audio is used so the
    voice carries over from the first intro."""
    problems = check_line(line)
    if problems:
        raise ProviderError("; ".join(problems))
    use_anchor = ANCHOR.exists()
    if use_anchor:
        model = "seedance-2-omni-reference-no-video-fast"
    payload = {"prompt": shot_prompt(line, seconds), "images_list": ["<reference photo>"], "aspect_ratio": "9:16", "duration": seconds}
    if model == "seedance-2-i2v":
        payload |= {"resolution": resolution, "quality": "basic"}
    if use_anchor:
        payload["audio_files"] = ["<voice anchor>"]
    price = muapi.estimate(model, {k: v for k, v in payload.items() if k not in ("images_list", "audio_files")} | {"images_list": ["x"]})
    out = {"model": model, "price_usd": price, "line": line, "words": len(line.split()), "voice_anchor": use_anchor, "applied": False}
    if not apply:
        return out
    if not REFERENCE.exists():
        raise ProviderUnavailable(f"no reference photograph at {REFERENCE}: put the host's picture there first")
    payload["images_list"] = [muapi.upload(REFERENCE)]
    if use_anchor:
        payload["audio_files"] = [muapi.upload(ANCHOR)]
    res = muapi.run(model, payload, DIR / "clips", max_usd=max_usd, label=f"host-{_today().isoformat()}")
    videos = [f for f in res.get("files", []) if str(f).lower().endswith((".mp4", ".mov", ".webm"))]
    if not videos:
        raise ProviderError("the video model returned no video file")
    out |= {"applied": True, "video": videos[0], "usd": res.get("usd"), "request_id": res.get("request_id")}
    events.emit("HOST_CLIP_MADE", model=model, usd=res.get("usd"), seconds=seconds)
    return out


def keep_voice_anchor(video: str | Path, seconds: float = 12.0) -> Path:
    """Cut the first intro's own audio into the voice anchor (mono WAV, at most 15 s): later clips take it as reference audio."""
    DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-t", f"{min(seconds, 15.0):.2f}", "-vn", "-ac", "1", "-ar", "24000",
                    str(ANCHOR)], check=True, timeout=120)
    return ANCHOR


# ------------------------------------------------------------------ weekly schedule
WEEKDAY = 0          # Monday


def due(today: date | None = None) -> bool:
    """True when it is the host's day and this week's video has not been made."""
    today = today or _today()
    if not config.load().get("host", {}).get("enabled", False):
        return False
    weekday = int(config.load().get("host", {}).get("weekday", WEEKDAY))
    last = max((v.get("date", "") for v in state().get("videos", [])), default="")
    if today.weekday() != weekday:
        return False
    return not last or (today - date.fromisoformat(last)).days >= 6


def weekly_line(theme: str = "", recent: list[str] | None = None) -> str:
    """This week's ten-second message from the host, written by the text chain under the persona rules; falls back to a fixed set when the chain is down.
    Every line is checked (length, complete sentence, no advice or promises) before it is used."""
    from faceless.providers import llm
    prompt = (f"Write one spoken message for the recurring host of the personal-finance channel Quiet Money, to be said in about ten seconds ({MAX_WORDS - 4} to {MAX_WORDS} words). "
              f"Persona: {LOOK.split(',')[0]}, calm, grounded, warm, talks to one person; the channel is a community working toward escaping the rat race; he never hypes, "
              f"never promises income, never gives personal financial advice. This week's theme: {theme or 'a check-in with the community and one small step for this week'}. "
              f"It must be complete sentences, end on a clear next step (watch this week's videos, comment your number, subscribe), and not repeat these earlier lines: "
              f"{recent or []}. Return JSON: {{\"line\": \"...\"}}")
    try:
        res = llm.complete(prompt, want_json=True, temperature=0.9)
        line = (res.get("line") if isinstance(res, dict) else "") or ""
    except (ProviderError, ProviderUnavailable, ValueError):
        line = ""
    if line and not check_line(line):
        return line.strip()
    pool = [v for v in INTRO_CANDIDATES.values() if v not in (recent or [])] or list(INTRO_CANDIDATES.values())
    return pool[_today().isocalendar()[1] % len(pool)]


def register(video: str | Path, line: str, title: str, approved: bool = False) -> dict:
    """Record a finished host clip: a packaged job (so the normal publisher and the backlog planner can post it once approved), and a line in host.json."""
    from faceless.state import new_job
    job = new_job("host", title, slot=0)
    job.artifacts.update(video=str(video), title=title)
    meta = {"title": title, "description": (f"{title}\n\nQuinton, Quiet Money's host, checks in. He is a virtual host: the picture, voice and video are AI-generated. "
                                              "Educational content, not financial advice.\n\n#quietmoney #personalfinance #financialfreedom #shorts"),
            "hashtags": ["#quietmoney", "#personalfinance", "#financialfreedom", "#shorts"], "caption": line, "first_comment": line}
    write_atomic(job.dir / "meta.json", json.dumps(meta, indent=1))
    job.scores = {"gauntlet": 100, "passed": approved, "note": "host clip: it passes only when the owner approves it (approved=True), not by the script gauntlet"}
    job.status = "packaged"
    job.save()
    s = state()
    s.setdefault("videos", []).append({"date": _today().isoformat(), "job": job.id, "line": line, "video": str(video)})
    save(s)
    return {"job": job.id, "meta": str(job.dir / "meta.json")}
