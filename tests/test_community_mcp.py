"""The YouTube Posts MCP server (mcp-servers/yt-community): its gates always, its browser flow against a stand-in composer page when a browser is present."""

import glob
import http.server
import socketserver
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-servers" / "yt-community"))
import core  # noqa: E402


def _item(tmp_path, text="A joke about rent.\nIllustrated with AI. Education and humour, not financial advice."):
    pic = tmp_path / "picture.png"
    pic.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    return {"slug": "2026-10-16/01-x", "picture": str(pic), "text": text, "alt": "", "title": "x"}


@pytest.fixture(autouse=True)
def _ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "LEDGER", tmp_path / "community_posts.jsonl")
    monkeypatch.delenv("QM_COMMUNITY_APPROVED", raising=False)


def test_a_dry_run_is_allowed_but_publishing_needs_the_owner_switch(tmp_path, monkeypatch):
    item = _item(tmp_path)
    assert core.gate(item, publish=False) is None
    assert "QM_COMMUNITY_APPROVED" in core.gate(item, publish=True)
    monkeypatch.setenv("QM_COMMUNITY_APPROVED", "1")
    assert core.gate(item, publish=True) is None


def test_a_bad_comic_is_refused_even_as_a_dry_run(tmp_path):
    assert "AI disclosure" in core.gate(_item(tmp_path, text="No disclosure here."), publish=False)
    assert "link" in core.gate(_item(tmp_path, text="See https://x.example Illustrated with AI."), publish=False)
    assert "limit" in core.gate(_item(tmp_path, text="a" * 1600 + " Illustrated with AI."), publish=False)


def test_a_post_is_never_made_twice_nor_past_the_daily_maximum(tmp_path, monkeypatch):
    monkeypatch.setenv("QM_COMMUNITY_APPROVED", "1")
    item = _item(tmp_path)
    core.record(item["slug"], published=True)
    assert core.gate(item, publish=True) == "already posted"
    monkeypatch.setattr(core, "MAX_PER_DAY", 1)
    other = dict(item, slug="2026-10-16/02-y")
    assert "already went out" in core.gate(other, publish=True)


def test_a_dry_run_is_not_counted_as_posted(tmp_path):
    core.record("2026-10-16/01-x", published=False, note="dry run")
    assert core.posted("2026-10-16/01-x") is None and core.posted_today() == 0


def test_the_kill_switch_stops_publishing(tmp_path, monkeypatch):
    monkeypatch.setenv("QM_COMMUNITY_APPROVED", "1")
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "PAUSE").write_text("test")
    monkeypatch.setattr(core, "REPO", tmp_path)
    assert "PAUSE" in core.gate(_item(tmp_path), publish=True)


STAND_IN = """<!doctype html><title>Posts</title>
<div id=c role=button>Create post</div>
<div id=box hidden><button id=img>Image</button><div role=textbox contenteditable=true id=t></div><button id=go>Post</button>
<input type=file id=f hidden></div><div id=feed></div>
<script>
c.onclick=()=>box.hidden=false; img.onclick=()=>f.click();
f.onchange=()=>feed.dataset.file=f.files[0].name;
go.onclick=()=>{const p=document.createElement('p');p.textContent=t.innerText;feed.appendChild(p)};
</script>"""


def _chrome():
    found = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return found[-1] if found else None


def test_the_browser_flow_fills_the_composer_and_only_posts_when_told(tmp_path, monkeypatch):
    pytest.importorskip("playwright.sync_api")
    if not _chrome():
        pytest.skip("no local chromium")
    import browser
    monkeypatch.setenv("QM_CHROME", _chrome())
    monkeypatch.setattr(browser, "PROFILE", tmp_path / "profile")
    monkeypatch.setattr(browser, "SHOTS", tmp_path / "shots")
    site = tmp_path / "site" / "channel" / "UCTEST" / "posts"
    site.mkdir(parents=True)
    (site / "index.html").write_text(STAND_IN, encoding="utf-8")
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(tmp_path / "site"), **k)  # noqa: E731
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        item = _item(tmp_path)
        dry = browser.post_image("UCTEST", item["picture"], item["text"], publish=False, headless=True, base=base)
        assert dry["published"] is False and Path(dry["screenshot"]).is_file()
        live = browser.post_image("UCTEST", item["picture"], item["text"], publish=True, headless=True, base=base)
        assert live["published"] is True
        srv.shutdown()
