"""Circuit breaker drills: a provider that is down for a systemic reason (revoked key, no credit, spent quota, outage) is skipped
after a few failures instead of being retried on every video, and per-input errors never trip it."""

import pytest

from faceless import providers
from faceless.providers import ProviderError, ProviderUnavailable, run_chain


@pytest.fixture(autouse=True)
def closed():
    providers.reset_breakers()
    yield
    providers.reset_breakers()


def _calls():
    return {"dead": 0, "good": 0}


def _chain(boom, counts):
    def dead():
        counts["dead"] += 1
        raise boom

    def good():
        counts["good"] += 1
        return "audio"
    return [("dead", dead), ("good", good)]


def test_a_revoked_key_stops_being_retried_after_three_failures():
    c = _calls()
    for _ in range(10):                                         # ten videos in a row, the ElevenLabs 401 pattern
        assert run_chain("tts", _chain(ProviderError("elevenlabs 401: invalid key"), c)) == ("good", "audio")
    assert c["dead"] == providers.FAIL_MAX                      # tried 3 times, then skipped 7 times
    assert c["good"] == 10


def test_per_input_errors_never_trip_the_breaker():
    c = _calls()
    for _ in range(10):                                         # a flagged prompt (HTTP 400) is the prompt's fault, not the provider's
        run_chain("image", _chain(ProviderError('cloudflare 400: {"code":3030} output flagged'), c))
    assert c["dead"] == 10


def test_a_timeout_or_bad_json_is_not_systemic():
    c = _calls()
    for _ in range(6):
        run_chain("llm", _chain(ProviderError("gemini: bad-json(STOP)"), c))
    assert c["dead"] == 6


def test_missing_keys_are_left_to_the_provider():
    c = _calls()
    for _ in range(5):                                          # ProviderUnavailable is already a cheap skip; it must not open a breaker
        run_chain("llm", _chain(ProviderUnavailable("KEY not set"), c))
    assert c["dead"] == 5


def test_after_the_cooldown_one_probe_goes_through_and_a_success_closes_it(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(providers.time, "time", lambda: now[0])
    c = _calls()
    for _ in range(5):
        run_chain("tts", _chain(ProviderError("edge 403"), c))
    assert c["dead"] == providers.FAIL_MAX                      # open
    now[0] += providers.COOLDOWN + 1                            # half-open: exactly one probe
    healed = {"ok": False}

    def maybe():
        c["dead"] += 1
        if not healed["ok"]:
            raise ProviderError("edge 403")
        return "audio"
    chain = [("dead", maybe), ("good", lambda: "fallback")]
    assert run_chain("tts", chain)[0] == "good"                 # probe failed, cooldown restarts
    assert c["dead"] == providers.FAIL_MAX + 1
    run_chain("tts", chain)
    assert c["dead"] == providers.FAIL_MAX + 1                  # skipped again, no second probe
    now[0] += providers.COOLDOWN + 1
    healed["ok"] = True
    assert run_chain("tts", chain)[0] == "dead"                 # probe succeeds
    assert run_chain("tts", chain)[0] == "dead"                 # and the breaker is closed again


def test_the_last_provider_in_a_chain_is_always_tried_even_when_open():
    n = {"calls": 0}

    def only():
        n["calls"] += 1
        raise ProviderError("openrouter 402")
    for _ in range(6):
        with pytest.raises(ProviderError, match="all llm providers failed"):
            run_chain("llm", [("only", only)])
    assert n["calls"] == 6                                      # a chain must try everything before giving up


def test_breakers_are_per_capability_and_provider():
    c = _calls()
    for _ in range(5):
        run_chain("tts", _chain(ProviderError("x 401"), c))
    d = _calls()
    run_chain("image", _chain(ProviderError("x 401"), d))       # same provider name, different capability: still closed
    assert d["dead"] == 1


def test_a_skipped_provider_is_journaled():
    from faceless import events
    c = _calls()
    for _ in range(5):
        run_chain("tts", _chain(ProviderError("elevenlabs 401"), c))
    assert any(e["type"] == "PROVIDER_SKIPPED" and e["reason"] == "circuit open" for e in events.read())
