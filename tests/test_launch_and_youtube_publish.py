"""Launch order and the YouTube publisher: the strongest lead takes the best slot, nothing uploads twice, the cap and the kill switch hold."""

from datetime import datetime, timedelta, timezone

import pytest

from faceless import launch
from faceless.providers import ProviderError, ProviderUnavailable
from faceless.providers import publish as pub

CFG = {"days": 3, "pillars": ["escape", "story", "math", "psychology", "myth", "playbook"], "slot_value": [1, 3, 4, 2, 0]}
DAY = ["story", "math", "psychology", "myth", "escape"]


def test_lead_pillar_takes_the_best_slot_in_the_window():
    plan = launch.strategic_plan(DAY, "2026-10-12", CFG, first=None)
    assert plan[1] == "escape" and plan[3] == "story" and plan[4] == "math"
    assert sorted(plan) == sorted(DAY)


def test_window_is_counted_from_the_first_scheduled_video_then_the_planner_rotates():
    assert launch.strategic_plan(DAY, "2026-10-14", CFG, first="2026-10-12") != DAY
    assert launch.strategic_plan(DAY, "2026-10-15", CFG, first="2026-10-12") == DAY
    assert launch.strategic_plan(DAY, "2026-10-12", {}, first=None) == DAY


class FakeJob:
    def __init__(self, tmp_path, day="2026-10-12", slot=1, youtube=None):
        self.id, self.day, self.slot, self.pillar = f"{day}-s{slot}", day, slot, "math"
        self.artifacts = {"video": str(tmp_path / "v.mp4"), **({"youtube": youtube} if youtube else {})}
        self.notes, self.dir = [], tmp_path
        self.saved = 0

    def save(self):
        self.saved += 1


META = {"title": "T", "description": "D", "hashtags": ["#a", "#b"], "first_comment": "Question?"}


@pytest.fixture
def wired(monkeypatch, tmp_path):
    from faceless import config
    from faceless.providers import composio_tools as ct
    cfg = dict(config.load())
    cfg["publish"] = {**cfg["publish"], "mode": "youtube", "youtube": {"channel_id": "UCq", "max_per_day": 2}}
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(pub, "slot_time", lambda day, slot: datetime(2099, 1, 1, 15, 30, tzinfo=timezone.utc))
    calls = []
    monkeypatch.setattr(ct, "youtube_upload", lambda *a, **k: calls.append((a, k)) or {"video_id": "v1", "channel_id": "UCq", "privacy": "private"})
    jobs = []
    monkeypatch.setattr("faceless.state.all_jobs", lambda: jobs)
    from faceless import ytchannel
    monkeypatch.setattr(ytchannel, "add_to_series", lambda video_id, pillar: True)
    return calls, jobs, ct


def test_schedules_once_and_never_twice(wired, tmp_path):
    calls, jobs, _ = wired
    job = FakeJob(tmp_path)
    out = pub.youtube(job, META)
    assert out["video_id"] == "v1" and job.artifacts["youtube"]["comment_posted"] is False
    assert calls[0][1]["publish_at"] == "2099-01-01T15:30:00Z" and calls[0][1]["expected_channel_id"] == "UCq"
    assert pub.youtube(job, META)["skipped"] == "already uploaded" and len(calls) == 1


def test_daily_cap_leaves_the_video_for_a_retry(wired, tmp_path):
    calls, jobs, _ = wired
    jobs += [FakeJob(tmp_path, slot=0, youtube={"video_id": "a"}), FakeJob(tmp_path, slot=2, youtube={"video_id": "b"})]
    with pytest.raises(ProviderUnavailable, match="cap"):
        pub.youtube(FakeJob(tmp_path, slot=3), META)
    assert not calls


def test_kill_switch_stops_the_upload_but_keeps_the_local_pack(monkeypatch, tmp_path):
    from faceless import config, safety
    cfg = dict(config.load())
    cfg["publish"] = {**cfg["publish"], "mode": "youtube"}
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(pub, "local_pack", lambda job, meta: {"mode": "local"})
    monkeypatch.setattr(safety, "paused", lambda: "test")
    monkeypatch.setitem(pub.PUBLISHERS, "youtube", lambda *a: pytest.fail("uploaded while paused"))
    out = pub.publish(FakeJob(tmp_path), META)
    assert out["youtube"]["skipped"].startswith("publish via youtube: studio is paused") and out["local"] == {"mode": "local"}


def test_first_comment_waits_for_the_video_to_go_public_and_gives_up_after_three(wired, tmp_path):
    _, jobs, ct = wired
    (tmp_path / "meta.json").write_text('{"first_comment": "Question?"}')
    now = datetime(2099, 1, 1, 16, 0, tzinfo=timezone.utc)
    early = FakeJob(tmp_path, youtube={"video_id": "e", "post_at": (now + timedelta(hours=1)).isoformat(), "comment_posted": False})
    due = FakeJob(tmp_path, slot=2, youtube={"video_id": "d", "post_at": (now - timedelta(hours=1)).isoformat(), "comment_posted": False})
    jobs += [early, due]
    sent = []
    ct.execute = lambda slug, args, job=None: sent.append(args)
    assert pub.post_due_comments(now) == [due.id]
    assert sent[0]["videoId"] == "d" and sent[0]["channelId"] == "UCq" and due.artifacts["youtube"]["comment_posted"]
    assert not early.artifacts["youtube"]["comment_posted"]

    def refuse(slug, args, job=None):
        raise ProviderError("nope")

    ct.execute = refuse
    again = FakeJob(tmp_path, slot=3, youtube={"video_id": "x", "post_at": (now - timedelta(hours=1)).isoformat(), "comment_posted": False})
    jobs.append(again)
    for _ in range(5):
        pub.post_due_comments(now)
    assert again.artifacts["youtube"]["comment_tries"] == 3 and not again.artifacts["youtube"]["comment_posted"]


def test_a_series_playlist_failure_never_costs_the_upload(wired, tmp_path, monkeypatch):
    from faceless import ytchannel
    calls, jobs, _ = wired

    def boom(video_id, pillar):
        raise ProviderError("playlist refused")

    monkeypatch.setattr(ytchannel, "add_to_series", boom)
    job = FakeJob(tmp_path)
    assert pub.youtube(job, META)["video_id"] == "v1"
    assert job.artifacts["youtube"]["video_id"] == "v1" and any("series playlist" in n for n in job.notes)
