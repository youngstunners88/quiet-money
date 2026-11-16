"""The instrument panel and the crew's working rules: source tags, limits, key health, claim locks, the heartbeat, Autopilot's gate.
All offline: keys are fake, services are fake sessions, the roster is a crew.toml written into a temp folder."""

import json
import os
import stat
import time
from datetime import datetime, timedelta, timezone

import pytest

from faceless import events, instruments, ledger, missions, team

ROSTER = '''
[autopilot]
enabled = true
max_parallel = 2
max_cost = 1
stale_minutes = 20
dormant_minutes = 45
hold_percent = 90

[agents.opencode]
name = "OpenCode"
kind = "opencode"
jobs = ["bulk", "writing"]
cost = 0
plan = "free"
limit = "unknown"

[agents.hermes]
name = "Hermes"
kind = "hermes"
jobs = ["writing", "research"]
cost = 0
plan = "free"
provider = "openrouter"
key_env = "OPENROUTER_API_KEY"
key_file = "{keyfile}"
limit = 1000
limit_unit = "tokens"
limit_window = "day"
reset = "08:00"
usage = "beats"

[agents.claude]
name = "Claude Code"
kind = "claude"
jobs = ["code", "review", "hard", "writing"]
cost = 2
plan = "subscription"
limit = "unknown"
usage = "beats"

# Agent Zero, when it is installed: uncomment.
# [agents.agent-zero]
# name = "Agent Zero"
# kind = "agent-zero"
# bin = "agent-zero"
# jobs = ["research", "bulk"]
# cost = 0
'''
SECRET = "sk-or-v1-" + "a1b2c3d4" * 8
DOC = {"agents": {"herdr": {"agents": []}}}


class Reply:
    def __init__(self, code, body=None):
        self.status_code, self._body = code, body or {}

    def json(self):
        return self._body


class Session:
    def __init__(self, code=200, body=None):
        self.code, self.body, self.calls = code, body, []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        return Reply(self.code, self.body)


@pytest.fixture
def crew(tmp_path, monkeypatch):
    """A crew.toml in a temp folder, every agent 'installed' as an empty launcher on a temp PATH, Hermes with a key file of its own."""
    bins = tmp_path / "bin"
    bins.mkdir()
    for name in ("opencode", "hermes", "claude"):
        f = bins / name
        f.write_text("#!/bin/sh\n")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    keyfile = tmp_path / "hermes.env"
    keyfile.write_text(f"OPENROUTER_API_KEY={SECRET}\n")
    roster = tmp_path / "crew.toml"
    roster.write_text(ROSTER.format(keyfile=keyfile))
    monkeypatch.setattr(missions, "ROSTER", roster)
    monkeypatch.setattr(missions, "_outside", lambda kind, n: False)
    monkeypatch.setenv("PATH", f"{bins}{os.pathsep}/usr/bin{os.pathsep}/bin")
    monkeypatch.setattr(instruments, "_run", lambda key, args, ttl=30.0: "active")
    return tmp_path


def _rows():
    return {r["id"]: r for r in instruments.crew_state(missions.crew(DOC["agents"]))}


def _old_beat(agent, status, minutes, task="a job"):
    """A beat written `minutes` ago, as if the agent had gone quiet since."""
    t = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    team.BEATS.parent.mkdir(parents=True, exist_ok=True)
    with team.BEATS.open("a") as f:
        f.write(json.dumps({"t": t, "agent": agent, "status": status, "task": task}) + "\n")


def _old_claim(mission, agent, minutes):
    missions.CLAIMS.mkdir(parents=True, exist_ok=True)
    t = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (missions.CLAIMS / f"{mission}.json").write_text(json.dumps({"mission": mission, "agent": agent, "t": t}))


def test_the_roster_is_the_crew_and_nothing_else(crew):
    rows = _rows()
    assert set(rows) == {"opencode", "hermes", "claude", "agent-zero"}
    ghost = rows["agent-zero"]
    assert ghost["lamp"] == "not-installed" and ghost["limit"] is None and ghost["tokensIn"] is None and ghost["key"] is None
    assert all(rows[a]["lamp"] == "idle" for a in ("opencode", "hermes", "claude"))


def test_the_real_crew_file_has_no_codex_and_no_gemini():
    text = (missions.Paths.root / "crew.toml").read_text().lower()
    assert "codex" not in text and "gemini" not in text
    ids = {a["id"] for a in missions.crew(DOC["agents"])}
    assert ids == {"opencode", "hermes", "claude", "agent-zero"}
    by_tag = {tag: [a["id"] for a in missions.crew(DOC["agents"]) if tag in a["jobs"] and not a.get("ghost")] for tag in ("code", "review", "hard")}
    assert by_tag == {"code": ["claude"], "review": ["claude"], "hard": ["claude"]}


def test_a_new_agent_block_comes_alive_with_no_code_change(crew, monkeypatch):
    roster = missions.ROSTER
    assert _rows()["agent-zero"]["lamp"] == "not-installed"
    text = roster.read_text().replace("# [agents.agent-zero]", "[agents.agent-zero]")
    for key in ("name", "kind", "bin", "jobs", "cost"):
        text = text.replace(f"# {key} =", f"{key} =")
    roster.write_text(text)
    assert _rows()["agent-zero"]["lamp"] == "not-installed"            # in the roster, but its launcher is not on this machine yet
    launcher = crew / "bin" / "agent-zero"
    launcher.write_text("#!/bin/sh\n")
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    z = _rows()["agent-zero"]
    assert z["lamp"] == "idle" and z["limit"]["source"] == "unknown" and z["plan"] == "unknown"
    team.beat("agent-zero", "running", "first job", tokens_in=120, tokens_out=30)
    z = _rows()["agent-zero"]
    assert z["lamp"] == "live" and z["task"] == "first job" and (z["tokensIn"], z["tokensOut"]) == (120, 30) and z["usageSource"] == "estimate"
    assert missions.route("research", missions.crew(DOC["agents"]))["id"] in ("agent-zero", "hermes")
    assert instruments.preflight("agent-zero", instruments.build(slow={"missions": {"crew": missions.crew(DOC["agents"]), "todo": [], "running": []}}))[0] == 0


def test_no_estimate_is_called_a_read_and_an_unknown_limit_stays_unknown(crew):
    team.beat("hermes", "running", "writing", tokens_in=300, tokens_out=100)
    team.beat("claude", "running", "review", tokens_in=5000, tokens_out=900)
    rows = _rows()
    h, c = rows["hermes"]["limit"], rows["claude"]["limit"]
    assert h["limit"] == 1000 and h["used"] == 400 and h["pct"] == 40.0 and h["limitSource"] == "read"
    assert h["usedSource"] == "estimate" and h["source"] == "estimate"      # we counted the use, so the reading as a whole is an estimate
    assert h["resetAt"] and h["resetSource"] == "estimate" and h["burnSource"] == "estimate" and h["projectedEmptyAt"]
    assert c["limit"] is None and c["source"] == "unknown" and c["pct"] is None and c["projectedEmptyAt"] is None and "crew.toml" in c["reason"]
    assert c["used"] == 5900 and c["usedSource"] == "estimate"
    snap = instruments.build(slow=None)
    assert snap["core"]["spend"]["source"] == "estimate" and snap["core"]["spend"]["ceilingSource"] == "read"
    assert snap["core"]["queue"]["source"] == "unknown" and snap["core"]["queue"]["ready"] is None      # no overview yet: nothing, not a zero
    assert all(m["source"] == "estimate" for m in snap["ledger"]["models"] + snap["ledger"]["providers"])


def test_ledger_rows_carry_a_time_so_spend_has_a_burn_rate(crew):
    ledger.spend("openrouter", "tokens", 100, usd=0.02, model="x/y", tokens_in=80, tokens_out=20)
    spend = instruments.build(slow=None)["core"]["spend"]
    assert spend["usd"] == 0.02 and spend["burnPerHour"] == 0.02 and spend["burnSource"] == "estimate" and spend["projectedEmptyAt"]


def test_key_health_names_the_state_and_never_the_key(crew, monkeypatch):
    roster = missions.crew(DOC["agents"])
    rows = {r["id"]: r for r in instruments.keyhealth(roster)}
    assert rows["agent-hermes"]["state"] == "present" and rows["openrouter"]["state"] == "missing"       # conftest removed every key from the environment
    bad = Session(401, {"error": {"message": f"No auth credentials found for {SECRET}"}})
    rows = {r["id"]: r for r in instruments.keyhealth(roster, refresh=True, session=bad)}
    assert rows["agent-hermes"]["state"] == "rejected" and rows["agent-hermes"]["usedBy"] == ["hermes"]
    assert any(e["type"] == "CC_KEY" and e["state"] == "rejected" for e in events.read())
    h = _rows()["hermes"]
    assert h["lamp"] == "key-rejected" and "rejected" in h["lampReason"]
    snap = instruments.build(slow=None)
    assert any(y["id"] == "key-agent-hermes" and "Paste a working key" in y["action"] for y in snap["you"])
    for text in (json.dumps(snap), instruments.KEYHEALTH.read_text(), events.JOURNAL.read_text(), instruments.summary(snap)):
        assert SECRET not in text and SECRET[:20] not in text
    good = Session(200, {"data": {"label": "sk-or-v1-abc...", "limit": 5.0, "usage": 1.25, "is_free_tier": True}})
    rows = {r["id"]: r for r in instruments.keyhealth(roster, refresh=True, session=good)}
    assert rows["agent-hermes"]["state"] == "ok" and _rows()["hermes"]["lamp"] == "idle"
    assert "sk-or-v1-abc" not in json.dumps(rows["agent-hermes"])               # the account's own label for the key is not kept either


def test_a_masked_paste_is_a_placeholder_not_a_key(crew, monkeypatch):
    (crew / "hermes.env").write_text("OPENROUTER_API_KEY=***\n")
    rows = {r["id"]: r for r in instruments.keyhealth(missions.crew(DOC["agents"]))}
    assert rows["agent-hermes"]["state"] == "placeholder" and _rows()["hermes"]["lamp"] == "key-rejected"


def test_two_agents_cannot_claim_the_same_mission(crew):
    assert missions.claim("held-review-2026-11-17", "hermes")["agent"] == "hermes"
    with pytest.raises(ValueError, match="held by hermes"):
        missions.claim("held-review-2026-11-17", "opencode")
    assert missions.claim("held-review-2026-11-17", "hermes").get("refreshed")         # the holder asking again is a sign of life, not a clash
    assert missions.claims()["held-review-2026-11-17"]["agent"] == "hermes"
    assert missions.main(["claim", "held-review-2026-11-17", "--agent", "opencode"]) == 1
    with pytest.raises(ValueError):
        missions.release("held-review-2026-11-17", "opencode")
    assert _rows()["hermes"]["lamp"] == "live" and _rows()["hermes"]["claims"][0]["mission"] == "held-review-2026-11-17"
    missions.report("held-review-2026-11-17", "done", "fixed", agent="hermes")
    assert missions.claims() == {} and missions.claim("held-review-2026-11-17", "opencode")["agent"] == "opencode"


def test_a_race_for_one_mission_has_exactly_one_winner(crew):
    from concurrent.futures import ThreadPoolExecutor

    def grab(i):
        try:
            return missions.claim("phone-lane", f"agent-{i}")["agent"]
        except ValueError:
            return None
    with ThreadPoolExecutor(8) as pool:
        won = [w for w in pool.map(grab, range(8)) if w]
    assert len(won) == 1 and missions.claims()["phone-lane"]["agent"] == won[0]


def test_a_silent_agent_goes_amber_then_red_and_its_mission_is_requeued(crew):
    _old_claim("held-review-2026-11-17", "hermes", 25)
    _old_beat("hermes", "running", 25)
    assert _rows()["hermes"]["lamp"] == "stale" and missions.reap() == []
    (missions.CLAIMS / "held-review-2026-11-17.json").unlink()
    team.BEATS.unlink()
    _old_claim("held-review-2026-11-17", "hermes", 50)                 # the 50-minute silence that went unnoticed
    _old_beat("hermes", "running", 50)
    h = _rows()["hermes"]
    assert h["lamp"] == "dormant" and "silent for 50 min" in h["lampReason"]
    assert "hermes" in instruments.fitness(missions.crew(DOC["agents"]))
    back = missions.reap()
    assert back[0]["mission"] == "held-review-2026-11-17" and back[0]["agent"] == "hermes" and missions.claims() == {}
    line = [e for e in events.read() if e.get("event") == "requeue"][0]
    assert line["mission"] == "held-review-2026-11-17" and "silent for 50 min" in line["note"]
    assert any(f["kind"] == "requeue" for f in instruments.build(slow=None)["feed"])
    assert missions.claim("held-review-2026-11-17", "opencode")["agent"] == "opencode"      # and the next agent may take it


def test_a_beating_agent_keeps_its_mission(crew):
    _old_claim("held-review-2026-11-17", "hermes", 50)
    team.beat("hermes", "running", "still on it")
    assert missions.reap() == [] and _rows()["hermes"]["lamp"] == "live"


def _board_with_ask(tag="writing"):
    missions.ask(tag, "tighten three scripts", agent="claude")
    return missions.board(dict(DOC))


def _ask(b):
    return next(m for m in b["todo"] if m["id"].startswith("ask-"))


def test_autopilot_holds_work_from_an_agent_with_a_rejected_key(crew, monkeypatch):
    instruments.keyhealth(missions.crew(DOC["agents"]), refresh=True, session=Session(401))
    monkeypatch.setattr(missions, "candidates", lambda tag, roster: [a for a in roster if a["id"] == "hermes"])
    m = _ask(_board_with_ask())
    assert m["route"]["agent"] is None and "key is not accepted" in m["held"] and m["auto"] is False
    plan = missions.plan_auto({"missions": missions.board(dict(DOC))})
    assert plan["state"] == "idle" and m["id"] in [h["mission"] for h in plan["held"]] and "because" in plan["text"]


def test_autopilot_skips_an_agent_at_its_limit_and_a_dormant_one_and_logs_why(crew):
    team.beat("hermes", "idle", "", tokens_in=900, tokens_out=50)          # 95% of 1000
    _old_claim("old-job", "opencode", 60)
    _old_beat("opencode", "running", 60)
    b = _board_with_ask()
    m = _ask(b)
    reasons = {s["agent"]: s["reason"] for s in m["skipped"]}
    assert "95% of its limit" in reasons["hermes"] and "silent for 60 min" in reasons["opencode"]
    assert m["route"]["agent"] == "claude" and "paid agent" in m["held"]        # the only one left is dearer than max_cost: held for the owner's click
    assert missions.plan_auto({"missions": b})["state"] == "idle"
    logged = missions.log_skips(b)
    assert {e["agent"] for e in logged} == {"hermes", "opencode"} and all(e["event"] == "skip" for e in logged)
    assert missions.log_skips(missions.board(dict(DOC))) == []                  # the same skip is not written again every five minutes
    snap = instruments.build(slow={"missions": missions.board(dict(DOC)), "jobs": None})
    assert snap["held"][0]["mission"] == m["id"] and any(f["kind"] == "skip" for f in snap["feed"])
    assert any(y["id"] == f"send-{m['id']}" for y in snap["you"])


def test_a_healthy_free_agent_still_gets_the_work(crew):
    b = _board_with_ask()
    m = _ask(b)
    assert m["route"]["agent"] in ("hermes", "opencode") and "held" not in m and "skipped" not in m
    assert missions.plan_auto({"missions": b}) == {"state": "run", "mission": m["id"], "text": missions.plan_auto({"missions": b})["text"]}


def test_a_handoff_is_drawn_from_the_asker_to_whoever_would_get_it(crew):
    missions.main(["ask", "code", "the", "retry", "path", "crashes", "--agent", "hermes"])
    h = instruments.handoffs(missions.crew(DOC["agents"]))[0]
    assert (h["from"], h["to"], h["tag"], h["open"]) == ("hermes", "claude", "code", True)
    missions.report(h["mission"], "done", "fixed", agent="claude")
    assert instruments.handoffs(missions.crew(DOC["agents"]))[0]["open"] is False


def test_preflight_tells_an_agent_its_budget_who_has_what_and_who_is_better_placed(crew):
    team.beat("hermes", "idle", "", tokens_in=950)
    missions.claim("daily-2026-11-17", "opencode")
    b = _board_with_ask()
    snap = instruments.build(slow={"missions": b, "jobs": None})
    instruments.save_slow({"missions": b, "generatedAt": snap["generatedAt"]})
    code, text = instruments.preflight("hermes", snap)
    assert code == 1 and "95.0% used" in text and "Do not start new work" in text and "daily-2026-11-17 by opencode" in text
    code, text = instruments.preflight("claude", snap)
    assert code == 0 and "crew claim <mission> --agent claude" in text and "limit unknown" in text
    assert instruments.preflight("codex", snap)[0] == 2


def test_the_dispatch_prompt_tells_every_agent_to_check_the_instrument_first(crew):
    text = missions.prompt_for({"id": "held-review-2026-11-17", "title": "Fix held videos"}, "hermes", "Do it.")
    for needle in ("instruments --for hermes", "agent beat hermes running", "--agent hermes", "crew ask"):
        assert needle in text
    assert "codex" not in text.lower() and "gemini" not in text.lower()


def test_the_snapshot_has_every_part_of_the_contract(crew):
    snap = instruments.build(slow=None, server={"state": "up", "startedAt": "2026-11-17T00:00:00Z"})
    assert {"generatedAt", "system", "you", "core", "crew", "engine", "handoffs", "claims", "held", "keys", "ledger", "feed", "thresholds", "slow"} <= set(snap)
    assert snap["system"]["autopilot"]["state"] == "on" and [r["id"] for r in snap["system"]["clocks"]["resets"]] == ["youtube-quota", "spend-day"]
    for r in snap["crew"]:
        assert {"plan", "lamp", "task", "lastBeatAt", "beatAgeSec", "tokensIn", "tokensOut", "usd", "limit"} <= set(r)
        if r["limit"]:
            assert {"limit", "used", "resetAt", "burnPerHour", "projectedEmptyAt", "source"} <= set(r["limit"]) and r["limit"]["source"] in ("read", "estimate", "unknown")
    text = json.dumps(snap).lower()
    assert "codex" not in text and "gemini cli" not in text


# ---------------------------------------------------------------- the page and its two routes

TOKEN = "t" * 32


def _serve(crew_dir, doc=None):
    import threading

    from faceless import serve
    source = serve.Source(lambda: doc or {"generatedAt": "2026-01-01T00:00:00Z", "day": "2026-01-01", "jobs": None, "missions": None, "alerts": []})
    httpd = serve.make_server("127.0.0.1", 0, TOKEN, build=source.build, panel=serve.Panel(source, background=False))
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def _get(url, headers=None):
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=10) as r:   # noqa: S310 - loopback test server
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_the_page_carries_no_data_no_sample_and_no_write(crew):
    from faceless import hud
    html = hud.render()
    assert "Quiet Money Command Center" in html and "instruments.json" in html and 'href="desk"' in html
    assert "prefers-reduced-motion" in html and "aria-label" in html and "setInterval" in html and ",5000)" in html
    low = html.lower()
    for word in ("codex", "gemini", "method:'post'", "publish", "lorem", "sample", "demo", "mock", "innerhtml"):
        assert word not in low, word
    for area in ('id="you"', 'id="core"', 'id="crew"', 'id="limits"', 'id="feed"'):
        assert area in html
    assert html.index('id="you"') < html.index('id="core"') < html.index('id="crew"') < html.index('id="limits"') < html.index('id="feed"')   # the phone's order


def test_the_server_serves_the_display_the_desk_and_the_snapshot_behind_the_token(crew, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET)
    httpd, base = _serve(crew)
    try:
        for path in ("/", "/desk", "/instruments.json"):
            assert _get(base + path)[0] == 401
        auth = {"Authorization": f"Bearer {TOKEN}"}
        code, page = _get(base + "/", auth)
        assert code == 200 and "COMMAND CENTER" in page and TOKEN not in page and SECRET not in page
        code, desk = _get(base + "/desk", auth)
        assert code == 200 and 'id="nav"' in desk
        code, body = _get(base + "/instruments.json", auth)
        snap = json.loads(body)
        assert code == 200 and snap["system"]["server"]["state"] == "up" and snap["slow"]["state"] == "ok"
        assert {r["id"] for r in snap["crew"]} == {"opencode", "hermes", "claude", "agent-zero"}
        assert SECRET not in body and TOKEN not in body and SECRET[:16] not in body
        assert {k["id"]: k["state"] for k in snap["keys"]}["openrouter"] in ("present", "unknown")     # set; its service cannot be reached from a test
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_same_feed_line_many_times_is_one_line_with_a_count(crew):
    for _ in range(4):
        events.emit("CC_MISSION", actor="autopilot", mission="daily-2026-11-17", event="dispatched", agent="engine")
    f = instruments.feed({"engine": "Engine"})
    assert len(f) == 1 and f[0]["count"] == 4
