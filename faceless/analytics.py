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
    """Spread slots across pillars proportional to weight, max 2 per pillar, rotated daily."""
    order = sorted(weights, key=lambda k: -weights[k])
    total = sum(weights.values())
    counts = {k: 0 for k in weights}
    for _ in range(slots):
        best = max(order, key=lambda k: (weights[k] / total) * slots - counts[k] if counts[k] < 2 else -9)
        counts[best] += 1
    plan = [k for k in order for _ in range(counts[k])]
    shift = day_index % len(plan) if plan else 0
    return plan[shift:] + plan[:shift]
