"""The phone lane (faceless/phone.py): its gates, its receipts and the text it hands the phone. No phone, adb or network needed."""

import json

import pytest

from faceless import phone, safety
from faceless.config import Paths

COMIC = "A joke about rent.\nIllustrated with AI. Education and humour, not financial advice."
POST_MD = """# Slot 1: Title
## YouTube Shorts
Title: The Bi-Weekly Mortgage Hack

Thirteen payments a year.

Free checklist: https://example.github.io/links/

Educational content, not financial advice. Narration and visuals are AI-assisted.

## TikTok / Instagram caption
How 26 half-payments equal 13.

Free reset checklist: link in bio.

#money

## Checklist
- [ ] x
"""


@pytest.fixture(autouse=True)
def lane(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "state", tmp_path / "state")
    monkeypatch.setattr(Paths, "root", tmp_path)
    monkeypatch.setattr(safety, "paused", lambda: None)
    monkeypatch.setattr(phone, "cfg", lambda: {"enabled": True, "post_community": True, "post_youtube": True, "post_tiktok": True, "branch": "phone-media",
                                               "caps": {"yt_community": 2, "yt_short": 5, "tiktok": 5, "flow_image": 30, "fiverr_inbox": 3, "fiverr_reply": 10}})
    return tmp_path


def _comic(tmp_path, text=COMIC, key="2026-10-25/01-x"):
    pic = tmp_path / "picture.png"
    pic.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    return phone.add("yt_community", "2026-10-25", key, {"text": text}, [pic])


def test_a_clean_comic_is_handed_out_and_a_bad_one_never_is(lane):
    good = _comic(lane)
    assert phone.gate(good) is None and phone.next_job()["id"] == good["id"]
    bad = _comic(lane, text="See https://x.example", key="2026-10-25/02-y")
    assert "link" in phone.gate(bad) and "AI disclosure" in phone.gate(bad)


def test_the_kill_switch_and_the_owner_switch_stop_everything(lane, monkeypatch):
    job = _comic(lane)
    monkeypatch.setattr(safety, "paused", lambda: "bad day")
    assert "paused" in phone.gate(job)
    monkeypatch.setattr(safety, "paused", lambda: None)
    monkeypatch.setattr(phone, "cfg", lambda: {"enabled": True, "post_community": False, "post_youtube": True, "post_tiktok": True, "branch": "b", "caps": {"yt_community": 5}})
    assert "post_community" in phone.gate(job)


def test_a_post_is_recorded_once_and_the_daily_cap_holds(lane):
    a, b = _comic(lane, key="k1"), _comic(lane, key="k2")
    with pytest.raises(ValueError):
        phone.record(a["id"], "posted")                      # the AI label must be stated for a post
    phone.record(a["id"], "posted", ai_label=True)
    assert phone.add("yt_community", "2026-10-25", "k1", {"text": COMIC}) is None    # never queued twice
    assert phone.gate(phone.load(a["id"])) == "job is done"
    phone.record(b["id"], "posted", ai_label=True)
    c = _comic(lane, key="k3")
    assert "cap of 2" in phone.gate(c)
    ledger = (lane / "state" / "community_posts.jsonl").read_text().splitlines()
    assert len(ledger) == 2 and json.loads(ledger[0])["slug"] == "k1"   # the browser route sees the same posts


def test_two_failures_hold_a_job_for_a_person(lane):
    job = _comic(lane)
    phone.record(job["id"], "failed", note="tap missed")
    assert phone.load(job["id"])["status"] == "queued"
    phone.record(job["id"], "failed", note="tap missed again")
    assert phone.load(job["id"])["status"] == "held" and phone.next_job() is None


def test_a_fiverr_reply_waits_for_the_owner(lane):
    job = phone.add("fiverr_reply", "2026-10-25", "buyer1", {"thread": "buyer1", "draft": "Thanks! What is the launch date?"})
    assert "approve" in phone.gate(job)
    phone.approve(job["id"])
    assert phone.gate(job) is None


def test_shorts_texts_come_from_the_pack_and_tiktok_gets_its_disclosure():
    t = phone.short_texts(POST_MD)
    assert t["title"] == "The Bi-Weekly Mortgage Hack"
    assert "AI-assisted" not in t["description"] and "AI-assisted" not in t["tiktok"] and not t["description"].startswith("Title")
    assert phone.TIKTOK_DISCLOSURE in t["tiktok"] and "#money" in t["tiktok"] and "Checklist" not in t["tiktok"]
    job = {"kind": "tiktok", "text": t["tiktok"], "media": [{"source": "v.mp4"}]}
    assert phone.problems(job) == []
    assert "link" in " ".join(phone.problems({**job, "text": t["tiktok"] + " https://x.example"}))


def test_flow_pictures_may_only_land_where_the_engine_looks(lane):
    ok = phone.add("flow_image", "2026-10-25", "s1", {"prompt": "a lake at dawn", "dest": "production/cache/vibe/x/shot01.png"})
    assert phone.gate(ok) is None
    for dest in ("../etc/passwd.png", "/tmp/x.png", "faceless/x.png"):
        job = {"kind": "flow_image", "prompt": "p", "dest": dest}
        assert "destination" in " ".join(phone.problems(job))


def test_a_vibe_plan_becomes_flow_jobs_for_the_missing_stills_only(lane, monkeypatch):
    monkeypatch.setattr(Paths, "cache", lane / "cache")
    work = lane / "cache" / "vibe" / "d-song"
    work.mkdir(parents=True)
    (work / "plan.json").write_text(json.dumps([{"prompt": "one"}, {"prompt": "two"}]))
    (work / "shot01.png").write_bytes(b"x")
    rows = json.loads(phone.flow_from_vibe("d-song").read_text())
    assert [r["prompt"] for r in rows] == ["two"] and rows[0]["dest"].endswith("shot02.png")


def test_the_host_heartbeat_commits_only_on_change_and_goes_stale(lane):
    assert phone.host() == {"seen": False, "stale": True}
    assert phone.heartbeat("192.168.1.5:4000", True, "ok")["commit"] is True
    assert phone.heartbeat("192.168.1.5:4000", True, "ok")["commit"] is False      # same state within 3 h: no new commit
    assert phone.host()["stale"] is False and phone.host()["reachable"] is True
    assert phone.heartbeat("192.168.1.5:4000", False, "phone not reachable")["commit"] is True
    assert phone.host()["stale"] is True
    assert phone.status()["host"]["note"] == "phone not reachable"
