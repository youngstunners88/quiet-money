"""Backlog posting: made, quality-passed videos that were never put on YouTube get a slot of their own.

The channel's ideal is five videos a day. When the daily run could not post (a day missed, a platform not ready yet) the finished
videos stay in the queue; this picks the strongest unposted video of each series, in the launch order, and gives each a time
spread over the day's remaining slots (a slot already gone is replaced by the next free half hour, never a minute earlier than
the upload needs). Nothing here uploads: `post-backlog` hands each planned job to the normal YouTube publisher, so the same
channel check, daily cap, kill switch and idempotency apply.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from faceless import config, launch
from faceless.providers.publish import LEAD, nominal_time


def candidates(jobs) -> list:
    """Passed jobs with a rendered file, not yet on YouTube, best score first (ties: newest)."""
    ok = [j for j in jobs if j.scores.get("passed") and j.artifacts.get("video") and Path(j.artifacts["video"]).exists()
          and not (j.artifacts.get("youtube") or {}).get("video_id")]
    return sorted(ok, key=lambda j: (-int(j.scores.get("gauntlet", 0)), j.day, j.id))


def meta(job) -> dict:
    """The posting meta of a job: its own, or the one in the local pack the daily run wrote (the first batches kept it only there)."""
    for p in (job.dir / "meta.json", Path((job.artifacts.get("publish") or {}).get("local", {}).get("folder", "/nonexistent")) / "meta.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"no meta.json for {job.id}")


def scheduled(jobs) -> set:
    """Times already taken on YouTube."""
    return {datetime.fromisoformat(j.artifacts["youtube"]["post_at"]) for j in jobs
            if (j.artifacts.get("youtube") or {}).get("video_id") and j.artifacts["youtube"].get("post_at")}


def _slot_times(post_day: str, now: datetime, n: int, taken: set = frozenset()) -> list[datetime]:
    """n times for post_day: each configured slot still ahead and free (with the upload lead), then catch-up half hours for the slots already gone."""
    cfg = config.load()["publish"]
    count = len(cfg["slots"])
    ahead = [nominal_time(post_day, k) for k in range(count)]
    live = [t for t in ahead if t > now + LEAD and t not in taken]
    gone = sum(1 for t in ahead if t <= now + LEAD)
    catch, t = [], now + LEAD + timedelta(minutes=10)
    t = t.replace(second=0, microsecond=0) + timedelta(minutes=(30 - t.minute % 30) % 30)
    for _ in range(max(0, min(gone, n - len(live)))):
        catch.append(t)
        t += timedelta(hours=1, minutes=30)
    return sorted(catch + live)[:n]


def plan(jobs, n: int, now: datetime | None = None) -> list[tuple]:
    """[(job, when)] for up to n videos: one per series in launch order first, then the next best; times ascending, strongest
    series in the slots expected to do best (`[publish.launch] slot_value`)."""
    cfg = config.load()["publish"]
    tz = ZoneInfo(cfg["timezone"])
    now = (now or datetime.now(tz)).astimezone(tz)
    order = launch.settings().get("pillars", [])
    pool = candidates(jobs)
    chosen, used = [], set()
    today = {j.pillar for j in jobs if (j.artifacts.get("youtube") or {}).get("post_at")
             and datetime.fromisoformat(j.artifacts["youtube"]["post_at"]).astimezone(tz).date() == now.date()}   # a series already out today waits its turn
    for pillar in [p for p in order + sorted({j.pillar for j in pool} - set(order)) if p not in today]:
        best = next((j for j in pool if j.pillar == pillar and j.id not in used), None)
        if best:
            chosen.append(best)
            used.add(best.id)
    for j in pool:                                           # fewer series than n: the best of what is left
        if len(chosen) >= n:
            break
        if j.id not in used:
            chosen.append(j)
            used.add(j.id)
    chosen = chosen[:n]
    times = _slot_times(now.date().isoformat(), now, len(chosen), scheduled(jobs))
    value = launch.settings().get("slot_value", [])          # slot index, best first; rank times by their configured slot where there is one
    slot_of = {nominal_time(now.date().isoformat(), k): k for k in range(len(cfg["slots"]))}
    rank = lambda t: value.index(slot_of[t]) if t in slot_of and slot_of[t] in value else len(value)
    by_value = sorted(times, key=lambda t: (rank(t), t))
    return list(zip(chosen, by_value))
