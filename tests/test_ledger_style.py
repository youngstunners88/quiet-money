"""The second look of the series: chosen per video by a fixed hash, off until the owner approves, every beat after the hook drawn."""

import pytest

from faceless import config
from faceless.pipeline import cards

SCRIPT = {"beats": [{"say": "Hook line here", "callout": ""}, {"say": "Nine hundred thousand dollars invested", "callout": "$900,000"},
                    {"say": "Save five hundred versus two thousand", "callout": "$500 VS $2,000"}, {"say": "First count your spend", "callout": "STEP ONE"},
                    {"say": "The number is smaller than you think", "callout": ""}]}


def with_ledger(monkeypatch, **over):
    cfg = dict(config.load())
    prod = dict(cfg["production"])
    prod["ledger"] = {"mode": "on", "pillars": ["escape"], "share": 1.0, **over}
    cfg["production"] = prod
    monkeypatch.setattr(config, "load", lambda: cfg)
    monkeypatch.setattr(cards, "available", lambda: True)


def test_off_by_default_in_the_shipped_config():
    assert config.load()["production"]["ledger"]["mode"] == "off"
    assert cards.style_for("any-job", "escape") == "cinematic"


def test_only_listed_series_and_the_configured_share_get_the_ledger_look(monkeypatch):
    with_ledger(monkeypatch, share=0.5)
    assert cards.style_for("a", "story") == "cinematic"
    looks = [cards.style_for(f"job-{i}", "escape") for i in range(200)]
    assert 60 < looks.count("ledger") < 140                       # about half, and fixed per id
    assert cards.style_for("job-7", "escape") == cards.style_for("job-7", "escape")


def test_ledger_style_draws_every_beat_after_the_hook(monkeypatch):
    with_ledger(monkeypatch)
    picked = cards.pick(SCRIPT, None, "escape", "ledger")
    assert sorted(picked) == [1, 2, 3, 4] and 0 not in picked
    assert [picked[i]["kind"] for i in (1, 2, 3, 4)] == ["stat", "compare", "steps", "phrase"]


def test_house_look_is_unchanged_by_the_new_argument(monkeypatch):
    with_ledger(monkeypatch)
    assert cards.pick(SCRIPT, None, "escape") == cards.pick(SCRIPT, None, "escape", "cinematic")


def test_theme_colours_land_in_the_page(tmp_path):
    cards.build_project(tmp_path / "p", [(1, {"kind": "phrase", "text": "HELLO"}, 3.0)], "escape", "#D9A400", 30, "KICK", theme="ledger")
    page = (tmp_path / "p" / "index.html").read_text(encoding="utf-8")
    assert "--ink:#14110a" in page and "#fbf4e3" in page
    cards.build_project(tmp_path / "q", [(1, {"kind": "phrase", "text": "HELLO"}, 3.0)], "escape", "#FFD23F", 30, "KICK")
    assert "--ink:#ffffff" in (tmp_path / "q" / "index.html").read_text(encoding="utf-8")
