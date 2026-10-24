"""The 2026-10-24 audit: a per-job Clef cap (the breaker and the word target have their own test files)."""
import pytest

from faceless import config
from faceless.providers import ProviderUnavailable, clef


@pytest.fixture(autouse=True)
def _fresh():
    clef._CALLS.clear()
    yield
    clef._CALLS.clear()


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
