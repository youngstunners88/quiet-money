"""Storefront rails: drafts only, dry run by default, never a publish, nothing while paused."""

import json
import os
import stat

import pytest

from faceless import events, listing, safety, shop
from faceless.config import Paths
from faceless.providers import ProviderUnavailable


@pytest.fixture
def pack(tmp_path, monkeypatch):
    """A built pack for one product in a temp folder, and a fake `gumroad` CLI that records its calls."""
    monkeypatch.setattr(listing, "OUT", tmp_path / "shop")
    monkeypatch.setattr(shop, "STUDIO", tmp_path)
    monkeypatch.setattr(Paths, "state", tmp_path / "state")
    for pid in ("rat-race-escape-planner", "money-reset-kit"):
        d = tmp_path / "shop" / pid
        (d / "etsy" / "images").mkdir(parents=True)
        (d / "gumroad").mkdir(parents=True)
        for i in range(1, 8):
            (d / "etsy" / "images" / f"{i:02d}-x.jpg").write_bytes(b"jpg")
        (d / "etsy" / "video.mp4").write_bytes(b"mp4")
        (d / "gumroad" / "cover.jpg").write_bytes(b"jpg")
        (d / "gumroad" / "thumbnail.jpg").write_bytes(b"jpg")
    log = tmp_path / "calls.jsonl"
    cli = tmp_path / "bin" / "gumroad"
    cli.parent.mkdir()
    cli.write_text(f"""#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
open({str(log)!r}, "a").write(json.dumps(args) + "\\n")
if args[:2] == ["products", "list"]:
    print(json.dumps({{"success": True, "products": [{{"name": "Money Reset Kit: two spreadsheet planners + six printable pages"}}]}}))
elif args[:2] == ["products", "create"]:
    print(json.dumps({{"success": True, "product": {{"id": "abc123", "published": False}}}}))
else:
    print(json.dumps({{"success": False, "error": "unexpected"}})); sys.exit(1)
""")
    cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{cli.parent}{os.pathsep}{os.environ['PATH']}")
    return log


def calls(log):
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def test_a_dry_run_creates_nothing(pack):
    res = shop.push("rat-race-escape-planner")
    assert res[0]["action"] == "would create a draft" and not pack.exists()


def test_create_arguments_are_a_draft_with_every_file_and_picture(pack):
    p = listing.products("rat-race-escape-planner")[0]
    argv = shop.create_args(p)
    assert argv[:2] == ["products", "create"] and "--draft" in argv and "publish" not in argv
    assert argv[argv.index("--price") + 1] == "19.00" and argv.count("--tag") == 5
    assert argv.count("--preview-image") == 5 and "--preview-video" in argv and "--cover-image" in argv and "--thumbnail" in argv
    assert argv[argv.index("--file") + 1].endswith("Rat-Race-Escape-Planner.xlsx") and argv[-2:] == ["--json", "--no-input"]
    desc = argv[argv.index("--description") + 1]
    assert desc.startswith("<p>") and "<strong>" in desc and "<li>" in desc and "**" not in desc


def test_push_needs_the_token_the_cli_and_an_unpaused_studio(pack, monkeypatch):
    monkeypatch.delenv("GUMROAD_ACCESS_TOKEN", raising=False)
    with pytest.raises(ProviderUnavailable, match="GUMROAD_ACCESS_TOKEN"):
        shop.push("rat-race-escape-planner", run=True)
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "not-a-real-token")
    safety.pause("drill")
    with pytest.raises(ProviderUnavailable, match="paused"):
        shop.push("rat-race-escape-planner", run=True)
    assert not pack.exists()


def test_push_creates_a_draft_and_skips_a_name_that_exists(pack, monkeypatch):
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "not-a-real-token")
    monkeypatch.setattr(listing, "products", lambda only=None: [p for p in listing.catalog()["products"] if p["id"] in ("rat-race-escape-planner", "money-reset-kit") and (only in (None, "all", p["id"]))])
    res = {r["product"]: r for r in shop.push(None, run=True)}
    assert res["rat-race-escape-planner"]["action"] == "draft created" and res["rat-race-escape-planner"]["id"] == "abc123"
    assert res["money-reset-kit"]["action"].startswith("skipped")
    sent = calls(pack)
    assert [c[:2] for c in sent] == [["products", "list"], ["products", "create"]] and "--draft" in sent[1]
    assert any(e["type"] == "SHOP_DRAFT_CREATED" and e["published"] is False for e in events.read())


def test_the_token_never_reaches_a_log_or_a_command_line(pack, monkeypatch):
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "super-secret-token-value-123")
    monkeypatch.setattr(listing, "products", lambda only=None: [p for p in listing.catalog()["products"] if p["id"] == "rat-race-escape-planner"])
    shop.push(None, run=True)
    assert "super-secret-token-value-123" not in pack.read_text()
    assert "super-secret-token-value-123" not in events.JOURNAL.read_text()


def test_markdown_becomes_the_html_gumroad_takes():
    html = shop.md_to_html("Intro with **bold** and *italic* & more.\n\nWhat you get:\n- **One**: a thing\n- Two\n\n- Solo list")
    assert html == "<p>Intro with <strong>bold</strong> and <em>italic</em> &amp; more.</p><p>What you get:</p><ul><li><strong>One</strong>: a thing</li><li>Two</li></ul><ul><li>Solo list</li></ul>"


def test_status_tells_the_owner_the_next_step(monkeypatch):
    monkeypatch.delenv("GUMROAD_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(shop, "gumroad_cli", lambda: None)
    rows = {r["rail"]: r for r in shop.status()}
    assert rows["gumroad draft products"]["state"] == "needs owner" and "GUMROAD_ACCESS_TOKEN" in rows["gumroad draft products"]["next"]
    assert rows["etsy"]["state"] == "manual" and "CHECKLIST" in rows["etsy"]["next"]
