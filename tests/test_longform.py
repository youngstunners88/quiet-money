"""The weekly long-form: the week's passed Shorts, most viewed first, cut into a 16:9 episode with chapters and disclosures."""

import json
import shutil
import subprocess

import pytest

from faceless import longform, podcast, state
from faceless.config import Paths
from faceless.state import Job

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def _tone(text, wav):
    secs = max(0.3, min(1.2, len(text) / 200))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={secs}", str(wav)], check=True, timeout=60)


@pytest.fixture
def week(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "final", tmp_path / "final")
    monkeypatch.setattr(Paths, "root", tmp_path)
    monkeypatch.setattr(longform, "OUT", tmp_path / "longform")
    (tmp_path / "final").mkdir()
    (tmp_path / "analytics").mkdir()
    jobs = []
    plan = [("2026-10-16", "published"), ("2026-10-17", "published"), ("2026-10-18", "held"), ("2026-10-19", "published"),
            ("2026-10-20", "published"), ("2026-10-10", "published")]
    for i, (day, status) in enumerate(plan):
        jid = f"{day}-s{i}-story-t{i}"
        jobs.append(Job(id=jid, pillar="story", topic=f"t{i}", day=day, slot=i, status=status))
        (tmp_path / "final" / f"{jid}.json").write_text(json.dumps({"title": f"Story {i}", "beats": [
            {"say": f"Beat one of story {i}.", "callout": "$700" if i == 1 else ""}, {"say": "Beat two."}]}))
    monkeypatch.setattr(state, "all_jobs", lambda: jobs)
    rows = [{"job": jobs[3].id, "platform": "youtube", "views": 5, "date": "2026-10-20"},
            {"job": jobs[3].id, "platform": "youtube", "views": 50, "date": "2026-10-21"},     # the latest reading counts
            {"job": jobs[1].id, "platform": "youtube", "views": 30, "date": "2026-10-21"},
            {"job": jobs[1].id, "platform": "tiktok", "views": 10, "date": "2026-10-21"},      # platforms add up
            {"job": jobs[2].id, "platform": "youtube", "views": 999, "date": "2026-10-21"}]    # held: never in the episode
    (tmp_path / "analytics" / "metrics.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + "not json\n")
    return tmp_path


def test_stories_are_the_week_s_passed_shorts_most_viewed_first(week):
    got = longform.stories("2026-10-21")
    assert [s["title"] for s in got] == ["Story 3", "Story 1", "Story 0", "Story 4"]
    assert [s["views"] for s in got] == [50, 40, 0, 0]
    assert [s["title"] for s in longform.stories("2026-10-21", most=2)] == ["Story 3", "Story 1"]


def test_the_episode_is_16x9_with_chapters_thumbnail_and_disclosures(week):
    r = longform.build("2026-10-21", music=False, synth=_tone)
    assert r["items"] == 4 and r["seconds"] > 2
    folder = week / "longform" / "2026-10-21"
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            str(folder / "episode.mp4")], capture_output=True, text=True, timeout=60).stdout.strip()
    assert probe == "1920,1080"
    meta = json.loads((folder / "episode.json").read_text())
    titles = [c["title"] for c in meta["chapters"]]
    assert titles == ["Intro", "Story 3", "Story 1", "Story 0", "Story 4", "Outro"]
    starts = [c["start"] for c in meta["chapters"]]
    assert starts[0] == 0 and starts == sorted(starts) and len(set(starts)) == len(starts)
    assert abs(meta["seconds"] - r["seconds"]) < 0.2
    notes = (folder / "EPISODE.md").read_text()
    assert podcast.DISCLAIMER in notes and podcast.AI_NOTE in notes and "0:00 Intro" in notes
    assert notes.count("https://") <= 1                                   # one link at most (rule 13)
    from PIL import Image
    assert Image.open(folder / "thumbnail.jpg").size == (1280, 720)


def test_too_few_stories_for_chapters_builds_nothing(week):
    r = longform.build("2026-10-12", music=False, synth=_tone)
    assert r["file"] is None and "chapters need" in r["reason"]


def test_cards_follow_the_voice_s_word_timings_and_skip_words_spoken_differently():
    cards = [{"text": "Number 1. Big title."}, {"text": "It cost $7,000,000 then."}, {"text": "Now it is gone."}]
    words = [{"w": "Number", "start": 0.0}, {"w": "1", "start": 0.4}, {"w": "Big", "start": 0.7}, {"w": "title", "start": 1.0},
             {"w": "It", "start": 2.0}, {"w": "cost", "start": 2.2}, {"w": "seven million", "start": 2.5}, {"w": "then", "start": 3.4},
             {"w": "Now", "start": 4.1}, {"w": "it", "start": 4.3}, {"w": "is", "start": 4.4}, {"w": "gone", "start": 4.6}]
    assert longform.cue_times(cards, words, 5.0) == [0.0, 2.0, 4.1]
    by_chars = longform.cue_times(cards, [], 5.0)                          # no timings: time follows the characters
    assert by_chars[0] == 0 and by_chars[0] < by_chars[1] < by_chars[2] < 5.0


def test_a_story_is_one_voice_call():
    segs = longform.segments([{"job": "j", "title": "T", "beats": [{"say": "a", "callout": ""}, {"say": "b", "callout": ""}]}] * 3, "2026-10-21")
    assert [len(g) for g in longform.units(segs)] == [1, 3, 3, 3, 1]
