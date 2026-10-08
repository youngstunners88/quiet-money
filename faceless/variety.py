"""Variety audit: how interchangeable do our recent videos look?

YouTube does not monetize channels whose videos feel "interchangeable from video to video" (inauthentic content policy, verified
2026-10-08). This reads the last N finished videos and scores sameness from things we control: how alike the scripts are in meaning
(centered embeddings), whether titles and hooks keep opening the same way, whether visual formats vary (cards, clips), and whether
music varies. 0 is very varied, 100 is a template. `python -m faceless variety` writes analytics/variety.md; the weekly scan raises a
proposal when the risk is high. Components that cannot be measured (no embeddings, no render data) are left out and the score says so.
"""

from __future__ import annotations

import itertools
import json
from collections import Counter

from faceless import embed
from faceless.config import Paths
from faceless.state import all_jobs

REPORT = Paths.analytics / "variety.md"
WEIGHTS = {"meaning": 35, "openers": 20, "formats": 25, "music": 10, "pillars": 10}


def recent(n: int = 20) -> list[dict]:
    rows = []
    for j in sorted((j for j in all_jobs() if j.status in ("packaged", "published")), key=lambda j: (j.day, j.id), reverse=True)[:n]:
        try:
            s = json.loads((Paths.final / f"{j.id}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        info = {}
        try:
            info = json.loads((Paths.output / j.day / j.id / "render.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        rows.append({"job": j.id, "pillar": j.pillar, "title": s.get("title", ""), "hook": s.get("hook_text", ""),
                     "text": s.get("title", "") + ". " + " ".join(b.get("say", "") for b in s.get("beats", [])), "render": info})
    return rows


def _all_texts() -> list[str]:
    out = []
    for p in sorted(Paths.final.glob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
            out.append(s.get("title", "") + ". " + " ".join(b.get("say", "") for b in s.get("beats", [])))
        except (OSError, ValueError):
            continue
    return out[-300:]


def _share(items: list[str]) -> float:
    """Share of the most common item (1.0 = all the same)."""
    return max(Counter(items).values()) / len(items) if items else 0.0


def audit(n: int = 20) -> dict:
    rows = recent(n)
    out = {"videos": len(rows), "components": {}, "notes": [], "pairs": []}
    if len(rows) < 6:
        out["risk"] = None
        out["notes"].append("fewer than 6 finished videos: not enough to judge")
        return out
    comp: dict[str, float] = {}
    ref_texts = _all_texts()
    vecs = embed.embed([r["text"] for r in rows] + ref_texts)
    if vecs is not None:
        # center on EVERYTHING we ever wrote: centering on the 20 under audit would force their mean similarity below zero by construction
        cv = embed.centered(vecs[:len(rows)], vecs[len(rows):] if len(ref_texts) >= 12 else vecs[:len(rows)])
        sims = [(embed.cosine(cv[i], cv[j]), i, j) for i, j in itertools.combinations(range(len(rows)), 2)]
        mean = sum(s for s, _, _ in sims) / len(sims)
        close = sorted((x for x in sims if x[0] >= 0.55), reverse=True)
        out["pairs"] = [(round(s, 2), rows[i]["title"], rows[j]["title"]) for s, i, j in close[:6]]
        # across all our scripts the centered mean is about 0 (median -0.04, 90th percentile 0.18); 0.10 or more means these keep saying the same thing
        comp["meaning"] = min(1.0, max(0.0, mean) / 0.10) * 0.6 + min(1.0, len(close) / max(1, len(rows) // 3)) * 0.4
    else:
        out["notes"].append("no embedding provider: script-meaning similarity not measured")
    opener = [r["title"].split()[0].lower() for r in rows if r["title"]] + [" ".join(r["hook"].lower().split()[:2]) for r in rows if r["hook"]]
    comp["openers"] = max(0.0, (_share(opener) - 0.2) / 0.5)
    rend = [r["render"] for r in rows if r["render"]]
    if len(rend) >= 6:
        plain = sum(1 for r in rend if not r.get("cards") and not r.get("clips")) / len(rend)
        comp["formats"] = plain
        tracks = [r["render"].get("music") for r in rows if r["render"].get("music")]
        if len(tracks) >= 6:
            comp["music"] = max(0.0, (_share(tracks) - 0.2) / 0.5) if len(set(tracks)) > 1 else 1.0
        else:
            out["notes"].append("music variety not measured (older renders do not record the bed)")
    else:
        out["notes"].append("visual format variety not measured (render data missing for most videos)")
    comp["pillars"] = max(0.0, (_share([r["pillar"] for r in rows]) - 0.3) / 0.4)
    out["components"] = {k: round(v, 2) for k, v in comp.items()}
    used = {k: WEIGHTS[k] for k in comp}
    out["risk"] = round(100 * sum(comp[k] * w for k, w in used.items()) / sum(used.values()))
    out["level"] = "high" if out["risk"] >= 60 else "medium" if out["risk"] >= 35 else "low"
    return out


def report(n: int = 20) -> str:
    a = audit(n)
    L = ["# Variety audit", "", f"Last {a['videos']} finished videos. YouTube does not monetize channels whose videos feel interchangeable; this is our sameness score."]
    if a["risk"] is None:
        return "\n".join(L + ["", *a["notes"]]) + "\n"
    L += ["", f"**Sameness risk: {a['risk']} / 100 ({a['level']})**", "", "| part | sameness 0-1 | weight |", "|---|---|---|"]
    L += [f"| {k} | {v} | {WEIGHTS[k]} |" for k, v in a["components"].items()]
    if a["pairs"]:
        L += ["", "Scripts that mean nearly the same thing:"] + [f"- {s}: {x} / {y}" for s, x, y in a["pairs"]]
    if a["notes"]:
        L += ["", "Not measured: " + "; ".join(a["notes"])]
    L += ["", "How to lower it: vary the opening words and formats (comparison and step cards, Flow hook clips), spread topics so two videos never teach the same lesson, "
          "and let the library rotate music beds."]
    return "\n".join(L) + "\n"


def write(n: int = 20) -> dict:
    a = audit(n)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report(n), encoding="utf-8")
    return a


def proposals(a: dict) -> list[dict]:
    if a.get("risk") is not None and a["risk"] >= 60:
        return [{"id": "variety-high", "title": f"Sameness risk {a['risk']}/100: videos look interchangeable", "category": "monetization",
                 "impact": 5, "effort": 2, "autonomy": "operator", "why": "YouTube's inauthentic-content policy; see analytics/variety.md"}]
    return []
