import html
import re

import pytest

from faceless import config, offer, site


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setitem(config.load()["offer"], "shop_urls", {"daily-quiet-money-planner": "https://shop.example/planner"})


def test_no_page_and_no_links_while_the_listing_is_not_live(monkeypatch):
    monkeypatch.setitem(config.load()["offer"], "shop_urls", {})
    assert site.planner_page() == "" and site.planner_line("../") == ""


def test_the_page_sells_from_the_live_url_with_tracking_and_no_ratings(live):
    page = site.planner_page()
    buys = re.findall(r'data-buy href="([^"]+)"', page)
    assert len(buys) == 2 and all(html.unescape(b) == "https://shop.example/planner?utm_source=site&utm_medium=planner_page&utm_campaign=daily-quiet-money-planner" for b in buys)
    assert "gumroad.com" not in page                                     # nothing hard-coded: the URL comes from shop_urls
    price = offer.catalog()["daily-quiet-money-planner"]["price"]
    assert f'"price": "{price:.2f}"' in page or f'"price":"{price:.2f}"' in page
    for word in ("aggregateRating", "ratingValue", "reviewCount", '"review"'):
        assert word not in page
    assert 'noindex' not in page


def test_the_page_text_passes_the_claim_check_and_carries_the_disclosures(live):
    body = re.sub(r"<script.*?</script>", " ", site.planner_page(), flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    assert offer.violations(text) == []
    for need in ("not financial advice", "AI assistance", "30-day refund", "not medical advice"):
        assert need in text


def test_the_page_numbers_match_the_book():
    from faceless import planner_wellness, product_planner
    assert site.PLANNER_FACTS["pages"] == product_planner.FRONT + 365 + len(planner_wellness.kept()) + product_planner.BACK
    assert site.PLANNER_FACTS["wellness"] == len(planner_wellness.kept())
