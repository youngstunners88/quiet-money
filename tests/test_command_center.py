"""The command center projects real state and is closed to anyone on the network without the token. It changes state only through the
action desk: an allowlisted name that runs one existing command, journals the result and stops for the kill switch.
The DM desk drafts and never sends; money is counted only from receipts."""

import json
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

from faceless import actions, config, dashboard, dmdesk, events, hermes, missions, moneybrief, overview, phone, qr, receipts, safety, serve
from faceless.state import scan_jobs

TOKEN = "-".join(["placeholder"] * 3)          # built, not written out: the hygiene test refuses anything shaped like a real key


@pytest.fixture
def desk(tmp_path, monkeypatch):
    """The DM desk and the receipts on scratch files, so a test never touches the real record."""
    monkeypatch.setattr(dmdesk, "LOG", tmp_path / "outbound.jsonl")
    monkeypatch.setattr(dmdesk, "DRAFTS", tmp_path / "drafts")
    monkeypatch.setattr(dmdesk, "BLOCKLIST", tmp_path / "private" / "blocklist.txt")
    monkeypatch.setattr(receipts, "RECEIPTS", tmp_path / "receipts.jsonl")
    monkeypatch.setattr(receipts, "SALES", tmp_path / "sales.jsonl")
    monkeypatch.setattr(moneybrief, "DIR", tmp_path / "brief")
    monkeypatch.setattr(moneybrief, "RAILS_MD", tmp_path / "INCOME-RAILS.md")
    return tmp_path


# ---------------------------------------------------------------- overview: real numbers, honest gaps

def test_job_counts_match_the_job_files(desk):
    doc = overview.build()
    jobs = [j for j in scan_jobs()[0] if not j.id.startswith("host-")]
    assert doc["jobs"]["total"] == len(jobs)
    assert doc["jobs"]["heldCount"] == sum(1 for j in jobs if j.status == "held") == doc["jobs"]["byStatus"].get("held", 0)
    assert doc["jobs"]["failedCount"] == sum(1 for j in jobs if j.status == "failed")
    assert sum(doc["jobs"]["byStatus"].values()) == len(jobs)
    assert all(row["step"] for row in doc["jobs"]["failed"])


def test_no_receipts_is_zero_with_a_note_and_never_a_target(desk):
    doc = overview.build()
    assert doc["cash"]["revenueMTD"] == 0 and doc["cash"]["receipts"] == 0 and doc["cash"]["note"] == "no receipts yet"
    assert doc["targets"] and all("studio.toml" in t["source"] and isinstance(t["target"], (int, float)) for t in doc["targets"])
    assert not any(w in json.dumps(doc["targets"]).lower() for w in ("revenue", "usd", "$", "followers"))    # only what studio.toml holds
    assert doc["links"]["hub"].startswith("https://") and doc["links"]["hub"].endswith("/links/")


def test_a_missing_dm_log_is_null_not_a_zero(desk):
    assert overview.build()["outbound"] is None
    dmdesk.draft(2)
    ob = overview.build()["outbound"]
    assert ob["drafted"] == 2 and ob["sent"] == 0 and ob["blockedOnOwner"] == 2


def test_every_section_names_its_source_and_every_alert_its_fix(desk):
    doc = overview.build()
    for key in ("jobs", "cash", "offers", "spend", "money"):
        assert doc[key]["source"], key
    assert doc["alerts"] and all(a["fix"] and a["source"] and a["level"] in ("stop", "warn", "info") for a in doc["alerts"])


def test_a_pause_is_the_first_alert(desk, monkeypatch):
    monkeypatch.setattr(safety, "paused", lambda: "owner said stop")
    assert overview.build()["alerts"][0]["level"] == "stop"


def test_building_the_overview_writes_nothing_but_its_own_file(desk, tmp_path, monkeypatch):
    monkeypatch.setattr(overview, "OUT", tmp_path / "overview.json")
    before = sorted(p.name for p in tmp_path.iterdir())
    doc = overview.write()
    assert sorted(set(p.name for p in tmp_path.iterdir()) - set(before)) == ["overview.json"]
    assert json.loads((tmp_path / "overview.json").read_text())["generatedAt"] == doc["generatedAt"]


# ---------------------------------------------------------------- the page

def test_the_page_is_self_contained_small_and_not_indexable(desk, tmp_path):
    r = dashboard.write(overview.build(), out=tmp_path / "cc")
    html = (tmp_path / "cc" / "index.html").read_text()
    assert r["bytes"] <= 150 * 1024
    assert 'name="robots" content="noindex' in html
    for needle in ("https://cdn", "googleapis", "<script src=", "<link rel=\"stylesheet\""):
        assert needle not in html
    assert json.loads((tmp_path / "cc" / "manifest.webmanifest").read_text())["display"] == "standalone"


def test_state_text_cannot_become_markup_on_the_page():
    doc = {"generatedAt": "2026-01-01T00:00:00+00:00", "alerts": [{"level": "warn", "text": "</script><script>alert(1)</script>", "fix": "x", "source": "y"}]}
    html = dashboard.render(doc)
    assert "</script><script>alert(1)" not in html and html.count("</script>") == 2
    assert "innerHTML" not in dashboard.JS


# ---------------------------------------------------------------- the server

@pytest.fixture
def server():
    doc = {"generatedAt": "2026-01-01T00:00:00+00:00", "day": "2026-01-01", "jobs": None, "cash": None, "alerts": [], "source": {}}
    httpd = serve.make_server("127.0.0.1", 0, TOKEN, build=lambda: doc)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _get(url, method="GET", headers=None):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:   # noqa: S310 - loopback test server
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_no_token_or_a_wrong_one_is_401_for_the_page_and_the_data(server):
    for path in ("/", "/overview.json", "/?t=wrong-wrong-wrong-wrong", "/index.html"):
        code, _, body = _get(server + path)
        assert code == 401 and b"generatedAt" not in body


def test_the_right_token_opens_the_page_by_query_and_the_data_by_header(server):
    code, head, body = _get(f"{server}/?t={TOKEN}")
    assert code == 200 and b"Quiet Money Command Center" in body and TOKEN.encode() not in body
    code, _, body = _get(server + "/overview.json", headers={"Authorization": f"Bearer {TOKEN}"})
    assert code == 200 and json.loads(body)["day"] == "2026-01-01"


def test_replies_are_never_cached_never_indexed_and_set_no_cookie(server):
    for path in (f"/?t={TOKEN}", "/", "/healthz", "/manifest.webmanifest"):
        _, head, _ = _get(server + path)
        assert head["Cache-Control"] == "no-store" and "noindex" in head["X-Robots-Tag"]
        assert "Set-Cookie" not in head
        assert TOKEN not in json.dumps(head)


def test_the_model_catalog_is_gated_and_read_only(server):
    assert _get(server + "/models.json")[0] == 401
    code, head, body = _get(server + "/models.json", headers={"Authorization": f"Bearer {TOKEN}"})
    assert code == 200 and "application/json" in head.get("Content-Type", "")
    doc = json.loads(body)
    assert doc["totalProviders"] >= 1 and doc["totalModels"] >= 1
    assert all(p["id"] and p["name"] and "models" in p for p in doc["providers"][:5])


def test_the_server_is_read_only_outside_the_action_door(server):
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        assert _get(f"{server}/?t={TOKEN}", method=method)[0] == 405
    for method in ("PUT", "DELETE", "PATCH"):
        assert _get(f"{server}/action", method=method, headers={"Authorization": f"Bearer {TOKEN}"})[0] == 405
    assert _get(server + "/../studio.toml")[0] in (401, 404) and _get(server + "/state/ledger.jsonl")[0] == 404


def test_a_run_of_wrong_tokens_is_locked_out_then_let_back_in():
    clock = [0.0]
    lim = serve.Limiter(per_minute=100, bad_per_minute=3, clock=lambda: clock[0])
    for _ in range(3):
        assert lim.allow("10.0.0.9")
        lim.wrong("10.0.0.9")
    assert not lim.allow("10.0.0.9") and lim.allow("10.0.0.7")
    clock[0] = 61.0
    assert lim.allow("10.0.0.9")


def test_it_will_not_start_without_a_real_token():
    for bad in ("", "short"):
        with pytest.raises(ValueError):
            serve.make_server("127.0.0.1", 0, bad)


def test_the_token_is_made_once_saved_owner_only_and_never_returned(tmp_path):
    env = tmp_path / "cfg" / "env"
    said = serve.init_token(env)
    value = env.read_text().strip().split("=", 1)[1]
    assert len(value) >= serve.MIN_TOKEN and value not in said and oct(env.stat().st_mode)[-3:] == "600"
    assert "already" in serve.init_token(env) and env.read_text().count(serve.TOKEN_NAME) == 1


def test_the_qr_code_has_the_right_shape_and_reads_back():
    import cv2
    import numpy as np
    text = "http://192.168.1.23:8787/?t=" + TOKEN
    m = qr.matrix(text)
    assert len(m) == len(m[0]) and (len(m) - 17) % 4 == 0
    img = np.kron((1 - np.pad(np.array(m, dtype=np.uint8), 4)) * 255, np.ones((8, 8))).astype(np.uint8)
    assert cv2.QRCodeDetector().detectAndDecode(img)[0] == text
    assert qr.matrix("x" * 500) is None and qr.terminal("x" * 500) is None


# ---------------------------------------------------------------- the DM desk

def test_drafts_are_short_link_free_one_question_and_built_on_a_real_video(desk):
    r = dmdesk.draft(10)
    assert len(r["drafts"]) == 10 and len({d["video"] for d in r["drafts"]}) == 10
    for d in r["drafts"]:
        assert not dmdesk.lint(d)
        for key in ("first", "follow_up_2", "follow_up_3"):
            assert len(d[key]) <= dmdesk.MAX_CHARS and "http" not in d[key]
        assert d["first"].count("?") == 1 and d["title"] in d["first"]
        assert (config.Paths.final / f"{d['video']}.json").exists()
        assert d["open_slots"] == ["first name", "their words"] and len(d["first"]) <= dmdesk.MAX_CHARS - dmdesk.SLOT_ROOM
    assert (desk / "drafts" / f"{r['day']}.md").exists()
    assert dmdesk.draft(10)["already"] and dmdesk.funnel()["drafted"] == 10        # a second run does not spend the day's cap


def test_the_only_links_are_the_hub_and_live_listings(desk):
    d = dmdesk.draft(3)["drafts"][0]
    assert "/links/" in d["after_reply_free"]
    bad = {**d, "after_reply_free": "Here: https://example.com/buy"}
    assert any("not the hub or a live listing" in p for p in dmdesk.lint(bad))
    assert any("carries a link" in p for p in dmdesk.lint({**d, "first": d["first"] + " see bit.ly/x"}))
    assert any("generic" in p for p in dmdesk.lint({**d, "follow_up_2": "quick question for you"}))
    assert dmdesk.lint({**d, "first": d["first"][:-1] + ", and you will make $500 a week?"})


def test_a_paused_studio_drafts_nothing(desk, monkeypatch):
    monkeypatch.setattr(safety, "paused", lambda: "owner said stop")
    with pytest.raises(dmdesk.DeskRefused):
        dmdesk.draft(5)
    assert not dmdesk.LOG.exists()


def test_the_daily_cap_holds(desk):
    people = desk / "p.csv"
    people.write_text("handle,name,context,last interaction,segment\n" + "".join(f"@person{i},P{i},the subscription math,comment,asked\n" for i in range(30)))
    r = dmdesk.draft(30, people)
    assert len(r["drafts"]) == dmdesk.MAX_PER_DAY and r["skipped"]
    with pytest.raises(dmdesk.DeskRefused):
        dmdesk.draft(1, people)


def test_one_message_per_person_no_duplicates_and_the_block_list(desk):
    (desk / "private").mkdir()
    (desk / "private" / "blocklist.txt").write_text("@Blocked\n")
    people = desk / "p.csv"
    people.write_text("handle,name,context,last interaction,segment\n@ana,Ana,asked about the $5 a day habit,comment,asked\n@ANA,Ana,again,comment,asked\n@blocked,B,hi,comment,shared\n")
    r = dmdesk.draft(10, people)
    assert [d["handle"] for d in r["drafts"]] == ["@ana"] and "Ana, you asked" in r["drafts"][0]["first"]
    assert sorted(s["why"] for s in r["skipped"]) == ["already in this batch", "on the block list"]
    again = dmdesk.draft(10, people)                                              # the next run, same day: she was just written to
    assert not again["drafts"] and any("last 3 days" in s["why"] for s in again["skipped"])


def test_handles_never_reach_the_committed_log_and_prospect_drafts_go_to_a_private_file(desk):
    people = desk / "p.csv"
    people.write_text("@realperson,Sam,the inflation one,comment,disagreed\n")
    r = dmdesk.draft(5, people)
    assert r["path"].endswith(".private.md") and (desk / "drafts" / f"{r['day']}.private.md").exists()
    assert "realperson" not in dmdesk.LOG.read_text() and dmdesk.handle_key("@RealPerson") in dmdesk.LOG.read_text()
    with pytest.raises(ValueError):
        dmdesk.log(r["drafts"][0]["id"], "sent", notes="wrote to @realperson")


def test_the_owners_log_moves_the_funnel_and_brings_up_follow_ups(desk):
    ids = [d["id"] for d in dmdesk.draft(3)["drafts"]]
    dmdesk.log(ids[0], "sent", handle="@a")
    dmdesk.log(ids[1], "sent", handle="@b")
    dmdesk.log(ids[1], "replied")
    dmdesk.log(ids[1], "bought")
    f = dmdesk.funnel()
    assert (f["drafted"], f["sent"], f["replied"], f["bought"], f["blockedOnOwner"]) == (3, 2, 1, 1, 1)
    later = (config.today_utc().replace(year=config.today_utc().year + 1)).isoformat()
    assert [x["draft_id"] for x in dmdesk.follow_ups(later)] == [ids[0]] and dmdesk.follow_ups() == []
    with pytest.raises(ValueError):
        dmdesk.log("dm-nope", "sent")
    assert dmdesk.weekly()["reply_rate"] is None                                    # two sends are not a rate


# ---------------------------------------------------------------- receipts and the brief

def test_only_a_receipt_is_revenue(desk):
    assert receipts.summary()["note"] == "no receipts yet"
    day = config.today_utc().isoformat()
    row = receipts.add("gumroad", 17, product="daily-quiet-money-planner", ref="order-1", day=day)
    assert row["fee_estimated"] and 0 < row["net"] < 17
    receipts.add("fiverr", 40, fee=8, ref="FO1", day=day)
    s = receipts.summary(day)
    assert s["revenueMTD"] == 57 and s["receipts"] == 2 and s["byRail"]["fiverr"]["net"] == 32 and s["note"] == ""
    (desk / "sales.jsonl").write_text(json.dumps({"id": "order-1", "at": day, "usd": 17}) + "\n" + json.dumps({"id": "order-2", "at": day, "usd": 9}) + "\n")
    assert receipts.summary(day)["receipts"] == 3                                   # the pulled sale typed in by hand counts once
    for bad in (lambda: receipts.add("gumroad", 0), lambda: receipts.add("tips", 5), lambda: receipts.add("gumroad", 9, note="from buyer@example.com"),
                lambda: receipts.add("gumroad", 17, ref="order-1")):
        with pytest.raises(ValueError):
            bad()


# ---------------------------------------------------------------- Hermes: status only, never content

def test_hermes_is_absent_not_zero_when_not_installed(tmp_path):
    assert hermes.build(tmp_path / "nothing-here", run=lambda *a, **k: "x") is None


def test_hermes_reads_version_gateway_and_session_labels_but_never_message_content(tmp_path):
    home = tmp_path / "hermes"
    home.mkdir()
    con = sqlite3.connect(home / "state.db")
    con.execute("create table sessions (id text, display_name text, source text, model text, started_at text, ended_at text, message_count int)")
    con.execute("create table messages (id integer, session_id text, content text)")
    con.execute("insert into sessions values ('s2', 'money work', 'desktop', 'm-1', '2026-11-13T10:00:00Z', null, 4)")
    con.execute("insert into sessions values ('s1', '', 'cli', 'm-2', '2026-11-12T09:00:00Z', '2026-11-12T09:30:00Z', 2)")
    con.execute("insert into messages values (1, 's2', 'a private buyer message')")
    con.commit()
    con.close()

    def fake_run(args, timeout=8.0):
        assert args[:2] == ["hermes", "--version"] or args[:3] == ["hermes", "gateway", "status"]
        return ("Hermes Agent v9.9.9+1.gabc (2026.1.1) · stable\nUpdate available — run 'hermes update'"
                if args[1] == "--version" else "✗ Gateway is not running")

    doc = hermes.build(home, run=fake_run)
    assert doc["installed"] and doc["version"] == "v9.9.9+1.gabc" and doc["release"] == "2026.1.1"
    assert doc["channel"] == "stable" and doc["updateAvailable"] is True
    assert doc["gateway"] == {"running": False, "state": "not running"}
    assert [s["id"] for s in doc["sessions"]] == ["s2", "s1"]
    assert doc["sessions"][0]["name"] == "money work" and doc["sessions"][0]["endedAt"] is None and doc["sessions"][1]["name"] is None
    assert "a private buyer message" not in json.dumps(doc)


def test_the_brief_has_three_short_actions_real_changes_and_no_forecast(desk):
    dmdesk.draft(10)
    b = moneybrief.write()
    text = (desk / "brief" / f"{b['day']}.md").read_text()
    assert 1 <= len(b["actions"]) <= 3 and all(a["minutes"] <= moneybrief.MAX_MINUTES and a["source"] for a in b["actions"])
    assert "no receipts yet" in text and "Since yesterday" in text and "could not be done" in text
    rails = (desk / "INCOME-RAILS.md").read_text()
    assert rails.count("\n| ") >= 7 and "unknown" in rails
    for word in ("projected", "expected revenue", "will earn", "potential"):
        assert word not in text.lower() and word not in rails.lower().replace("'potential'", "")


# ---------------------------------------------------------------- the action desk: clicks that run real commands

@pytest.fixture
def journal(tmp_path, monkeypatch):
    """The journal on a scratch file, so a test click never lands in the studio's real log."""
    monkeypatch.setattr(events, "JOURNAL", tmp_path / "journal.jsonl")
    monkeypatch.setattr(safety, "paused", lambda: None)
    return tmp_path / "journal.jsonl"


def _runner(code=0, out="", err="", calls=None):
    def run(argv, **kw):
        if calls is not None:
            calls.append((argv, kw))
        return subprocess.CompletedProcess(argv, code, out, err)
    return run


def test_advance_phone_runs_phone_next_push_and_returns_a_structured_result(journal):
    calls = []
    out = json.dumps({"job": {"id": "2026-01-01-tiktok-a", "kind": "tiktok"}, "local_files": ["/x/final.mp4"], "on_phone": ["/sdcard/Download/QuietMoney/final.mp4"]})
    r = actions.run("phone_next", runner=_runner(0, out, calls=calls))
    argv, kw = calls[0]
    assert argv == [sys.executable, "-m", "faceless", "phone", "next", "--push"] and kw["timeout"] and kw.get("shell") is None
    assert r["ok"] is True and r["exit"] == 0 and r["state"] == "done" and r["job"] == "2026-01-01-tiktok-a" and "on the phone" in r["summary"]
    lines = [json.loads(x) for x in journal.read_text().splitlines()]
    assert len(lines) == 1 and lines[0]["type"] == "CC_ACTION" and lines[0]["job"] == "2026-01-01-tiktok-a" and "stdout" not in lines[0]
    assert actions.recent(5)[0]["id"] == r["id"] and actions.recent(5)[0]["ok"] is True


def test_a_failed_action_is_never_silent(journal):
    r = actions.run("phone_next", runner=_runner(1, "", "RuntimeError: adb push failed: no devices/emulators found"))
    assert r["ok"] is False and r["exit"] == 1 and "no devices" in r["error"] and "no devices" in r["summary"]
    assert actions.recent(5)[0]["ok"] is False and actions.recent(5)[0]["exit"] == 1 and "no devices" in actions.recent(5)[0]["error"]

    def slow(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw["timeout"])
    t = actions.run("phone_next", runner=slow)
    assert t["ok"] is False and t["exit"] is None and "timed out" in t["error"]


def test_only_allowlisted_actions_with_plain_ids_ever_reach_a_command(journal):
    calls = []
    for name, args in (("rm", {}), ("job_retry", {"job": "--force"}), ("job_retry", {"job": "../../etc/passwd"}), ("job_retry", {"job": "no-such-job-anywhere"}),
                       ("dm_log", {"draft": "dm-1", "status": "paid"}), ("dm_log", {"draft": "dm-1", "status": "sent", "handle": "a b; rm"}),
                       ("herdr_focus", {"target": "w1; herdr server stop"}), ("outbound_outcome", {"slug": "x y", "event": "sent"})):
        r = actions.run(name, args, runner=_runner(calls=calls))
        assert r["ok"] is False and r["refused"] and r["exit"] is None, name
    assert calls == []
    assert actions.run("herdr_focus", {"target": "w2:p1"}, runner=_runner(calls=calls))["ok"] and calls[-1][0] == ["herdr", "agent", "focus", "w2:p1"]
    assert actions.run("herdr_focus", {"target": "w2"}, runner=_runner(calls=calls))["ok"] and calls[-1][0] == ["herdr", "workspace", "focus", "w2"]
    r = actions.run("dm_log", {"draft": "dm-1", "status": "sent", "handle": "some.person"}, runner=_runner(0, "{}", calls=calls))
    assert calls[-1][0][-4:] == ["dm-1", "sent", "--handle", "@some.person"] and "handle" not in r["args"]
    assert "some.person" not in journal.read_text()                                    # a handle is a person: never in the committed journal


def test_the_kill_switch_refuses_everything_that_moves_the_pipeline(journal, monkeypatch):
    monkeypatch.setattr(safety, "paused", lambda: "owner said stop")
    calls = []
    for name in (n for n, spec in actions.ACTIONS.items() if spec["moves"]):
        r = actions.run(name, {"job": "x"}, runner=_runner(calls=calls))
        assert r["ok"] is False and r["refused"], name
    assert calls == [] and "paused" in actions.run("phone_next", runner=_runner(calls=calls))["refused"]
    assert actions.plan_tick()["state"] == "paused"
    assert {"phone_next", "phone_requeue", "job_retry", "daily"} <= {n for n, spec in actions.ACTIONS.items() if spec["moves"]}


def test_non_stop_advances_when_a_job_closes_waits_while_one_is_staged_and_trips_after_two_failures(journal, monkeypatch):
    queue = [{"id": "2026-01-01-tiktok-a", "kind": "tiktok", "day": "2026-01-01", "status": "queued"}]
    monkeypatch.setattr(phone, "next_job", lambda day=None: queue[0] if queue else None)
    monkeypatch.setattr(phone, "jobs", lambda day=None: list(queue))
    gone = []
    monkeypatch.setattr(phone, "media_missing", lambda job, on_branch=None: list(gone))
    first = actions.plan_tick(history=[])
    assert first["state"] == "run" and first.get("do") is None
    gone.append("final.mp4")                                                           # the head of the queue lost its video: hold it, do not fail for ever
    assert actions.plan_tick(history=[])["do"] == "phone_park"
    gone.clear()
    pushed = {"action": "phone_next", "ok": True, "job": "2026-01-01-tiktok-a", "at": events.now_iso()}
    assert actions.plan_tick(history=[pushed])["state"] == "waiting"                    # the same job is never pushed twice
    queue[0] = {**queue[0], "id": "2026-01-01-tiktok-b"}                               # the driver closed it: the next one goes at once
    assert actions.plan_tick(history=[pushed])["state"] == "run"
    failed = {"action": "phone_next", "ok": False, "at": events.now_iso(), "summary": "adb push failed"}
    assert actions.plan_tick(history=[failed, pushed])["state"] == "run"
    assert actions.plan_tick(history=[failed, failed, pushed])["state"] == "tripped"
    old = {**failed, "at": "2026-01-01T00:00:00Z"}
    assert actions.plan_tick(history=[old, old, pushed])["state"] == "run"              # the breaker closes again after its half hour
    queue.clear()
    assert actions.plan_tick(history=[])["state"] == "idle"


def test_the_desk_runs_one_action_per_lane_answers_fast_and_tells_the_page_when_it_ends(journal):
    gate, done = threading.Event(), []

    def slow(name, args=None, *, actor="owner", rid=None, **kw):
        gate.wait(5)
        return {"id": rid, "action": name, "label": name, "state": "done", "ok": True, "exit": 0, "summary": "ok", "actor": actor}
    desk = actions.Desk(run_action=slow, plan=lambda: {"state": "run", "text": "go"}, on_done=done.append, wait=0.05)
    first = desk.start("phone_next", {})
    assert first["state"] == "running" and desk.snapshot()["running"][0]["id"] == first["id"]
    second = desk.start("phone_requeue", {"job": "x"})
    assert second["ok"] is False and second["busy"] and "busy" in second["refused"]
    assert desk.tick()["state"] == "busy"
    gate.set()
    for _ in range(100):
        if done:
            break
        time.sleep(0.02)
    assert done and done[0]["id"] == first["id"] and desk.snapshot()["running"] == []
    ticked = desk.tick()
    assert ticked["state"] == "run" and ticked["result"]["action"] == "phone_next" and ticked["result"]["actor"] == "non-stop"


class _FakeDesk:
    def __init__(self):
        self.calls = []

    def start(self, name, args=None, **kw):
        self.calls.append((name, args))
        return {"id": "abcd1234", "action": name, "state": "done", "ok": True, "exit": 0, "summary": "ran"}

    def tick(self):
        self.calls.append(("nonstop_tick", {}))
        return {"state": "idle", "text": "The phone queue is empty."}

    def plan(self):
        return {"state": "idle", "text": "The phone queue is empty."}

    def snapshot(self):
        return {"generatedAt": "2026-01-01T00:00:00+00:00", "paused": None, "running": [], "recent": []}


@pytest.fixture
def acting():
    desk = _FakeDesk()
    doc = {"generatedAt": "2026-01-01T00:00:00+00:00", "day": "2026-01-01", "jobs": None, "cash": None, "alerts": [], "source": {}}
    httpd = serve.make_server("127.0.0.1", 0, TOKEN, build=lambda: doc, desk=desk)
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", desk
    httpd.shutdown()
    httpd.server_close()


def _post(url, body, headers=None):
    req = urllib.request.Request(url, method="POST", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:   # noqa: S310 - loopback test server
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_the_action_door_needs_the_header_token_json_and_the_same_origin(acting):
    url, desk = acting
    auth = {"Authorization": f"Bearer {TOKEN}"}
    assert _post(f"{url}/action", {"name": "phone_next"})[0] == 401
    assert _post(f"{url}/action?t={TOKEN}", {"name": "phone_next"})[0] == 401             # the query token opens the page, never a button
    assert _post(f"{url}/action", {"name": "phone_next"}, {**auth, "Origin": "http://evil.example"})[0] == 403
    assert _post(f"{url}/action", {"name": "phone_next"}, {**auth, "Content-Type": "text/plain"})[0] == 400
    assert _post(f"{url}/action", {"args": {}}, auth)[0] == 400
    assert desk.calls == []
    code, body = _post(f"{url}/action", {"name": "phone_next", "args": {}}, auth)
    assert code == 200 and body["ok"] is True and body["state"] == "done" and body["exit"] == 0 and desk.calls == [("phone_next", {})]
    code, body = _post(f"{url}/action", {"name": "nonstop_tick"}, auth)
    assert code == 200 and body["state"] == "idle" and desk.calls[-1][0] == "nonstop_tick"


def test_activity_and_job_steps_are_gated_reads(acting):
    url, _ = acting
    assert _get(url + "/actions.json")[0] == 401 and _get(url + "/job.json?id=x")[0] == 401
    code, _, body = _get(url + "/actions.json", headers={"Authorization": f"Bearer {TOKEN}"})
    doc = json.loads(body)
    assert code == 200 and doc["running"] == [] and doc["nonstop"]["state"] == "idle" and any(a["name"] == "phone_next" for a in doc["actions"])
    assert _get(url + "/job.json?id=no-such-job-anywhere", headers={"Authorization": f"Bearer {TOKEN}"})[0] == 404
    assert _get(url + "/job.json?id=../studio.toml", headers={"Authorization": f"Bearer {TOKEN}"})[0] == 404


def test_a_held_phone_job_is_released_only_when_its_gate_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr(phone, "home", lambda: tmp_path / "phone")
    monkeypatch.setattr(safety, "paused", lambda: None)
    caps = {"yt_community": 5, "yt_short": 5, "tiktok": 5, "flow_image": 30, "fiverr_inbox": 3, "fiverr_reply": 10}
    switches = {"enabled": True, "post_community": True, "post_youtube": False, "post_tiktok": True, "branch": "b", "caps": caps}
    monkeypatch.setattr(phone, "cfg", lambda: switches)
    for kind in ("tiktok", "yt_short"):
        phone.save({"id": f"2026-01-01-{kind}-a", "kind": kind, "day": "2026-01-01", "key": "a", "status": "held", "title": "T", "text": "words",
                    "media": [{"source": "x.mp4", "name": "x.mp4"}], "history": [{"at": "t", "result": "failed", "note": "n"}] * 2})
    stuck = phone.requeue("2026-01-01-yt_short-a")
    assert stuck["runs"] is False and "post_youtube is off" in stuck["why"] and phone.load("2026-01-01-yt_short-a")["status"] == "held"
    freed = phone.requeue("2026-01-01-tiktok-a")
    assert freed["runs"] is True and phone.load("2026-01-01-tiktok-a")["status"] == "queued"
    assert phone.load("2026-01-01-tiktok-a")["history"][-1]["result"] == "requeued"
    with pytest.raises(ValueError):
        phone.requeue("2026-01-01-tiktok-a")


def test_jobs_whose_media_is_gone_are_parked_with_the_reason_and_the_rest_stay(tmp_path, monkeypatch):
    monkeypatch.setattr(phone, "home", lambda: tmp_path / "phone")
    monkeypatch.setattr(phone.Paths, "root", tmp_path)
    monkeypatch.setattr(safety, "paused", lambda: None)
    caps = {"yt_community": 5, "yt_short": 5, "tiktok": 5, "flow_image": 30, "fiverr_inbox": 3, "fiverr_reply": 10}
    monkeypatch.setattr(phone, "cfg", lambda: {"enabled": True, "post_community": True, "post_youtube": False, "post_tiktok": True, "branch": "b", "caps": caps})
    for key in ("old", "new"):
        phone.save({"id": f"2026-01-01-tiktok-{key}", "kind": "tiktok", "day": "2026-01-01", "key": key, "status": "queued", "text": "words",
                    "media": [{"source": f"production/{key}.mp4", "name": "final.mp4"}]})
    phone.save({"id": "2026-01-01-fiverr_inbox-x", "kind": "fiverr_inbox", "day": "2026-01-01", "key": "x", "status": "queued"})
    monkeypatch.setattr(phone, "_branch_files", lambda: {"out/2026-01-01/2026-01-01-tiktok-new/final.mp4"})
    assert phone.media_missing(phone.load("2026-01-01-tiktok-old")) == ["final.mp4"] and phone.media_missing(phone.load("2026-01-01-tiktok-new")) == []
    r = phone.park_missing(refresh=False)
    assert r["held"] == ["2026-01-01-tiktok-old"] and r["next"] == "2026-01-01-tiktok-new"
    assert phone.load("2026-01-01-tiktok-old")["status"] == "held" and "media gone" in phone.receipts()[-1]["note"]
    assert phone.load("2026-01-01-fiverr_inbox-x")["status"] == "queued"                # a job with no media is never parked
    monkeypatch.setattr(phone, "_branch_files", lambda: None)                           # branch unreadable: nothing is parked on a guess
    assert phone.media_missing(phone.load("2026-01-01-tiktok-new")) == []
    with pytest.raises(RuntimeError):
        phone.park_missing(refresh=False)


def test_alerts_follow_the_owners_order_and_carry_their_button(desk, monkeypatch):
    doc = overview.build()
    doc["jobs"].update(ranToday=False, failedCount=3, failedLast7=1, heldCount=9, heldLast7=2,
                       failed=[{"step": "planned", "why": "all llm providers failed"}] * 3)
    doc["outbound"] = {"blockedOnOwner": 4, "followUpsDue": 0}
    doc["hermes"] = {"installed": True, "messaging": ["telegram"], "gateway": {"running": False}}
    doc["spend"]["paused"] = None
    texts = [a["text"] for a in overview.alerts(doc)]
    order = [next(i for i, t in enumerate(texts) if needle in t) for needle in ("Nothing ran today", "failed job", "held for review", "wait for you to send", "Hermes gateway is down")]
    assert order == sorted(order) and order[0] == 0
    by = {a["text"]: a for a in overview.alerts(doc)}
    assert by[texts[order[0]]]["action"]["name"] == "daily" and "planned" in texts[order[1]] and by[texts[order[4]]]["fix"] == "hermes gateway run"
    doc["hermes"]["messaging"] = []
    assert not any("Hermes" in a["text"] for a in overview.alerts(doc))                  # no messaging set up: a quiet gateway is not an alert
    assert all(a["action"]["name"] in actions.ACTIONS for a in overview.alerts(doc) if a.get("action"))


def test_every_control_on_the_page_is_wired(desk):
    js = dashboard.JS
    assert "k==='on')e.addEventListener('click'" in js                                  # the click shorthand every tab and button uses
    for name in ("phone_next", "phone_park", "phone_requeue", "job_retry", "daily", "dm_log", "dm_draft", "money_brief", "herdr_focus", "nonstop_tick"):
        assert f"'{name}'" in js, name
    from faceless import hud
    for name in (n for n in actions.ACTIONS if n != "outbound_outcome"):
        assert f"'{name}'" in js or f"{name}:1" in hud.JS, name                         # wired on the desk, or on the head-up display's YOU strip
    assert "LS.get('qm_ns')==='1'" in js                                                # Non-stop is off until the owner turns it on
    assert "typing()" in js and "Display only" in js
    assert "'mission'" in js and "'autopilot_tick'" in js and "LS.get('qm_ap')==='1'" in js       # Autopilot is off until the owner turns it on


# ---------------------------------------------------------------- mission control: one board for every agent

def _crew(**status):
    base = {"opencode": (0, ["bulk", "phone", "writing"]), "hermes": (0, ["writing", "research"]), "claude": (2, ["code", "writing", "phone"])}
    return [{"id": k, "name": k.title(), "kind": k, "jobs": jobs, "cost": cost, "costLabel": missions.COST[cost], "installed": status.get(k, "asleep") != "missing",
             "panes": [], "status": status.get(k, "asleep")} for k, (cost, jobs) in base.items()]


def test_work_goes_to_the_cheapest_installed_agent_that_lists_the_job():
    assert missions.route("writing", _crew())["id"] in ("hermes", "opencode")            # free before paid
    assert missions.route("writing", _crew(hermes="idle"))["id"] == "hermes"             # among equals, the one already awake
    assert missions.route("code", _crew())["id"] == "claude"                             # paid only when nothing cheaper lists it
    assert missions.route("writing", _crew(opencode="missing", hermes="missing"))["id"] == "claude"
    assert missions.route("video-editing", _crew()) is None


def test_the_board_is_derived_from_real_state_and_owner_work_is_never_dispatched(desk, journal, monkeypatch):
    monkeypatch.setattr(missions, "crew", lambda agents_doc=None: _crew(hermes="idle"))
    doc = overview.build()
    doc["jobs"].update(ranToday=False, passedToday=0, failed=[], held=[{"id": "2099-01-01-s1-x", "day": "2099-01-01", "title": "T", "step": "packaged"}])
    doc["outbound"] = {"blockedOnOwner": 3, "followUpsDue": 0}
    doc["phone"] = None
    b = missions.board(doc)
    kinds = {m["id"].split("-")[0]: m for m in b["todo"]}
    assert kinds["send"]["route"]["agent"] == "owner" and kinds["daily"]["route"] == {**kinds["daily"]["route"], "agent": "engine", "cost": "0 tokens"}
    assert kinds["held"]["route"]["agent"] == "hermes" and all("brief" not in m for m in b["todo"])
    monkeypatch.setattr(overview, "build", lambda today=None: doc)
    with pytest.raises(RuntimeError, match="yours"):
        missions.dispatch(kinds["send"]["id"])
    doc["missions"] = b
    plan = missions.plan_auto(doc)
    assert plan["state"] == "run" and plan["mission"].startswith("daily-")                # zero-token engine work first, never the owner's
    monkeypatch.setattr(safety, "paused", lambda: "owner said stop")
    assert missions.plan_auto(doc)["state"] == "paused"
    with pytest.raises(RuntimeError, match="paused"):
        missions.dispatch(kinds["daily"]["id"])


def test_agents_hand_work_to_each_other_through_the_board_and_a_silent_agent_sits_out(desk, journal, monkeypatch):
    roster = _crew(hermes="idle")
    roster[1]["panes"] = [{"pane": "w2:p1", "status": "idle"}]
    monkeypatch.setattr(missions, "crew", lambda agents_doc=None: [dict(a) for a in roster])
    doc = {"day": "2026-01-01", "jobs": None, "phone": None, "outbound": None, "offers": None, "agents": {}}
    asked = missions.ask("research", "find three sources on index funds", agent="opencode")
    b = missions.board(doc)
    m = next(x for x in b["todo"] if x["id"] == asked["mission"])
    assert m["route"]["agent"] == "hermes" and m["kind"] == "agent"
    events.emit(missions.EVENT, mission=m["id"], event="dispatched", agent="hermes", pane="w2:p1")
    assert [x["id"] for x in missions.board(doc)["running"]] == [m["id"]]
    monkeypatch.setattr(missions, "_minutes", lambda iso: 10.0)                          # ten minutes on: Hermes is idle and never reported
    b = missions.board(doc)
    again = next(x for x in b["todo"] if x["id"] == m["id"])
    assert again["route"]["agent"] is None and "went idle without a report" in again["note"]      # nobody else lists research here
    assert next(a for a in b["crew"] if a["id"] == "hermes")["status"] == "no answer"
    missions.report(m["id"], "done", "three sources filed", agent="hermes")
    b = missions.board(doc)
    assert not any(x["id"] == m["id"] for x in b["todo"] + b["running"]) and b["done"][0]["note"] == "three sources filed"
    with pytest.raises(ValueError):
        missions.report(m["id"], "maybe")
