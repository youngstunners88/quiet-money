"""Flint is free extra capacity for side work. These tests keep it off the daily critical path and keep it free."""

import re
from pathlib import Path

import pytest

from faceless import config, flint
from faceless.providers import ProviderError, ProviderUnavailable

ROOT = Path(__file__).resolve().parent.parent


def test_flint_is_not_in_the_critical_chain():
    llm = config.load()["llm"]
    assert not any("flint" in str(x).lower() for x in [*llm["chain"], *llm["openrouter_models"], *llm["gemini_models"]])


def test_no_pipeline_gauntlet_script_offer_or_publish_code_imports_flint():
    importers = []
    for f in (ROOT / "faceless").rglob("*.py"):
        if f.name == "flint.py":
            continue
        if re.search(r"^\s*(from faceless import .*\bflint\b|from faceless\.flint import|import faceless\.flint)", f.read_text(encoding="utf-8"), re.M):
            importers.append(f.relative_to(ROOT).as_posix())
    assert importers == ["faceless/cli.py"]          # the command line only: the CLI is how a person or a routine asks for extra hands


def test_only_free_model_ids_are_accepted(monkeypatch):
    monkeypatch.setattr(flint, "cfg", lambda: {"enabled": True, "model": "recursive/flint-v1.0", "daily_calls": 5, "retries": 1, "backoff_s": 0, "timeout_s": 5})
    with pytest.raises(ProviderError, match=":free"):
        flint.model()


def test_a_switched_off_flint_refuses_and_a_pause_stops_it(monkeypatch):
    monkeypatch.setattr(flint, "cfg", lambda: {"enabled": False, "model": "x:free", "daily_calls": 5, "retries": 1, "backoff_s": 0, "timeout_s": 5})
    with pytest.raises(ProviderUnavailable, match="switched off"):
        flint.ask("hi", task="t")
    monkeypatch.setattr(flint, "cfg", lambda: {"enabled": True, "model": "x:free", "daily_calls": 5, "retries": 1, "backoff_s": 0, "timeout_s": 5})
    monkeypatch.setattr(flint.safety, "paused", lambda: "owner pause")
    with pytest.raises(ProviderUnavailable, match="paused"):
        flint.ask("hi", task="t")


class Resp:
    def __init__(self, code, body=None):
        self.status_code, self._b = code, body or {}

    def json(self):
        return self._b


def _setup(monkeypatch, tmp_path, replies):
    monkeypatch.setattr(flint, "LOG", tmp_path / "flint.jsonl")
    monkeypatch.setattr(flint, "cfg", lambda: {"enabled": True, "model": "recursive/flint-v1.0:free", "daily_calls": 50, "retries": 3, "backoff_s": 0, "timeout_s": 5})
    monkeypatch.setattr(flint.safety, "paused", lambda: None)
    monkeypatch.setattr(flint.ledger, "used", lambda *a, **k: 0.0)
    monkeypatch.setattr(flint.ledger, "spend", lambda *a, **k: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k-test")
    it = iter(replies)

    class S:
        def post(self, *a, **k):
            return next(it)
    monkeypatch.setattr(flint, "http", lambda: S())


def ok(text):
    return Resp(200, {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": 9}})


def test_a_rate_limit_is_retried_bad_json_is_retried_and_every_call_is_measured(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, [Resp(429), ok("not json"), ok('{"seeds": []}')])
    assert flint.ask("p", task="seeds", want_json=True) == {"seeds": []}
    monkeypatch.setattr(flint, "read_jsonl", lambda p: [__import__("json").loads(x) for x in Path(p).read_text().splitlines()])
    st = flint.status()
    assert st["calls"] == 1 and st["ok_rate"] == 1.0 and st["by_task"]["seeds"]["json_ok"] == 1


def test_failure_raises_and_is_recorded_unless_a_fallback_is_asked_for(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, [Resp(429), Resp(429), Resp(429)])
    with pytest.raises(ProviderError, match="429"):
        flint.ask("p", task="t")
    assert '"ok": false' in (tmp_path / "flint.jsonl").read_text()
    _setup(monkeypatch, tmp_path, [Resp(500)])
    from faceless.providers import llm
    monkeypatch.setattr(llm, "complete", lambda prompt, **k: "from the normal chain")
    assert flint.ask("p", task="t", fallback=True) == "from the normal chain"
