"""Backlog posting: the strongest unposted video of each series gets a time of its own, in the launch order, never in the past."""

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from faceless import backlog

ET = ZoneInfo("America/New_York")


def job(i, pillar, score, passed=True, yt=None, video=True, tmp=None):
    f = tmp / f"{i}.mp4"
    if video:
        f.write_bytes(b"x")
    return SimpleNamespace(id=i, pillar=pillar, day="2026-10-01", scores={"gauntlet": score, "passed": passed},
                           artifacts={"video": str(f), **({"youtube": yt} if yt else {})})


def test_picks_best_per_series_skips_posted_failed_and_missing(tmp_path):
    jobs = [job("e1", "escape", 90, tmp=tmp_path), job("e2", "escape", 96, tmp=tmp_path), job("s1", "story", 100, tmp=tmp_path),
            job("m1", "math", 99, yt={"video_id": "v"}, tmp=tmp_path), job("m2", "math", 95, passed=False, tmp=tmp_path),
            job("p1", "psychology", 100, video=False, tmp=tmp_path), job("y1", "myth", 95, tmp=tmp_path)]
    plan = backlog.plan(jobs, 5, datetime(2026, 10, 11, 8, 0, tzinfo=ET))
    assert [j.id for j, _ in plan][:3] == ["e2", "s1", "y1"]          # escape leads; posted, failed and fileless ones are not candidates


def test_times_are_spread_ahead_of_now_and_the_best_slot_goes_to_the_lead_series(tmp_path):
    jobs = [job(f"j{i}", p, 99 - i, tmp=tmp_path) for i, p in enumerate(["escape", "story", "math", "psychology", "myth"])]
    now = datetime(2026, 10, 11, 8, 0, tzinfo=ET)
    plan = backlog.plan(jobs, 5, now)
    times = sorted(t for _, t in plan)
    assert len(set(times)) == 5 and times[0] > now and [t.strftime("%H:%M") for t in times] == ["08:30", "11:30", "15:00", "18:30", "21:00"]
    assert dict((j.pillar, t.strftime("%H:%M")) for j, t in plan)["escape"] == "11:30"
    assert dict((j.pillar, t.strftime("%H:%M")) for j, t in plan)["myth"] == "08:30"   # the catch-up slot is the weakest


def test_late_in_the_day_fewer_times_are_offered_than_requested_never_in_the_past(tmp_path):
    jobs = [job(f"j{i}", p, 90, tmp=tmp_path) for i, p in enumerate(["escape", "story", "math"])]
    now = datetime(2026, 10, 11, 20, 50, tzinfo=ET)
    plan = backlog.plan(jobs, 3, now)
    assert all(t > now for _, t in plan)
