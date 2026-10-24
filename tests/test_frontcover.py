"""The shop's front covers: the research's checks as tests, the free gift, and the Gumroad refresh guard."""
import pytest

from faceless import frontcover, offer, shop
from faceless.providers import ProviderError


@pytest.fixture(scope="module")
def covers():
    return {pid: frontcover.render(pid) for pid in frontcover.SPECS}


def test_every_cover_is_the_ebook_size_and_passes_its_checks(covers):
    for pid, img in covers.items():
        assert img.size == (frontcover.W, frontcover.H)
        failed = [(n, d) for n, ok, d in frontcover.gates(pid, img) if not ok]
        assert not failed, (pid, failed)


def test_the_series_is_distinct_on_a_grid(covers):
    assert all(ok for _, ok, _ in frontcover.series_gates(covers))


def test_thumb_is_square_and_scene_has_the_asked_size(covers):
    img = covers["debt-payoff-planner"]
    assert frontcover.thumb(img, 600).size == (600, 600)
    assert frontcover.scene(img, None, ["Free download"], (960, 540), spreadsheet=True).size == (960, 540)


def test_dark_cover_scene_is_not_dark(covers):
    s = frontcover.scene(covers["debt-payoff-planner"], None, [], (960, 540), spreadsheet=True).convert("L")
    assert __import__("numpy").asarray(s).mean() > 120


def test_debt_planner_is_a_free_gift_and_never_a_paid_offer(monkeypatch):
    monkeypatch.setattr(offer, "settings", lambda: {"shop_urls": {"debt-payoff-planner": "https://example.com/l/x"}, "paid_every": 3, "copy": {}})
    d = {x["slug"]: x for x in offer.destinations()}
    assert d["debt-payoff-planner"]["kind"] == "gift"


def test_refresh_changes_nothing_when_a_picture_is_missing(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(shop, "token_present", lambda: True)
    monkeypatch.setattr(shop.safety, "guard", lambda *_: None)
    monkeypatch.setattr(shop.listing, "OUT", tmp_path)
    monkeypatch.setattr(shop, "_run", lambda argv, timeout=600: calls.append(argv[:2]) or {"products": [{"id": "abc", "name": shop.listing.products("debt-payoff-planner")[0]["gumroad"]["name"], "published": False, "price": 0}]})
    with pytest.raises(ProviderError, match="build the pack first"):
        shop.refresh("debt-payoff-planner")
    assert calls == [["products", "list"]]
