"""Voice stage: synthesize narration, fit it into the target duration, align beats to word timings."""

from __future__ import annotations

import json
import re
import subprocess

from faceless import config, events
from faceless.pipeline.script import narration
from faceless.providers import tts


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def align_beats(beat_texts: list[str], words: list[dict], total: float) -> list[tuple[float, float]]:
    """Map each beat to [start, end) using character progress through the spoken words.

    TTS engines re-tokenize ("$8" vs "8", "J.P." vs "J", "P"), so we match on normalized
    characters instead of word counts.
    """
    beat_starts_chars, pos = [], 0
    for t in beat_texts:
        beat_starts_chars.append(pos)
        pos += len(_norm(t))
    total_chars = max(pos, 1)
    word_chars, wpos = [], 0
    spoken_total = sum(len(_norm(w["w"])) for w in words) or 1
    for w in words:
        word_chars.append(wpos * total_chars / spoken_total)  # rescale in case of verbalization drift
        wpos += len(_norm(w["w"]))
    spans = []
    for i, c in enumerate(beat_starts_chars):
        idx = next((k for k, wc in enumerate(word_chars) if wc >= c - 0.5), len(words) - 1)
        start = 0.0 if i == 0 else words[idx]["start"]
        spans.append(start)
    out = []
    for i, s in enumerate(spans):
        e = spans[i + 1] if i + 1 < len(spans) else total
        out.append((round(s, 3), round(max(e, s + 0.5), 3)))
    return out


def attach_display(words: list[dict], text: str) -> list[dict]:
    """Give each spoken word its original script spelling, punctuation included.

    Edge/ElevenLabs drop punctuation from word timings, which breaks sentence-aware caption
    chunking. Walk both streams by normalized characters; TTS words that split one script
    token are merged, and one TTS word covering several tokens shows them all.
    """
    tokens = text.split()
    tok_end, pos = [], 0
    for t in tokens:
        pos += len(_norm(t))
        tok_end.append(pos)
    spoken = sum(len(_norm(w["w"])) for w in words)
    if not tokens or not words or abs(spoken - pos) > 0.1 * pos:
        return words  # verbalized numbers etc.: keep raw words rather than mislabel them
    out, cpos, ti = [], 0, 0
    for w in words:
        n = len(_norm(w["w"]))
        if n == 0:                       # symbols like "&" or "-" carry no characters to align
            if out:
                out[-1]["end"] = w["end"]
            continue
        cpos += n
        first = ti
        while ti < len(tokens) - 1 and tok_end[ti] < cpos:
            ti += 1
        if out and out[-1]["_tok"] == first == ti:      # continuation of a split token ("J" + "C")
            out[-1]["end"] = w["end"]
        else:
            out.append({**w, "display": " ".join(tokens[first:ti + 1]), "_tok": ti})
        if tok_end[ti] <= cpos and ti < len(tokens) - 1:
            ti += 1
    for o in out:
        o.pop("_tok", None)
    return out


def _atempo(src, dst, factor: float) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                    "-af", f"atempo={factor:.4f}", str(dst)], check=True)


def run(job, script: dict, prefer: str | None = None) -> dict:
    cfg = config.load()
    lo, hi = cfg["production"]["target_seconds"]
    text = narration(script)
    wav = job.dir / "voice.wav"
    base_rate = cfg["voice"]["edge_rate"]
    provider, words = tts.synthesize(text, wav, rate=base_rate, prefer=prefer, job=job.id)
    dur = tts.duration(wav)
    speech_end = words[-1]["end"] if words else dur
    if not (lo + 0.5 <= speech_end + 0.35 <= hi):
        # aim just inside the nearest edge of the window: the smallest audible change in pace
        target = lo + 2.0 if speech_end + 0.35 < lo + 0.5 else hi - 2.0
        speed = tts.rate_to_speed(base_rate) * (speech_end + 0.35) / target
        speed = max(0.88, min(1.18, speed))
        if provider in ("edge", "elevenlabs"):
            provider, words = tts.synthesize(text, wav, rate=tts.speed_to_rate(speed), prefer=provider, job=job.id)
        else:
            factor = speed / tts.rate_to_speed(base_rate)
            tmp = job.dir / "voice.tmp.wav"
            _atempo(wav, tmp, factor)
            tmp.replace(wav)
            words = [{**w, "start": round(w["start"] / factor, 3), "end": round(w["end"] / factor, 3)} for w in words]
        dur = tts.duration(wav)
        speech_end = words[-1]["end"] if words else dur
        events.emit("VOICE_REFIT", job=job.id, speed=round(speed, 3), seconds=round(speech_end, 2))
    total = round(min(dur, speech_end + 0.35), 3)
    words = attach_display(words, text)
    spans = align_beats([b["say"] for b in script["beats"]], words, total)
    data = {"provider": provider, "duration": total, "words": words, "beats": spans}
    (job.dir / "voice.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    job.add_cost(f"tts:{provider}:chars", len(text))
    return data
