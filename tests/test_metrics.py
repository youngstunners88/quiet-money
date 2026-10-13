from datetime import datetime, timedelta, timezone

from faceless import metrics

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def row(job, hours_ago, privacy="public", views=100):
    post = (NOW - timedelta(hours=hours_ago)).isoformat()
    return {"job": job, "video": "v" + job, "pillar": "math", "post_at": post, "privacy": privacy, "views": views, "likes": 5, "comments": 1}


def test_nothing_is_recorded_before_48_hours_or_while_private():
    assert metrics.due([row("a", 10), row("b", 60, privacy="private")], [], NOW) == []


def test_the_48_hour_mark_is_recorded_once_and_the_7_day_mark_later():
    first = metrics.due([row("a", 60)], [], NOW)
    assert [s["mark_h"] for s in first] == [48]
    assert metrics.due([row("a", 60)], first, NOW) == []
    later = metrics.due([row("a", 200)], first, NOW)
    assert [s["mark_h"] for s in later] == [168]


def test_scorer_row_has_no_retention_or_follows():
    snap = metrics.due([row("a", 60)], [], NOW)[0]
    r = metrics.metric_row(snap)
    assert r["views"] == 100 and r["pillar"] == "math" and "avg_view_pct" not in r and "follows" not in r


def test_coverage_counts_scheduled_jobs_only():
    snaps = [{"job": "a", "mark_h": 48}, {"job": "a", "mark_h": 168}, {"job": "zz", "mark_h": 48}]
    assert metrics.coverage(["a", "b"], snaps) == {48: 1, 168: 1}


def test_bad_post_time_is_skipped():
    r = row("a", 60)
    r["post_at"] = "not a date"
    assert metrics.due([r], [], NOW) == []
