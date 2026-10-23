"""The money desk reads the engine's state, ranks the owner's steps, and never acts."""

from faceless import cash, config


def test_waiting_products_become_one_price_line_and_live_ones_do_not(monkeypatch):
    real = config.load()
    monkeypatch.setattr(config, "load", lambda: {**real, "offer": {**real.get("offer", {}), "shop_urls": {"daily-quiet-money-planner": "https://x"}}})
    p = cash.products()
    ids = [w["id"] for w in p["waiting"]]
    assert "daily-quiet-money-planner" not in ids and ids and p["state"] == "live"
    assert all(f"{w['id']} at ${w['placeholder_price']}" in p["owner_step"] for w in p["waiting"])


def test_the_desk_ranks_service_then_prices_then_gigs_and_writes_the_page(tmp_path, monkeypatch):
    monkeypatch.setattr(cash, "OUT", tmp_path / "CASH.md")
    d = cash.write()
    rails = [x["rail"] for x in d["next30"]]
    assert rails[0] == "Web3 video and KOL service" and rails[1] == "Gumroad products" and len(rails) == 3
    page = (tmp_path / "CASH.md").read_text()
    assert "Your next 30 minutes" in page and "judgment" in page
