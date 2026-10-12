"""quiet-planner MCP server, the FreeConvert normaliser and the picture review (all offline: every network reply is a fake)."""

from __future__ import annotations

import io
import json

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from faceless import brand, config, decide, freeconvert, ledger, planner_art, planner_clean, planner_mcp, planner_review
from faceless.providers import ProviderError, ProviderUnavailable


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(decide, "RECORDS", tmp_path / "decisions.jsonl")
    for name, sub in (("SOURCE", "source"), ("CLEAN", "clean")):
        monkeypatch.setattr(planner_art, name, tmp_path / sub)
    monkeypatch.setattr(planner_clean, "REPORT", tmp_path / "report.json")
    monkeypatch.setattr(planner_clean, "INVENTORY", tmp_path / "INVENTORY.md")
    monkeypatch.setattr(planner_clean, "_sheet", lambda pairs, cell=360: tmp_path / "sheet.jpg")
    monkeypatch.setattr(freeconvert, "INCOMING", tmp_path / "incoming")


def marked(seed: int = 5, text: str = "@youngstunnersss") -> tuple[Image.Image, Image.Image]:
    base = planner_art.render_motif("stack", seed).resize((1600, 727))
    f = ImageFont.truetype(str(brand.Paths.fonts / "Montserrat-ExtraBold.ttf"), 26)
    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((660, 672), text, font=f, fill=(235, 230, 215, 200))
    return base, Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")


# ---------------------------------------------------------------- the protocol

def test_the_server_speaks_mcp_and_lists_every_tool():
    r = planner_mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}})
    assert r["result"]["protocolVersion"] == "2025-03-26" and r["result"]["serverInfo"]["name"] == "quiet-planner"
    assert planner_mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    tools = planner_mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    assert {t["name"] for t in tools} == set(planner_mcp.TOOLS) and all(t["inputSchema"]["type"] == "object" for t in tools)
    assert planner_mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})["error"]["code"] == -32601
    assert planner_mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "ping"})["result"] == {}


def test_no_tool_can_publish_or_spend_without_its_caps():
    names = " ".join(planner_mcp.TOOLS)
    assert not any(w in names for w in ("publish", "post", "list_", "price", "upload", "push"))


def test_a_bad_call_is_an_error_reply_not_a_crash(tmp_path):
    out = planner_mcp.call("planner_ingest", {"folder": str(tmp_path / "missing")})
    assert out["isError"] and "not a folder" in out["content"][0]["text"] and "Traceback" not in out["content"][0]["text"]
    assert planner_mcp.call("planner_nope", {})["isError"]


def test_the_stdio_loop_survives_garbage_and_answers_each_line():
    stdin = io.StringIO('not json\n\n[1]\n{"jsonrpc":"2.0","id":7,"method":"ping"}\n')
    out = io.StringIO()
    planner_mcp.serve(stdin, out)
    replies = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [r.get("error", {}).get("code") for r in replies[:2]] == [-32700, -32600] and replies[2] == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_status_reports_keys_as_yes_or_no_never_the_value(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-secret-value")
    out = planner_mcp.call("planner_status", {})["content"][0]["text"]
    s = json.loads(out)
    assert s["services"]["openrouter_vision_review"] is True and s["services"]["freeconvert_normalize"] is False
    assert "secret" not in out


# ---------------------------------------------------------------- the end to end job

def test_ingest_then_clean_then_review_a_marked_picture(tmp_path):
    base, dirty = marked()
    src = tmp_path / "in"
    src.mkdir()
    dirty.save(src / "pic1.png")
    base.save(src / "pic2.png")                                      # a picture with no handle is left alone
    assert json.loads(planner_mcp.call("planner_ingest", {"folder": str(src), "start": 10})["content"][0]["text"])["copied"] == 2
    out = json.loads(planner_mcp.call("planner_clean", {"vision": False})["content"][0]["text"])
    assert out["checked"] == 2 and out["handle_removed"] == 1 and out["needs_a_person"] == []
    rep = json.loads((tmp_path / "report.json").read_text())
    assert rep["day-010.png"]["review"]["status"] == "accepted_local_only" and rep["day-011.png"]["removed"] == []
    cleaned = np.asarray(Image.open(tmp_path / "clean" / "day-010.png")).astype(int)
    assert np.abs(cleaned - np.asarray(base).astype(int))[665:715, 650:950].mean() < 3
    one = json.loads(planner_mcp.call("planner_review", {"day": 10, "vision": False})["content"][0]["text"])
    assert one["status"] == "accepted_local_only" and one["local"]["ok"]


# ---------------------------------------------------------------- the review

def test_local_checks_hold_a_picture_that_changed_where_it_should_not():
    base, dirty = marked()
    out, found = planner_clean.clean_image(dirty)
    assert planner_review.local_checks(dirty, out, found)["ok"]
    bad = np.array(out)
    bad[100:300, 100:600] = 0                                        # real artwork wiped
    r = planner_review.local_checks(dirty, Image.fromarray(bad), found)
    assert not r["ok"] and any("outside" in m for m in r["reasons"])
    assert not planner_review.local_checks(dirty, dirty, found)["ok"]   # the handle is still there


class FakeResp:
    def __init__(self, code=200, payload=None, content=b""):
        self.status_code, self._p, self.content, self.headers = code, payload or {}, content, {}

    def json(self):
        return self._p


def vision_reply(text, cost=0.0002):
    return FakeResp(200, {"choices": [{"message": {"content": text}}], "usage": {"cost": cost}})


def test_the_vision_look_is_capped_spent_and_can_only_hold_more(monkeypatch):
    base, dirty = marked()
    out, found = planner_clean.clean_image(dirty)
    sent = []

    class S:
        def post(self, url, json=None, timeout=None, headers=None):
            sent.append((url, json))
            return vision_reply('{"handle_still_visible": false, "artwork_damaged": false, "smudge": true, "note": "grey patch"}')
    monkeypatch.setattr(planner_review, "http", lambda: S())
    assert planner_review.review(dirty, out, found)["vision"] is None              # no key: the local checks stand alone
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    r = planner_review.review(dirty, out, found)
    assert r["status"] == "needs_human" and any("smudge" in x for x in r["reasons"]) and r["vision"]["usd"] == 0.0002
    url, body = sent[0]
    assert url.startswith("https://openrouter.ai/") and body["model"] == config.load()["planner"]["review_model"]
    assert body["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert ledger.used(planner_review.PROVIDER, "usd") == pytest.approx(0.0002)
    monkeypatch.setitem(config.load()["planner"], "daily_usd", 0.0001)             # cap below one look: it does not ask
    sent.clear()
    assert planner_review.review(dirty, out, found)["vision"] is None and not sent


def test_a_model_that_cannot_answer_does_not_break_the_review(monkeypatch):
    base, dirty = marked()
    out, found = planner_clean.clean_image(dirty)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")

    class S:
        def post(self, *a, **k):
            return vision_reply("sorry, I cannot help with that")
    monkeypatch.setattr(planner_review, "http", lambda: S())
    assert planner_review.review(dirty, out, found)["status"] == "accepted_local_only"


def test_a_reply_with_no_text_is_a_look_not_taken(monkeypatch):
    base, dirty = marked()
    out, found = planner_clean.clean_image(dirty)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")

    class S:
        def post(self, *a, **k):                                    # a reasoning model that ran out of tokens answers with content null
            return FakeResp(200, {"choices": [{"message": {"content": None}, "finish_reason": "length"}], "usage": {"cost": 0.0001}})
    monkeypatch.setattr(planner_review, "http", lambda: S())
    r = planner_review.review(dirty, out, found)
    assert r["status"] == "accepted_local_only" and r["vision"] is None


def test_the_decision_gate_may_hold_a_picture_but_never_release_one(monkeypatch):
    base, dirty = marked()
    out, found = planner_clean.clean_image(dirty)
    D = decide.Decision
    monkeypatch.setattr(decide, "ask", lambda qs, state, job=None, backend=None: {"person_should_look": D("person_should_look", "needs_human", 0.99, "jev")})
    assert planner_review.review(dirty, out, found, use_vision=False)["status"] == "needs_human"
    monkeypatch.setattr(decide, "ask", lambda qs, state, job=None, backend=None: {"person_should_look": D("person_should_look", "accepted", 0.99, "jev")})
    assert planner_review.review(dirty, dirty, found, use_vision=False)["status"] == "needs_human"   # local checks failed: the gate cannot override


# ---------------------------------------------------------------- FreeConvert

def png_bytes():
    b = io.BytesIO()
    Image.new("RGB", (40, 20), (200, 160, 20)).save(b, "PNG")
    return b.getvalue()


class FC:
    """Replays the documented FreeConvert flow: upload task, form upload, job, poll, export url."""
    def __init__(self, host="https://server100.freeconvert.com/api/upload/abc", final="completed"):
        self.calls, self.host, self.final = [], host, final

    def request(self, method, url, headers=None, timeout=None, json=None):
        self.calls.append((method, url.replace(freeconvert.BASE, "")))
        assert headers["Authorization"] == "Bearer tok" and timeout
        if url.endswith("/process/import/upload"):
            return FakeResp(200, {"id": "up1", "status": "waiting", "result": {"form": {"url": self.host, "parameters": {"signature": "s"}}}})
        if url.endswith("/process/jobs"):
            return FakeResp(200, {"id": "job1", "status": "processing", "tasks": []})
        done = {"id": "job1", "status": self.final, "tasks": [{"name": "export", "status": self.final, "result": {"url": "https://cdn.freeconvert.com/x.png", "errorCode": "bad_input"}}]}
        return FakeResp(200, done)

    def post(self, url, data=None, files=None, timeout=None):
        self.calls.append(("UPLOAD", url))
        assert data == {"signature": "s"} and files["file"][0] == "phone.heic"
        return FakeResp(200, {})


def test_freeconvert_turns_a_heic_into_a_png_and_counts_the_minute(monkeypatch, tmp_path):
    src = tmp_path / "phone.heic"
    src.write_bytes(b"heic-bytes")
    with pytest.raises(ProviderUnavailable):
        freeconvert.normalize(src)                                  # no token: off
    monkeypatch.setenv("FREECONVERT_API_KEY", "tok")
    fc = FC()
    monkeypatch.setattr(freeconvert, "http", lambda: fc)
    monkeypatch.setattr(freeconvert, "fetch_bytes", lambda url, limit=0: (png_bytes(), "image/png"))
    monkeypatch.setitem(config.load()["freeconvert"], "poll_seconds", 0)
    out = freeconvert.normalize(src)
    assert out == tmp_path / "incoming" / "phone.png" and Image.open(out).size == (40, 20)
    assert ledger.used("freeconvert", "minutes") == 1
    assert [c[0] for c in fc.calls][:3] == ["POST", "UPLOAD", "POST"]


def test_freeconvert_refuses_what_it_should(monkeypatch, tmp_path):
    monkeypatch.setenv("FREECONVERT_API_KEY", "tok")
    monkeypatch.setitem(config.load()["freeconvert"], "poll_seconds", 0)
    jpg = tmp_path / "ok.jpg"
    jpg.write_bytes(b"x")
    with pytest.raises(ValueError, match="Pillow opens the rest"):
        freeconvert.normalize(jpg)
    src = tmp_path / "phone.heic"
    src.write_bytes(b"x")
    monkeypatch.setattr(freeconvert, "http", lambda: FC(host="https://evil.example.com/upload"))
    with pytest.raises(ProviderError, match="no usable upload address"):                       # the file is never sent to another host
        freeconvert.normalize(src)
    monkeypatch.setattr(freeconvert, "http", lambda: FC(final="failed"))
    with pytest.raises(ProviderError, match="bad_input"):
        freeconvert.normalize(src)
    monkeypatch.setattr(freeconvert, "http", lambda: FC())
    monkeypatch.setattr(freeconvert, "fetch_bytes", lambda url, limit=0: (b"<html>not a picture</html>", "text/html"))
    with pytest.raises(Exception):                                                              # a download that is not a picture is not saved
        freeconvert.normalize(src)
    assert not (tmp_path / "incoming" / "phone.png").exists()
    monkeypatch.setitem(config.load()["freeconvert"], "daily_minutes", 0)
    with pytest.raises(ProviderUnavailable, match="daily cap"):
        freeconvert.normalize(src)


# ---------------------------------------------------------------- Jev through OpenRouter, the locator, Photopea and the poster pipeline

def test_jev_through_openrouter_answers_typed_questions_and_is_capped(monkeypatch):
    q = {"look": decide.Q("choice", "Should a person look?", fallback="accepted", options={"accepted": "fine", "needs_human": "off"})}
    seen = []

    class S:
        def post(self, url, json=None, timeout=None, headers=None):
            seen.append(json["model"])
            return FakeResp(200, {"model": "x/y", "choices": [{"message": {"content": '{"look": {"answer": "needs_human", "confidence": 0.97}, "other": {"answer": 1, "confidence": 1}}'}}], "usage": {"cost": 0.001}})
    import faceless.providers as prov
    monkeypatch.setattr(prov, "http", lambda: S())
    with pytest.raises(RuntimeError):                                                          # no key: it says so, ask() then keeps the fallback
        decide._ask_jev_openrouter(q, {})
    assert decide.ask(q, {"x": 1}, backend="jev-openrouter")["look"].value == "accepted"
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    d = decide.ask(q, {"x": 1}, backend="jev-openrouter")["look"]
    assert seen == ["typesafe/jev-router"] and d.jev_value == "needs_human" and d.jev_confidence == 0.97 and d.value == "accepted"   # dry_run: logged, not acted on
    assert ledger.used("openrouter-jev", "usd") == pytest.approx(0.001)
    monkeypatch.setitem(config.load()["decide"], "jev_openrouter_daily_usd", 0.0005)
    assert decide.ask(q, {"x": 1}, backend="jev-openrouter")["look"].jev_value is None         # over the cap: no call


def test_the_review_honours_a_jev_hold_even_in_dry_run(monkeypatch):
    base, dirty = marked()
    out, found = planner_clean.clean_image(dirty)
    D = decide.Decision
    monkeypatch.setattr(decide, "ask", lambda qs, state, job=None, backend=None: {"person_should_look": D("person_should_look", "accepted", 1.0, "heuristic", "needs_human", 0.99)})
    assert planner_review.review(dirty, out, found, use_vision=False)["status"] == "needs_human"


def poster(handle: bool, y0: int = 1180, size=(832, 1248)) -> Image.Image:
    """A synthetic poster: white sheet on a coloured wall, a beige floor strip below it, and (optionally) a dark handle line on the floor."""
    w, h = size
    im = Image.new("RGB", size, (190, 60, 60))
    d = ImageDraw.Draw(im)
    d.rectangle([60, 140, w - 60, 1090], fill=(250, 250, 250))
    d.rectangle([0, 1100, w, h], fill=(212, 190, 160))
    d.rectangle([150, 400, 700, 470], fill=(20, 20, 20))                                      # poster text
    if handle:
        f = ImageFont.truetype(str(brand.Paths.fonts / "Montserrat-ExtraBold.ttf"), 44)
        d.text((260, y0), "@youngstunnersss", font=f, fill=(15, 15, 15))
    return im


def test_the_locator_cuts_above_a_handle_on_the_floor_and_leaves_clean_posters_alone():
    from faceless import planner_locate as pl
    y = pl.plan_crop(poster(True))
    assert y["action"] == "crop" and 1100 < y["y"] < 1185
    assert pl.plan_crop(poster(False))["action"] == "keep"
    yes = {"handle_present": True, "handle_top": 0.95, "note": "", "usd": 0, "model": "m"}
    no = {"handle_present": False, "handle_top": None, "note": "none", "usd": 0, "model": "m"}
    assert pl.plan_crop(poster(False), yes)["action"] == "needs_human"                          # the model sees one the pixels cannot find
    assert pl.plan_crop(poster(True), no)["action"] == "needs_human"                            # the pixels see one the model cannot
    assert pl.plan_crop(poster(True), {**yes, "handle_top": 0.70})["action"] == "needs_human"   # they disagree about where it is
    assert pl.plan_crop(poster(True), yes)["action"] == "crop"


def test_the_pillow_crop_and_the_agreement_check():
    from faceless import planner_photopea as ph
    b = io.BytesIO()
    poster(True).save(b, "JPEG", quality=95)
    ref = ph.pillow_crop(b.getvalue(), (0, 0, 832, 1170))
    assert Image.open(io.BytesIO(ref)).size == (832, 1170) and ph.agrees(ref, ref)
    assert not ph.agrees(ref, ph.pillow_crop(b.getvalue(), (0, 0, 832, 1100)))                  # a different size never agrees


def test_the_poster_pipeline_crops_keeps_paints_and_never_touches_originals(monkeypatch, tmp_path):
    from faceless import planner_posters as P
    monkeypatch.setattr(P, "ORIGINAL", tmp_path / "o")
    monkeypatch.setattr(P, "CROPPED", tmp_path / "c")
    monkeypatch.setattr(P, "REPORT", tmp_path / "r.json")
    monkeypatch.setattr(P, "ROOT", tmp_path)
    (tmp_path / "o").mkdir()
    for i, h in ((1, True), (2, False), (3, True)):
        poster(h).save(tmp_path / "o" / f"wellness-{i:03d}.jpg", "JPEG", quality=95)
    before = {p.name: p.read_bytes() for p in (tmp_path / "o").iterdir()}
    rep = P.process(use_model=False, engine="pillow", manual_cuts={"wellness-003": 1170 / 1248})
    assert rep["wellness-001"]["action"] == "cropped" and rep["wellness-002"]["action"] == "kept" and rep["wellness-003"].get("manual") is True
    assert 1100 < Image.open(tmp_path / "c" / "wellness-001.jpg").height < 1190 and Image.open(tmp_path / "c" / "wellness-002.jpg").size == (832, 1248)
    assert {p.name: p.read_bytes() for p in (tmp_path / "o").iterdir()} == before             # originals byte-identical
    assert json.loads((tmp_path / "r.json").read_text())["wellness-001"]["engine"] == "pillow"
    assert P.summary(rep)["cropped"] == 2 and P.summary(rep)["kept"] == 1


def test_the_photopea_host_serves_one_page_and_nothing_else():
    import threading
    import socketserver
    import urllib.request
    from faceless import planner_photopea as ph
    srv = socketserver.TCPServer(("127.0.0.1", 0), ph._Host)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        ok = urllib.request.urlopen(f"http://127.0.0.1:{port}/host.html", timeout=10)
        assert ok.status == 200 and b"photopea.com" in ok.read()
        with pytest.raises(Exception):
            urllib.request.urlopen(f"http://127.0.0.1:{port}/../../etc/passwd", timeout=10)
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.mark.skipif(not __import__("os").environ.get("PLANNER_PHOTOPEA_LIVE"), reason="drives the real photopea.com in Chromium: set PLANNER_PHOTOPEA_LIVE=1")
def test_live_photopea_crop_matches_pillow():
    from faceless import planner_photopea as ph
    b = io.BytesIO()
    poster(True).save(b, "JPEG", quality=95)
    with ph.Photopea() as pp:
        out = pp.crop(b.getvalue(), (0, 0, 832, 1170))
    assert ph.agrees(out, ph.pillow_crop(b.getvalue(), (0, 0, 832, 1170)))


# ---------------------------------------------------------------- the model panel

def test_the_panel_tallies_votes_counts_failures_and_respects_its_cap(monkeypatch):
    from faceless import panel
    replies = iter(['{"choice": "A", "confidence": 0.6}', '{"choice": "C", "confidence": 0.5}', "no json here", '{"choice": "C", "confidence": 0.9}'])

    class S:
        def post(self, url, json=None, timeout=None, headers=None):
            assert json["reasoning"] == {"effort": "low"} and json["max_tokens"] >= 2000
            return FakeResp(200, {"model": json["model"], "choices": [{"message": {"content": next(replies)}}], "usage": {"cost": 0.001}})
    monkeypatch.setattr(panel, "http", lambda: S())
    with pytest.raises(ProviderUnavailable):
        panel.ask("m/one", "brief")                                                              # no key: refused
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    res = panel.run("brief", ["m/one", "m/two"], runs=2, label="Test: A or C?")
    assert res["models"]["m/one"]["votes"] == {"A": 1, "C": 1} and res["models"]["m/two"]["failed"] == 1 and res["tally"] == {"A": 1, "C": 2}
    assert res["models"]["m/two"]["mean_confidence"] == 0.9 and ledger.used(panel.PROVIDER, "usd") == pytest.approx(0.004)
    monkeypatch.setitem(config.load()["panel"], "daily_usd", 0.0035)                             # the fifth call would pass the cap
    again = panel.run("brief", ["m/one"], runs=1)
    assert again["models"]["m/one"]["failed"] == 1 and "cap" in again["models"]["m/one"]["answers"][0]["out"]["error"]
    assert panel.run("brief", ["m/one"], runs=99)["runs"] == config.load()["panel"]["max_runs"]
