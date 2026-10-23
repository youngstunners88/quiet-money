"""R1: the road to the YouTube Partner Program, measured, with a pace and a date for each tier.

The thresholds are YouTube's, read from its help pages on 2026-10-23 (SOURCES below); YouTube has announced YPP updates from
2027-02-01 without saying how the numbers change, so re-check the pages then. Two tiers matter:

- expanded YPP (fan funding, Shopping): 500 subscribers, 3 public uploads in 90 days, and 3,000 watch hours in 12 months or
  3 million Shorts views in 90 days;
- ad revenue sharing: 1,000 subscribers and 4,000 watch hours in 12 months or 10 million Shorts views in 90 days.

What is measured: subscribers live from the channel (Data API through the studio's connection), public uploads in the last 90 days
from the engine's own records, and Shorts views in the last 90 days as the latest view count of each Short posted in that window
(an approximation: YouTube counts only views made inside the window, and only qualified ones). Watch hours of long-form need the
YouTube Analytics API, which the connection does not have, so they are reported as unknown, never guessed (rule 1).

Each `--pull` appends a snapshot to `analytics/ypp.jsonl`; the pace (per day, over the last 14 days of snapshots) gives an estimated
date for each tier, labelled as an estimate. `python -m faceless ypp [--pull]`.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from faceless import config
from faceless.config import Paths
from faceless.fsutil import read_jsonl

LOG = Paths.analytics / "ypp.jsonl"
SOURCES = ["https://support.google.com/youtube/answer/72851", "https://support.google.com/youtube/answer/13429240"]
CHECKED = "2026-10-23"
TIERS = {
    "expanded": {"label": "Expanded YPP (fan funding, Shopping)", "subs": 500, "uploads90": 3, "shorts90": 3_000_000, "hours365": 3_000},
    "revenue": {"label": "Ad revenue sharing", "subs": 1_000, "uploads90": 0, "shorts90": 10_000_000, "hours365": 4_000},
}
PACE_DAYS = 14


def subscribers() -> int | None:
    from faceless import ytchannel
    items = ytchannel.api("channels", part="statistics", mine="true").get("items") or []
    stats = (items[0].get("statistics") or {}) if items else {}
    return int(stats["subscriberCount"]) if "subscriberCount" in stats else None


def _posted_on(job) -> date | None:
    y = job.artifacts.get("youtube") or {}
    if not y.get("video_id"):
        return None
    try:
        return datetime.fromisoformat(y.get("post_at") or job.day).date()
    except ValueError:
        return None


def measure(today: date | None = None, subs: int | None = None) -> dict:
    """The counts YouTube judges, as far as the engine can see them. `subs` lets a test (or an offline run) skip the network."""
    from faceless import longform
    from faceless.state import all_jobs
    today = today or config.today_utc()
    since = today - timedelta(days=90)
    posted = {j.id: d for j in all_jobs() if (d := _posted_on(j)) and since < d <= today}
    long_posts = [r for r in read_jsonl(longform.LEDGER) if r.get("video_id") and str(r.get("week", "")) > since.isoformat()]
    latest: dict[str, dict] = {}
    for r in read_jsonl(Paths.analytics / "metrics.jsonl"):
        if r.get("platform") == "youtube" and r.get("job") in posted and str(r.get("date", "")) >= str(latest.get(r["job"], {}).get("date", "")):
            latest[r["job"]] = r
    return {"day": today.isoformat(), "subscribers": subs, "uploads90": len(posted) + len(long_posts),
            "shorts90": sum(int(r.get("views") or 0) for r in latest.values()), "hours365": None}


def pull(today: date | None = None) -> dict:
    """Measure with live subscribers and append the snapshot. A refused read (the shared quota) records subscribers as unknown, never a guess."""
    from faceless.providers import ProviderError, ProviderUnavailable
    try:
        subs, note = subscribers(), None
    except (ProviderError, ProviderUnavailable) as e:
        subs, note = None, str(e)[:120]
    snap = measure(today, subs)
    if note:
        snap["note"] = note
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(snap) + "\n")
    return snap


def pace(rows: list[dict], key: str) -> float | None:
    """Growth per day of `key` over the last PACE_DAYS of snapshots (first and last reading); None without two readings."""
    pts = [(date.fromisoformat(r["day"]), r[key]) for r in rows if r.get(key) is not None and r.get("day")]
    if len(pts) < 2:
        return None
    end = pts[-1][0]
    window = [p for p in pts if (end - p[0]).days <= PACE_DAYS]
    (d0, v0), (d1, v1) = window[0], window[-1]
    return (v1 - v0) / (d1 - d0).days if (d1 - d0).days else None


def report(rows: list[dict] | None = None) -> dict:
    """Where each tier stands: progress per requirement, the pace, and an estimated date (labelled) when the pace is positive."""
    rows = rows if rows is not None else read_jsonl(LOG)
    now = rows[-1] if rows else measure()
    rates = {k: pace(rows, k) for k in ("subscribers", "shorts90")}
    out = {"asOf": now["day"], "checked": CHECKED, "sources": SOURCES, "now": now, "perDay": rates, "tiers": []}
    for key, t in TIERS.items():
        needs = []
        for k in ("subs", "uploads90", "shorts90"):
            have = now.get({"subs": "subscribers"}.get(k, k))
            if not t[k]:
                continue
            rate = rates.get({"subs": "subscribers"}.get(k, k))
            gap = None if have is None else max(0, t[k] - have)
            eta = None
            if gap == 0:
                eta = now["day"]
            elif gap and rate and rate > 0:
                eta = (date.fromisoformat(now["day"]) + timedelta(days=int(gap / rate) + 1)).isoformat()
            needs.append({"what": k, "need": t[k], "have": have, "pct": None if have is None else round(min(1.0, have / t[k]) * 100, 1),
                          "estimatedDate": eta})
        out["tiers"].append({"tier": key, "label": t["label"], "needs": needs,
                             "alternative": f"or {t['hours365']:,} long-form watch hours in 12 months (not measurable here)",
                             "met": all(n["pct"] == 100.0 for n in needs)})
    return out


def text(r: dict) -> str:
    n = r["now"]
    lines = [f"YouTube Partner Program, as of {r['asOf']} (thresholds checked {r['checked']})",
             f"subscribers {n['subscribers'] if n['subscribers'] is not None else 'unknown'}, public uploads in 90 days {n['uploads90']}, "
             f"Shorts views in 90 days about {n['shorts90']:,} (latest count of each Short posted in the window)"]
    for t in r["tiers"]:
        parts = [f"{x['what']} {x['have'] if x['have'] is not None else '?'}/{x['need']:,} ({x['pct'] if x['pct'] is not None else '?'}%"
                 + (f", est. {x['estimatedDate']}" if x["estimatedDate"] else "") + ")" for x in t["needs"]]
        lines.append(f"{t['label']}: " + ("MET" if t["met"] else "; ".join(parts)) + f"; {t['alternative']}")
    lines.append("Estimated dates assume the last 14 days' pace holds; they are estimates, not forecasts.")
    return "\n".join(lines)
