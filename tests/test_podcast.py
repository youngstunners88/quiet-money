"""The weekly audio edition: only Shorts that passed, voiced from their committed scripts, with the disclaimer and AI disclosure."""

import json
import shutil
import subprocess

import pytest

from faceless import podcast, state
from faceless.config import Paths
from faceless.state import Job

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _tone(text, wav):
    secs = max(0.3, min(2.0, len(text) / 200))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={secs}", str(wav)], check=True, timeout=60)


@pytest.fixture
def week(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "final", tmp_path / "final")
    monkeypatch.setattr(podcast, "OUT", tmp_path / "podcast")
    (tmp_path / "final").mkdir()
    jobs = []
    for i, (day, status) in enumerate([("2026-10-19", "published"), ("2026-10-20", "held"), ("2026-10-21", "published"), ("2026-10-10", "published")]):
        jid = f"{day}-s{i}-story-t{i}"
        jobs.append(Job(id=jid, pillar="story", topic=f"t{i}", day=day, slot=i, status=status))
        (tmp_path / "final" / f"{jid}.json").write_text(json.dumps({"title": f"Story {i}", "beats": [{"say": f"Beat one of {i}."}, {"say": "Beat two."}]}))
    monkeypatch.setattr(state, "all_jobs", lambda: jobs)
    return tmp_path


def test_only_the_week_s_passed_shorts_go_in_oldest_first(week):
    assert [i["title"] for i in podcast.week_items("2026-10-21")] == ["Story 0", "Story 2"]


def test_the_episode_is_built_with_chapters_disclaimer_and_ai_disclosure(week):
    r = podcast.build("2026-10-21", music=False, synth=_tone)
    assert r["items"] == 2 and r["seconds"] > 1
    notes = (week / "podcast" / "2026-10-21" / "EPISODE.md").read_text()
    assert podcast.DISCLAIMER in notes and podcast.AI_NOTE in notes
    meta = json.loads((week / "podcast" / "2026-10-21" / "episode.json").read_text())
    assert [c["title"] for c in meta["chapters"]] == ["Intro", "Story 0", "Story 2", "Outro"]
    assert meta["chapters"][0]["start"] == 0 and meta["chapters"][1]["start"] > 0


def test_an_empty_week_says_why_and_builds_nothing(week):
    r = podcast.build("2026-09-01", music=False, synth=_tone)
    assert r["file"] is None and r["items"] == 0
