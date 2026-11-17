"""Variety audit: how interchangeable do our recent videos look?

YouTube does not monetize channels whose videos feel "interchangeable from video to video" (inauthentic content policy, verified
2026-10-08). This reads the last N finished videos and scores sameness from things we control: how alike the scripts are in meaning
(centered embeddings), whether titles and hooks keep opening the same way, whether visual formats vary (cards, clips), whether
music varies, whether the composition and camera pairing varies, and whether the stills' style sentence varies. 0 is very varied, 100 is a template. `python -m faceless variety` writes analytics/variety.md; the weekly scan raises a
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
WEIGHTS = {"meaning": 35, "openers": 20, "formats": 25, "music": 10, "pillars": 10, "looks": 20, "stills": 20}


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
        rows.append({"job": j.id, "day": j.day, "pillar": j.pillar, "title": s.get("title", ""), "hook": s.get("hook_text", ""),
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
    looks, out["looks"] = look_component(rows)
    if looks is None:
        out["notes"].append(f"composition and camera variety not measured ({out['looks']['recorded']} renders record a look; it is recorded from 2026-11-17)")
    else:
        comp["looks"] = looks
    stills, out["stills"] = still_style_component(rows)
    if stills is None:
        out["notes"].append("the stills' style sentence was not measured (images.json missing)")
    else:
        comp["stills"] = stills
        if out["stills"]["distinct"] == 1:
            out["notes"].append("every still of these videos was prompted with the same style sentence (studio.toml [[pillars]] style)")
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


# ---------------------------------------------------------------- the look of each new video
# A video's look is three choices: the pillar's grade (studio.toml, fixed per pillar), a composition family for its stills and a camera
# family for the moves on them. The last two are picked per video so that two videos in a row never share the same pairing: the new one
# differs from the previous one in both its composition and its camera, and repeats no pairing of the last few. Picks go to
# state/looks.jsonl under a file lock (a re-render keeps its look; two jobs rendering at once cannot pick the same thing), and the
# render records the look in render.json so `audit` can measure it.

LOOKS = Paths.state / "looks.jsonl"
LOOKS_LOCK = Paths.state / "tmp" / "looks.lock"
AVOID_LAST = 4                                               # no pairing of the last four videos is used again
COMPOSITIONS = {
    "center": "vertical 9:16 composition, subject centred and symmetrical at eye level",
    "thirds": "vertical 9:16 composition, subject on the left third from a low camera angle, open negative space above",
    "macro": "vertical 9:16 composition, extreme close-up on one telling detail filling the frame, very shallow depth of field",
    "wide": "vertical 9:16 composition, wide establishing shot, a small subject in a vast space, strong leading lines",
}
STILL_TAIL = "cinematic, highly detailed, no text, no letters, no numbers, no watermark, no logo, any printed surface out of focus"
# (z0, z1, (cx0, cy0), (cx1, cy1)) like render.MOTIONS; "hook" is the first shot's move, "moves" cycle over the rest
CAMERAS = {
    "drift": {"hook": (1.00, 1.20, (0.5, 0.45), (0.5, 0.40)),
              "moves": [(1.00, 1.13, (0.5, 0.42), (0.5, 0.40)), (1.15, 1.02, (0.5, 0.44), (0.5, 0.50))]},
    "pan": {"hook": (1.16, 1.20, (0.22, 0.45), (0.70, 0.43)),
            "moves": [(1.13, 1.15, (0.80, 0.45), (0.20, 0.45)), (1.13, 1.15, (0.20, 0.45), (0.80, 0.45))]},
    "tilt": {"hook": (1.16, 1.20, (0.5, 0.18), (0.5, 0.58)),
             "moves": [(1.13, 1.15, (0.5, 0.78), (0.5, 0.25)), (1.13, 1.15, (0.5, 0.25), (0.5, 0.72))]},
    "punch": {"hook": (1.00, 1.34, (0.5, 0.46), (0.5, 0.40)),
              "moves": [(1.00, 1.24, (0.5, 0.42), (0.5, 0.38)), (1.26, 1.04, (0.45, 0.40), (0.5, 0.48)), (1.02, 1.22, (0.5, 0.55), (0.52, 0.45))]},
}


def looks_log() -> list[dict]:
    from faceless.fsutil import read_jsonl
    return [r for r in (read_jsonl(LOOKS) if LOOKS.exists() else []) if r.get("job") and r.get("composition") in COMPOSITIONS and r.get("camera") in CAMERAS]


def choose(history: list[dict], job_id: str) -> tuple[str, str]:
    """The pairing for the next video, given the earlier picks (oldest first). Deterministic for a given history and job id."""
    import hashlib
    prev = history[-1] if history else None
    recent = {(r["composition"], r["camera"]) for r in history[-AVOID_LAST:]}
    pairs = [(c, m) for c in COMPOSITIONS for m in CAMERAS]
    fit = [p for p in pairs if p not in recent and (not prev or (p[0] != prev["composition"] and p[1] != prev["camera"]))]
    fit = fit or [p for p in pairs if not prev or (p[0] != prev["composition"] and p[1] != prev["camera"])] or pairs
    return fit[int(hashlib.sha256(job_id.encode()).hexdigest(), 16) % len(fit)]


def pick_look(job_id: str, pillar_id: str) -> dict:
    """This job's look: the one already recorded for it, else a new pick, written before anything is drawn."""
    import fcntl
    from faceless import config, events
    grade = getattr(config.pillar(pillar_id), "grade", "warm")
    LOOKS_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LOOKS_LOCK, "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            history = looks_log()
            mine = next((r for r in reversed(history) if r["job"] == job_id), None)
            if mine:
                return {k: mine[k] for k in ("composition", "camera", "grade")}
            comp, cam = choose(history, job_id)
            row = {"t": events.now_iso(), "job": job_id, "pillar": pillar_id, "composition": comp, "camera": cam, "grade": grade}
            LOOKS.parent.mkdir(parents=True, exist_ok=True)
            with open(LOOKS, "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            return {"composition": comp, "camera": cam, "grade": grade}
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def still_suffix(look: dict | None) -> str:
    comp = COMPOSITIONS.get((look or {}).get("composition") or "center", COMPOSITIONS["center"])
    return f"{comp}, {STILL_TAIL}"


def look_component(rows: list[dict]) -> tuple[float | None, dict]:
    """Sameness of the recorded looks: how often the most common pairing occurs, and how often a video repeats the one before it."""
    looks = [(r["render"]["look"].get("composition"), r["render"]["look"].get("camera")) for r in rows if (r.get("render") or {}).get("look")]
    if len(looks) < 6:
        return None, {"recorded": len(looks)}
    rows_order = looks[::-1]                                 # recent() is newest first
    repeats = sum(1 for a, b in zip(rows_order, rows_order[1:]) if a == b)
    share = _share([f"{c}/{m}" for c, m in looks])
    score = max(0.0, (share - 0.15) / 0.5) + repeats / max(1, len(looks) - 1)
    return min(1.0, score), {"recorded": len(looks), "topShare": round(share, 2), "backToBack": repeats}


def still_style_component(rows: list[dict]) -> tuple[float | None, dict]:
    """Sameness of the stills' own style sentence, read from the prompts the image model was sent (images.json)."""
    styles = []
    for r in rows:
        try:
            imgs = json.loads((Paths.output / r["day"] / r["job"] / "images.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError):
            continue
        p = next((x.get("prompt") or "" for x in imgs if x.get("provider") not in ("card", "flow") and x.get("prompt")), "")
        if ". " in p:
            styles.append(p.rsplit(". ", 1)[-1].split(", vertical 9:16")[0][:120])
    if len(styles) < 6:
        return None, {"measured": len(styles)}
    share = _share(styles)
    return min(1.0, max(0.0, (share - 0.35) / 0.5)), {"measured": len(styles), "distinct": len(set(styles)), "topShare": round(share, 2)}
