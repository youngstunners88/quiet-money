"""Preflight says whether a run can succeed before it starts. Each check is staged in a temp folder with the fault present and absent, the
secret-leak scan is shown to find a value without ever printing it, and a check that crashes must become a warning, never a crash."""

import json
from collections import namedtuple
from datetime import datetime, timedelta, timezone

import pytest

from faceless import config, ledger, muapi, preflight, safety
from faceless.config import Paths

by_name = lambda checks: {c.name: c for c in checks}               # noqa: E731


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for name in ("reports", "jobs", "state", "ideas"):
        monkeypatch.setattr(Paths, name, tmp_path / name)
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(preflight, "STUDIO", tmp_path)
    return tmp_path


def test_config_loads_and_a_missing_section_fails(monkeypatch):
    assert preflight.checks_config()[0].level == preflight.OK
    cfg = {k: v for k, v in config.load().items() if k != "safety"}
    monkeypatch.setattr(config, "load", lambda: cfg)
    c = preflight.checks_config()[0]
    assert c.level == preflight.FAIL and "safety" in c.detail
    monkeypatch.setattr(config, "load", lambda: (_ for _ in ()).throw(ValueError("bad toml")))
    assert preflight.checks_config()[0].level == preflight.FAIL


def test_keys_are_reported_by_name_and_the_script_writer_is_mandatory(monkeypatch):
    c = by_name(preflight.checks_keys())
    assert c["keys:llm"].level == preflight.FAIL and c["keys:images"].level == preflight.WARN and c["keys:qa"].level == preflight.WARN
    monkeypatch.setenv("GEMINI_API_KEY", "g-secret-value-1234567890")
    monkeypatch.setenv("CLOUDFLARE_API_KEY", "c-secret-value-1234567890")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct")
    monkeypatch.setenv("MUAPI_API_KEY", "m-secret-value-1234567890")
    c = by_name(preflight.checks_keys())
    assert c["keys:llm"].level == c["keys:images"].level == c["keys:qa"].level == preflight.OK
    assert "GEMINI_API_KEY" in c["keys:llm"].detail
    assert "secret-value" not in json.dumps([x.__dict__ for x in preflight.checks_keys()])        # names only, never a value


def test_kill_switch_and_spend_lights(repo, monkeypatch):
    monkeypatch.setattr(safety, "ceiling", lambda: 3.0)
    c = by_name(preflight.checks_safety())
    assert c["kill switch"].level == preflight.OK and c["spend today"].level == preflight.OK
    ledger.spend("openrouter", "images", 1, usd=2.6)
    assert by_name(preflight.checks_safety())["spend today"].level == preflight.WARN
    ledger.spend("openrouter", "images", 1, usd=0.5)
    assert by_name(preflight.checks_safety())["spend today"].level == preflight.FAIL
    safety.pause("drill")
    k = by_name(preflight.checks_safety())["kill switch"]
    assert k.level == preflight.FAIL and "drill" in k.detail and "--resume" in k.fix


def test_state_logs_are_checked_for_conflict_markers_and_damaged_lines(repo):
    (Paths.state / "journal.jsonl").write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")
    (Paths.state / "ledger.jsonl").write_text('{"a": 1}\nnot json\n', encoding="utf-8")
    c = by_name(preflight.checks_state())
    assert c["state:journal.jsonl"].level == preflight.OK and c["state:ledger.jsonl"].level == preflight.WARN
    (Paths.state / "journal.jsonl").write_text('{"a": 1}\n<<<<<<< HEAD\n{"b": 2}\n=======\n>>>>>>> x\n', encoding="utf-8")
    assert by_name(preflight.checks_state())["state:journal.jsonl"].level == preflight.FAIL


def test_a_half_finished_git_operation_and_a_full_disk_fail(repo, monkeypatch):
    (repo / ".git").mkdir()
    assert by_name(preflight.checks_machine())["git state"].level == preflight.OK
    (repo / ".git" / "MERGE_HEAD").write_text("abc", encoding="utf-8")
    assert by_name(preflight.checks_machine())["git state"].level == preflight.FAIL
    Usage = namedtuple("Usage", "total used free")
    monkeypatch.setattr(preflight.shutil, "disk_usage", lambda p: Usage(10, 10, int(0.5 * 2**30)))
    assert by_name(preflight.checks_machine())["disk:repo"].level == preflight.FAIL
    monkeypatch.setattr(preflight.shutil, "disk_usage", lambda p: Usage(10, 1, int(50 * 2**30)))
    assert by_name(preflight.checks_machine())["disk:repo"].level == preflight.OK


@pytest.mark.parametrize("days_ago, level", [(0, preflight.OK), (2, preflight.WARN), (5, preflight.FAIL)])
def test_the_last_daily_report_ages_from_ok_to_fail(repo, days_ago, level):
    day = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    (Paths.reports / f"daily-{day}.md").write_text("x", encoding="utf-8")
    assert by_name(preflight.checks_freshness())["last daily batch"].level == level


def test_no_report_yet_is_a_warning_not_a_failure(repo):
    assert preflight.checks_freshness()[0].level == preflight.WARN


def test_cloudflare_pool_warns_when_over_the_cap_or_told_to_stop(monkeypatch):
    cap = config.load()["images"]["cloudflare_daily_neurons"]
    assert by_name(preflight.checks_quota())["cloudflare free pool"].level == preflight.OK
    ledger.spend("cloudflare", "neurons", cap + 1)
    assert by_name(preflight.checks_quota())["cloudflare free pool"].level == preflight.WARN


def test_wallet_lights_follow_the_balance(monkeypatch):
    monkeypatch.setenv("MUAPI_API_KEY", "k")
    assert preflight.checks_wallet()[0].level in (preflight.OK, preflight.WARN, preflight.FAIL)
    for bal, level in ((0.4, preflight.FAIL), (3.0, preflight.WARN), (30.0, preflight.OK)):
        monkeypatch.setattr(muapi, "balance", lambda b=bal: b)
        assert preflight.checks_wallet()[0].level == level
    monkeypatch.setattr(muapi, "balance", lambda: None)
    assert preflight.checks_wallet()[0].level == preflight.WARN
    monkeypatch.delenv("MUAPI_API_KEY")
    assert preflight.checks_wallet()[0].level == preflight.WARN


def test_a_secret_value_in_a_tracked_file_is_found_by_file_name_only(repo, monkeypatch):
    secret = "sk-live-0123456789abcdef-NOT-REAL"
    monkeypatch.setenv("SOME_SERVICE_API_KEY", secret)
    clean, dirty = repo / "notes.md", repo / "channel" / "oops.md"
    dirty.parent.mkdir()
    clean.write_text("nothing here", encoding="utf-8")
    dirty.write_text(f"token: {secret}", encoding="utf-8")
    monkeypatch.setattr(preflight, "tracked_text_files", lambda: [clean, dirty])
    assert preflight.leaked_secrets() == ["channel/oops.md"]
    c = preflight.checks_secrets()[0]
    assert c.level == preflight.FAIL and "oops.md" in c.detail and secret not in json.dumps(c.__dict__) and "rotate" in c.fix
    dirty.write_text("clean now", encoding="utf-8")
    assert preflight.checks_secrets()[0].level == preflight.OK


def test_short_and_url_like_values_are_not_treated_as_secrets(repo, monkeypatch):
    monkeypatch.setenv("SHORT_TOKEN", "abc123")
    monkeypatch.setenv("PROXY_TOKEN_URL", "https://proxy.example/some/long/path/value")
    f = repo / "a.md"
    f.write_text("abc123 https://proxy.example/some/long/path/value", encoding="utf-8")
    monkeypatch.setattr(preflight, "tracked_text_files", lambda: [f])
    assert preflight.leaked_secrets() == []


def test_a_check_that_crashes_becomes_a_warning(monkeypatch):
    def boom():
        raise RuntimeError("disk exploded")
    monkeypatch.setattr(preflight, "GROUPS", [boom, lambda: [preflight.Check("fine", preflight.OK, "x")]])
    out = preflight.run(wallet=False)
    assert [c.level for c in out] == [preflight.WARN, preflight.OK] and "RuntimeError" in out[0].detail


def test_exit_codes_and_the_report(monkeypatch):
    ok, warn, fail = (preflight.Check(n, lv, n, "do this") for n, lv in (("a", "ok"), ("b", "warn"), ("c", "fail")))
    assert preflight.exit_code([ok]) == 0 and preflight.exit_code([ok, warn]) == 0
    assert preflight.exit_code([ok, warn], strict=True) == 2 and preflight.exit_code([ok, fail], strict=True) == 1
    text = preflight.report([ok, warn, fail])
    assert "1 ok, 1 warn, 1 fail" in text and text.count("fix: do this") == 2          # an ok check prints no fix line


def test_the_tool_checks_name_what_to_install(monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda t: None)
    c = by_name(preflight.checks_tools())
    assert c["ffmpeg"].level == preflight.FAIL and "apt-get" in c["ffmpeg"].fix
    assert c["optional:node"].level == preflight.WARN and c["optional:libreoffice"].level == preflight.WARN
