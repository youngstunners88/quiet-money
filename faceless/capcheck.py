"""Caption drift check for any finished video, built by the engine or by hand.

    python -m faceless caption-check VIDEO_OR_WAV CAPTIONS.ass [--max 0.35]

The audio is transcribed with word times (faceless.align), the highlighted word of every caption is matched to the word heard, and
the gap between when the caption lights and when the word is spoken is measured. A caption that lights more than `max` seconds
away from the speech fails; so does a track where too few captions match anything heard. Hand-built videos must pass this before
they are approved (skill faceless-gauntlet, "Caption timing").
"""

from __future__ import annotations

import re
import statistics
import subprocess
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

from faceless import align

ACTIVE = re.compile(r"\{\\c&H[0-9A-Fa-f]{8}\\fscx108\\fscy108\}([^{]+)\{")
DIALOGUE = re.compile(r"^Dialogue:\s*\d+,(\d+):(\d+):([\d.]+),[^,]*,Caption,")
PHRASE = re.compile(r"^Dialogue:\s*\d+,(\d+):(\d+):([\d.]+),[^,]*,(?:C|Phrase),[^,]*,\d+,\d+,\d+,[^,]*,(.+)$")


def active_words(ass_text: str) -> list[tuple[float, str]]:
    """(start seconds, word) for the highlighted word of each Caption line."""
    out = []
    for line in ass_text.splitlines():
        m, a = DIALOGUE.match(line), ACTIVE.search(line)
        if m and a:
            out.append((int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), a[1].strip()))
    if out:
        return out
    for line in ass_text.splitlines():                       # phrase-style tracks: the first word of each line is what must be on time
        m = PHRASE.match(line)
        if m and m[4].split():
            out.append((int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]), re.sub(r"\{[^}]*\}", "", m[4]).split()[0]))
    return out


def audio_of(media: Path, dest: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(media), "-vn", "-ac", "1", "-ar", "24000", str(dest)],
                   check=True, timeout=120)
    return dest


def drifts(caps: list[tuple[float, str]], heard: list[dict]) -> list[float]:
    a = [align._norm(w) for _, w in caps]
    b = [align._norm(h["w"]) for h in heard]
    out = []
    for blk in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            out.append(caps[blk.a + k][0] - heard[blk.b + k]["start"])
    return out


def check(media: Path, ass: Path, max_drift: float = 0.35, min_match: float = 0.6) -> dict:
    caps = active_words(Path(ass).read_text(encoding="utf-8"))
    if not caps:
        return {"ok": False, "reason": "no highlighted caption words found in the .ass file"}
    with tempfile.TemporaryDirectory() as d:
        wav = audio_of(Path(media), Path(d) / "a.wav") if Path(media).suffix.lower() != ".wav" else Path(media)
        heard = align.transcribe(wav)
    ds = drifts(caps, heard)
    cov = len(ds) / len(caps)
    if not ds or cov < min_match:
        return {"ok": False, "reason": f"only {cov:.0%} of captions matched a heard word", "coverage": round(cov, 2)}
    late = [abs(x) for x in ds]
    res = {"coverage": round(cov, 2), "median": round(statistics.median(late), 3), "p90": round(sorted(late)[int(0.9 * (len(late) - 1))], 3),
           "max": round(max(late), 3), "limit": max_drift, "captions": len(caps)}
    res["ok"] = res["p90"] <= max_drift and res["median"] <= max_drift / 2
    if not res["ok"]:
        res["reason"] = f"captions drift from the speech (median {res['median']}s, p90 {res['p90']}s, limit {max_drift}s): rebuild them from faceless.align timings"
    return res
