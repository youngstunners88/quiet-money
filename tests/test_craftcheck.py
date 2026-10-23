import re
from pathlib import Path

from faceless import craftcheck, reel

LESSONS = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "faceless-craft" / "LESSONS.md"


def test_every_lesson_a_check_cites_is_written_down():
    """The loop only works if the rule and its reason live together: a check citing L7 needs an L7 in LESSONS.md."""
    cited = set(re.findall(r'"(L\d+)"', Path(craftcheck.__file__).read_text(encoding="utf-8")))
    written = set(re.findall(r"^## (L\d+)", LESSONS.read_text(encoding="utf-8"), flags=re.M))
    assert cited, "craftcheck cites its lessons"
    assert cited <= written, f"checks cite lessons that are not recorded: {sorted(cited - written)}"


def test_only_a_confirmed_rule_becomes_work_for_the_next_render():
    findings = [{"rule": "a", "lesson": "L4", "ok": False, "detail": "", "confirmed": True},
                {"rule": "b", "lesson": "L5", "ok": False, "detail": "", "confirmed": False},
                {"rule": "c", "lesson": "L2", "ok": True, "detail": "", "confirmed": True}]
    assert [f["rule"] for f in craftcheck.to_fix(findings)] == ["a"]


def test_the_craft_check_never_stops_the_engine(monkeypatch, tmp_path, capsys):
    """Lesson L11: the engine is autonomous. A failed check is reported and recorded, and the command still exits 0."""
    from types import SimpleNamespace
    from faceless import cli
    monkeypatch.setattr(craftcheck, "LEDGER", tmp_path / "craft.jsonl")
    monkeypatch.setattr(craftcheck, "check_reel", lambda video, report: [
        {"rule": "the sound fades out", "lesson": "L4", "ok": False, "detail": "", "confirmed": True}])
    assert cli.cmd_craftcheck(SimpleNamespace(video="reel.mp4", report=None)) == 0
    assert "FIX" in capsys.readouterr().out
    assert (tmp_path / "craft.jsonl").exists()


def test_a_line_is_budgeted_by_its_slot():
    assert craftcheck.word_budget(7.0) > craftcheck.word_budget(3.0)
    assert craftcheck.word_budget(0.5) == 0, "no room after the lead-in means no line"


def test_the_card_holds_after_the_last_word():
    """Lesson L4: the closing line had 0.55 s before the file ended and felt cut off."""
    line = 2.4
    card = reel.card_seconds_for(line)
    assert card - reel.CTA_LEAD - line >= 1.0
    assert reel.END_FADE > 0


def test_the_ending_is_not_a_hole():
    """Lesson L3: the card has no clip sound, so the bed must come up under it and the closing line must not be the quietest."""
    assert reel.CTA_BED_GAIN > reel.BED_GAIN
    assert reel.CTA_VO_GAIN >= 1.0


def test_the_card_lands_on_a_sound(tmp_path):
    """Lesson L3, second render: levelling and the bed swell still left a hole at the cut; the card needs its own hit."""
    lead = reel.card_sting(tmp_path / "sting.wav")
    assert 0.0 < lead < 1.0, "the impact sits inside the file so it can be placed on the cut"
    assert (tmp_path / "sting.wav").stat().st_size > 10_000
    assert reel.STING_GAIN > 0
