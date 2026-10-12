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


def test_a_switched_off_pillar_never_enters_the_daily_plan(monkeypatch):
    from dataclasses import replace
    from faceless import analytics
    cfg = dict(config.load())
    cfg["pillars"] = [replace(p, enabled=False) if p.id == "ledger" else p for p in cfg["pillars"]]
    monkeypatch.setattr(config, "load", lambda: cfg)
    assert "ledger" not in analytics.pillar_weights() and "story" in analytics.pillar_weights()


def test_the_drawn_series_is_on_in_the_shipped_plan():
    assert config.pillar("ledger").enabled and config.pillar("ledger").name == "Penny's Money Lab"
