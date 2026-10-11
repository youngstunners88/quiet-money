"""The second-opinion helper: secrets never leave, and a brief that could blow the cap is refused before any call."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("consult", Path(__file__).resolve().parents[1] / ".claude/skills/faceless-unblock/scripts/consult.py")
consult = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consult)


class Resp:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_unknown_router_price_is_planned_at_a_high_ceiling(monkeypatch):
    models = {"data": [{"id": "r/router", "pricing": {"prompt": "-1", "completion": "-1"}}]}
    monkeypatch.setattr(consult.requests, "get", lambda *a, **k: Resp(models))
    assert consult.prices("r/router") == consult.UNKNOWN_PRICE


def test_over_cap_brief_is_refused_before_any_request(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-" + "a" * 40)
    monkeypatch.setattr(consult, "prices", lambda m: (1e-5, 1e-4))
    monkeypatch.setattr(consult.requests, "post", lambda *a, **k: pytest.fail("a request was sent"))
    with pytest.raises(SystemExit, match="over the"):
        consult.consult("x" * 300_000, ["a/b"], max_cost=0.25)


def test_key_shaped_text_is_redacted_before_sending(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-" + "b" * 40)
    monkeypatch.setattr(consult, "prices", lambda m: (1e-7, 1e-7))
    sent = {}

    def post(url, json=None, **kw):
        sent["content"] = json["messages"][0]["content"]
        return Resp({"choices": [{"message": {"content": "ok"}}], "usage": {"cost": 0.001}})

    monkeypatch.setattr(consult.requests, "post", post)
    consult.consult("the key is sk-or-v1-" + "c" * 40 + " please help", ["a/b"], max_cost=0.25)
    assert "c" * 40 not in sent["content"]
