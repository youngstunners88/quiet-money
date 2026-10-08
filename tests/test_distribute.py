"""The distribution rails report: honest states from what the repository and environment can see, never a post or a payment."""

import json

from faceless import config, distribute, offer


def state_of(rows, start):
    return next(r for r in rows if r["rail"].startswith(start))


def test_the_default_studio_posts_nothing_and_every_gap_names_the_owners_next_step():
    rows = distribute.status(connected={"youtube": "ok"})
    assert state_of(rows, "posting")["state"] == "manual"
    for r in rows:
        assert r["state"] in {"ready", "needs owner", "manual", "planned"}
        if r["state"] == "needs owner":
            assert r["next"], f"{r['rail']} needs the owner but says nothing about what to do"
    assert "metrics" in state_of(rows, "auto-post: YouTube")["detail"]


def test_upload_post_is_ready_only_with_both_values(monkeypatch):
    assert state_of(distribute.status(connected={}), "auto-post: Upload-Post")["state"] == "needs owner"
    monkeypatch.setenv("UPLOAD_POST_API_KEY", "x")
    assert state_of(distribute.status(connected={}), "auto-post: Upload-Post")["state"] == "needs owner"
    monkeypatch.setenv("UPLOAD_POST_USER", "u")
    assert state_of(distribute.status(connected={}), "auto-post: Upload-Post")["state"] == "ready"


def test_the_muapi_youtube_publisher_is_not_offered_as_the_rail_because_it_has_no_synthetic_flag():
    row = state_of(distribute.status(connected={}), "auto-post: Muapi")
    assert row["state"] == "planned" and "no synthetic-content flag" in row["detail"] and "Upload-Post is the better rail" in row["next"]


def test_a_pinned_offer_means_the_profile_link_is_in_place(monkeypatch):
    assert state_of(distribute.status(connected={}), "profile links")["state"] == "needs owner"
    offer.append_row({"video_id": "v1", "slug": "checklist", "status": "pinned"})
    assert state_of(distribute.status(connected={}), "profile links")["state"] == "ready"


def test_the_email_rail_lists_exactly_what_is_missing(monkeypatch):
    nl = config.load().setdefault("newsletter", {})
    monkeypatch.setitem(nl, "form_action", "")
    monkeypatch.setitem(nl, "postal_address", "")
    row = state_of(distribute.status(connected={}), "email list")
    assert "form_action" in row["next"] and "postal_address" in row["next"]
    monkeypatch.setitem(nl, "form_action", "https://esp.example/sub")
    monkeypatch.setitem(nl, "postal_address", "1 Main St, Town")
    assert state_of(distribute.status(connected={}), "email list")["state"] in {"ready", "needs owner"}
    assert "form_action" not in state_of(distribute.status(connected={}), "email list")["next"]


def test_a_paid_product_counts_only_with_a_live_url(monkeypatch):
    assert state_of(distribute.status(connected={}), "paid products")["state"] == "needs owner"
    monkeypatch.setitem(config.load()["offer"], "shop_urls", {"debt-payoff-planner": "https://shop.example/debt"})
    row = state_of(distribute.status(connected={}), "paid products")
    assert row["state"] == "ready" and row["detail"].startswith("1 of ")


def test_live_check_reports_the_hub_answering_or_not(monkeypatch):
    monkeypatch.setattr(distribute, "_hub_live", lambda url: (True, "HTTP 200"))
    assert state_of(distribute.status(live=True, connected={}), "hub page published")["state"] == "ready"
    monkeypatch.setattr(distribute, "_hub_live", lambda url: (False, "HTTP 404"))
    row = state_of(distribute.status(live=True, connected={}), "hub page published")
    assert row["state"] == "needs owner" and "404" in row["detail"]
    assert not [r for r in distribute.status(connected={}) if r["rail"] == "hub page published"]       # offline by default


def test_render_and_json_round_trip():
    rows = distribute.status(connected={})
    text = distribute.render(rows)
    assert text.count("\n") >= len(rows) and "next:" in text
    assert json.loads(distribute.as_json(rows)) == rows
