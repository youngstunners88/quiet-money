"""Engine unit tests: pure logic only (no network, no ffmpeg), so they run anywhere in seconds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from faceless import analytics, config, moneymath
from faceless.gauntlet import check_package, check_script, score
from faceless.pipeline.captions import callout_text, chunk_words, wrap_hook
from faceless.pipeline.ideate import similarity
from faceless.pipeline.script import normalize, word_count
from faceless.pipeline.voice import align_beats, attach_display
from faceless.providers.tts import rate_to_speed, speed_to_rate
from faceless.state import Job, TransitionError

SEED = Path(__file__).resolve().parent.parent / "script-lab" / "final" / "_seed-001-ronald-read.json"


def words(*tokens, step=0.3):
    return [{"w": t, "start": round(i * step, 3), "end": round(i * step + step * 0.9, 3)} for i, t in enumerate(tokens)]


# ---- money math -------------------------------------------------------------------------------

def test_future_value_matches_known_value():
    assert round(moneymath.future_value_monthly(200, 0.08, 40)) == 698202


def test_card_payoff_with_fixed_payment():
    months, interest = moneymath.card_payoff(3000, 0.24, 300)
    assert months == 12 and 370 < interest < 400


def test_card_payoff_never_ends_when_payment_below_interest():
    months, interest = moneymath.card_payoff(10000, 0.24, 100)
    assert interest == float("inf")


def test_fact_sheet_mentions_assumptions():
    sheet = moneymath.fact_sheet()
    assert "8%/yr" in sheet and "24% APR" in sheet


# ---- voice alignment ---------------------------------------------------------------------------

def test_attach_display_restores_punctuation():
    w = attach_display(words("Not", "his", "friends", "Not", "his", "neighbors"), "Not his friends. Not his neighbors.")
    assert [x["display"] for x in w] == ["Not", "his", "friends.", "Not", "his", "neighbors."]


def test_attach_display_merges_split_tokens():
    w = attach_display(words("J", "C", "Penney", "for"), "J.C. Penney for")
    assert [x["display"] for x in w] == ["J.C.", "Penney", "for"]
    assert w[0]["end"] == pytest.approx(0.57)


def test_attach_display_keeps_raw_words_when_streams_disagree():
    raw = words("eight", "million", "dollars")
    assert attach_display(raw, "$8M") == raw


def test_align_beats_starts_at_zero_and_is_contiguous():
    ws = words("One", "two", "three", "four", "five", "six")
    spans = align_beats(["One two three.", "Four five six."], ws, total=2.0)
    assert spans[0][0] == 0.0
    assert spans[0][1] == spans[1][0] == pytest.approx(0.9)
    assert spans[1][1] == 2.0


def test_rate_speed_roundtrip():
    assert rate_to_speed("+14%") == pytest.approx(1.14)
    assert speed_to_rate(0.94) == "-6%"


# ---- captions ----------------------------------------------------------------------------------

def test_chunks_break_at_sentence_end():
    ws = [{"w": t, "display": t, "start": 0, "end": 0} for t in "He pumped gas. Then he cleaned floors.".split()]
    chunks = [" ".join(x["display"] for x in c) for c in chunk_words(ws, 3, 16)]
    assert "gas." in chunks[0] and all("gas. Then" not in c for c in chunks)


def test_chunks_do_not_end_on_weak_word():
    ws = [{"w": t, "display": t, "start": 0, "end": 0} for t in "He bought a house in the city".split()]
    for c in chunk_words(ws, 3, 16)[:-1]:
        assert c[-1]["display"].lower() not in {"a", "the", "in"}


def test_hook_wraps_without_escaping_newlines():
    lines = wrap_hook("A janitor died with $8 million")
    assert len(lines) == 2 and all("\\" not in l for l in lines)


def test_long_callout_wraps_smaller():
    text, size = callout_text("25 years at a gas pump")
    assert "\\N" in text and size < 150
    assert callout_text("$698,000") == ("$698,000", 150)


# ---- scripts + gauntlet ------------------------------------------------------------------------

def seed_script():
    return normalize(json.loads(SEED.read_text(encoding="utf-8")))


def test_seed_script_passes_code_gates():
    gates = check_script(seed_script(), history=[])
    s, hard = score(gates)
    assert not hard, [g.name for g in hard]
    assert s >= 90


def test_compliance_gate_blocks_promises():
    scr = seed_script()
    scr["beats"][3]["say"] = "This fund has guaranteed returns, you should buy it now."
    hard = {g.name for g in check_script(scr, history=[]) if g.hard and not g.passed}
    assert "compliance_phrases" in hard


def test_originality_gate_blocks_duplicates():
    scr = seed_script()
    hard = {g.name for g in check_script(scr, history=[scr["title"] + " " + scr["beats"][0]["say"]])
            if g.hard and not g.passed}
    assert "originality" in hard


def test_judge_compliance_ignores_factual_score(monkeypatch):
    """Compliance risk 4 with stated assumptions passes; factual risk is judged by its own gate."""
    from faceless import gauntlet
    monkeypatch.setattr(gauntlet.llm, "complete", lambda *a, **k: {
        "hook": 8, "retention": 7, "value": 7, "factual_risk": 6, "compliance_risk": 4,
        "suspect_claims": ["x"], "fixes": []})
    monkeypatch.setattr("faceless.decide.RECORDS", Path("/dev/null"))
    monkeypatch.setattr("faceless.events.JOURNAL", Path("/dev/null"))
    gates = {g.name: g for g in gauntlet.judge_script(seed_script())[0]}
    assert gates["judge_compliance"].passed
    assert not gates["judge_facts"].passed


def test_word_count_hard_only_when_far_out_of_range():
    scr = seed_script()
    gate = lambda s: next(g for g in check_script(s, history=[]) if g.name == "word_count")  # noqa: E731
    near = dict(scr, beats=scr["beats"][:-1])            # a few words short: soft
    far = dict(scr, beats=scr["beats"][:8])              # ~60 words short: hard, rewrite in the script loop
    assert not gate(near).hard or gate(near).passed
    assert gate(far).hard and not gate(far).passed


def test_length_brief_gives_a_word_target():
    from faceless.orchestrator import length_brief
    brief = length_brief(53.3, 124)
    assert "too short" in brief and "about 187 words" in brief


def test_normalize_strips_hook_punctuation():
    assert normalize({"title": "t", "hook_text": "21 YEARS.", "beats": []})["hook_text"] == "21 YEARS"


def test_normalize_clears_callout_on_hook_beat():
    scr = normalize({"title": "t", "beats": [{"say": "a b", "callout": "X", "visual": "v"}]})
    assert scr["beats"][0]["callout"] == ""


def test_word_count():
    assert word_count({"beats": [{"say": "one two"}, {"say": "three"}]}) == 3


def test_package_gate_requires_disclaimers():
    bad = {"description": "great video", "caption": "#money"}
    good = {"description": "Educational content, not financial advice. Narration and visuals are AI-assisted.",
            "caption": "#money"}
    assert any(g.hard and not g.passed for g in check_package(bad))
    assert not any(g.hard and not g.passed for g in check_package(good))


def test_similarity_is_symmetric_and_bounded():
    a, b = "janitor died with 8 million", "the janitor who died with $8 million"
    assert 0 <= similarity(a, b) <= 1 and similarity(a, b) == similarity(b, a)


# ---- routing + state ---------------------------------------------------------------------------

def test_allocate_balanced_by_default():
    weights = {p.id: 1.0 for p in config.load()["pillars"]}
    plan = analytics.allocate(5, weights, day_index=3)
    assert sorted(plan) == sorted(weights)


def test_allocate_favours_winners_but_caps_at_two():
    weights = {"story": 3.0, "math": 1.0, "psychology": 0.4, "myth": 0.4, "playbook": 0.4}
    plan = analytics.allocate(5, weights, day_index=0)
    assert plan.count("story") == 2 and len(plan) == 5


def test_job_cannot_move_backwards(tmp_path, monkeypatch):
    monkeypatch.setattr("faceless.config.Paths.jobs", tmp_path)
    monkeypatch.setattr("faceless.events.JOURNAL", tmp_path / "journal.jsonl")
    job = Job(id="t", pillar="story", topic="x", day="2026-01-01")
    job.advance("scripted")
    job.advance("voiced")
    with pytest.raises(TransitionError):
        job.advance("scripted")
    assert job.reached("scripted") and not job.reached("rendered")


def test_playbook_needs_three_steps():
    from faceless.gauntlet import check_structure
    beats = lambda *xs: [{"say": x} for x in xs]  # noqa: E731
    one = {"pillar": "playbook", "beats": beats("Hook.", "Step one. Open your bank app.", "Then save.")}
    three = {"pillar": "playbook", "beats": beats("Hook.", "Step one. Open the app.", "Step two. Set a transfer.",
                                                 "Step three. Turn on alerts.")}
    assert not check_structure(one, "")[0].passed
    assert check_structure(three, "")[0].passed
    assert check_structure({"pillar": "story", "beats": []}, "") == []


def test_spoken_words_expand_numbers():
    from faceless.pipeline.script import spoken_words
    assert spoken_words("$226,000") == 6          # two hundred twenty six thousand dollars
    assert spoken_words("in 2014") == 3           # in twenty fourteen
    assert spoken_words("8% a year") == 4         # eight percent a year
    assert spoken_words("plain words only") == 3


def test_normalize_caps_callouts_keeping_numbers():
    beats = [{"say": "x", "callout": c, "visual": "v"} for c in
             ["", "A", "B", "$1", "C", "$2", "D", "E", "$3", "F", "G"]]
    out = normalize({"title": "t", "beats": beats})["beats"]
    kept = [b["callout"] for b in out if b["callout"]]
    assert len(kept) == 7 and {"$1", "$2", "$3"} <= set(kept)


def test_composio_key_alias_and_execute_parsing(monkeypatch):
    import os
    from faceless.providers import composio_tools as ct
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    monkeypatch.setenv("COMPOSIO_API", "ak_test_alias")
    ct._ensure_key()
    assert os.environ["COMPOSIO_API_KEY"] == "ak_test_alias"

    class FakeSession:
        def execute(self, slug, arguments):
            assert slug == "YOUTUBE_LIST_CHANNELS" and arguments == {"mine": True}
            return {"data": {"items": [{"id": "UC1"}]}, "successful": True, "error": None, "log_id": "log_123"}

    monkeypatch.setattr(ct, "session", lambda: FakeSession())
    monkeypatch.setattr("faceless.events.JOURNAL", Path("/dev/null"))
    monkeypatch.setattr("faceless.ledger.LEDGER", Path("/dev/null"))
    res = ct.execute("YOUTUBE_LIST_CHANNELS", {"mine": True})
    assert res["log_id"] == "log_123" and res["data"]["items"][0]["id"] == "UC1"


def test_composio_execute_raises_with_log_id(monkeypatch):
    from faceless.providers import ProviderError
    from faceless.providers import composio_tools as ct

    class FailSession:
        def execute(self, slug, arguments):
            return {"data": {}, "successful": False, "error": "token expired", "log_id": "log_bad"}

    monkeypatch.setattr(ct, "session", lambda: FailSession())
    monkeypatch.setattr("faceless.events.JOURNAL", Path("/dev/null"))
    monkeypatch.setattr("faceless.ledger.LEDGER", Path("/dev/null"))
    with pytest.raises(ProviderError, match="log_bad"):
        ct.execute("YOUTUBE_LIST_CHANNELS", {})


def test_voice_classifier_separates_slop_from_our_voice():
    from faceless import quality
    slop = ("In today's fast-paced world, managing money can feel overwhelming. Let's dive into simple yet "
            "powerful tips that will transform your financial journey and unlock the life you deserve.")
    ours = ("A $6,000 card at 24% takes about 21 years on minimum payments. You'd pay $10,887 in interest. "
            "Pay $300 a month and it's gone in 26 months. Same debt. Two different lives.")
    assert quality.classify(slop)[0] == "slop"
    assert quality.classify(ours)[0] == "quality"


def test_aeo_name_parsing_and_self_match():
    from faceless import aeo
    assert aeo._names('["Graham Stephan", "Quiet Money", "The Financial Diet"]')[1] == "Quiet Money"
    assert aeo._names("1. Ali Abdaal\n2. QuietMoneyRules") == ["Ali Abdaal", "QuietMoneyRules"]
    assert aeo._is_us("QuietMoneyRules") and not aeo._is_us("Money Guy Show")


# ---- scheduling: resume + bank-ahead ----------------------------------------------------------

def test_extra_slots_roll_into_later_days():
    from faceless.providers.publish import nominal_slot
    assert nominal_slot("2026-10-02", 0) == ("2026-10-02", 0)
    assert nominal_slot("2026-10-02", 6) == ("2026-10-03", 1)
    assert nominal_slot("2026-10-02", 12) == ("2026-10-04", 2)


def test_open_slots_resume_and_bank_ahead(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from faceless import orchestrator
    today = datetime.now(timezone.utc).date()
    done = [Job(id=f"j{s}", pillar="math", topic="t", day=today.isoformat(), slot=s, status=st)
            for s, st in [(0, "published"), (1, "packaged"), (2, "held"), (5, "published")]]
    monkeypatch.setattr(orchestrator, "all_jobs", lambda: done)
    d0, d1 = today.isoformat(), (today + timedelta(days=1)).isoformat()
    assert orchestrator.open_slots(5) == [(d0, 2), (d0, 3), (d0, 4)]        # held slot is retried
    assert orchestrator.open_slots(5, extra=5) == [(d0, 2), (d0, 3), (d0, 4), (d1, 1), (d1, 2)]


def test_dotenv_loads_without_overriding(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# comment\nQM_TEST_A="from-file"\nexport QM_TEST_B=b\nQM_TEST_EMPTY=\n')
    monkeypatch.setenv("QM_TEST_B", "from-env")
    monkeypatch.delenv("QM_TEST_A", raising=False)
    assert config.load_dotenv(f) == 1
    import os
    assert os.environ["QM_TEST_A"] == "from-file" and os.environ["QM_TEST_B"] == "from-env"
    monkeypatch.delenv("QM_TEST_A")


def test_paid_image_fallback_is_capped(tmp_path, monkeypatch):
    from faceless import ledger
    from faceless.providers import ProviderUnavailable, images
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr(ledger, "used", lambda provider, unit, day=None: 60 if provider == "openrouter" else 0)
    with pytest.raises(ProviderUnavailable):
        images.openrouter("a quiet kitchen table", 864, 1536, 1, tmp_path / "x.jpg")
