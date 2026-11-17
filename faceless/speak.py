"""The command center's voice, both ways.

Voice OUT (the center talks): `python -m faceless speak summary|next` (the action desk's `voice_say`). The words are composed here from the
instrument snapshot: never free text from the page. Fish Audio's REST TTS (`POST https://api.fish.audio/v1/tts`, not its MCP endpoint, which
refuses API keys) says them in Quinton's voice: his voice anchor (`channel/host/voice-anchor.wav`, the first intro's own audio) and its
transcript go along as the inline reference, which the API only accepts as MessagePack. The key (`FISH_AUDIO_API_KEY`) stays on this
machine; the browser only ever receives the finished audio. Audio is cached by a hash of the model, the voice and the words, so the same
sentence is never paid for twice, and a day's characters are capped in the ledger.

Voice IN (the owner talks): the page records only while its button is held down or toggled on, shows that it is recording and that it is
sending, and posts the clip to `POST /voice-in`. Gemini transcribes it (REST `generateContent`, model and price in `[voice]`). The
transcript is matched to at most one of the actions a button on the page may already press, and the page shows the transcript and the
proposed action and runs nothing until the owner presses and holds to allow it. Off until the owner turns it on (`[voice] listen = true`):
the model and its price are the owner's call, and no Gemini key is set for the studio yet. No audio is written to disk.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import struct
import sys
from datetime import datetime, timezone

from faceless import config, events, ledger
from faceless.config import Paths
from faceless.fsutil import write_atomic

CACHE = Paths.state / "tmp" / "voice"
ANCHOR = Paths.root / "channel" / "host" / "voice-anchor.wav"
HOST = Paths.root / "channel" / "host" / "host.json"
TTS_URL = "https://api.fish.audio/v1/tts"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
KEY_VARS = ("FISH_AUDIO_API_KEY", "FISH_API_KEY")
WHAT = ("summary", "next")
AUDIO_TYPES = ("audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac")
MAX_AUDIO = 1_500_000                                        # about a minute of Opus; the page stops at 15 s
DEFAULTS = {"tts_model": "s2.1-pro-free", "tts_daily_chars": 4000, "listen": False, "listen_model": "gemini-3.5-flash-lite",
            "listen_usd_per_mtok_in": 0.30, "listen_usd_per_mtok_out": 2.50, "listen_daily_usd": 0.05}


def cfg() -> dict:
    return {**DEFAULTS, **(config.load().get("voice") or {})}


# ---------------------------------------------------------------- a small MessagePack writer (the types this request uses)

def pack(v) -> bytes:
    """MessagePack for None, bool, int, str, bytes, list and dict with string keys. Enough for Fish's TTS request; nothing else uses it."""
    if v is None:
        return b"\xc0"
    if v is True:
        return b"\xc3"
    if v is False:
        return b"\xc2"
    if isinstance(v, int):
        if 0 <= v < 128:
            return bytes([v])
        if -32 <= v < 0:
            return struct.pack("b", v)
        return b"\xd3" + struct.pack(">q", v)
    if isinstance(v, str):
        b = v.encode("utf-8")
        n = len(b)
        head = bytes([0xA0 | n]) if n < 32 else b"\xd9" + bytes([n]) if n < 256 else b"\xda" + struct.pack(">H", n) if n < 65536 else b"\xdb" + struct.pack(">I", n)
        return head + b
    if isinstance(v, (bytes, bytearray)):
        n = len(v)
        head = b"\xc4" + bytes([n]) if n < 256 else b"\xc5" + struct.pack(">H", n) if n < 65536 else b"\xc6" + struct.pack(">I", n)
        return head + bytes(v)
    if isinstance(v, (list, tuple)):
        n = len(v)
        head = bytes([0x90 | n]) if n < 16 else b"\xdc" + struct.pack(">H", n)
        return head + b"".join(pack(x) for x in v)
    if isinstance(v, dict):
        n = len(v)
        head = bytes([0x80 | n]) if n < 16 else b"\xde" + struct.pack(">H", n)
        return head + b"".join(pack(str(k)) + pack(x) for k, x in v.items())
    raise TypeError(f"cannot pack {type(v).__name__}")


# ---------------------------------------------------------------- voice out

def key() -> tuple[str | None, str | None]:
    for name in KEY_VARS:
        if (os.environ.get(name) or "").strip():
            return os.environ[name].strip(), name
    return None, None


def anchor() -> tuple[bytes, str]:
    """Quinton's voice: the anchor audio and what he says in it (the first registered host video's line)."""
    data = ANCHOR.read_bytes()
    try:
        line = (json.loads(HOST.read_text(encoding="utf-8")).get("videos") or [{}])[0].get("line") or ""
    except (OSError, ValueError):
        line = ""
    if not line:
        raise RuntimeError("channel/host/host.json has no line for the voice anchor; the reference needs its transcript")
    return data, line


def words(what: str, snap: dict) -> str:
    """What the center says. Plain sentences from the snapshot: numbers as they are, nothing invented."""
    if what == "next":
        nx = snap.get("next")
        return f"Next: {nx['text']}. {nx['action']}." if nx else "Nothing is waiting for you right now."
    m, sh, y = snap.get("money") or {}, snap.get("shipped") or {}, snap.get("youCount") or 0
    parts = []
    if m.get("usd") is None:
        parts.append("Money in this month is unknown.")
    else:
        parts.append(f"Money in this month: {m['usd']:,.2f} dollars from {m['receipts']} receipt{'s' if m['receipts'] != 1 else ''}.")
    if sh.get("today") is not None:
        parts.append(f"Videos shipped today: {sh['today']} of {sh['target']}. {sh['week']} in the last seven days.")
    live = [r["name"] for r in snap.get("crew") or [] if r.get("lamp") == "live"]
    parts.append(f"{len(live)} agent{'s' if len(live) != 1 else ''} at work" + (f": {', '.join(live)}." if live else "."))
    parts.append(f"{y} thing{'s' if y != 1 else ''} wait{'s' if y == 1 else ''} for you." if y else "Nothing waits for you.")
    return " ".join(parts)


def _clip_id(model: str, text: str, voice: bytes) -> str:
    return hashlib.sha256(model.encode() + b"\0" + hashlib.sha256(voice).digest() + b"\0" + text.encode()).hexdigest()[:20]


def say(what: str, snap: dict | None = None, session=None) -> dict:
    """Make (or reuse) the audio for `what` and point `latest-<what>.json` at it. Raises RuntimeError with a plain reason when it cannot."""
    if what not in WHAT:
        raise ValueError(f"what must be one of {', '.join(WHAT)}")
    if snap is None:
        from faceless import instruments
        snap = instruments.build()
    c = cfg()
    text = re.sub(r"\s+", " ", words(what, snap)).strip()[:600]
    voice, line = anchor()
    cid = _clip_id(c["tts_model"], text, voice)
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{cid}.mp3"
    cached = out.exists() and out.stat().st_size > 0
    if not cached:
        k, var = key()
        if not k:
            raise RuntimeError(f"no Fish Audio key: set {KEY_VARS[0]} in ~/.config/quiet-money/env (it never reaches the browser)")
        if not ledger.allow("fishaudio", "chars", len(text), float(c["tts_daily_chars"])):
            raise RuntimeError(f"today's voice allowance is used up ([voice] tts_daily_chars = {c['tts_daily_chars']})")
        body = pack({"text": text, "references": [{"audio": voice, "text": line}], "format": "mp3", "normalize": True, "latency": "normal"})
        if session is None:
            from faceless.providers import http
            session = http()
        try:
            r = session.post(TTS_URL, data=body, timeout=60, headers={"Authorization": f"Bearer {k}", "Content-Type": "application/msgpack",
                                                                       "model": c["tts_model"]})
        except Exception as e:   # noqa: BLE001
            raise RuntimeError(f"Fish Audio unreachable ({type(e).__name__})") from None
        if r.status_code != 200 or not r.content:
            detail = config.redact((r.text or "")[:160]).replace(k, "[key]")
            raise RuntimeError(f"Fish Audio answered {r.status_code}: {detail}")
        tmp = out.with_suffix(".part")
        tmp.write_bytes(r.content)
        os.replace(tmp, out)
        ledger.spend("fishaudio", "chars", len(text), usd=0.0, model=c["tts_model"])
    pointer = {"id": cid, "what": what, "text": text, "model": c["tts_model"], "voice": "channel/host/voice-anchor.wav",
               "t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "cached": cached}
    write_atomic(CACHE / f"latest-{what}.json", json.dumps(pointer))
    return pointer


def latest(what: str) -> tuple[bytes, dict] | None:
    """The newest audio for `what`, for GET /voice/<what>.mp3. None when nothing has been said yet."""
    if what not in WHAT:
        return None
    try:
        pointer = json.loads((CACHE / f"latest-{what}.json").read_text(encoding="utf-8"))
        if not re.fullmatch(r"[0-9a-f]{20}", str(pointer.get("id") or "")):
            return None
        return (CACHE / f"{pointer['id']}.mp3").read_bytes(), pointer
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- voice in

INTENTS = (
    (re.compile(r"\b(do|send|run|start)\b.*\b(next|that|it)\b", re.I), "next", "Do the next action"),
    # "do" first: "do the next thing" must not be read as "read out the next thing"
    (re.compile(r"\b(re-?check|check|test|probe)\b.*\bkeys?\b|\bkeys?\b.*\b(check|working)\b", re.I), "keys_probe", "Re-check keys"),
    (re.compile(r"\b(take|bring|get)\b.*\bback\b|\breap\b|\bsilent agents?\b", re.I), "crew_reap", "Take back missions from silent agents"),
    (re.compile(r"\b(read|say|tell)\b.*\b(summary|status|where)\b|\bhow are we doing\b|\bstatus\b", re.I), "voice_say:summary", "Read out the summary"),
    (re.compile(r"\b(what'?s|what is)\b.*\bnext\b|\bnext (action|thing)\b|\bread\b.*\bnext\b", re.I), "voice_say:next", "Read out the next action"),
)


def propose(transcript: str, snap: dict) -> dict | None:
    """At most one action, and only one a button on the page could already press. Never anything that sends, posts or uploads."""
    t = (transcript or "").strip()
    for rx, name, label in INTENTS:
        if not rx.search(t):
            continue
        if name == "next":
            nx = snap.get("next") or {}
            do = nx.get("do")
            if not do:
                return {"name": None, "label": "The next action has no button here: " + (nx.get("action") or "nothing waits"), "args": {}}
            return {"name": do["name"], "args": do.get("args") or {}, "label": do.get("label") or label, "confirm": True}
        if name.startswith("voice_say:"):
            return {"name": "voice_say", "args": {"what": name.split(":", 1)[1]}, "label": label, "confirm": True}
        return {"name": name, "args": {}, "label": label, "confirm": True}
    return None


def transcribe(audio: bytes, mime: str, session=None) -> dict:
    """Gemini's transcript of one short clip. Refuses when voice input is off, the key is missing, the clip is too big or the day's cap is spent."""
    c = cfg()
    if not c["listen"]:
        raise PermissionError("voice input is off: the owner turns it on with [voice] listen = true in studio.toml, after confirming the model and price")
    k = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not k:
        raise PermissionError("no GEMINI_API_KEY in this machine's env file")
    if not audio or len(audio) > MAX_AUDIO or mime.split(";")[0].strip() not in AUDIO_TYPES:
        raise ValueError("send one short audio clip (webm, ogg, mp4, mpeg or wav, under 1.5 MB)")
    est = 32 * 60 * float(c["listen_usd_per_mtok_in"]) / 1e6 + 200 * float(c["listen_usd_per_mtok_out"]) / 1e6    # a minute of audio, generously
    if not ledger.allow_usd("gemini-voice", est, float(c["listen_daily_usd"])):
        raise PermissionError(f"today's voice-input cap is spent ([voice] listen_daily_usd = {c['listen_daily_usd']})")
    payload = {"contents": [{"parts": [{"text": "Transcribe exactly what is said in this audio. Reply with the transcript only, no quotes."},
                                       {"inline_data": {"mime_type": mime.split(";")[0].strip(), "data": base64.b64encode(audio).decode()}}]}],
               "generationConfig": {"temperature": 0, "maxOutputTokens": 200}}
    if session is None:
        from faceless.providers import http
        session = http()
    try:
        r = session.post(GEMINI_URL.format(model=c["listen_model"]), json=payload, timeout=30, headers={"x-goog-api-key": k})
    except Exception as e:   # noqa: BLE001
        raise RuntimeError(f"Gemini unreachable ({type(e).__name__})") from None
    if r.status_code != 200:
        raise RuntimeError(f"Gemini answered {r.status_code}: {config.redact((r.text or '')[:160]).replace(k, '[key]')}")
    doc = r.json()
    text = " ".join(p.get("text", "") for p in ((doc.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []).strip()
    u = doc.get("usageMetadata") or {}
    tin, tout = int(u.get("promptTokenCount") or 0), int(u.get("candidatesTokenCount") or 0)
    usd = tin * float(c["listen_usd_per_mtok_in"]) / 1e6 + tout * float(c["listen_usd_per_mtok_out"]) / 1e6
    ledger.spend_usd("gemini-voice", usd)
    events.emit("CC_VOICE", actor="owner", heard=config.redact(text)[:200], model=c["listen_model"], tokens_in=tin, tokens_out=tout)
    return {"transcript": text[:400], "model": c["listen_model"], "usd": round(usd, 6)}


def main(argv: list[str]) -> int:
    what = argv[0] if argv else "summary"
    config.load_keys()
    try:
        p = say(what)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(json.dumps(p))
    return 0
