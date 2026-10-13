"""Measurement: what each video earned, read back from YouTube, written where the pillar scorer and the weekly brief can use it.

`python -m faceless metrics --pull` reads every video scheduled in the last 14 days (the same call as yt-verify) and appends:
  * a snapshot to analytics/snapshots.jsonl at the 48-hour and 7-day marks (one per job per mark): views, likes, comments, age, and the counting basis;
  * one row per job to analytics/metrics.jsonl at the 48-hour mark, the format the pillar scorer already reads (analytics/CONTEXT.md).
Weights therefore never move on a video younger than 48 hours (the marketing strategy's rule), and the scorer's 35% exploration floor is untouched.
The YouTube Data API gives views, likes and comments, not retention or follows: `avg_view_pct` and `follows` are left out of the row, which the scorer reads as neutral.
Views are counted on YouTube's rules at the time; `basis` records which API produced the number, because the counting rules have changed before.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone

from faceless import config
from faceless.config import Paths
from faceless.fsutil import read_jsonl

SNAPSHOTS = Paths.analytics / "snapshots.jsonl"
METRICS = Paths.analytics / "metrics.jsonl"
MARKS = (48, 168)                       # hours after the post time
BASIS = "youtube-data-api-v3"


def _append(path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def age_hours(post_at: str | None, now: datetime) -> float | None:
    try:
        t = datetime.fromisoformat(post_at) if post_at else None
    except ValueError:
        return None
    if t is None:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (now - t).total_seconds() / 3600


def due(rows: list[dict], snapshots: list[dict], now: datetime) -> list[dict]:
    """The snapshots to record now. rows: [{job, video, pillar, post_at, privacy, views, likes, comments}]. A video that is still private has no audience yet."""
    have = {(s.get("job"), s.get("mark_h")) for s in snapshots}
    out = []
    for r in rows:
        if r.get("privacy") != "public":
            continue
        age = age_hours(r.get("post_at"), now)
        if age is None:
            continue
        for mark in MARKS:
            if age >= mark and (r["job"], mark) not in have:
                out.append({"day": now.strftime("%Y-%m-%d"), "job": r["job"], "video": r["video"], "pillar": r.get("pillar", ""), "platform": "youtube",
                            "mark_h": mark, "age_h": round(age, 1), "views": r["views"], "likes": r["likes"], "comments": r["comments"], "basis": BASIS})
    return out


def metric_row(snap: dict) -> dict:
    """The row the pillar scorer reads. No retention and no follows are known from this source, so those fields are absent."""
    return {"job": snap["job"], "pillar": snap["pillar"], "platform": "youtube", "views": snap["views"], "likes": snap["likes"],
            "comments": snap["comments"], "date": snap["day"], "source": "metrics --pull", "basis": snap["basis"]}


def pull(now: datetime | None = None, days: int = 14) -> dict:
    """Read back the last `days` days of scheduled videos and record what is due. Returns {checked, snapshots, rows, problems}."""
    from faceless import ytchannel
    from faceless.state import all_jobs
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    jobs = {}
    for j in all_jobs():
        y = j.artifacts.get("youtube") or {}
        if y.get("video_id") and (not y.get("post_at") or datetime.fromisoformat(y["post_at"]).astimezone(timezone.utc) > since):
            jobs[y["video_id"]] = {"job": j.id, "pillar": j.pillar, "post_at": y.get("post_at")}
    problems, got = ytchannel.verify({v: {"job": i["job"], "post_at": i["post_at"]} for v, i in jobs.items()}, now=now)
    rows = [{**r, "pillar": jobs[r["video"]]["pillar"], "post_at": jobs[r["video"]]["post_at"]} for r in got if r["video"] in jobs]
    fresh = due(rows, read_jsonl(SNAPSHOTS), now)
    _append(SNAPSHOTS, fresh)
    scored = [metric_row(s) for s in fresh if s["mark_h"] == MARKS[0]]
    _append(METRICS, scored)
    return {"checked": len(rows), "snapshots": len(fresh), "rows": len(scored), "problems": problems}


def coverage(jobs_with_youtube: list[str], snapshots: list[dict]) -> dict:
    """How many scheduled videos have each mark recorded (the KPI: every upload gets a 48-hour and a 7-day snapshot)."""
    out = {}
    for mark in MARKS:
        got = {s["job"] for s in snapshots if s.get("mark_h") == mark}
        out[mark] = len(got & set(jobs_with_youtube))
    return out


def to_csv(path=SNAPSHOTS) -> str:
    rows = read_jsonl(path)
    cols = ["day", "job", "pillar", "platform", "mark_h", "age_h", "views", "likes", "comments", "basis"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def summary(window_days: int = 14) -> dict:
    """Median 48-hour views by pillar over the last `window_days`, for the weekly brief."""
    import statistics
    floor = (config.today_utc() - timedelta(days=window_days)).isoformat()
    by: dict[str, list[int]] = {}
    for s in read_jsonl(SNAPSHOTS):
        if s.get("mark_h") == MARKS[0] and str(s.get("day", "")) >= floor:
            by.setdefault(s.get("pillar", ""), []).append(int(s.get("views", 0)))
    return {p: {"n": len(v), "median_views": statistics.median(v)} for p, v in sorted(by.items())}
