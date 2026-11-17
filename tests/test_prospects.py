"""The prospect machine and the toolbox: both are plain code over local files, so every test runs offline."""

import json

import pytest

from faceless import dmdesk, missions, prospects, safety, toolbox


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setattr(dmdesk, "LOG", tmp_path / "outbound.jsonl")
    monkeypatch.setattr(dmdesk, "DRAFTS", tmp_path / "drafts")
    monkeypatch.setattr(dmdesk, "BLOCKLIST", tmp_path / "private" / "blocklist.txt")
    monkeypatch.setattr(prospects, "INBOX", tmp_path / "private" / "inbox")
    monkeypatch.setattr(prospects, "LISTS", tmp_path / "private" / "prospects")
    monkeypatch.setattr(prospects, "SEEN", tmp_path / "private" / "prospects" / "seen.jsonl")
    monkeypatch.setattr(safety, "paused", lambda: None)
    monkeypatch.setattr(prospects.events, "emit", lambda *a, **k: {})
    monkeypatch.setattr(dmdesk.events, "emit", lambda *a, **k: {})
    return tmp_path


def no_youtube():
    raise RuntimeError("not connected")


ROWS = [
    {"handle": "@ana.saves", "name": "Ana Lopez", "text": "How do I start if my rent is half my income?", "video": "The 50/30/20 myth"},
    {"handle": "budgetbro", "text": "This is wrong, paying the mortgage early beats the market for most people", "video": "Mortgage myth"},
    {"handle": "jo_22", "text": "I paid off my car last year and my savings finally moved", "video": "Car payments"},
    {"handle": "spammy", "text": "great video check my page for crypto signal"},
    {"handle": "lol", "text": "so true 🔥"},
    {"handle": "moneywithmia", "kind": "peer", "text": "sinking funds for irregular bills"},
]


def test_classify_sorts_people_by_what_they_wrote():
    seg = [prospects.classify(prospects.clean(r))[0] for r in ROWS[:4]] + [prospects.classify(prospects.clean(ROWS[5]))[0]]
    assert seg == ["asked", "disagreed", "shared", None, "peer"]
    assert prospects.classify(prospects.clean(ROWS[4]))[0] is None            # a reaction is not a conversation


def test_add_refuses_bad_rows_and_never_doubles(desk):
    assert prospects.add(ROWS[0])["added"] is True
    assert prospects.add(ROWS[0])["added"] is False
    for bad in ({"handle": "a b", "text": "two words"}, {"handle": "ok", "text": "x"}, {"handle": "ok", "text": "two words", "kind": "stranger"},
                {"handle": "ok", "text": "two words", "url": "http://x.test"}):
        with pytest.raises(ValueError):
            prospects.add(bad)


def test_run_drafts_real_people_once_and_keeps_handles_out_of_the_log(desk):
    for r in ROWS[:4] + ROWS[5:]:
        prospects.add(r)
    r = prospects.run(day="2026-11-15", youtube=no_youtube)
    assert r["found"] == 5 and r["ready"] == 4 and r["dropped"] == 1
    assert r["drafted"] >= 1 and r["path"]
    batch = json.loads((dmdesk.DRAFTS / "2026-11-15.private.json").read_text())
    first = batch["drafts"][0]
    assert first["handle"] == "@ana.saves" and first["segment"] == "asked" and "rent is half my income" in first["first"]
    assert not first["open_slots"]
    assert "ana" not in (desk / "outbound.jsonl").read_text().lower()            # the committed log holds hashes only
    assert any(s["source"] == "youtube comments" and "unavailable" in s["note"] for s in r["sources"])
    with pytest.raises(prospects.Refused):
        prospects.run(day="2026-11-15", youtube=no_youtube)                      # one batch a day: nothing is overwritten
    again = prospects.run(day="2026-11-16", youtube=no_youtube)
    assert again["ready"] == 0 and again["drafted"] == 0                         # everyone handled is remembered


def test_run_respects_pause_and_the_block_list(desk, monkeypatch):
    prospects.add(ROWS[0])
    monkeypatch.setattr(safety, "paused", lambda: "owner said stop")
    with pytest.raises(prospects.Refused):
        prospects.run(youtube=no_youtube)
    monkeypatch.setattr(safety, "paused", lambda: None)
    dmdesk.BLOCKLIST.parent.mkdir(parents=True, exist_ok=True)
    dmdesk.BLOCKLIST.write_text("@ana.saves\n")
    ready, dropped = prospects.queue(prospects.from_inbox())
    assert not ready and dropped[0]["why"] == "on the block list"


def test_youtube_comments_become_rows_and_skip_our_own():
    def api(path, **q):
        if path == "channels":
            return {"items": [{"id": "UCme"}]}
        mk = lambda who, cid, text: {"snippet": {"videoId": "v1", "topLevelComment": {"snippet": {   # noqa: E731
            "authorDisplayName": who, "authorChannelId": {"value": cid}, "textOriginal": text, "publishedAt": "2026-11-14T10:00:00Z"}}}}
        return {"items": [mk("@viewer1", "UCx", "What about people with no emergency fund?"), mk("@quietmoneyrule", "UCme", "Pinned: the checklist")]}
    rows = prospects.from_youtube(api)
    assert [r["handle"] for r in rows] == ["viewer1"] and rows[0]["platform"] == "youtube"


def test_board_offers_the_run_only_when_there_is_someone():
    base = {"day": "2026-11-15", "jobs": None, "phone": None, "outbound": None, "offers": None}
    ids = lambda pr: [m["id"] for m in missions.derive({**base, "prospects": pr})]   # noqa: E731
    assert "prospect-2026-11-15" in ids({"ready": 3, "draftedToday": False, "youtube": False, "addedToday": True})
    assert "prospect-2026-11-15" not in ids({"ready": 3, "draftedToday": True, "youtube": False, "addedToday": True})
    assert "prospect-2026-11-15" not in ids({"ready": 0, "draftedToday": False, "youtube": False, "addedToday": True})
    m = next(m for m in missions.derive({**base, "prospects": {"ready": 2, "draftedToday": False}}) if m["id"].startswith("prospect-"))
    assert m["kind"] == "engine" and m["action"] == "prospect"


CATALOG = [[
    {"id": "spectral", "name": "Spectral", "url": "https://github.com/x/spectral", "kind": "integration", "targets": ["app", "protocol"],
     "category": "protocol-analysis", "description_en": "Analyze captured HTTP traffic and generate OpenAPI specifications."},
    {"id": "ghidra", "name": "Ghidra", "url": "https://github.com/x/ghidra", "kind": "tool", "targets": ["binary"], "category": "native-analysis",
     "description_en": "Decompiler and disassembler suite."},
    {"id": "case-1", "name": "Some app case", "url": "https://github.com/x/case", "kind": "case-study", "targets": ["app"], "description_en": "HTTP traffic of an app."},
    {"id": "evil", "name": "No https", "url": "javascript:alert(1)", "kind": "tool", "description_en": "traffic"},
    {"id": "spectral", "name": "Duplicate", "url": "https://github.com/x/dup", "kind": "tool", "description_en": "traffic"},
]]


def test_toolbox_finds_tools_by_need_and_keeps_cases_apart():
    box = toolbox.build(CATALOG)
    assert [t["id"] for t in box["tools"]] == ["spectral", "ghidra"] and [c["id"] for c in box["cases"]] == ["case-1"]
    assert toolbox.find("turn app traffic into an api", box=box)[0]["id"] == "spectral"
    assert toolbox.find("decompile a binary", target="binary", box=box)[0]["id"] == "ghidra"
    assert toolbox.find("traffic", target="binary", box=box) == []
    assert [h["id"] for h in toolbox.find("app traffic", cases=True, box=box)] == ["spectral", "case-1"]
    assert toolbox.show("ghidra", box)["url"].startswith("https://") and toolbox.show("nope", box) is None


def test_autopilot_never_starts_a_paid_agent_by_itself(monkeypatch):
    monkeypatch.setattr(safety, "paused", lambda: None)
    card = {"id": "x-1", "title": "T", "kind": "agent", "auto": True, "route": {"agent": "claude", "name": "Claude Code", "cost": "paid"}}
    board = {"todo": [card], "running": [], "autopilot": {"max_parallel": 2, "max_cost": 1}}
    assert missions.plan_auto({"missions": board})["state"] == "idle"
    board["autopilot"]["max_cost"] = 2
    assert missions.plan_auto({"missions": board})["state"] == "run"
    card["route"]["cost"] = "free"
    board["autopilot"]["max_cost"] = 0
    assert missions.plan_auto({"missions": board})["state"] == "run"


def test_board_reports_the_last_real_youtube_read_not_the_key(desk, monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "present")
    assert prospects.board_state()["youtube"] is True                            # a key and no read yet: worth one try
    prospects.collect(no_youtube)
    b = prospects.board_state()
    assert b["youtube"] is False and "not connected" in b["youtubeNote"]         # a key that does not work is not a source
    monkeypatch.setattr(prospects, "_now", lambda: prospects.datetime.now(prospects.timezone.utc) + prospects.timedelta(hours=7))
    assert prospects.board_state()["youtube"] is True                            # after the wait the board lets one run try again
    monkeypatch.setattr(prospects, "_now", lambda: prospects.datetime.now(prospects.timezone.utc))
    prospects.collect(lambda: [])
    assert prospects.board_state()["youtube"] is True and "0 comment" in prospects.board_state()["youtubeNote"]
    monkeypatch.delenv("COMPOSIO_API_KEY")
    monkeypatch.delenv("COMPOSIO_API", raising=False)
    assert prospects.board_state()["youtube"] is False


def test_board_runs_the_client_hunt_once_a_day_and_hands_packages_to_the_owner():
    base = {"day": "2026-11-15", "jobs": None, "phone": None, "outbound": None, "offers": None, "prospects": None}
    got = lambda sd: {m["id"]: m for m in missions.derive({**base, "serviceDesk": sd})}   # noqa: E731
    hunt = got({"ranToday": False, "waiting": 0})["client-hunt-2026-11-15"]
    assert hunt["kind"] == "engine" and hunt["action"] == "outbound_run" and hunt["auto"]
    after = got({"ranToday": True, "waiting": 4})
    assert "client-hunt-2026-11-15" not in after                                  # one batch a day
    assert after["send-packages-2026-11-15"]["kind"] == "owner" and not after["send-packages-2026-11-15"]["auto"]   # a person sends
    for sd in (None, {"waiting": 0}):                                           # an unreadable desk offers nothing
        assert not [i for i in got(sd) if i.startswith(("client-hunt-", "send-packages-"))]


def test_a_hand_typed_command_gets_the_machine_keys_the_timer_has(tmp_path, monkeypatch):
    from faceless import config
    studio, machine = tmp_path / "studio", tmp_path / "env"
    studio.mkdir()
    (studio / ".env").write_text("QM_TEST_A=from-studio\n")
    machine.write_text("QM_TEST_A=from-machine\nQM_TEST_B=only-machine\n")
    monkeypatch.setattr(config, "STUDIO", studio)
    monkeypatch.setattr(config, "MACHINE_ENV", machine)
    for k in ("QM_TEST_A", "QM_TEST_B"):
        monkeypatch.delenv(k, raising=False)
    try:
        assert config.load_keys() == 2
        assert config.env("QM_TEST_A") == "from-studio" and config.env("QM_TEST_B") == "only-machine"
    finally:
        import os
        os.environ.pop("QM_TEST_A", None)
        os.environ.pop("QM_TEST_B", None)


def test_a_successful_read_is_not_offered_again_for_hours(desk, monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "present")
    assert prospects.board_state()["youtubeDue"] is True                          # never read: one run is worth it
    prospects.collect(lambda: [])
    b = prospects.board_state()
    assert b["youtube"] is True and b["youtubeDue"] is False                      # read just now, nobody there: do not loop
    base = {"day": "2026-11-15", "jobs": None, "phone": None, "outbound": None, "offers": None}
    assert not [m for m in missions.derive({**base, "prospects": b}) if m["id"].startswith("prospect-")]
    monkeypatch.setattr(prospects, "_now", lambda: prospects.datetime.now(prospects.timezone.utc) + prospects.timedelta(hours=7))
    assert prospects.board_state()["youtubeDue"] is True
