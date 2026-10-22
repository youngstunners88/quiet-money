"""The measured half of the craft loop: assess a finished piece against every rule learned so far.

Taste cannot be fully measured, but the defects the owner has caught can be, and each one becomes a check here so it is
never shipped twice. Every rule below cites the lesson that produced it (.claude/skills/faceless-craft/LESSONS.md).
A check that fails stops the piece; the fix goes into the code or the skill that caused it, and this file gains the rule.

Run: python -m faceless craftcheck <video> [--report build.json]
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from faceless.config import Paths

LEDGER = Paths.state / "craft.jsonl"
TIMEOUT = 300
TARGET_I = -14.0
WORDS_PER_SECOND = 2.6       # a calm narrator's pace; a line that needs more than this is too long for its slot


def momentary(video: Path) -> list[tuple[float, float]]:
    """(time, momentary LUFS) every 100 ms. Silence reads as -70."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=TIMEOUT)
    rows = []
    for line in r.stderr.splitlines():
        m = re.search(r"t:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+|-inf)", line)
        if m:
            rows.append((float(m.group(1)), -70.0 if m.group(2) == "-inf" else max(-70.0, float(m.group(2)))))
    return rows


def integrated(video: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, timeout=TIMEOUT)
    return float(json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])["input_i"])


def last_frame_luma(video: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-sseof", "-0.05", "-i", str(video), "-vf", "signalstats,metadata=print",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=TIMEOUT)
    vals = [float(x) for x in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", r.stderr)]
    return vals[-1] if vals else 255.0


def word_budget(slot_seconds: float, lead: float = 0.45, tail: float = 0.4) -> int:
    """How many words a narration line may carry in a slot of this length: the pace times the time left after the
    line's lead-in and before the next cut. The script side uses this so a line is never written longer than its act."""
    return max(0, int((slot_seconds - lead - tail) * WORDS_PER_SECOND))


def _median(rows, a, b) -> float | None:
    vals = [m for t, m in rows if a <= t < b and m > -60]
    return statistics.median(vals) if vals else None


def check_reel(video: Path, report: dict) -> list[dict]:
    """Every check returns {rule, lesson, ok, detail}. `report` is what faceless.reel.build returned."""
    video = Path(video)
    rows = momentary(video)
    total = rows[-1][0] if rows else 0.0
    starts, cta_at = report["act_starts"], report["cta_at"]
    found = []

    def add(rule, lesson, ok, detail, gate=True):
        """gate=False is a provisional rule: reported, never blocking, until the owner confirms it."""
        found.append({"rule": rule, "lesson": lesson, "ok": bool(ok), "detail": detail, "gate": gate})

    i = integrated(video)
    add("integrated loudness is the channel standard (-14 LUFS, +-1)", "L2", abs(i - TARGET_I) <= 1.0, f"{i:.1f} LUFS")

    acts = [m for m in (_median(rows, s + 0.5, e - 0.3) for s, e in zip(starts, starts[1:] + [cta_at])) if m is not None]
    acts_med = statistics.median(acts) if acts else None
    end_med = _median(rows, cta_at + 0.2, total - 0.9)
    if acts_med is not None and end_med is not None:
        add("the ending is not a drop in energy (CTA within 4 LU of the acts)", "L3", end_med >= acts_med - 4.0,
            f"acts {acts_med:.1f}, ending {end_med:.1f} LUFS")

    worst_cut = min((m for t, m in rows if cta_at - 0.1 <= t <= cta_at + 0.6), default=0.0)
    if acts_med is not None:
        add("no hole at the cut into the card", "L3", worst_cut >= acts_med - 10.0,
            f"lowest {worst_cut:.1f} vs acts {acts_med:.1f} LUFS")

    # A median over the whole ending hid the real defect: the closing line itself sagged. Compare the spans where each
    # line is actually spoken, so the line that asks for the follow is never the quietest thing in the piece.
    spans = report.get("narration", [])
    act_voice = [m for m in (_median(rows, l["at"] + 0.1, l["ends"]) for l in spans if not l.get("cta")) if m is not None]
    cta_voice = [_median(rows, l["at"] + 0.1, l["ends"]) for l in spans if l.get("cta")]
    if act_voice and cta_voice and cta_voice[0] is not None:
        ref = statistics.median(act_voice)
        add("the closing line is as present as the act lines", "L3", cta_voice[0] >= ref - 2.0,
            f"closing {cta_voice[0]:.1f} vs lines {ref:.1f} LUFS")

    for line in report.get("narration", []):
        room = line["act_ends"] - line["ends"]
        if line.get("cta"):
            add(f"the closing line holds before the end ({line['line'][:32]}...)", "L4", room >= 0.9,
                f"{room:.2f}s after the last word")
        else:
            add(f"line finishes before its cut ({line['line'][:32]}...)", "L4", room >= 0.2, f"{room:.2f}s to spare")
        wps = len(line["line"].split()) / max(0.1, line["seconds"])
        add(f"line is at a calm pace ({line['line'][:32]}...)", "L5", wps <= 3.2, f"{wps:.1f} words/s", gate=False)

    tail = [m for t, m in rows if t >= total - 0.15]
    peak_end = max((m for t, m in rows if total - 2.0 <= t < total - 0.8), default=-70.0)
    add("the sound fades out, it does not stop dead", "L4", bool(tail) and max(tail) <= peak_end - 10.0,
        f"last 150ms {max(tail) if tail else -70:.1f} vs before the fade {peak_end:.1f} LUFS")
    luma = last_frame_luma(video)
    add("the picture fades to black with the sound", "L4", luma <= 20.0, f"last frame luma {luma:.0f}")
    return found


def record(piece: str, findings: list[dict]) -> dict:
    """Append the run to the ledger: what was checked, what failed. The ledger is how improvement is measured."""
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "piece": piece,
           "passed": sum(f["ok"] for f in findings),
           "failed": [f["rule"] for f in findings if not f["ok"] and f.get("gate", True)],
           "watch": [f["rule"] for f in findings if not f["ok"] and not f.get("gate", True)]}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def blocking(findings: list[dict]) -> list[dict]:
    """The failures that stop a piece from shipping: confirmed rules only."""
    return [f for f in findings if not f["ok"] and f.get("gate", True)]
