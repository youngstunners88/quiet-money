"""Crouton is free extra capacity for side work. These tests keep it free, private, measured and off the daily critical path."""

import json
import re
from pathlib import Path

import pytest

from faceless import config, crouton
from faceless.providers import ProviderError, ProviderUnavailable

ROOT = Path(__file__).resolve().parent.parent
FAKE_KEY = "sk" + "-" + "a1b2c3d4" * 4                                 # built at run time so no secret-shaped literal is committed
BASE = {"enabled": True, "model": "stealth/crouton-alpha", "daily_calls": 50, "retries": 3, "backoff_s": 0, "timeout_s": 5, "bench_min_cases": 40,
        "min_recall": 0.9, "max_false_alarm": 0.1, "private_prefixes": crouton.PRIVATE_DEFAULT}


def test_crouton_is_not_in_the_critical_chain():
    llm = config.load()["llm"]
    assert not any("crouton" in str(x).lower() for x in [*llm["chain"], *llm["openrouter_models"], *llm["gemini_models"]])


def test_no_pipeline_gauntlet_script_offer_or_publish_code_imports_crouton():
    importers = []
    for f in (ROOT / "faceless").rglob("*.py"):
        if f.name == "crouton.py":
            continue
        if re.search(r"^\s*(from faceless import .*\bcrouton\b|from faceless\.crouton import|import faceless\.crouton)", f.read_text(encoding="utf-8"), re.M):
            importers.append(f.relative_to(ROOT).as_posix())
    assert importers == ["faceless/cli.py"]          # the command line only


def test_only_known_free_ids_are_accepted(monkeypatch):
    monkeypatch.setattr(crouton, "cfg", lambda: {**BASE, "model": "anthropic/claude-haiku-5.5"})
    with pytest.raises(ProviderError, match="free"):
        crouton.model()
    monkeypatch.setattr(crouton, "cfg", lambda: {**BASE, "model": "some/other:free"})
    assert crouton.model() == "some/other:free"


class Resp:
    def __init__(self, code, body=None):
        self.status_code, self._b = code, body or {}

    def json(self):
        return self._b


def ok(text, finish="stop", cost=0, reasoning=0):
    return Resp(200, {"choices": [{"message": {"content": text}, "finish_reason": finish}], "model": "stealth/crouton-alpha", "provider": "Stealth",
                      "usage": {"total_tokens": 9, "cost": cost, "completion_tokens_details": {"reasoning_tokens": reasoning}}})


CATALOG_FREE = Resp(200, {"data": [{"id": "stealth/crouton-alpha", "pricing": {"prompt": "0", "completion": "0"}}]})


def setup(monkeypatch, tmp_path, replies, catalog=CATALOG_FREE):
    sent = []
    monkeypatch.setattr(crouton, "LOG", tmp_path / "crouton.jsonl")
    monkeypatch.setattr(crouton, "BREAKER", tmp_path / "crouton.tripped")
    monkeypatch.setattr(crouton, "PRICE_CACHE", tmp_path / "price.json")
    monkeypatch.setattr(crouton, "cfg", lambda: dict(BASE))
    monkeypatch.setattr(crouton.safety, "paused", lambda: None)
    monkeypatch.setattr(crouton.ledger, "used", lambda *a, **k: 0.0)
    monkeypatch.setattr(crouton.ledger, "spend", lambda *a, **k: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k-test-not-a-real-key")
    it = iter(replies)

    class S:
        def get(self, *a, **k):
            if isinstance(catalog, Exception):
                raise catalog
            return catalog

        def post(self, url, json=None, **k):
            sent.append(dict(json))
            return next(it)
    monkeypatch.setattr(crouton, "http", lambda: S())
    return sent


def test_a_switched_off_crouton_refuses_and_a_pause_stops_it(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, [])
    monkeypatch.setattr(crouton, "cfg", lambda: {**BASE, "enabled": False})
    with pytest.raises(ProviderUnavailable, match="switched off"):
        crouton.ask("hi", task="t")
    monkeypatch.setattr(crouton, "cfg", lambda: dict(BASE))
    monkeypatch.setattr(crouton.safety, "paused", lambda: "owner pause")
    with pytest.raises(ProviderUnavailable, match="paused"):
        crouton.ask("hi", task="t")


def test_the_standard_template_sets_effort_per_kind_and_never_sends_under_4000_tokens(monkeypatch, tmp_path):
    sent = setup(monkeypatch, tmp_path, [ok("a"), ok("b"), ok("c"), ok("d")])
    for kind, effort in (("classify", "minimal"), ("review", "low"), ("draft", "low"), ("digest", "medium")):
        crouton.ask("p", task="t", kind=kind, max_tokens=100)
        assert sent[-1]["reasoning"] == {"effort": effort} and sent[-1]["max_tokens"] == 4000
    with pytest.raises(ProviderError, match="kind"):
        crouton.ask("p", task="t", kind="chat")


def test_an_empty_answer_cut_off_by_length_is_retried_once_with_double_the_budget(monkeypatch, tmp_path):
    sent = setup(monkeypatch, tmp_path, [ok("", finish="length", reasoning=4000), ok("the answer")])
    assert crouton.ask("p", task="t") == "the answer"
    assert [s["max_tokens"] for s in sent] == [4000, 8000]
    row = json.loads((tmp_path / "crouton.jsonl").read_text().splitlines()[-1])
    assert row["ok"] and row["grown"] and row["max_tokens"] == 8000


def test_a_rate_limit_is_retried_bad_json_is_retried_and_every_call_is_measured(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, [Resp(429), ok("not json"), ok('{"seeds": []}')])
    assert crouton.ask("p", task="seeds", kind="draft", want_json=True) == {"seeds": []}
    st = crouton.status()
    assert st["calls"] == 1 and st["ok_rate"] == 1.0 and st["by_task"]["seeds"]["json_ok"] == 1


def test_failure_raises_and_is_recorded_unless_a_fallback_is_asked_for(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, [Resp(429), Resp(429), Resp(429)])
    with pytest.raises(ProviderError, match="429"):
        crouton.ask("p", task="t")
    assert '"ok": false' in (tmp_path / "crouton.jsonl").read_text()
    setup(monkeypatch, tmp_path, [Resp(500)])
    from faceless.providers import llm
    monkeypatch.setattr(llm, "complete", lambda prompt, **k: "from the normal chain")
    assert crouton.ask("p", task="t", fallback=True) == "from the normal chain"


def test_one_billed_call_trips_the_breaker_and_stops_every_later_call(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, [ok("x", cost=0.002)])
    with pytest.raises(ProviderError, match="billed"):
        crouton.ask("p", task="t")
    assert (tmp_path / "crouton.tripped").exists()
    with pytest.raises(ProviderUnavailable, match="tripped"):
        crouton.ask("p", task="t")
    assert crouton.status()["tripped"]


def test_a_price_that_is_no_longer_zero_or_an_unreachable_catalog_refuses_before_any_call(monkeypatch, tmp_path):
    paid = Resp(200, {"data": [{"id": "stealth/crouton-alpha", "pricing": {"prompt": "0.0000001", "completion": "0"}}]})
    sent = setup(monkeypatch, tmp_path, [ok("x")], catalog=paid)
    with pytest.raises(ProviderError, match="no longer free"):
        crouton.ask("p", task="t")
    sent = setup(monkeypatch, tmp_path, [ok("x")], catalog=ConnectionError("down"))
    with pytest.raises(ProviderUnavailable, match="catalog"):
        crouton.ask("p", task="t")
    assert sent == []                                                  # nothing was sent in either case


def test_the_free_check_is_cached_for_the_day(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path, [ok("a"), ok("b")])
    crouton.ask("p", task="t")
    setup(monkeypatch, tmp_path, [ok("b")], catalog=ConnectionError("down"))   # same tmp_path: today's cache is still there
    assert crouton.ask("p", task="t") == "b"


def test_a_prompt_that_looks_like_a_secret_never_leaves(monkeypatch, tmp_path):
    sent = setup(monkeypatch, tmp_path, [ok("x")])
    with pytest.raises(ProviderError, match="secret"):
        crouton.ask("here is my key " + FAKE_KEY + " please", task="t")
    monkeypatch.setenv("SOME_API_KEY", "value-that-is-long-enough-1234")
    with pytest.raises(ProviderError, match="SOME_API_KEY"):
        crouton.ask("the value-that-is-long-enough-1234 is in here", task="t")
    assert sent == []


def test_private_paths_and_missing_files_are_refused_before_anything_is_sent(tmp_path):
    with pytest.raises(ProviderError, match="private"):
        crouton.read_files(["state/ledger.jsonl"])
    with pytest.raises(ProviderError, match="private"):
        crouton.read_files(["channel/services/web3-video/leads/anyone.md"])
    with pytest.raises(ProviderError, match="does not exist"):
        crouton.read_files(["channel/not-a-file.md"])
    assert "--- FILE: CLAUDE.md ---" in crouton.read_files(["CLAUDE.md"])


def test_screen_only_adds_holds_an_unreadable_answer_is_a_hold(monkeypatch):
    seen = {}

    def fake(prompt, **k):
        seen.update(k)
        return answer
    monkeypatch.setattr(crouton, "ask", fake)
    answer = {"verdict": "pass", "violated_rules": [], "reason": "fine"}
    assert crouton.screen("text")["advise_hold"] is False and seen["kind"] == "classify"
    for bad in ({"verdict": "maybe"}, {}, {"verdict": "hold", "violated_rules": [2, 99, "x"]}):
        answer = bad
        s = crouton.screen("text")
        assert s["advise_hold"] is True
    assert s["violated_rules"] == [2]


def test_the_rules_excerpt_comes_from_the_real_rules():
    ex = crouton.rules_excerpt()
    assert all(f"\n{n}. " in "\n" + ex for n in crouton.SCREEN_RULES) and "Education, never advice" in ex


def test_gate_cases_are_deterministic_labelled_and_the_holdout_never_overlaps_the_dev_split(monkeypatch, tmp_path):
    monkeypatch.setattr(crouton, "GATE_CASES", tmp_path / "dev.jsonl")
    monkeypatch.setattr(crouton, "HOLDOUT_CASES", tmp_path / "holdout.jsonl")
    dev, hold = crouton.make_gate_cases(split="dev"), crouton.make_gate_cases(split="holdout")
    assert dev == crouton.make_gate_cases(split="dev") and hold == crouton.make_gate_cases(split="holdout")
    assert (len(dev), sum(c["truth"] == "pass" for c in dev), sum(c["truth"] == "hold" for c in dev)) == (80, 40, 40)
    assert (len(hold), sum(c["truth"] == "pass" for c in hold), sum(c["truth"] == "hold" for c in hold)) == (64, 40, 24)
    assert {r for c in dev + hold for r in c["rules"]} == {1, 2, 8, 13}
    base = lambda cs: {c["source"].split(" ")[0 if c["truth"] == "hold" else 2] for c in cs}    # noqa: E731 - the script file each case was built from
    assert not base(dev) & base(hold)
    dev_lines = {line for v in crouton.INJECTIONS.values() for line in v[1]}
    hold_lines = {line for v in crouton.INJECTIONS_HOLDOUT.values() for line in v[1]}
    assert not dev_lines & hold_lines                                  # the holdout phrasings were never in the tuning set
    assert all(any(line in c["text"] for line in dev_lines) for c in dev if c["truth"] == "hold")
    assert all(any(line in c["text"] for line in hold_lines) for c in hold if c["truth"] == "hold")


def test_the_committed_cases_match_the_generator():
    for path, n in ((crouton.GATE_CASES, 80), (crouton.HOLDOUT_CASES, 64)):
        cases = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        assert len(cases) == n and len({c["id"] for c in cases}) == n


def test_scoring_counts_right_wrongly_flagged_and_missed_and_has_no_opinion_when_small():
    rows = ([{"truth": "hold", "rules": [2], "verdict": "hold", "violated_rules": [2]}] * 38 + [{"truth": "hold", "rules": [2], "verdict": "pass", "violated_rules": []}] * 2
            + [{"truth": "pass", "rules": [], "verdict": "pass", "violated_rules": []}] * 38 + [{"truth": "pass", "rules": [], "verdict": "hold", "violated_rules": [1]}] * 2)
    s = crouton.score_gate(rows)
    assert (s["caught"], s["missed"], s["false_alarms"], s["right_pass"]) == (38, 2, 2, 38)
    assert s["recall"] == 0.95 and s["false_alarm_rate"] == 0.05 and "eligible" in s["verdict"] and "release" in s["verdict"]
    assert "no opinion" in crouton.score_gate(rows[:10])["verdict"]
    failed = [dict(r, verdict=None) for r in rows[:20]] + rows[20:]
    assert "no opinion" in crouton.score_gate(failed)["verdict"]               # a failed call is not a look
    flagged_everything = [dict(r, verdict="hold") for r in rows]
    assert "not eligible" in crouton.score_gate(flagged_everything)["verdict"]


def test_bench_runs_every_case_and_writes_a_report_without_the_script_text(monkeypatch, tmp_path):
    monkeypatch.setattr(crouton, "GATE_CASES", tmp_path / "cases.jsonl")
    monkeypatch.setattr(crouton, "HOLDOUT_CASES", tmp_path / "holdout.jsonl")
    monkeypatch.setattr(crouton, "REPORTS", tmp_path / "reports")
    crouton.make_gate_cases()
    crouton.make_gate_cases(split="holdout")
    monkeypatch.setattr(crouton.ledger, "used", lambda *a, **k: 0.0)
    monkeypatch.setattr(crouton, "screen", lambda t: {"verdict": "hold" if "injected" in t or "buy" in t.lower() else "pass", "violated_rules": [2], "reason": "r", "advise_hold": True})
    assert crouton.bench(dry_run=True)["calls"] == 80 and crouton.bench(dry_run=True, split="holdout")["calls"] == 64
    rep = crouton.bench(limit=10)
    assert rep["score"]["cases"] == 10 and "informational" in rep["score"]["verdict"]       # a tuned-on split never gives the verdict
    crouton.bench(split="holdout")
    saved = json.loads(next((tmp_path / "reports").glob("*-gate-dev-*.json")).read_text())
    assert "text" not in saved["rows"][0] and saved["rows"][0]["id"] and saved["prompt"] == crouton.SCREEN_VERSION
    held = json.loads(next((tmp_path / "reports").glob("*-gate-holdout-*.json")).read_text())
    assert "informational" not in held["score"]["verdict"]
