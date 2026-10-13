import pytest

from faceless import monid
from faceless.providers import ProviderUnavailable


def test_money_comes_as_a_number_or_a_value_object():
    assert monid._num(0.01) == 0.01 and monid._num({"value": 0.02, "currency": "USD"}) == 0.02 and monid._num(None) is None


def test_per_call_price_is_known_and_per_result_needs_a_count():
    assert monid.estimate({"price": {"type": "PER_CALL", "amount": {"value": 0.01}}}) == 0.01
    per = {"price": {"type": "PER_RESULT", "amount": 0.002, "flatFee": 0.01}}
    assert monid.estimate(per) is None and monid.estimate(per, 100) == pytest.approx(0.21)


def test_no_key_means_unavailable_not_a_crash(monkeypatch):
    monkeypatch.delenv("MONID_API_KEY", raising=False)
    assert monid.balance() is None
    with pytest.raises(ProviderUnavailable):
        monid.run("p", "/e", {})


def test_run_is_refused_over_the_per_call_limit(monkeypatch):
    monkeypatch.setenv("MONID_API_KEY", "not-a-real-key")
    monkeypatch.setattr(monid, "inspect", lambda p, e: {"price": {"type": "PER_CALL", "amount": 5.0}})
    with pytest.raises(ProviderUnavailable, match="per-call limit"):
        monid.run("p", "/e", {})


def test_saved_results_carry_no_signed_links():
    out = monid._clean({"a": ["https://cdn.example/x.jpg?x-signature=abc&token=eyJ.eyJ.sig", {"b": "plain"}], "c": "z" * 900})
    assert out["a"][0] == "https://cdn.example/x.jpg" and out["a"][1] == {"b": "plain"} and len(out["c"]) < 400
