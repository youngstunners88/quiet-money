"""The command center projects real state, never writes it, and is closed to anyone on the network without the token.
The DM desk drafts and never sends; money is counted only from receipts."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from faceless import config, dashboard, dmdesk, moneybrief, overview, qr, receipts, safety, serve
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
    assert doc["targets"] == []
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


def test_the_server_is_read_only(server):
    for method in ("POST", "PUT", "DELETE", "PATCH"):
        assert _get(f"{server}/?t={TOKEN}", method=method)[0] == 405
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
