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
    print(json.dumps({{"success": True, "products": [{{"name": "Tier 3 · Complete | Money Reset Kit: two spreadsheet planners + six printable pages"}}]}}))
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
    monkeypatch.delenv("GUMROAD", raising=False)
    monkeypatch.delenv("GUMROAD_TOKEN", raising=False)
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
    monkeypatch.delenv("GUMROAD", raising=False)
    monkeypatch.delenv("GUMROAD_TOKEN", raising=False)
    monkeypatch.setattr(shop, "gumroad_cli", lambda: None)
    rows = {r["rail"]: r for r in shop.status()}
    assert rows["gumroad draft products"]["state"] == "needs owner" and "GUMROAD_ACCESS_TOKEN" in rows["gumroad draft products"]["next"]
    monkeypatch.delenv("ETSY_API_KEY", raising=False)
    monkeypatch.setenv("ETSY_SECRETS_DIR", "/nonexistent-secrets")
    monkeypatch.delenv("ETSY_REFRESH_TOKEN", raising=False)
    rows = {r["rail"]: r for r in shop.status()}
    assert rows["etsy draft + publish"]["state"] == "needs owner" and "ETSY_API_KEY" in rows["etsy draft + publish"]["next"]


def test_token_accepts_the_owners_variable_name(monkeypatch):
    for n in shop.TOKEN_NAMES:
        monkeypatch.delenv(n, raising=False)
    assert not shop.token_present()
    monkeypatch.setenv("GUMROAD", "not-a-real-token")
    assert shop.token_present() and shop.token() == "not-a-real-token"


def test_sale_rows_keep_money_and_source_but_no_buyer(tmp_path, monkeypatch):
    monkeypatch.setattr(shop, "SALES", tmp_path / "sales.jsonl")
    raw = [{"id": "s1", "email": "buyer@example.com", "price": 1700, "product_name": "Planner", "created_at": "2026-10-20T10:00:00Z", "url_params": {"src": "dm"}},
           {"id": "s2", "price": 1700, "product_name": "Planner", "refunded": True, "discover_fee_charged": True}, {"no": "id"}, "junk"]
    fresh = shop._record_sales(raw)
    assert [r["id"] for r in fresh] == ["s1", "s2"] and fresh[0]["usd"] == 17.0 and fresh[0]["src"] == "dm" and fresh[1]["refunded"] and fresh[1]["discover"]
    assert "email" not in (tmp_path / "sales.jsonl").read_text(encoding="utf-8")
    assert shop._record_sales(raw) == []                     # each sale is recorded once


def test_the_cli_is_found_in_go_bin_when_path_lacks_it(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "/nonexistent")
    bindir = tmp_path / "go" / "bin"
    bindir.mkdir(parents=True)
    exe = bindir / "gumroad"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    exe.chmod(0o755)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert shop.gumroad_cli() == str(exe)


def test_sync_urls_follows_a_username_change_and_never_adds_a_product(tmp_path, monkeypatch):
    from faceless import config
    toml = tmp_path / "studio.toml"
    toml.write_text('[offer]\nshop_urls = { "money-reset-kit" = "https://old.gumroad.com/l/k" }   # comment stays\n')
    real = config.load()
    monkeypatch.setattr(config, "load", lambda: {**real, "offer": {"shop_urls": {"money-reset-kit": "https://old.gumroad.com/l/k"}}})
    name = {p["id"]: p["gumroad"]["name"] for p in listing.catalog()["products"]}
    prods = [{"name": name["money-reset-kit"], "published": True, "short_url": "https://quietmoney.gumroad.com/l/k"},
             {"name": name["money-reset-printables"], "published": True, "short_url": "https://quietmoney.gumroad.com/l/p"},
             {"name": name["rat-race-escape-planner"], "published": False, "short_url": "https://quietmoney.gumroad.com/l/r"}]
    dry = shop.sync_urls(prods=prods, path=toml)
    assert dry["changed"] == {"money-reset-kit": ("https://old.gumroad.com/l/k", "https://quietmoney.gumroad.com/l/k")}
    assert "old.gumroad" in toml.read_text()                                    # a dry run writes nothing
    r = shop.sync_urls(apply=True, prods=prods, path=toml)
    text = toml.read_text()
    assert "quietmoney.gumroad.com/l/k" in text and "# comment stays" in text and "money-reset-printables" not in text
    assert r["live_not_offered"] == ["money-reset-printables"]
