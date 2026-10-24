"""The writer undershoots (64% of first drafts too short, a rewrite delivers ~61% of the change it is asked for, measured Oct 1-24).
The prompt aims above the middle of the range and a length rewrite over-asks, while the gate window itself never moves."""

import re

import pytest

from faceless import config, orchestrator, prompts


@pytest.fixture
def prod():
    return config.load()["production"]


def test_the_first_draft_aims_above_the_middle_but_never_above_the_range(prod):
    lo, hi = prod["words_range"]
    assert (lo + hi) // 2 < prompts.aim_words() <= hi


def test_the_aim_is_capped_at_the_top_of_the_range(prod, monkeypatch):
    monkeypatch.setitem(prod, "draft_word_bias", 500)
    assert prompts.aim_words() == prod["words_range"][1]


def test_a_zero_bias_restores_the_old_behavior(prod, monkeypatch):
    monkeypatch.setitem(prod, "draft_word_bias", 0)
    lo, hi = prod["words_range"]
    assert prompts.aim_words() == (lo + hi) // 2


def test_the_first_prompt_carries_the_aim_and_the_unchanged_range(prod):
    p = prompts.script_prompt(config.pillar("story"), "any topic")
    lo, hi = prod["words_range"]
    assert f"{lo}-{hi} words" in p and f"aim for {prompts.aim_words()}" in p


def _asked(seconds, words):
    return int(re.search(r"about (\d+) words", orchestrator.length_brief(seconds, words)).group(1))


def test_a_short_rewrite_asks_for_more_than_the_gap_so_the_partial_result_lands(prod):
    lo, hi = prod["words_range"]
    mid = (lo + hi) // 2
    assert _asked(50.0, 150) > mid                              # over-asks: 61% compliance on the bigger ask still reaches the window
    achieved_spoken = (150 + 0.6 * (_asked(50.0, 150) - 150)) * 1.087       # 60% compliance, 8.7% spoken/written ratio, both measured
    assert lo + 5 <= achieved_spoken <= hi + 25                 # inside the gate's spoken window


def test_a_long_script_is_still_told_to_cut_to_inside_the_range(prod):
    lo, hi = prod["words_range"]
    assert lo <= _asked(80.0, 240) <= hi


def test_the_ask_stays_inside_the_written_range(prod):
    lo, hi = prod["words_range"]
    for words in (60, 120, 150, 180, 220, 300, 500):
        assert lo <= _asked(50.0, words) <= hi


def test_an_overshoot_of_one_is_the_old_behavior(prod, monkeypatch):
    monkeypatch.setitem(prod, "rewrite_overshoot", 1.0)
    lo, hi = prod["words_range"]
    assert _asked(50.0, 150) == (lo + hi) // 2


def test_the_gate_window_is_untouched():
    import inspect
    from faceless import gauntlet
    assert "slo, shi = lo + 5, hi + 25" in inspect.getsource(gauntlet.check_script)
