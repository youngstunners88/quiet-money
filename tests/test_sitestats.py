"""O15: cookieless analytics on the pages only with a token-shaped project token from the environment; the stats reader counts the funnel."""

import json

from faceless import config, site, sitestats
from faceless.config import Paths

TOKEN = "phc_" + "A1b2C3d4E5f6G7h8J9k0L1m2N3"   # made up: the shape, not a real token (not-real)


def test_no_token_no_tag_and_the_privacy_page_says_so(monkeypatch):
    monkeypatch.setattr(config, "env", lambda name, *a: None)
    assert site.analytics_snippet() == ""
    assert "do not run an analytics tag" in site.privacy_page()


def test_a_token_shaped_project_token_adds_cookieless_tracking(monkeypatch):
    monkeypatch.setattr(config, "env", lambda name, *a: TOKEN if name == "POSTHOG_TOKEN" else "personal-secret-not-real")
    tag = site.analytics_snippet()
    assert TOKEN in tag and '"persistence": "memory"' in tag and '"disable_session_recording": true' in tag
    assert "shop_click" in tag and "calculator_used" in tag and "personal-secret" not in tag
    assert "cookieless" in site.privacy_page()
    for bad in ("sk-not-a-posthog-token-not-real", "phc_x</script><script>alert(1)"):
        monkeypatch.setattr(config, "env", lambda name, *a, b=bad: b)
        assert site.analytics_snippet() == ""            # anything not shaped like a project token never reaches a page


def test_pull_counts_the_funnel_and_appends_a_row(tmp_path, monkeypatch):
    monkeypatch.setattr(sitestats, "LOG", tmp_path / "site.jsonl")
    rows = {"events": [["$pageview", 200], ["shop_click", 5], ["calculator_used", 12], ["other", 9]], "pages": [["/rules/x/", 80]]}
    r = sitestats.pull(7, rows=rows)
    assert (r["pageviews"], r["calculator_uses"], r["shop_clicks"], r["shop_click_rate"]) == (200, 12, 5, 0.025)
    assert json.loads((tmp_path / "site.jsonl").read_text())["top_pages"][0] == {"path": "/rules/x/", "views": 80}
    assert sitestats.latest()["pageviews"] == 200
