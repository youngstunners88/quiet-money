"""The content mix: posture, the daily caps, the offense floor, and that the picker never gets stuck on them."""

import json

from faceless import mix
from faceless.pipeline import ideate

CFG = dict(mix.DEFAULTS)


def item(topic, posture=None):
    return {"topic": topic, "pillar": "story", **({"posture": posture} if posture else {})}


def test_posture_reads_a_hand_label_first_then_the_words():
    assert mix.posture(item("The Mortgage Payoff Trap", "offense")) == "offense"
    assert mix.posture(item("How George Foreman Turned a Kitchen Appliance Into $138M")) == "offense"
    assert mix.posture(item("Cancel Kindle and Audible in 3 Steps")) == "defense"
    assert mix.posture(item("The Circle That Controls Your Net Worth")) == "neutral"


def test_defense_is_capped_per_day():
    taken = [item("Cancel Kindle in 3 Steps"), item("The Mortgage Payoff Trap")]
    assert "defense cap" in mix.admissible(item("Stop paying hidden fees"), taken, 0, CFG)
    assert mix.admissible(item("Why Elon built an empire"), taken, 0, CFG) is None


def test_offense_floor_binds_only_when_the_slots_left_are_needed():
    assert mix.admissible(item("A neutral explainer", "neutral"), [], 4, CFG) is None                  # two offense still fit in four slots
    assert "offense floor" in mix.admissible(item("A neutral explainer", "neutral"), [], 2, CFG)         # two slots left, two offense owed
    assert mix.admissible(item("A neutral explainer", "neutral"), [item("x", "offense"), item("y", "offense")], 1, CFG) is None
    assert mix.admissible(item("Some defense", "defense"), [], 0, CFG) is None                           # remaining 0 turns the floor off


def test_a_lead_word_is_used_once_a_day():
    taken = [item("The Mortgage Payoff Trap")]
    assert "lead word 'trap'" in mix.admissible(item("The 0% Interest Trap", "neutral"), taken, 0, CFG)
    assert mix.admissible(item("Why your raise matters", "neutral"), taken, 0, CFG) is None
    assert "lead word 'why your'" in mix.admissible(item("Why your cash sits idle", "neutral"),
                                                     [item("Why your budget fails", "neutral")], 0, CFG)


def _backlog(tmp_path, monkeypatch, rows):
    path = tmp_path / "backlog.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    monkeypatch.setattr(ideate, "BACKLOG", path)
    monkeypatch.setattr(ideate, "history_texts", lambda: [])
    monkeypatch.setattr(ideate, "recent_scripts", lambda n=120: [])
    monkeypatch.setattr(ideate, "first_distinct", lambda items, reserved, limit: items[0])


def test_next_topic_skips_what_the_mix_forbids(tmp_path, monkeypatch):
    _backlog(tmp_path, monkeypatch, [
        {"pillar": "story", "topic": "Cancel hidden app fees", "posture": "defense"},
        {"pillar": "story", "topic": "He took equity instead of a fee", "posture": "offense"}])
    taken = ["Stop the subscription leak", "The mortgage trap"]
    monkeypatch.setattr(ideate, "find_topic", lambda t: {"topic": t, "posture": "defense"})
    assert ideate.next_topic("story", taken, taken, 3)["topic"] == "He took equity instead of a fee"


def test_next_topic_relaxes_rather_than_stalling(tmp_path, monkeypatch):
    _backlog(tmp_path, monkeypatch, [{"pillar": "story", "topic": "Cancel hidden app fees", "posture": "defense"}])
    taken = ["Stop the subscription leak", "The mortgage trap"]
    monkeypatch.setattr(ideate, "find_topic", lambda t: {"topic": t, "posture": "defense"})
    events = []
    monkeypatch.setattr(ideate.events, "emit", lambda name, **kw: events.append(name))
    assert ideate.next_topic("story", taken, taken, 3)["topic"] == "Cancel hidden app fees"            # nothing admissible: the old order still ships
    assert "MIX_RELAXED" in events


def test_the_slot_moves_to_a_pillar_with_offense_when_the_floor_binds(tmp_path, monkeypatch):
    _backlog(tmp_path, monkeypatch, [
        {"pillar": "myth", "topic": "Myth one", "posture": "defense"},
        {"pillar": "escape", "topic": "Build the asset", "posture": "offense"}])
    monkeypatch.setattr(ideate, "find_topic", lambda t: None)
    assert ideate.pillar_for_mix("myth", ["A neutral", "B neutral", "C neutral"], 2) == "escape"
    assert ideate.pillar_for_mix("myth", [], 5) == "myth"                                               # nothing owed yet: the plan stands
    assert ideate.pillar_for_mix("myth", None, 2) == "myth"                                             # outside a daily run the mix is off
