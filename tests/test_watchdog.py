"""The watchdog reads only the repo, so every finding can be staged in a temp folder: a late batch, a pause, a spend overrun, slots that never
got a finished video, a corrupted log, broken skills. An empty list means healthy, and a healthy repo must stay silent."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from faceless import events, ledger, policy, safety, skilllint, watchdog
from faceless.config import Paths

NOW = datetime(2026, 10, 8, 13, 0, tzinfo=timezone.utc)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for name in ("reports", "jobs", "state"):
        monkeypatch.setattr(Paths, name, tmp_path / name)
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(skilllint, "lint_all", lambda: {})               # the real skills are linted by their own tests
    monkeypatch.setattr(policy, "stale", lambda: [])
    (Paths.reports / "daily-2026-10-08.md").write_text("# report", encoding="utf-8")
    return tmp_path


def _job(day, slot, status, n=iter(range(1, 10**6))):
    k = next(n)
    (Paths.jobs / f"{day}-{slot}-{k}.json").write_text(json.dumps({"day": day, "slot": slot, "status": status}), encoding="utf-8")


def whats(findings):
    return [f["what"] for f in findings]


def test_a_healthy_repo_has_no_findings(repo):
    assert watchdog.evaluate(NOW) == []
    assert watchdog.summary([]) == "healthy"
    assert "healthy" in watchdog.render_md([], NOW)


def test_no_report_at_all_is_a_warning(repo):
    (Paths.reports / "daily-2026-10-08.md").unlink()
    assert whats(watchdog.evaluate(NOW)) == ["no daily batch yet"]


@pytest.mark.parametrize("hours_after, level", [(10, None), (30, None), (36, "warn"), (60, "critical")])
def test_a_late_batch_warns_and_a_stopped_one_is_critical(repo, hours_after, level):
    now = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc) + timedelta(hours=hours_after)
    found = [f for f in watchdog.evaluate(now) if "daily batch" in f["what"]]
    assert (found[0]["level"] if found else None) == level


def test_a_pause_is_reported_and_old_pauses_escalate(repo):
    safety.pause("owner asked for a break")
    fresh = watchdog.evaluate(datetime.now(timezone.utc))
    assert [f["level"] for f in fresh if f["what"] == "the studio is paused"] == ["info"]
    old = watchdog.evaluate(datetime.now(timezone.utc) + timedelta(hours=48))
    assert [f["level"] for f in old if f["what"] == "the studio is paused"] == ["warn"]
    assert "owner asked for a break" in watchdog.render_md(fresh)


def test_spend_near_and_over_the_ceiling(repo, monkeypatch):
    monkeypatch.setattr(safety, "ceiling", lambda: 3.0)
    ledger.spend("openrouter", "images", 1, usd=2.5)
    assert [f["level"] for f in watchdog.evaluate(NOW) if "ceiling" in f["what"]] == ["warn"]
    ledger.spend("openrouter", "images", 1, usd=0.6)
    assert [f["level"] for f in watchdog.evaluate(NOW) if "ceiling" in f["what"]] == ["critical"]


def test_slots_with_no_finished_video_are_open_but_a_refill_resolves_them(repo):
    _job("2026-10-08", 1, "held")
    assert not [f for f in watchdog.evaluate(NOW) if "slots" in f["what"]]            # one open slot is normal churn
    _job("2026-10-08", 2, "failed")
    assert [f["level"] for f in watchdog.evaluate(NOW) if "slots" in f["what"]] == ["warn"]
    _job("2026-10-08", 2, "packaged")                                                 # slot 2 got its video on a later attempt
    assert not [f for f in watchdog.evaluate(NOW) if "slots" in f["what"]]


def test_four_open_slots_is_critical_and_old_days_are_ignored(repo):
    for slot in range(1, 5):
        _job("2026-10-08", slot, "held")
    assert [f["level"] for f in watchdog.evaluate(NOW) if "slots" in f["what"]] == ["critical"]
    for slot in range(5, 9):
        _job("2026-10-01", slot, "failed")                                            # a week old: history, not an alert
    found = [f for f in watchdog.evaluate(NOW) if "slots" in f["what"]]
    assert "4 slot(s)" in found[0]["detail"]


def test_merge_conflict_markers_in_a_state_log_are_critical(repo):
    (Paths.state / "journal.jsonl").write_text('{"a": 1}\n<<<<<<< HEAD\n{"b": 2}\n=======\n{"c": 3}\n>>>>>>> main\n', encoding="utf-8")
    found = watchdog.evaluate(NOW)
    assert any(f["level"] == "critical" and "journal.jsonl" in f["what"] for f in found)


def test_broken_skills_are_critical_and_a_crashing_check_never_crashes_the_watchdog(repo, monkeypatch):
    monkeypatch.setattr(skilllint, "failures", lambda res: 2)
    assert any(f["level"] == "critical" and f["what"] == "skills are broken" for f in watchdog.evaluate(NOW))
    monkeypatch.setattr(skilllint, "lint_all", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert "the skill check could not run" in whats(watchdog.evaluate(NOW))


def test_findings_are_sorted_worst_first_and_summarised(repo):
    safety.pause("x")
    (Paths.reports / "daily-2026-10-08.md").unlink()
    (Paths.reports / "daily-2026-10-01.md").write_text("old", encoding="utf-8")
    found = watchdog.evaluate(NOW)
    levels = [f["level"] for f in found]
    assert levels == sorted(levels, key={"critical": 0, "warn": 1, "info": 2}.get)
    assert watchdog.summary(found).startswith("critical: ")


def test_failing_decides_the_exit_code_by_level():
    crit, warn, info = ({"level": lv} for lv in ("critical", "warn", "info"))
    assert not watchdog.failing([crit], None)
    assert watchdog.failing([crit], "critical") and watchdog.failing([crit], "warn")
    assert not watchdog.failing([warn], "critical") and watchdog.failing([warn], "warn")
    assert not watchdog.failing([info], "warn") and not watchdog.failing([], "warn")


def test_emit_leaves_a_line_in_the_journal(repo):
    watchdog.emit([{"level": "warn", "what": "x", "detail": "", "action": ""}])
    assert any(e["type"] == "WATCHDOG" and e["status"].startswith("warn") and e["findings"] == 1 for e in events.read())


def test_a_video_shipped_without_an_offer_is_a_warning(repo, monkeypatch):
    from faceless import offer
    monkeypatch.setattr(offer, "unoffered", lambda day=None: ["2026-10-08-s1-math-x"] if day == "2026-10-08" else [])
    found = [f for f in watchdog.evaluate(NOW) if f["what"] == "videos shipped without an offer"]
    assert found and found[0]["level"] == "warn" and "offer --batch" in found[0]["action"]
    monkeypatch.setattr(offer, "unoffered", lambda day=None: [])
    assert not [f for f in watchdog.evaluate(NOW) if "offer" in f["what"]]
