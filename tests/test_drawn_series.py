"""The Ledger series is drawn entirely in code: no image provider of any kind is called, and it needs the renderer or it refuses."""

import json
import types

import pytest

from faceless import config
from faceless.pipeline import cards, visuals
from faceless.providers import ProviderUnavailable

SCRIPT = {"beats": [{"say": "A one percent fee costs you two fifty four thousand", "callout": ""},
                    {"say": "Thirty years of compounding", "callout": "30 YEARS"},
                    {"say": "Two portfolios", "callout": "$500 VS $2,000"},
                    {"say": "First, check your fee", "callout": "STEP ONE"},
                    {"say": "Follow for the money rules", "callout": ""}]}


def job(tmp_path):
    return types.SimpleNamespace(id="j-ledger", dir=tmp_path, pillar="ledger", artifacts={})


def test_the_ledger_pillar_is_drawn_and_always_in_the_ledger_look():
    assert config.pillar("ledger").drawn and not config.pillar("story").drawn
    assert cards.style_for("anything", "ledger") == "ledger"


def test_every_beat_including_the_hook_is_a_drawn_scene(monkeypatch):
    monkeypatch.setattr(cards, "available", lambda: True)
    picked = cards.pick(SCRIPT, None, "ledger", "ledger")
    assert sorted(picked) == [0, 1, 2, 3, 4] and all(p["kind"] == "stage" for p in picked.values())
    assert picked[0]["tpl"] == "hero" and picked[0]["hook"] is True          # Penny opens the video, below the caption band
    assert picked[1]["tpl"] == "years" and picked[2]["tpl"] == "race" and picked[3]["tpl"] == "step"


def test_no_image_provider_is_called(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "available", lambda: True)

    def boom(*a, **k):
        raise AssertionError("an image provider was called for a drawn series")

    monkeypatch.setattr(visuals.images, "generate", boom)
    rows = visuals.run(job(tmp_path), SCRIPT)
    assert [r["provider"] for r in rows] == ["card"] * 5 and all(r["path"] is None for r in rows)
    assert json.loads((tmp_path / "images.json").read_text())[0]["card"]["kind"] == "stage"


def test_without_the_renderer_the_video_is_refused_not_shipped_with_placeholder_art(tmp_path, monkeypatch):
    monkeypatch.setattr(cards, "available", lambda: False)
    with pytest.raises(ProviderUnavailable, match="Node 22"):
        visuals.run(job(tmp_path), SCRIPT)


def test_paper_cover_is_made_without_a_still(tmp_path):
    from faceless.pipeline import render
    out = render.paper_page(tmp_path / "p.jpg")
    from PIL import Image
    assert Image.open(out).size == (1080, 1920)


def test_open_scene_has_no_text_of_its_own(tmp_path):
    cards.build_project(tmp_path / "p", [(0, {"kind": "open"}, 3.0)], "ledger", "#D9A400", 30, "THE LEDGER", theme="ledger")
    page = (tmp_path / "p" / "index.html").read_text(encoding="utf-8")
    assert 'class="mk"' in page and "THE LEDGER" in page


def test_a_switched_off_pillar_never_enters_the_daily_plan():
    from faceless import analytics
    assert config.pillar("ledger").enabled is False
    assert "ledger" not in analytics.pillar_weights()
    assert all(p.enabled for p in config.load()["pillars"] if p.id != "ledger")


def test_no_two_neighbouring_scenes_share_a_template_or_a_colour_and_the_gremlin_is_capped(monkeypatch):
    from faceless.pipeline import cast
    monkeypatch.setattr(cards, "available", lambda: True)
    beats = [{"say": "The fee drains your money", "callout": ""} for _ in range(14)]
    plan = cast.choose({"beats": beats})
    rows = [plan[i] for i in sorted(plan)]
    assert all(a["tpl"] != b["tpl"] and a["pal"] != b["pal"] for a, b in zip(rows, rows[1:]))
    assert sum(1 for r in rows if r["tpl"] == "fee") <= 2


def test_every_template_builds_a_scene_without_error(tmp_path):
    from faceless.pipeline import cast
    n = {"value": 254000.0, "prefix": "$", "suffix": "", "decimals": 0, "label": "GAP", "static": False}
    specs = [{"kind": "stage", "tpl": "hero", "pal": 0, "text": "HELLO", "hook": True, "words": [(0.1, 0.4)]},
             {"kind": "stage", "tpl": "stack", "pal": 1, "num": n, "text": "X", "words": [(0.1, 0.4)]},
             {"kind": "stage", "tpl": "fee", "pal": 2, "num": n, "text": "$254,000", "words": [(0.1, 0.4)]},
             {"kind": "stage", "tpl": "race", "pal": 3, "cmp": {"a": "$5", "b": "$9", "va": 5, "vb": 9, "numeric": True}, "text": "", "words": []},
             {"kind": "stage", "tpl": "step", "pal": 4, "step": {"n": 1, "word": "ONE", "gist": "CHECK"}, "words": []},
             {"kind": "stage", "tpl": "years", "pal": 0, "num": {**n, "value": 30.0, "label": "YEARS"}, "words": []},
             {"kind": "stage", "tpl": "shock", "pal": 1, "text": "WOW", "words": []},
             {"kind": "stage", "tpl": "think", "pal": 2, "text": "HMM", "words": []},
             {"kind": "stage", "tpl": "sign", "pal": 3, "text": "SIGN", "words": []}]
    cards.build_project(tmp_path / "p", [(i, s, 4.0) for i, s in enumerate(specs)], "ledger", "#D9A400", 30, "THE LEDGER", theme="ledger")
    page = (tmp_path / "p" / "index.html").read_text(encoding="utf-8")
    assert page.count('class="scene clip"') + page.count("class=\"scene clip\"") >= 9 and "tl.fromTo" in page


def test_a_script_must_end_on_a_complete_sentence():
    from faceless import gauntlet
    base = {"title": "A fee that costs you $254,000 over thirty years", "hashtags": ["#a", "#b", "#c", "#d", "#e"], "beats": [{"say": f"Beat {i}.", "callout": ""} for i in range(11)]}

    def gate(last):
        beats = base["beats"][:-1] + [{"say": last, "callout": ""}]
        gates = gauntlet.check_script({**base, "beats": beats, "pillar": "math"}, [])
        return next(g for g in gates if g.name == "complete_ending")

    assert gate("Follow for the money rules school never taught you.").passed
    assert not gate("Follow for the money rules, because the textbook approach...").passed
    assert not gate("Follow for the money rules and the").passed


def test_narration_gets_a_tail_after_the_last_word(tmp_path):
    import subprocess
    from faceless.pipeline import voice
    from faceless.providers import tts
    wav = tmp_path / "v.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=2", str(wav)], check=True)
    dur = voice._pad_tail(wav, 2.0, 0.65)
    assert dur >= 2.65 and abs(tts.duration(wav) - dur) < 0.01
    assert voice._pad_tail(wav, 2.0, 0.65) == dur          # already long enough: untouched
