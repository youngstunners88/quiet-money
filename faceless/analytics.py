"""Performance feedback: per-pillar weights from real post metrics.

Append one JSON line per post per platform to analytics/metrics.jsonl, e.g.
{"job": "...", "pillar": "story", "platform": "tiktok", "views": 12000, "avg_view_pct": 71, "follows": 40}
(manually, from a CSV export, or via a connector such as Windsor.ai). The router then
shifts tomorrow's slots toward what works while keeping exploration alive.
"""

from __future__ import annotations

import json
import math

from faceless import config
from faceless.config import Paths

METRICS = Paths.analytics / "metrics.jsonl"


def load() -> list[dict]:
    if not METRICS.exists():
        return []
    return [json.loads(l) for l in METRICS.read_text(encoding="utf-8").splitlines() if l.strip()]


def pillar_weights(window: int = 60) -> dict[str, float]:
    pillars = config.load()["pillars"]
    base = {p.id: p.weight for p in pillars}
    rows = load()[-window:]
    if len(rows) < 10:          # not enough signal yet: stay balanced
        return base
    scores: dict[str, list[float]] = {}
    for r in rows:
        v = math.log10(1 + float(r.get("views", 0))) * (0.5 + float(r.get("avg_view_pct", 50)) / 100)
        v += 0.5 * math.log10(1 + float(r.get("follows", 0)))
        scores.setdefault(r.get("pillar", ""), []).append(v)
    means = {k: sum(v) / len(v) for k, v in scores.items() if k in base}
    if not means:
        return base
    top = max(means.values())
    # exploration floor: an untested or weak pillar keeps at least 35% of the leader's weight
    return {k: base[k] * max(0.35, means.get(k, top * 0.6) / top) for k in base}


def allocate(slots: int, weights: dict[str, float], day_index: int) -> list[str]:
    """Spread a day's slots across pillars by weight, max 2 per pillar.

    With more pillars than slots, one pillar that isn't guaranteed a daily slot (weight share x slots < 1)
    rests each day in rotation, so every series keeps appearing even when metrics make weights unequal.
    Repeats go last, so the first slots of the day always cover different pillars."""
    order = sorted(weights, key=lambda k: -weights[k])
    if not order or slots <= 0:
        return []
    total = sum(weights.values()) or 1.0
    pool = list(order)
    if len(pool) > slots:
        resting = [k for k in order if weights[k] / total * slots < 1]
        if resting:
            pool.remove(resting[day_index % len(resting)])
    sub = sum(weights[k] for k in pool) or 1.0
    counts = {k: 0 for k in pool}
    shift = day_index % len(pool)
    tie_order = pool[shift:] + pool[:shift]          # ties go to a different pillar each day
    for _ in range(min(slots, 2 * len(pool))):
        best = max(tie_order, key=lambda k: (weights[k] / sub) * slots - counts[k] if counts[k] < 2 else -9)
        counts[best] += 1
    firsts = [k for k in pool if counts[k] >= 1]
    shift = day_index % len(firsts)
    return firsts[shift:] + firsts[:shift] + [k for k in pool if counts[k] >= 2]