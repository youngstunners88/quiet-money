"""Failure drills. Each test breaks one thing the studio depends on and checks that the day still ends well: a finished video, no
runaway spend, nothing public sent by accident, and no crash. They run on every push (see .github/workflows/ci.yml), so a change
that removes a safety net fails CI before it can fail a production day."""

import json

import pytest

from faceless import config, events, ledger, orchestrator, safety
from faceless.config import Paths
from faceless.providers import ProviderError, ProviderUnavailable, clef, images, llm, publish, run_chain


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "state", tmp_path / "state")
    return tmp_path / "state"


# ---------------------------------------------------------------- the kill switch

def test_pause_halts_the_daily_run_and_a_single_make(state):
    safety.pause("drill: stop everything")
    assert orchestrator.daily(2) == []
    with pytest.raises(RuntimeError, match="paused"):
        orchestrator.run_one("story", "any topic")
    assert any(e["type"] == "DAILY_HALTED" and "drill" in e["reason"] for e in events.read())


def test_pause_stops_posting_but_the_local_pack_is_still_written(state, monkeypatch):
    monkeypatch.setitem(config.load()["publish"], "mode", "upload_post")
    monkeypatch.setattr(publish, "local_pack", lambda job, meta: {"mode": "local", "folder": "x"})
    monkeypatch.setitem(publish.PUBLISHERS, "upload_post", lambda job, meta: pytest.fail("posted while the studio was paused"))
    safety.pause("drill")
    out = publish.publish(object(), {})
    assert out["local"]["folder"] == "x" and "paused" in out["upload_post"]["skipped"]


def test_pause_makes_every_paid_image_provider_stand_down(state, monkeypatch):
    monkeypatch.setenv("MUAPI_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    safety.pause("drill")
    for name in ("muapi", "openrouter"):
        with pytest.raises(ProviderUnavailable, match="paused"):
            images.PROVIDERS[name]("p", 720, 1280, 1, "unused.jpg")


def test_the_daily_ceiling_stops_spend_across_providers_together(state, monkeypatch):
    monkeypatch.setenv("MUAPI_API_KEY", "k")
    monkeypatch.setitem(config.load(), "safety", {"daily_usd_ceiling": 1.0})
    ledger.spend("openrouter", "images", 24, usd=0.999)                              # another provider already spent almost everything
    with pytest.raises(ProviderUnavailable, match="ceiling"):
        images.muapi("p", 720, 1280, 1, "unused.jpg")


# ---------------------------------------------------------------- quota starvation

class _Cf:
    def post(self, url, **kw):
        class R:
            status_code = 200
            text = ""
            def json(self):
                return {"success": True, "result": {"answers": {"q": {"noul": 0.1}}, "usage": {"input_tokens": 1000}}}
        return R()


def test_image_generation_leaves_the_qa_reserve_so_the_checks_never_starve(state, monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_KEY", "k")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "a")
    cfg = config.load()["images"]
    ledger.spend("cloudflare", "neurons", cfg["cloudflare_daily_neurons"] - cfg["cloudflare_qa_reserve"])     # the generation share is gone
    with pytest.raises(ProviderUnavailable, match="neuron"):
        images.cloudflare("p", 720, 1280, 1, "unused.jpg")
    monkeypatch.setattr(clef, "http", lambda: _Cf())
    assert clef.run("state", {"q": {"type": "noul", "instructions": "x"}})["q"]["noul"] == 0.1                # the reserve still pays for a check


# ---------------------------------------------------------------- provider failure

def test_the_image_chain_always_ends_in_a_picture(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "cache", tmp_path / "cache")
    for name in ("cloudflare", "muapi", "openrouter", "pollinations"):
        monkeypatch.setitem(images.PROVIDERS, name, lambda *a, **k: (_ for _ in ()).throw(ProviderError("down")))
    provider, path = images.generate("a stack of coins on a desk", seed=3)
    assert provider == "procedural" and path.endswith(".jpg")
    assert any(e["type"] == "PROVIDER_FAIL" for e in events.read())                                          # and the failures were recorded


def test_the_script_chain_skips_a_rate_limited_provider(monkeypatch):
    def limited(*a, **k):
        raise ProviderError("gemini 429 quota")

    def missing(*a, **k):
        raise ProviderUnavailable("LONGCAT_API_KEY not set")
    monkeypatch.setitem(llm.PROVIDERS, "gemini", limited)
    monkeypatch.setitem(llm.PROVIDERS, "longcat", missing)
    monkeypatch.setitem(llm.PROVIDERS, "openrouter", lambda p, **k: "  a script  ")
    assert llm.complete("write") == "a script"
    assert [e["provider"] for e in events.read() if e["type"] == "PROVIDER_OK"][-1] == "openrouter"


def test_a_chain_where_everything_fails_raises_one_clear_error():
    def boom():
        raise ProviderError("nope")
    with pytest.raises(ProviderError, match="all demo providers failed"):
        run_chain("demo", [("a", boom), ("b", boom)])


# ---------------------------------------------------------------- damaged state

def test_a_corrupted_journal_or_ledger_line_is_skipped_not_fatal(state, monkeypatch):
    state.mkdir(parents=True)
    j = state / "journal.jsonl"
    j.write_text('{"type": "OK", "t": 1}\n{"type": "TRUNC\n\x00\x00\nnot json at all\n{"type": "OK2", "t": 2}\n', encoding="utf-8")
    assert [e["type"] for e in events.read(j)] == ["OK", "OK2"]
    led = state / "ledger.jsonl"
    monkeypatch.setattr(ledger, "LEDGER", led)
    led.write_text(json.dumps({"day": ledger.today(), "provider": "p", "unit": "u", "amount": 2, "usd": 0.5}) + "\n{broken\n", encoding="utf-8")
    assert ledger.used("p", "u") == 2 and ledger.usd_total() == 0.5
    ledger.spend("p", "u", 1)                                                                                 # appends past the damage
    assert ledger.used("p", "u") == 3


def test_the_ledger_and_journal_create_their_own_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "fresh" / "ledger.jsonl")
    monkeypatch.setattr(events, "JOURNAL", tmp_path / "fresh" / "journal.jsonl")
    ledger.spend("p", "u", 1)
    events.emit("HELLO")
    assert ledger.used("p", "u") == 1 and events.read()[0]["type"] == "HELLO"


def test_secrets_never_reach_the_committed_journal(state, monkeypatch):
    monkeypatch.setenv("SOME_SERVICE_API_KEY", "abcdef1234567890SECRET")
    events.emit("PROVIDER_FAIL", error="401 for key abcdef1234567890SECRET at https://x.test/?key=hunter2hunter2")
    text = events.JOURNAL.read_text(encoding="utf-8")
    assert "abcdef1234567890SECRET" not in text and "hunter2hunter2" not in text
