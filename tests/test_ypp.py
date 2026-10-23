"""R1: Partner Program progress counts only what YouTube counts, and dates are estimates from a measured pace."""

import json
from datetime import date

from faceless import longform, state, ypp
from faceless.config import Paths
from faceless.state import Job


def test_measure_counts_uploads_and_shorts_views_in_the_90_day_window(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "analytics", tmp_path)
    monkeypatch.setattr(longform, "LEDGER", tmp_path / "lf.jsonl")
    jobs = [Job(id=f"j{i}", pillar="story", topic="t", day=d, slot=0, status="published", artifacts={"youtube": {"video_id": f"v{i}", "post_at": f"{d}T15:00:00"}})
            for i, d in enumerate(["2026-10-20", "2026-09-01", "2026-06-01"])]
    jobs.append(Job(id="never", pillar="story", topic="t", day="2026-10-20", slot=1, status="published"))
    monkeypatch.setattr(state, "all_jobs", lambda: jobs)
    rows = [{"job": "j0", "platform": "youtube", "views": 10, "date": "2026-10-21"}, {"job": "j0", "platform": "youtube", "views": 40, "date": "2026-10-22"},
            {"job": "j1", "platform": "youtube", "views": 5, "date": "2026-10-22"}, {"job": "j2", "platform": "youtube", "views": 999, "date": "2026-10-22"},
            {"job": "j0", "platform": "tiktok", "views": 500, "date": "2026-10-22"}]
    (tmp_path / "metrics.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (tmp_path / "lf.jsonl").write_text(json.dumps({"week": "2026-10-21", "video_id": "L"}) + "\n")
    m = ypp.measure(date(2026, 10, 23), subs=120)
    assert m == {"day": "2026-10-23", "subscribers": 120, "uploads90": 3, "shorts90": 45, "hours365": None}


def test_report_gives_progress_and_estimated_dates_only_from_a_positive_pace():
    rows = [{"day": "2026-10-09", "subscribers": 100, "uploads90": 40, "shorts90": 10_000},
            {"day": "2026-10-23", "subscribers": 240, "uploads90": 60, "shorts90": 80_000}]
    r = ypp.report(rows)
    exp = next(t for t in r["tiers"] if t["tier"] == "expanded")
    subs = next(n for n in exp["needs"] if n["what"] == "subs")
    assert r["perDay"]["subscribers"] == 10 and subs["pct"] == 48.0 and subs["estimatedDate"] == "2026-11-19"
    assert next(n for n in exp["needs"] if n["what"] == "uploads90")["estimatedDate"] == "2026-10-23"     # already met
    assert not exp["met"] and "not measurable" in exp["alternative"]
    flat = ypp.report([rows[1]])
    assert all(n["estimatedDate"] in (None, "2026-10-23") for t in flat["tiers"] for n in t["needs"])      # one reading: no pace, no date
    assert "estimates" in ypp.text(r)
