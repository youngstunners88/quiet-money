"""The 2026-10-24 audit's wins: a provider circuit breaker, a calibrated word target, and a per-job Clef cap."""
import pytest

from faceless import config, prompts
from faceless import providers as P
from faceless.providers import ProviderError, ProviderUnavailable, clef
from faceless.orchestrator import length_brief


@pytest.fixture(autouse=True)
def _fresh():
    P._breaker.clear()
    clef._CALLS.clear()
    yield
    P._breaker.clear()
    clef._CALLS.clear()


def _chain(calls, bad_error):
    def bad():
        calls.append("bad")
        raise ProviderError(bad_error)

    def good():
        calls.append("good")
        return "ok"
    return [("bad", bad), ("good", good)]


def test_three_systemic_failures_open_the_breaker_and_the_provider_is_skipped():
    calls = []
    for _ in range(3):
        assert P.run_chain("tts", _chain(calls, "elevenlabs 401: unauthorized"))[0] == "good"
    calls.clear()
    assert P.run_chain("tts", _chain(calls, "elevenlabs 401"))[0] == "good"
    assert calls == ["good"]                                       # the fourth call never touched the dead provider


def test_per_input_errors_never_open_the_breaker():
    calls = []
    for _ in range(6):
        P.run_chain("img", _chain(calls, "clef 400: output flagged"))
    assert calls.count("bad") == 6


def test_one_probe_goes_through_after_the_cooldown(monkeypatch):
    calls = []
    for _ in range(3):
        P.run_chain("tts", _chain(calls, "edge 403"))
    calls.clear()
    P._breaker[("tts", "bad")]["opened"] -= P.BREAKER_COOLDOWN + 1
    P.run_chain("tts", _chain(calls, "edge 403"))
    assert calls == ["bad", "good"]                                # the probe, then the fallback; the breaker is open again
    calls.clear()
    P.run_chain("tts", _chain(calls, "edge 403"))
    assert calls == ["good"]


def test_the_last_provider_in_a_chain_is_always_tried():
    for _ in range(4):
        with pytest.raises(ProviderError):
            P.run_chain("only", [("solo", lambda: (_ for _ in ()).throw(ProviderError("503 down")))])
    assert P._breaker[("only", "solo")]["fails"] >= 3
    assert P.run_chain("only", [("solo", lambda: "back")])[1] == "back"


def test_the_first_draft_aims_above_the_middle_and_rewrites_overshoot(monkeypatch):
    prod = config.load()["production"]
    lo, hi = prod["words_range"]
    assert (lo + hi) // 2 < prompts.aim_words() <= hi
    monkeypatch.setitem(prod, "draft_word_bias", 500)
    assert prompts.aim_words() == hi                               # never past the top of the range
    monkeypatch.setitem(prod, "rewrite_overshoot", 1.0)
    assert "about 187 words" in length_brief(53.3, 124)


def test_the_clef_cap_hands_over_to_the_second_judge(monkeypatch):
    monkeypatch.setitem(config.load()["safety"], "max_clef_calls_per_job", 2)
    monkeypatch.setattr(config, "env", lambda *k: "x")
    clef._CALLS["job-1"] = 2
    with pytest.raises(ProviderUnavailable, match="cap reached"):
        clef.run({}, {"q": {}}, job="job-1")
    clef._CALLS.clear()
    clef._CALLS["process"] = 2
    with pytest.raises(ProviderUnavailable, match="cap reached"):
        clef.run({}, {"q": {}})                                    # no job id: counted per process
