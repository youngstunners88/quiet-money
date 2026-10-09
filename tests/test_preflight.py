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


# ---------------------------------------------------------------- the gate in front of production

def test_the_gate_names_only_failures_that_make_a_run_impossible(monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda t: None)
    names = {c.name for c in preflight.gate()}
    assert {"ffmpeg", "ffprobe"} <= names
    assert not names & {"optional:node", "optional:libreoffice", "last daily batch", "skills", "secrets in git"}


def test_a_stale_report_or_a_leaked_secret_never_blocks_production(repo, monkeypatch):
    (Paths.reports / "daily-2020-01-01.md").write_text("old", encoding="utf-8")
    monkeypatch.setattr(preflight, "leaked_secrets", lambda: ["notes.md"])
    assert by_name(preflight.checks_freshness())["last daily batch"].level == preflight.FAIL          # the standalone report still fails loudly
    assert by_name(preflight.checks_secrets())["secrets in git"].level == preflight.FAIL
    assert not [c for c in preflight.gate() if c.name in ("last daily batch", "secrets in git")]


def test_a_broken_git_state_blocks_and_edge_tts_blocks_only_without_another_voice(repo, monkeypatch):
    (repo / ".git").mkdir()
    (repo / ".git" / "rebase-merge").mkdir()
    assert "git state" in {c.name for c in preflight.gate()}
    real_import = preflight.importlib.import_module

    def no_edge(name):
        if name == "edge_tts":
            raise ImportError(name)
        return real_import(name)
    monkeypatch.setattr(preflight.importlib, "import_module", no_edge)
    assert by_name(preflight.checks_tools())["python:edge_tts"].level == preflight.FAIL
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    assert by_name(preflight.checks_tools())["python:edge_tts"].level == preflight.WARN


def test_daily_and_make_stop_before_spending_anything_when_the_machine_cannot_finish(monkeypatch, capsys):
    import argparse
    from faceless import cli, orchestrator
    monkeypatch.setattr(preflight, "gate", lambda: [preflight.Check("ffmpeg", preflight.FAIL, "missing", "apt-get install -y ffmpeg")])
    monkeypatch.setattr(orchestrator, "daily", lambda *a, **k: pytest.fail("a run started on a machine that cannot render"))
    assert cli.cmd_daily(argparse.Namespace(count=None, extra=0, pillar=None, no_judge=False, no_publish=True, skip_preflight=False)) == 4
    out = capsys.readouterr().out
    assert "BLOCKED" in out and "apt-get install -y ffmpeg" in out and "nothing was spent" in out
    assert cli.cmd_make(argparse.Namespace(pillar="math", topic=None, script=None, slot=0, voice=None, no_judge=True, no_publish=True, skip_preflight=False)) == 4
    from faceless import events
    assert [e["checks"] for e in events.read() if e["type"] == "PREFLIGHT_BLOCKED"] == [["ffmpeg"], ["ffmpeg"]]


def test_offer_checks_warn_when_a_passed_video_has_no_offer_and_pass_when_it_does(tmp_path, monkeypatch):
    from faceless import offer
    monkeypatch.setattr(offer, "unoffered", lambda day=None: ["v1", "v2"])
    got = {c.name: c for c in preflight.checks_offer()}
    assert got["offer:hub"].level == preflight.OK and got["offer:coverage"].level == preflight.WARN and "2 passed" in got["offer:coverage"].detail
    monkeypatch.setattr(offer, "unoffered", lambda day=None: [])
    assert {c.name: c.level for c in preflight.checks_offer()}["offer:coverage"] == preflight.OK
    monkeypatch.setitem(preflight.config.load()["site"], "base_url", "")
    assert {c.name: c.level for c in preflight.checks_offer()}["offer:hub"] == preflight.WARN


def test_the_motion_scene_key_check_only_appears_when_the_lane_is_on(monkeypatch):
    names = lambda: {c.name: c for c in preflight.checks_keys()}               # noqa: E731
    assert "keys:sketch" not in names()
    monkeypatch.setitem(config.load()["production"]["sketch"], "mode", "on")
    assert names()["keys:sketch"].level == preflight.WARN and "keeps its stills" in names()["keys:sketch"].detail
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    assert names()["keys:sketch"].level == preflight.OK
