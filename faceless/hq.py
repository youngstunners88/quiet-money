"""HQ: one snapshot of the whole business for the owner's dashboard, computed from the repo so every number is true (rule 1).

`python -m faceless hq` prints it; `--json` gives the document the dashboard reads (the Quiet Money HQ artifact, `hq/state`). It only reads:
the daily Shorts factory (state/jobs), the audience (analytics/metrics.jsonl), money (analytics/sales.jsonl, the ledger), the products
(channel/shop/catalog.json and the live URLs in studio.toml [offer]), the service desk (faceless/outbound.py) and what to build next
(faceless/empire.py). Each section names its source, so the page can say where a figure came from.

Nothing here is a forecast. A projection belongs to `faceless forecast`, labelled as an assumption.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone

from faceless import config
from faceless.config import Paths
from faceless.fsutil import read_jsonl

TARGET_PER_DAY = 5                                  # rule 15: at least five Shorts a day
WINDOW_DAYS = 14


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def shorts(today: str | None = None) -> dict:
    """The factory: Shorts that passed the gauntlet per day, what was held, and how many are on YouTube."""
    from faceless.state import all_jobs
    today = today or config.today_utc().isoformat()
    floor = (datetime.fromisoformat(today) - timedelta(days=WINDOW_DAYS - 1)).date().isoformat()
    jobs = [j for j in all_jobs() if not j.id.startswith("host-")]
    days: dict[str, dict] = {}
    for j in jobs:
        if floor <= j.day <= today:
            d = days.setdefault(j.day, {"day": j.day, "passed": 0, "held": 0})
            if j.status == "published":
                d["passed"] += 1
            elif j.status == "held":
                d["held"] += 1
    series = [days.get(d, {"day": d, "passed": 0, "held": 0})
              for d in ((datetime.fromisoformat(floor) + timedelta(days=i)).date().isoformat() for i in range(WINDOW_DAYS))]
    last7 = series[-7:]
    made7 = sum(d["passed"] + d["held"] for d in last7)
    scores = [float(j.scores["gauntlet"]) for j in jobs
              if j.day >= last7[0]["day"] and isinstance((j.scores or {}).get("gauntlet"), (int, float))]
    return {
        "targetPerDay": TARGET_PER_DAY,
        "days": series,
        "passedLast7": sum(d["passed"] for d in last7),
        "daysOnTargetLast7": sum(1 for d in last7 if d["passed"] >= TARGET_PER_DAY),
        "holdRateLast7": round(sum(d["held"] for d in last7) / made7, 3) if made7 else None,
        "avgScoreLast7": round(statistics.mean(scores), 1) if scores else None,
        "passedAllTime": sum(1 for j in jobs if j.status == "published"),
        "onYouTube": sum(1 for j in jobs if (j.artifacts.get("youtube") or {}).get("video_id")),
        "source": "state/jobs",
    }


def audience() -> dict:
    """What the Shorts earned: the latest view count per measured video, the best one, and the median by series."""
    from faceless.state import all_jobs
    rows = [r for r in read_jsonl(Paths.analytics / "metrics.jsonl") if r.get("platform") == "youtube"]
    latest: dict[str, dict] = {}
    for r in rows:
        latest[r.get("job", "")] = r
    topics = {j.id: j.topic for j in all_jobs()}
    measured = [r for k, r in latest.items() if k]
    by: dict[str, list[int]] = {}
    for r in measured:
        by.setdefault(r.get("pillar") or "other", []).append(int(r.get("views") or 0))
    best = max(measured, key=lambda r: int(r.get("views") or 0), default=None)
    return {
        "measured": len(measured),
        "views": sum(int(r.get("views") or 0) for r in measured),
        "best": {"title": topics.get(best["job"], best["job"]), "views": int(best.get("views") or 0), "pillar": best.get("pillar")} if best else None,
        "byPillar": sorted(({"pillar": p, "n": len(v), "medianViews": statistics.median(v)} for p, v in by.items()),
                           key=lambda x: -x["medianViews"]),
        "pulledOn": max((r.get("date") or "" for r in measured), default=None) or None,
        "source": "analytics/metrics.jsonl (YouTube Data API v3)",
    }


def money(today: str | None = None) -> dict:
    """Sales and spend. Income is what sold, net of the platform's fee; there is no other income line yet."""
    from faceless import ledger, marketing, safety
    today = today or config.today_utc().isoformat()
    s = marketing.sales_summary()
    floor = (datetime.fromisoformat(today) - timedelta(days=30)).date().isoformat()
    recent = [r for r in read_jsonl(marketing.SALES)
              if not r.get("refunded") and str(r.get("day") or r.get("date") or "")[:10] >= floor]
    net30 = sum(marketing.net_per_sale(float(r.get("usd") or 0)) for r in recent if float(r.get("usd") or 0) > 0)
    return {
        "sales": s["sales"], "grossUsd": s["gross"], "netUsd": s["net_estimate"],
        "netLast30Usd": round(net30, 2),
        "balanceGateUsd": marketing.GATE_USD, "toGateUsd": s["to_gate"],
        "spendTodayUsd": round(ledger.usd_total(), 2), "ceilingUsd": safety.ceiling(),
        "spendWeekUsd": round(marketing.week_spend(), 2),
        "source": "analytics/sales.jsonl, state/ledger.jsonl",
    }


def products() -> list[dict]:
    """The catalog, and which items have a live listing URL (the only proof a product is on sale)."""
    live = (config.load().get("offer", {}) or {}).get("shop_urls") or {}
    try:
        cat = json.loads((Paths.root / "channel" / "shop" / "catalog.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = cat if isinstance(cat, list) else cat.get("products", list(cat.values()) if isinstance(cat, dict) else [])
    out = []
    for it in items:
        if isinstance(it, dict) and it.get("id"):
            out.append({"id": it["id"], "name": it.get("title") or it.get("name") or it["id"].replace("-", " ").title(),
                        "priceUsd": it.get("price"), "live": it["id"] in live})
    return out


def service() -> dict:
    """The Web3 video + KOL service desk. Lead cards are gitignored, so a fresh checkout counts from the hashed memory."""
    from faceless import outbound
    p = outbound.pipeline()
    return {"projectsSeen": p["projects_seen"], "packagesWaiting": len(p["packages_waiting"]),
            "outcomes": p["outcomes"], "replies": sum(v for k, v in p["outcomes"].items() if k.startswith("reply-")),
            "calls": p["outcomes"].get("call-booked", 0), "closed": p["outcomes"].get("closed", 0),
            "source": "state/outbound-seen.json, state/outbound-outcomes.jsonl"}


def brief(item: dict) -> str:
    """A ready prompt for a Claude Code session that builds one portfolio item."""
    return (f"Build {item['id']}: {item['name']}. {item.get('what', '').strip()}\n\n"
            "Read CLAUDE.md and the skill the routing table names for this work first. Build it fully, add tests, run "
            "`python -m faceless ci` until it is green, open a pull request and merge it once CI passes. "
            "Then update the portfolio stage in channel/empire/portfolio.jsonl and say what the owner needs to do to launch it, if anything.")


def next_moves(limit: int = 6) -> dict:
    """What to work on: what the agent can build now, what is built and waits on one owner step, and the owner's unlocks by value."""
    from faceless import empire, marketing
    rows = empire.rank()

    def pick(lane: str) -> list[dict]:
        return [{"id": r["id"], "title": r["name"], "rail": r["rail"], "score": r["score"], "next": r["action"],
                 **({"brief": brief(r)} if lane == "agent" else {})}
                for r in rows if r["lane"] == lane][:limit]

    unlocks = [{"ask": ask, "unlocksScore": score, "items": ids} for ask, score, ids in empire.asks(rows)[:limit]]
    queue = [{"id": i.get("id"), "text": i.get("ask") or i.get("text") or i.get("title") or ""} for i in marketing.owner_queue(3)]
    return {"agent": pick("agent"), "launch": pick("launch"), "unlocks": unlocks, "ownerQueue": queue,
            "source": "faceless/empire.py (channel/empire/portfolio.jsonl), channel/empire/owner_queue.json"}


def snapshot() -> dict:
    return {"asOf": _now(), "shorts": shorts(), "audience": audience(), "money": money(), "products": products(),
            "service": service(), "next": next_moves()}


def summary(s: dict | None = None) -> str:
    s = s or snapshot()
    sh, au, mo = s["shorts"], s["audience"], s["money"]
    live = [p["name"] for p in s["products"] if p["live"]]
    lines = [
        f"Quiet Money HQ, {s['asOf']}",
        f"Shorts: {sh['passedLast7']} passed in 7 days ({sh['daysOnTargetLast7']}/7 days at {sh['targetPerDay']}), "
        f"{sh['passedAllTime']} all time, {sh['onYouTube']} on YouTube",
        f"Audience: {au['views']:,} views on {au['measured']} measured videos"
        + (f"; best {au['best']['views']} ({au['best']['title'][:50]})" if au["best"] else ""),
        f"Money: {mo['sales']} sales, ${mo['netUsd']:.2f} net; spent ${mo['spendTodayUsd']:.2f} of ${mo['ceilingUsd']:.2f} today",
        f"Products: {len(s['products'])} built, live: {', '.join(live) or 'none'}",
        f"Service desk: {s['service']['projectsSeen']} projects screened, {s['service']['replies']} replies",
        "Build next: " + ", ".join(f"{a['id']} {a['title']}" for a in s["next"]["agent"][:3]),
    ]
    return "\n".join(lines)
