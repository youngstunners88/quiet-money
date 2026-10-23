"""Second-language editions: the same numbers, the claim check in the language, no job file, never the English channel."""

import json
import subprocess

import pytest

from faceless import edition, gauntlet, state
from faceless.config import Paths
from faceless.state import Job

SCRIPT = {"title": "The $700 car note", "hook_text": "Debt in disguise", "caption": "c", "description": "d", "first_comment": "f",
          "beats": [{"say": "A $700 note costs $8,400 a year.", "callout": "$700", "visual": "a car at night"},
                    {"say": "Over 6 years that is $50,400.", "callout": "", "visual": "keys on a desk"}]}


def _es(beats=None, title="La cuota de $700"):
    return {"title": title, "hook_text": "Deuda disfrazada", "caption": "c", "description": "d", "first_comment": "f",
            "beats": beats or [{"say": "Una cuota de $700 cuesta $8.400 al año.", "callout": "$700"},
                               {"say": "En 6 años son $50.400.", "callout": ""}]}


def test_numbers_must_survive_translation_and_separators_do_not_matter():
    assert edition.numbers("$8,400 and 6") == edition.numbers("8.400 y 6")
    assert edition.problems(SCRIPT, _es(), "es") == []
    wrong = _es([{"say": "Una cuota de $700 cuesta $8.500 al año.", "callout": ""}, {"say": "En 6 años son $50.400.", "callout": ""}])
    assert "different numbers" in edition.problems(SCRIPT, wrong, "es")[0]
    assert "beat count" in edition.problems(SCRIPT, _es(_es()["beats"][:1]), "es")[0]
    promise = _es([{"say": "Una cuota de $700 cuesta $8.400 al año, garantizado.", "callout": ""}, {"say": "En 6 años son $50.400.", "callout": ""}])
    assert any("claim check (es)" in p for p in edition.problems(SCRIPT, promise, "es"))


def test_translate_retries_once_with_the_reason_then_keeps_the_english_visuals():
    calls = []

    def complete(prompt):
        calls.append(prompt)
        return _es(title="") if len(calls) == 1 else _es()
    out = edition.translate(SCRIPT, "es", complete=complete)
    assert len(calls) == 2 and "REJECTED" in calls[1]
    assert out["beats"][0]["visual"] == "a car at night" and out["language"] == "es" and out["hashtags"][0] == "#finanzaspersonales"
    with pytest.raises(ValueError, match="title"):
        edition.translate(SCRIPT, "es", complete=lambda p: _es(title=""))


def test_an_edition_is_a_local_pack_and_leaves_no_job_file(tmp_path, monkeypatch):
    for name in ("final", "jobs", "output"):
        monkeypatch.setattr(Paths, name, tmp_path / name)
    monkeypatch.setattr(edition, "OUT", tmp_path / "editions")
    (tmp_path / "final").mkdir()
    (tmp_path / "final" / "j1.json").write_text(json.dumps(SCRIPT))
    Job(id="j1", pillar="math", topic="t", day="2026-10-22", slot=1, status="published").save()
    before = sorted(p.name for p in (tmp_path / "jobs").iterdir())

    def render(job, scr, vo, imgs):
        out = job.dir / "final.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1", str(out)], check=True, timeout=60)
        return {"video": str(out)}
    stages = {"voice": lambda job, scr: {"duration": 65.0, "beats": [[0, 30], [30, 65]], "words": [], "provider": "edge"},
              "visuals": lambda job, scr: [{"beat": 0}, {"beat": 1}], "render": render}
    monkeypatch.setattr(gauntlet, "check_voice", lambda vo: [gauntlet.Gate("voice", True, 10, True, "")])      # the engine's own gates, tested elsewhere
    monkeypatch.setattr(gauntlet, "check_render", lambda info, vo: [gauntlet.Gate("render", True, 10, True, "")])
    r = edition.make("j1", "es", complete=lambda p: _es(), stages=stages)
    assert r["passed"] and r["title"] == "La cuota de $700"
    folder = tmp_path / "editions" / "es" / "2026-10-22" / "j1"
    assert (folder / "video.mp4").exists() and "no asesoramiento financiero" in (folder / "POST.md").read_text()
    assert json.loads((folder / "meta.json").read_text())["ai_label"] is True
    assert sorted(p.name for p in (tmp_path / "jobs").iterdir()) == before          # the daily machine never sees an edition
    assert "editions" in str(edition.EditionJob(id="j1", pillar="m", topic="t", day="d").dir)
    monkeypatch.setattr(gauntlet, "check_render", lambda info, vo: [gauntlet.Gate("render", False, 10, True, "black frames")])
    held = edition.make("j1", "es", complete=lambda p: _es(), stages=stages)
    assert not held["passed"] and "HELD" in (folder / "POST.md").read_text()
