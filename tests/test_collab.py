"""Collaboration notes: only small, active shows; no contact scraping; code gates before Jev; nothing named in committed state."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from faceless import collab, decide

NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)
FEED = b"""<?xml version="1.0"?><rss><channel><title>Small Money Show</title><link>https://smallmoney.example</link>
<description>Budgeting for beginners. Write to host@smallmoney.example</description>
<item><title>Why your raise disappears</title></item><item><title>The envelope method, revisited</title></item></channel></rss>"""


def _result(name, episodes=80, days_ago=5, feed="https://feeds.example/x"):
    return {"collectionId": hash(name), "collectionName": name, "artistName": "Host", "feedUrl": feed, "trackCount": episodes,
            "releaseDate": f"2026-10-{23 - days_ago:02d}T10:00:00Z", "collectionViewUrl": "https://podcasts.apple.com/x?uo=4"}


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setattr(collab, "SEEN", tmp_path / "seen.json")
    monkeypatch.setattr(collab, "LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(collab, "DRAFTS", tmp_path / "drafts")
    return tmp_path


def _ask(body=None, episode="Why your raise disappears"):
    words = body or ("Hi Sam, your episode title Why your raise disappears caught our eye: lifestyle creep eating the first raise. "
                     "We run Quiet Money, a small Shorts channel on money psychology. We would like to make one free 60-second Short "
                     "built on that idea, crediting your show by name and pointing viewers to the episode. No cost and nothing needed "
                     "from you beyond a yes. May we make it? The Quiet Money team")
    return lambda model, brief: {"out": {"episode": episode, "angle": "episode Short", "subject": "A Short on your raise episode", "body": words},
                                 "model_used": model}


def _jev(pers, spam, conf=0.95):
    return lambda qs, state, job, backend: {"personalization": SimpleNamespace(jev_value=pers, jev_confidence=conf),
                                            "spam_risk": SimpleNamespace(jev_value=spam, jev_confidence=conf)}


def test_only_small_active_new_shows_are_candidates(desk):
    rows = [_result("Small Money Show"), _result("Huge Network Show", episodes=1500), _result("Gone Quiet", days_ago=22 + 60 if False else 0),
            _result("Old Show", days_ago=0), _result("No Feed", feed="http://insecure.example")]
    rows[2]["releaseDate"] = "2026-06-01T10:00:00Z"
    rows.append({**_result("Life Kit: Money"), "artistName": "NPR"})
    got = [c["name"] for c in collab.candidates(rows, NOW)]
    assert got == ["Small Money Show", "Old Show"]
    collab.remember("small-money-show", "drafted-pass")
    assert [c["name"] for c in collab.candidates(rows, NOW)] == ["Old Show"]


def test_research_reads_the_feed_and_removes_addresses(desk):
    card = collab.research(collab.candidates([_result("Small Money Show")], NOW)[0], fetch=lambda url: FEED)
    assert card["recent"] == ["Why your raise disappears", "The envelope method, revisited"]
    assert "@" not in card["about"] and card["website"] == "https://smallmoney.example"


def test_a_good_note_passes_and_state_holds_no_names(desk, monkeypatch):
    monkeypatch.setattr(decide, "ask", _jev(4, 0))
    r = collab.run(5, results=[_result("Small Money Show")], fetch=lambda url: FEED, ask=_ask())
    assert r["verdicts"] == {"pass": 1, "review": 0, "hold": 0}
    assert (desk / "drafts" / "small-money-show.md").exists()
    collab.record("small-money-show", "sent")
    committed = (desk / "seen.json").read_text() + (desk / "log.jsonl").read_text()
    assert "Small Money" not in committed and "small-money-show" not in committed
    assert collab.status()["outcomes"]["sent"] == 1


@pytest.mark.parametrize("body,episode,why", [
    (None, "An episode that does not exist", "real recent episode"),
    ("Short note " * 5, "Why your raise disappears", "words"),
    (None, "Why your raise disappears", None),
])
def test_code_gates_hold_before_jev_is_asked(desk, monkeypatch, body, episode, why):
    asked = []
    monkeypatch.setattr(decide, "ask", lambda *a, **k: asked.append(1) or _jev(4, 0)(*a, **k))
    card = collab.research(collab.candidates([_result("Small Money Show")], NOW)[0], fetch=lambda url: FEED)
    note = collab.draft(card, _ask(body, episode))
    if why:
        assert note["gates"]["verdict"] == "hold" and any(why in p for p in note["gates"]["problems"]) and not asked
    else:
        assert note["gates"]["verdict"] == "pass" and asked


def test_a_link_or_a_promise_is_held_and_an_unsure_jev_leaves_the_code_proof_standing(desk, monkeypatch):
    card = collab.research(collab.candidates([_result("Small Money Show")], NOW)[0], fetch=lambda url: FEED)
    base = _ask()("m", "b")["out"]["body"]
    for bad in (base + " See https://x.example", base.replace("No cost", "This will go viral, no cost"),
                base.replace("caught our eye", "stuck with us")):
        assert collab.draft(card, _ask(bad))["gates"]["verdict"] == "hold"
    monkeypatch.setattr(decide, "ask", _jev(4, 0, conf=0.4))
    g = collab.draft(card, _ask())["gates"]
    assert g["verdict"] == "pass" and g["jev"]["personalization"] == [4, 0.4]       # below the floor: the code's proof stands in
    monkeypatch.setattr(decide, "ask", _jev(0, 4))
    assert collab.draft(card, _ask())["gates"]["verdict"] == "hold"                  # a confident Jev saying spam holds it


def test_outcomes_are_checked():
    with pytest.raises(ValueError):
        collab.record("x", "spammed")
