"""The Etsy rail, the go-live gate and the quiet-shop MCP server. No network: Etsy is a fake session."""

from __future__ import annotations

import json
import os
import stat

import pytest

from faceless import config, etsy, listing, providers, shop, shop_mcp
from faceless.providers import ProviderError

PID = "daily-quiet-money-planner"


class Resp:
    def __init__(self, code=200, body=None):
        self.status_code, self._b = code, body if body is not None else {}
        self.content, self.text = json.dumps(self._b).encode(), json.dumps(self._b)

    def json(self):
        return self._b


class Fake:
    """Answers the Etsy calls a draft makes and remembers them."""

    def __init__(self, existing=None):
        self.calls, self.existing = [], existing or []

    def request(self, method, url, headers=None, data=None, files=None, params=None, timeout=None):
        assert timeout and headers["x-api-key"] and headers["Authorization"].startswith("Bearer ")
        path = url.removeprefix(etsy.API)
        self.calls.append((method, path, dict(data or {}), sorted(files or {})))
        if path.endswith("/shops") and method == "GET":
            return Resp(200, {"shop_id": 777})
        if path.endswith("/seller-taxonomy/nodes"):
            return Resp(200, {"results": [{"id": 1, "name": "Paper", "children": [{"id": 2, "name": "Planners", "children": []}]}]})
        if path.endswith("/listings") and method == "GET":
            return Resp(200, {"results": self.existing})
        if path.endswith("/listings") and method == "POST":
            return Resp(200, {"listing_id": 4242, "url": "https://www.etsy.com/listing/4242"})
        if method == "PATCH":
            return Resp(200, {"listing_id": 4242, "state": "active", "url": "https://www.etsy.com/listing/4242"})
        return Resp(201, {})

    def post(self, *a, **k):
        raise AssertionError("no token call expected")


@pytest.fixture(autouse=True)
def pack(tmp_path, monkeypatch):
    """A tiny built pack in a temp folder (the real images are git-ignored, so CI has none)."""
    from PIL import Image
    folder = tmp_path / "shop" / PID
    (folder / "etsy" / "images").mkdir(parents=True)
    (folder / "gumroad").mkdir(parents=True)
    for i in range(1, 10):
        Image.new("RGB", (40, 40), (i * 20, 0, 0)).save(folder / "etsy" / "images" / f"{i:02d}.jpg")
    for n in ("cover.jpg", "thumbnail.jpg"):
        Image.new("RGB", (40, 40)).save(folder / "gumroad" / n)
    (folder / "etsy" / "video.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    monkeypatch.setattr(listing, "OUT", tmp_path / "shop")
    monkeypatch.setattr(etsy.listing, "OUT", tmp_path / "shop")


@pytest.fixture()
def rail(tmp_path, monkeypatch):
    monkeypatch.setenv("ETSY_API_KEY", "keystring-test")
    monkeypatch.delenv("ETSY_SHARED_SECRET", raising=False)
    monkeypatch.delenv("ETSY_SHOP_ID", raising=False)
    monkeypatch.setenv("ETSY_SECRETS_DIR", str(tmp_path / "secrets"))
    etsy._cache.clear()
    etsy._save_tokens({"access_token": "12345.abc", "refresh_token": "r1", "expires_in": 3600})
    fake = Fake()
    monkeypatch.setattr(providers, "http", lambda: fake)
    monkeypatch.setattr(etsy.providers, "http", lambda: fake)
    from faceless import safety
    monkeypatch.setattr(safety, "paused", lambda: None)
    return fake


def test_the_listing_payload_follows_etsys_limits_and_is_a_draft():
    p = listing.products(PID)[0]
    pl = etsy.payload(p, 99)
    assert pl["state"] == "draft" and pl["type"] == "download" and pl["taxonomy_id"] == 99 and len(pl["title"]) <= 140
    assert len(pl["tags"].split(",")) == 13 and all(len(t) <= 20 for t in pl["tags"].split(","))
    up = etsy.uploads(p)
    assert [f.suffix for f in up["files"]] == [".pdf", ".pdf"] and len(up["images"]) == 9
    p2 = json.loads(json.dumps(p))
    p2["etsy"]["tags"] = p["etsy"]["tags"][:5]
    with pytest.raises(ProviderError, match="13 tags"):
        etsy.payload(p2)


def test_a_draft_is_created_with_files_images_and_video_and_never_activated(rail):
    out = etsy.create_draft(PID)
    assert out["action"] == "draft created" and out["listing_id"] == 4242
    kinds = [(m, p.rsplit("/", 1)[-1]) for m, p, *_ in rail.calls]
    assert ("POST", "listings") in kinds and kinds.count(("POST", "files")) == 2 and kinds.count(("POST", "images")) == 9 and ("POST", "videos") in kinds
    assert not any(m == "PATCH" for m, *_ in rail.calls)
    created = next(d for m, p, d, _ in rail.calls if m == "POST" and p.endswith("/listings"))
    assert created["state"] == "draft" and created["taxonomy_id"] == 2


def test_a_listing_that_exists_is_not_duplicated(rail):
    title = listing.products(PID)[0]["etsy"]["title"]
    rail.existing = [{"title": title, "listing_id": 9, "state": "draft"}]
    out = etsy.create_draft(PID)
    assert out["action"].startswith("skipped") and not any(m == "POST" for m, *_ in rail.calls)


def test_tokens_are_saved_outside_the_repo_with_a_private_mode(rail, tmp_path):
    f = etsy._tokens_file()
    assert tmp_path in f.parents and stat.S_IMODE(os.stat(f).st_mode) == 0o600 and f.is_relative_to(config.STUDIO) is False


def test_the_login_link_uses_pkce_and_the_exchange_checks_state(rail, monkeypatch):
    url = etsy.auth_url()
    assert "code_challenge_method=S256" in url and "client_id=keystring-test" in url and "listings_w" in url
    with pytest.raises(ProviderError, match="state"):
        etsy.finish_auth("code", "wrong")
    seen = {}

    class Tok:
        def post(self, url, data=None, timeout=None):
            seen.update(data)
            return Resp(200, {"access_token": "9.new", "refresh_token": "r2", "expires_in": 3600})
    monkeypatch.setattr(etsy.providers, "http", lambda: Tok())
    monkeypatch.setenv("ETSY_SHOP_ID", "5")
    etsy._cache.clear()
    assert etsy.finish_auth("abc")["shop_id"] == "5" and seen["code_verifier"] and seen["grant_type"] == "authorization_code"
    assert json.loads(etsy._tokens_file().read_text())["refresh_token"] == "r2"


def test_publishing_is_refused_without_the_owners_approval_of_this_price(rail, monkeypatch):
    cfg = config.load()
    monkeypatch.setattr(config, "load", lambda: cfg)
    ok, why = shop.approval(PID, "etsy")
    assert not ok and "no approval" in why
    with pytest.raises(ProviderError, match="refused"):
        shop.publish(PID, "etsy")
    price = listing.products(PID)[0]["price"]
    stale = {**cfg, "shop": {"approved": {PID: {"price": price + 5, "etsy": True}}}}
    monkeypatch.setattr(config, "load", lambda: stale)
    assert "catalog price" in shop.approval(PID, "etsy")[1]
    wrong_rail = {**cfg, "shop": {"approved": {PID: {"price": price, "gumroad": True}}}}
    monkeypatch.setattr(config, "load", lambda: wrong_rail)
    assert "not approved the etsy rail" in shop.approval(PID, "etsy")[1]
    assert not any(m == "PATCH" for m, *_ in rail.calls)


def test_with_the_approval_the_draft_goes_live(rail, monkeypatch):
    cfg = config.load()
    price = listing.products(PID)[0]["price"]
    monkeypatch.setattr(config, "load", lambda: {**cfg, "shop": {"approved": {PID: {"price": price, "etsy": True}}}})
    title = listing.products(PID)[0]["etsy"]["title"]
    rail.existing = [{"title": title, "listing_id": 4242, "state": "draft"}]
    monkeypatch.setattr(listing, "check", lambda only=None: {PID: []})                 # the toy pack above is not a real one; the gate itself is tested next
    res = shop.publish(PID, "etsy")
    assert res["state"] == "active" and any(m == "PATCH" and d["state"] == "active" for m, _p, d, _ in rail.calls)


def test_a_failing_listing_gauntlet_blocks_going_live_even_with_approval(rail, monkeypatch):
    cfg = config.load()
    price = listing.products(PID)[0]["price"]
    monkeypatch.setattr(config, "load", lambda: {**cfg, "shop": {"approved": {PID: {"price": price, "etsy": True}}}})
    assert "gauntlet fails" in shop.approval(PID, "etsy")[1]                           # the toy pack's images fail the real gates


def test_a_pause_stops_publishing(rail, monkeypatch):
    from faceless import safety
    monkeypatch.setattr(safety, "paused", lambda: "owner pause")
    with pytest.raises(providers.ProviderUnavailable):
        shop.publish(PID, "etsy")


def test_draft_all_reports_a_rail_that_is_not_ready_instead_of_hiding_it(monkeypatch, tmp_path):
    monkeypatch.delenv("ETSY_API_KEY", raising=False)
    monkeypatch.delenv("GUMROAD_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(shop, "gumroad_cli", lambda: None)
    from faceless import safety
    monkeypatch.setattr(safety, "paused", lambda: None)
    out = shop.draft_all(PID)
    assert {r["rail"] for r in out} == {"gumroad", "etsy"} and all(r["action"] == "not ready" for r in out)


def test_the_shop_mcp_speaks_the_protocol_and_publish_is_refused_over_it(monkeypatch):
    assert shop_mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})["result"]["serverInfo"]["name"] == "quiet-shop"
    names = {t["name"] for t in shop_mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]}
    assert names == {"shop_status", "shop_plan", "shop_draft", "shop_publish", "etsy_auth_url", "etsy_auth_finish", "shop_sales"}
    cfg = config.load()
    monkeypatch.setattr(config, "load", lambda: {**cfg, "shop": {}})
    r = shop_mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "shop_publish", "arguments": {"product": PID, "rail": "etsy"}}})["result"]
    assert r["isError"] and "refused" in r["content"][0]["text"]
    plan = json.loads(shop_mcp.call("shop_plan", {"product": PID})["content"][0]["text"])
    assert plan["etsy"]["state"] == "draft" and "no approval" in plan["live"]["etsy"]
    assert shop_mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "nope"})["error"]["code"] == -32601
