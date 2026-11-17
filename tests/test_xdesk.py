"""The X desk: a draft per finished video, never two for one video, never a post. Offline."""

import json
from types import SimpleNamespace

import pytest

from faceless import config, missions, safety, xdesk

SCRIPT = {"title": "The 10-second saving habit", "hook_text": "you skip this every morning",
          "beats": [{"say": "Move ten dollars before coffee. Do it daily for a year."}, {"say": "That is 3,650 dollars saved."}]}


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setattr(xdesk, "DIR", tmp_path / "x")
    monkeypatch.setattr(xdesk, "LOG", tmp_path / "x.jsonl")
    monkeypatch.setattr(xdesk, "STUDIO", tmp_path)
    monkeypatch.setattr(xdesk.Paths, "output", tmp_path / "output")
    monkeypatch.setattr(xdesk.Paths, "final", tmp_path / "final")
    monkeypatch.setattr(safety, "paused", lambda: None)
    monkeypatch.setattr(xdesk.events, "emit", lambda *a, **k: {})
    monkeypatch.setattr(config, "today_utc", lambda: config.date(2026, 11, 15) if hasattr(config, "date") else __import__("datetime").date(2026, 11, 15))
    jobs = []
    for jid, day, status in [("2026-11-15-s1-story-a", "2026-11-15", "packaged"), ("2026-11-14-s2-math-b", "2026-11-14", "published"),
                             ("2026-11-15-s3-myth-c", "2026-11-15", "held"), ("2026-11-01-s1-story-old", "2026-11-01", "packaged")]:
        (tmp_path / "output" / day / jid).mkdir(parents=True)
        (tmp_path / "output" / day / jid / "final.mp4").write_bytes(b"x")
        (tmp_path / "final").mkdir(exist_ok=True)
        (tmp_path / "final" / f"{jid}.json").write_text(json.dumps(SCRIPT))
        jobs.append(SimpleNamespace(id=jid, day=day, status=status))
    import faceless.state
    monkeypatch.setattr(faceless.state, "all_jobs", lambda: jobs)
    monkeypatch.setattr(__import__("faceless.repurpose", fromlist=["link"]), "link", lambda *a, **k: "https://hub.example/x")
    return tmp_path


def test_drafts_only_finished_recent_videos_once(desk):
    r = xdesk.draft("2026-11-15")
    assert sorted(r["drafted"]) == ["2026-11-14-s2-math-b", "2026-11-15-s1-story-a"]      # held and old videos are not drafted
    assert xdesk.draft("2026-11-15")["drafted"] == []                                     # a second run never rewrites one
    text = (desk / "x" / "2026-11-15" / "2026-11-15-s1-story-a.md").read_text()
    assert "Attach: `output/2026-11-15/2026-11-15-s1-story-a/final.mp4`" in text and xdesk.AI_LINE in text
    lead = text.split("## Post (with the video attached)\n\n")[1].split("\n\n## Replies")[0]
    assert len(lead) <= xdesk.MAX_LEAD and lead.startswith("1/") and "https://hub.example/x" in text
    long = {**SCRIPT, "title": "word " * 60, "hook_text": "hook " * 60}
    assert len(xdesk.lead_post(long, "1/7 ")) <= xdesk.MAX_LEAD                          # a long title still fits


def test_a_posted_video_leaves_the_queue_and_the_log_refuses_nonsense(desk):
    xdesk.draft("2026-11-15")
    assert xdesk.status("2026-11-15")["waiting"] == 2
    with pytest.raises(ValueError):
        xdesk.log("2026-11-15-s1-story-a", "posted", url="https://evil.example/")
    with pytest.raises(ValueError):
        xdesk.log("never-drafted", "posted")
    xdesk.log("2026-11-15-s1-story-a", "posted", url="https://x.com/quietmoneyrule/status/1")
    s = xdesk.status("2026-11-15")
    assert s["waiting"] == 1 and s["postedAllTime"] == 1 and s["undrafted"] == 0
    assert xdesk.draft("2026-11-15")["drafted"] == []                                     # posted is never drafted again


def test_the_board_drafts_by_engine_and_leaves_posting_to_the_owner():
    base = {"day": "2026-11-15", "jobs": None, "phone": None, "outbound": None, "offers": None, "prospects": None}
    got = {m["id"]: m for m in missions.derive({**base, "x": {"waiting": 2, "undrafted": 3}})}
    assert got["x-draft-2026-11-15"]["kind"] == "engine" and got["x-draft-2026-11-15"]["action"] == "x_draft"
    assert got["post-x-2026-11-15"]["kind"] == "owner" and not got["post-x-2026-11-15"]["auto"]


def test_the_overview_puts_x_on_the_board_before_the_missions_read_it():
    import inspect
    from faceless import overview
    src = inspect.getsource(overview.build)
    assert src.index('doc["x"]') < src.index('doc["missions"]')
