"""The strategy file (faceless/strategy.py): its data block is regenerated, its judgment is kept, and the trend keeps one row a day."""

import json

import pytest

from faceless import scout, strategy


@pytest.fixture
def lane(tmp_path, monkeypatch):
    snaps = tmp_path / "analytics" / "snapshots"
    snaps.mkdir(parents=True)
    (snaps / "youtube-2026-10-29.json").write_text(json.dumps({"date": "2026-10-29", "shorts": [
        {"title": "How George Foreman Turned a Kitchen Appliance Into $138M", "views": 229},
        {"title": "The Price Tag Hidden Behind Your Monthly Life", "views": 0},
        {"title": "The Mortgage Payoff Trap", "views": 104},
    ]}), encoding="utf-8")
    monkeypatch.setattr(strategy, "OUT", tmp_path / "channel" / "STRATEGY.md")
    monkeypatch.setattr(strategy, "LOG", tmp_path / "analytics" / "strategy.jsonl")
    monkeypatch.setattr(strategy, "SNAPS", snaps)
    monkeypatch.setattr(strategy, "METRICS", tmp_path / "analytics" / "metrics.jsonl")
    monkeypatch.setattr(strategy, "RECEIPTS", tmp_path / "state" / "phone" / "receipts.jsonl")
    monkeypatch.setattr(strategy, "OFFERS", tmp_path / "state" / "offers.jsonl")
    monkeypatch.setattr(strategy, "YPP", tmp_path / "analytics" / "ypp.jsonl")
    monkeypatch.setattr(strategy, "SITE", tmp_path / "analytics" / "site.jsonl")
    monkeypatch.setattr(scout, "health", lambda days=7: {"videos": 0, "held": 0, "hold_rate": 0.0, "top_failing_gates": []})
    return tmp_path


def test_title_tests_split_the_snapshot(lane):
    shorts = strategy.latest_snapshot()[1]
    groups = {name: (yn, ym, nn, nm) for name, yn, ym, nn, nm in strategy.title_groups(shorts)}
    assert groups["title has a number"][:2] == (1, 229)          # only the George Foreman title has a number
    assert groups["abstract words (hidden, silent, brain, direction)"][:2] == (1, 0)


def test_regeneration_keeps_the_judgment_and_replaces_the_data(lane):
    strategy.write()
    out = strategy.OUT
    text = out.read_text(encoding="utf-8")
    out.write_text(text.replace("## Judgment (written by the review, kept between runs)",
                                "## Judgment (written by the review, kept between runs)\n\nA human judgment line."), encoding="utf-8")
    text = out.read_text(encoding="utf-8").replace("| 229 |", "| 999 |")         # a stale number in the data block
    out.write_text(text, encoding="utf-8")

    strategy.write()
    after = out.read_text(encoding="utf-8")
    assert "A human judgment line." in after                    # the review's words survive
    assert "| 999 |" not in after and "229" in after              # the data block is regenerated
    assert after.count(strategy.BEGIN) == 1 and after.count(strategy.END) == 1


def test_the_trend_keeps_one_row_a_day(lane):
    strategy.write()
    strategy.write()
    rows = [json.loads(line) for line in strategy.LOG.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["shorts"] == 3


def test_a_missing_snapshot_is_said_plainly(lane, monkeypatch):
    monkeypatch.setattr(strategy, "SNAPS", lane / "nothing")
    strategy.write()
    assert "No public snapshot yet" in strategy.OUT.read_text(encoding="utf-8")
