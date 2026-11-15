"""The team board: beats in, one row per agent out; batches counted from real job files; gauges from the ledger. All offline."""

import json
import os
import time

import pytest

from faceless import team


@pytest.fixture
def beats(tmp_path, monkeypatch):
    monkeypatch.setattr(team, "BEATS", tmp_path / "agents" / "beats.jsonl")
    return tmp_path


def _job(d, name, status, ts):
    d.mkdir(parents=True, exist_ok=True)
    hist = [{"from": "planned", "to": "scripted", "ts": ts}] if ts else []
    (d / f"{name}.json").write_text(json.dumps({"id": name, "status": status, "history": hist}))


def test_a_beat_refuses_what_would_mislead_the_board(beats):
    with pytest.raises(ValueError):
        team.beat("hermes", "working")                               # not a status the board knows
    with pytest.raises(ValueError):
        team.beat("hermes", "running", done=-1)
    with pytest.raises(ValueError):
        team.beat("", "running")
    row = team.beat("Hermes", "running", "write  ten\nscripts", done=2, total=10, tokens_in=100, usd=0.0)
    assert row["agent"] == "hermes" and row["task"] == "write ten scripts" and row["total"] == 10


def test_latest_beat_wins_and_tokens_add_up_across_the_day(beats):
    team.beat("hermes", "running", "batch", tokens_in=100, tokens_out=40, usd=0.001, model="free-a")
    team.beat("hermes", "refreshing", "batch", tokens_in=50, tokens_out=10, usd=0.002, model="free-b")
    b = team.board(roster=[{"id": "hermes"}, {"id": "codex", "installed": False}])
    rows = {r["agent"]: r for r in b["agents"]}
    h = rows["hermes"]
    assert h["status"] == "refreshing" and h["tokensIn"] == 150 and h["tokensOut"] == 50 and h["usd"] == 0.003
    assert h["models"] == ["free-a", "free-b"]
    assert rows["codex"]["status"] == "missing" and rows["codex"]["lastBeat"] is None   # roster only: no invented numbers


def test_a_silent_running_agent_shows_stale(beats, monkeypatch):
    team.beat("hermes", "running", "batch")
    later = team._now() + team.timedelta(minutes=team.STALE_MIN + 1)
    monkeypatch.setattr(team, "_now", lambda: later)
    h = team.board()["agents"][0]
    assert h["status"] == "stale" and "min" in h["note"]


def test_a_batch_counts_only_jobs_started_after_it_and_job_changes_keep_it_alive(beats, monkeypatch):
    jobs = beats / "jobs"
    old = jobs / "old.json"
    _job(jobs, "old", "packaged", "2026-01-01T00:00:00Z")
    os.utime(old, (time.time() - 7200, time.time() - 7200))         # before the batch: not counted
    since = team._iso(team._now() - team.timedelta(minutes=30))
    _job(jobs, "a", "packaged", team._iso(team._now() - team.timedelta(minutes=20)))
    _job(jobs, "b", "held", team._iso(team._now() - team.timedelta(minutes=10)))
    _job(jobs, "c", "planned", None)                                 # not started yet: its file time stands in
    team.beat("engine", "running", "10 extra", run="batch-x", total=10, since=since)
    later = team._now() + team.timedelta(minutes=team.STALE_MIN + 5)
    monkeypatch.setattr(team, "_now", lambda: later)
    os.utime(jobs / "c.json", (later.timestamp(), later.timestamp()))   # a job just changed: the batch is alive
    e = team.board(jobs_dir=jobs, day=since[:10])["agents"][0]
    assert e["done"] == 1 and e["total"] == 10
    assert e["batch"]["held"] == 1 and e["batch"]["inProgress"] == 1 and e["status"] == "running"


def test_gauges_read_the_ledger_and_mark_free_and_paid(tmp_path, monkeypatch):
    from faceless import ledger
    led = tmp_path / "ledger.jsonl"
    rows = [{"day": "2026-11-15", "provider": "openrouter", "unit": "tokens", "amount": 1000, "usd": 0.01},
            {"day": "2026-11-15", "provider": "edge", "unit": "chars", "amount": 500, "usd": 0},
            {"day": "2026-11-14", "provider": "openrouter", "unit": "tokens", "amount": 9999, "usd": 9},
            {"day": "2026-11-15", "provider": "openrouter", "unit": "tokens", "amount": 300, "usd": 0, "model": "x/y:free", "tokens_in": 250, "tokens_out": 50},
            {"day": "2026-11-15", "provider": "openrouter", "unit": "tokens", "amount": 100, "usd": 0, "model": "x/y:free", "tokens_in": 80, "tokens_out": 20}]
    led.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(ledger, "LEDGER", led)
    g = team.gauges("2026-11-15")
    by = {p["provider"]: p for p in g["providers"]}
    assert by["openrouter"]["units"]["tokens"] == 1400 and not by["openrouter"]["free"]
    m = g["models"][0]                                                  # rows that name a model also add up per model
    assert m["model"] == "x/y:free" and m["calls"] == 2 and (m["tokensIn"], m["tokensOut"], m["tokens"]) == (330, 70, 400) and m["free"]
    assert by["edge"]["free"] and g["usdToday"] == 0.01                # yesterday is not today


def test_the_ledger_keeps_the_model_and_split_when_given(tmp_path, monkeypatch):
    from faceless import ledger
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "l.jsonl")
    ledger.spend("openrouter", "tokens", 30, usd=0.0, model="a/b:free", tokens_in=20, tokens_out=10)
    ledger.spend("edge", "chars", 5)
    rows = [json.loads(x) for x in (tmp_path / "l.jsonl").read_text().splitlines()]
    assert rows[0]["model"] == "a/b:free" and rows[0]["tokens_in"] == 20 and "model" not in rows[1]


def test_every_board_action_that_moves_reports_on_the_team_board(beats, monkeypatch):
    import subprocess
    from faceless import actions, safety
    monkeypatch.setattr(safety, "paused", lambda: None)
    monkeypatch.setattr(actions.events, "emit", lambda *a, **k: {})
    ok = lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "3 found, 1 worth a message, 1 drafted", "")   # noqa: E731
    actions.run("prospect", {}, runner=ok)
    bad = lambda argv, **kw: subprocess.CompletedProcess(argv, 1, "", "Traceback\nRuntimeError: boom")   # noqa: E731
    monkeypatch.setattr(actions.Paths, "jobs", beats / "jobs")
    _job(beats / "jobs", "2026-11-15-s1-story-x", "held", None)
    actions.run("job_retry", {"job": "2026-11-15-s1-story-x"}, runner=bad)
    rows = [json.loads(x) for x in team.BEATS.read_text().splitlines()]
    assert [(r["agent"], r["status"]) for r in rows] == [("engine-desk", "running"), ("engine-desk", "done"),
                                                        ("engine-render", "running"), ("engine-render", "error")]
    assert "2026-11-15-s1-story-x" in rows[2]["task"] and "boom" in rows[3]["task"]
    by = {r["agent"]: r for r in team.board()["agents"]}
    assert by["engine-render"]["status"] == "error" and by["engine-desk"]["status"] == "done"


def test_a_mission_whose_dispatch_failed_is_blocked_for_the_day(tmp_path, monkeypatch):
    from faceless import events, missions
    j = tmp_path / "journal.jsonl"
    j.write_text(json.dumps({"ts": "2026-11-15T10:31:58Z", "type": "CC_ACTION", "actor": "autopilot", "action": "mission",
                             "args": {"mission": "held-review-2026-11-15", "by": "autopilot"}, "ok": False, "summary": "refused: herdr workspace create"}) + "\n")
    monkeypatch.setattr(events, "JOURNAL", j)
    rows = missions.log()
    assert any(r["mission"] == "held-review-2026-11-15" and r["event"] == "blocked" and r["agent"] == "dispatch" for r in rows)
