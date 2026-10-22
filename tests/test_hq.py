"""The HQ snapshot: every figure on the owner's dashboard comes from here, so each one must be counted from the repo, never guessed."""

import json

import pytest

from faceless import hq, state
from faceless.config import Paths
from faceless.state import Job


@pytest.fixture
def jobs(monkeypatch):
    rows = []
    monkeypatch.setattr(state, "all_jobs", lambda: rows)
    return rows


def _job(day, slot, status, score=90, yt=False, pillar="story", jid=None):
    return Job(id=jid or f"{day}-s{slot}-{pillar}-x{slot}", pillar=pillar, topic=f"topic {slot}", day=day, slot=slot, status=status,
               scores={"gauntlet": score, "passed": status == "published"},
               artifacts={"youtube": {"video_id": f"v{slot}"}} if yt else {})


def test_shorts_counts_passed_and_held_per_day_against_the_five_a_day_standard(jobs):
    jobs += [_job("2026-10-22", s, "published", yt=True) for s in range(1, 6)]
    jobs += [_job("2026-10-21", 1, "published"), _job("2026-10-21", 2, "held", score=70)]
    s = hq.shorts(today="2026-10-22")
    by = {d["day"]: d for d in s["days"]}
    assert by["2026-10-22"] == {"day": "2026-10-22", "passed": 5, "held": 0}
    assert by["2026-10-21"] == {"day": "2026-10-21", "passed": 1, "held": 1}
    assert s["daysOnTargetLast7"] == 1 and s["passedLast7"] == 6
    assert s["holdRateLast7"] == round(1 / 7, 3) and s["onYouTube"] == 5
    assert len(s["days"]) == hq.WINDOW_DAYS and s["days"][-1]["day"] == "2026-10-22"     # empty days are shown as zero, not skipped


def test_the_weekly_host_clip_is_not_counted_as_a_short(jobs):
    jobs += [_job("2026-10-22", 1, "published", jid="host-2026-10-22-abc")]
    assert hq.shorts(today="2026-10-22")["passedAllTime"] == 0


def test_audience_uses_each_video_s_latest_count_and_names_the_best(jobs, tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "analytics", tmp_path)
    jobs += [_job("2026-10-16", 5, "published", jid="a"), _job("2026-10-16", 6, "published", jid="b")]
    rows = [{"job": "a", "platform": "youtube", "pillar": "story", "views": 10, "date": "2026-10-18"},
            {"job": "a", "platform": "youtube", "pillar": "story", "views": 176, "date": "2026-10-20"},   # a later pull replaces the earlier
            {"job": "b", "platform": "youtube", "pillar": "math", "views": 14, "date": "2026-10-20"},
            {"job": "b", "platform": "tiktok", "pillar": "math", "views": 999, "date": "2026-10-20"}]
    (tmp_path / "metrics.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    a = hq.audience()
    assert a["measured"] == 2 and a["views"] == 190
    assert a["best"] == {"title": "topic 5", "views": 176, "pillar": "story"}
    assert a["pulledOn"] == "2026-10-20"


def test_a_product_is_live_only_when_its_listing_url_is_in_studio_toml(monkeypatch):
    from faceless import config
    real = config.load()
    monkeypatch.setattr(config, "load", lambda: {**real, "offer": {"shop_urls": {"daily-quiet-money-planner": "https://x"}}})
    live = {p["id"]: p["live"] for p in hq.products()}
    assert live["daily-quiet-money-planner"] is True
    assert live["debt-payoff-planner"] is False


def test_every_build_suggestion_carries_a_prompt_a_session_can_run():
    n = hq.next_moves()
    assert n["agent"], "the portfolio always has something the agent can build"
    for item in n["agent"]:
        assert item["brief"].startswith(f"Build {item['id']}:")
        assert "python -m faceless ci" in item["brief"]
    assert all("brief" not in item for item in n["launch"])          # a built item waits on the owner; there is nothing to build
    assert all(q["text"] for q in n["ownerQueue"])                     # the queue's own field is "ask"


def test_rule_16_moved_the_already_held_keys_out_of_the_owner_s_queue():
    """Mistral and PostHog were 'say yes to the key already in the environment'; rule 16 answered both (2026-10-22)."""
    asks = " ".join(u["ask"] for u in hq.next_moves(limit=50)["unlocks"])
    assert "Mistral key already in the environment" not in asks
    assert "PostHog key already in the environment" not in asks


def test_the_snapshot_is_one_json_document_that_names_its_sources():
    s = hq.snapshot()
    json.dumps(s)
    for section in ("shorts", "audience", "money", "service", "next"):
        assert s[section]["source"], section
    assert len(json.dumps(s).encode()) < 200_000                      # the dashboard's store refuses a document over 256 KB
