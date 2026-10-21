"""Forced alignment: real word timings for a voice track that came without them (the Gemini voice).

Captions drawn from estimated timings drift from the speech. Here the finished narration is transcribed with word timestamps by
Cloudflare's Whisper (free Workers AI pool), and the script's own words are matched to the transcript, so captions keep the script's
spelling and punctuation but take the timing of what was actually said.

    words, coverage = align(text, wav)     # None when Cloudflare is unavailable: the caller keeps its estimate and says so
"""

from __future__ import annotations

import base64
import re
from difflib import SequenceMatcher
from pathlib import Path

from faceless import config, ledger
from faceless.providers import ProviderError, ProviderUnavailable, http

MODEL = "@cf/openai/whisper-large-v3-turbo"
NEURONS_PER_MINUTE = 47          # Workers AI price for this model, about $0.0005 a minute of audio; logged against the free pool


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def transcribe(wav: Path) -> list[dict]:
    """Whisper's words with start and end times (seconds)."""
    key = config.env("CLOUDFLARE_API_KEY", "CLOUDFLARE_API_TOKEN")
    acct = config.env("CLOUDFLARE_ACCOUNT_ID")
    if not (key and acct):
        raise ProviderUnavailable("CLOUDFLARE_API_KEY / CLOUDFLARE_ACCOUNT_ID not set")
    audio = Path(wav).read_bytes()
    r = http().post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{MODEL}", headers={"Authorization": f"Bearer {key}"},
                    json={"audio": base64.b64encode(audio).decode(), "word_timestamps": True}, timeout=180)
    if r.status_code != 200:
        raise ProviderError(f"whisper {r.status_code}: {r.text[:200]}")
    res = r.json().get("result") or {}
    words = res.get("words") or [w for s in res.get("segments", []) for w in s.get("words", [])]
    secs = len(audio) / 48000.0                                  # 24 kHz mono 16-bit; close enough for the pool log
    ledger.spend("cloudflare", "neurons", round(NEURONS_PER_MINUTE * secs / 60, 1))
    return [{"w": w["word"].strip(), "start": float(w["start"]), "end": float(w["end"])} for w in words if w.get("word", "").strip()]


def match(tokens: list[str], heard: list[dict], total: float) -> tuple[list[dict], float]:
    """The script's tokens with times taken from the transcript. Matched runs copy the heard timing; words in between are spread over
    the gap by their length. Returns the words and the share of script words that matched a heard word."""
    a = [_norm(t) for t in tokens]
    b = [_norm(h["w"]) for h in heard]
    times: list[tuple[float, float] | None] = [None] * len(tokens)
    for blk in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            h = heard[blk.b + k]
            times[blk.a + k] = (h["start"], h["end"])
    matched = sum(t is not None for t in times)
    i = 0
    while i < len(tokens):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tokens) and times[j] is None:
            j += 1
        lo = times[i - 1][1] if i > 0 else (heard[0]["start"] if heard else 0.0)
        hi = times[j][0] if j < len(tokens) else max(lo, heard[-1]["end"] if heard else total)
        hi = max(hi, lo + 0.05 * (j - i))
        weights = [len(a[k]) + 1 for k in range(i, j)]
        step, t = (hi - lo) / sum(weights), lo
        for k, wgt in zip(range(i, j), weights):
            times[k] = (t, t + wgt * step)
            t += wgt * step
        i = j
    words = [{"w": tok, "start": round(s, 3), "end": round(max(e, s + 0.04), 3)} for tok, (s, e) in zip(tokens, times)]
    return words, (matched / len(tokens) if tokens else 0.0)


def align(text: str, wav: Path, total: float | None = None) -> tuple[list[dict], float] | None:
    """Real timings for `text` spoken in `wav`, or None when the transcriber is unavailable (the caller keeps its estimate)."""
    try:
        heard = transcribe(wav)
    except (ProviderError, ProviderUnavailable, ValueError, KeyError):
        return None
    if not heard:
        return None
    return match(text.split(), heard, total or heard[-1]["end"])
