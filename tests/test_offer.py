"""The offer layer: one offer per video, from vetted copy, claim-checked, tracked where a link can be tapped, logged append-only.
Nothing here reaches a network or a model, and nothing posts."""

import json

import pytest

from faceless import config, gauntlet, offer, site
from faceless.config import Paths
from faceless.pipeline import package
from faceless.providers import publish
from faceless.state import Job

HUB = "https://youngstunners88.github.io/quiet-money/links/"


@pytest.fixture
def live(monkeypatch):
    """Two products have live listings; the owner has said so in [offer] shop_urls."""
    cfg = config.load()
    monkeypatch.setitem(cfg["offer"], "shop_urls", {"debt-payoff-planner": "https://shop.example/debt", "rat-race-escape-planner": "https://shop.example/rat"})
    return cfg


def row(vid, slug="checklist", status="draft"):
    return {"video_id": vid, "slug": slug, "status": status, "pillar": "math"}


# ---------------------------------------------------------------- the claim check

@pytest.mark.parametrize("text", [
    "Guaranteed to fix your budget", "You will make $5,000 a month", "Make $500 a week from home", "Build passive income now",
    "Risk-free way to save", "10% returns every year", "Get rich with this", "Clear your debt fast", "This is financial advice",
    "You should buy this fund", "Become a millionaire", "Earn $300 today"])
def test_the_claim_check_refuses_money_promises(text):
    assert offer.violations(text), text


@pytest.mark.parametrize("text", [
    "Free 60-second money reset checklist is in my bio. Educational only, not financial advice.",
    "The Debt Payoff & Compound Interest Planner is in my bio (paid). Educational only, not financial advice.",
    "Not financial advice.", "Free money reset checklist: link in bio.", "See what a $15 subscription costs over ten years."])
def test_the_claim_check_lets_the_built_in_copy_through(text):
    assert offer.violations(text) == []


def test_every_built_in_line_for_every_product_passes_the_check_and_fits_a_comment():
    for p in offer.catalog():
        dest = {"slug": p, "kind": "paid", "name": offer.catalog()[p]["name"], "short": "The " + offer.catalog()[p]["name"], "price": 1}
        for field, template in offer.COPY["paid"].items():
            text = offer._fill(template, dest, HUB)
            assert not offer.violations(text), (p, field, text)
        assert len(offer._fill(offer.COPY["paid"]["pinned"], dest, HUB)) <= offer.PINNED_MAX, p
    for template in offer.COPY["free"].values():
        assert not offer.violations(offer._fill(template, offer.destinations()[0], HUB))


# ---------------------------------------------------------------- what is offered

def test_with_no_live_listing_every_video_gets_the_free_checklist():
    for pillar in ("story", "math", "psychology", "myth", "playbook", "escape"):
        o = offer.build(f"v-{pillar}", pillar, "Title", history=[row("a"), row("b"), row("c")])
        assert o["slug"] == "checklist" and o["status"] == "draft" and o["problems"] == []


def test_a_product_without_a_live_url_is_never_an_offer(monkeypatch):
    monkeypatch.setitem(config.load()["offer"], "shop_urls", {"debt-payoff-planner": "http://not-https.example", "not-in-catalog": "https://x.example"})
    assert [d["slug"] for d in offer.destinations()] == ["checklist"]


def test_the_free_list_leads_then_the_matching_product_follows_and_never_twice_running(live):
    quiet = [row("a"), row("b")]
    assert offer.choose("math", [])["slug"] == "checklist"                                # a cold start builds the list first
    assert offer.choose("math", quiet[:1])["slug"] == "checklist"
    assert offer.choose("math", quiet)["slug"] == "debt-payoff-planner"                   # two free ones, then the match
    assert offer.choose("escape", quiet)["slug"] == "rat-race-escape-planner"
    assert offer.choose("playbook", quiet)["slug"] == "checklist"                         # a how-to always points at the free checklist
    assert offer.choose("psychology", quiet)["slug"] == "checklist"                       # its product is not live
    assert offer.choose("math", [row("a", "debt-payoff-planner"), row("b")])["slug"] == "checklist"     # too soon after a paid one
    after = [row("a", "debt-payoff-planner"), row("b"), row("c")]
    assert offer.choose("math", after)["slug"] == "checklist"                             # same product twice running is refused
    assert offer.choose("escape", after)["slug"] == "rat-race-escape-planner"


def test_a_paid_offer_names_the_product_and_says_paid(live):
    o = offer.build("v1", "math", "T", history=[row("a"), row("b")])
    assert o["kind"] == "paid" and "(paid)" in o["pinned_comment"] and "Debt Payoff" in o["pinned_comment"] and len(o["pinned_comment"]) <= 150
    assert "not financial advice" in o["pinned_comment"] and o["utm_campaign"] == "debt-payoff-planner"


# ---------------------------------------------------------------- links

def test_the_video_link_is_the_hub_with_utm_parts_and_exactly_one():
    o = offer.build("2026-10-08-s1-math-x", "math", "T", history=[])
    assert o["url"].startswith(HUB + "?utm_source=youtube&utm_medium=short&utm_campaign=checklist&utm_content=2026-10-08-s1-math-x")
    assert o["description_line"].count("http") == 1 and o["url"] in o["description_line"]


def test_profile_links_are_one_page_tagged_by_platform():
    links = offer.profile_links()
    assert set(links) == {"tiktok", "youtube", "instagram"}
    assert all(u.startswith(HUB) and f"utm_source={p}" in u and "utm_medium=bio" in u for p, u in links.items())


def test_an_empty_site_url_means_no_offer_not_an_invented_link(monkeypatch):
    monkeypatch.setitem(config.load()["site"], "base_url", "")
    o = offer.build("v1", "math", "T", history=[])
    assert o["status"] == "LINK_MISSING" and o["url"] == "" and o["description_line"] == "" and offer.tracked("", "a", "b", "c") == ""
    assert "LINK_MISSING" in offer.render_md(o)
    meta = {"caption": "Hello #money", "description": "d"}
    assert offer.apply_to_meta(dict(meta), o) == meta                                   # nothing is written into a post


def test_an_owner_edit_that_makes_a_promise_falls_back_to_the_safe_line(monkeypatch):
    monkeypatch.setitem(config.load()["offer"], "copy", {"free": {"pinned": "Guaranteed freedom, link in bio", "caption": "Free checklist: link in bio."}})
    o = offer.build("v1", "math", "T", history=[])
    assert o["pinned_comment"] == offer.COPY["free"]["pinned"] and any("pinned copy refused" in p for p in o["problems"])
    assert o["caption_line"] == "Free checklist: link in bio."                          # the clean edit is kept


def test_an_owner_description_with_two_links_is_a_problem(monkeypatch):
    monkeypatch.setitem(config.load()["offer"], "copy", {"free": {"description": "See {url} and https://other.example"}})
    assert any("2 links" in p for p in offer.build("v1", "math", "T", history=[])["problems"])


# ---------------------------------------------------------------- the caption and the pack

def test_the_call_to_action_goes_before_the_hashtags_once():
    cap = "Line one.\nLine two. #money #personalfinance"
    out = offer.put_in_caption(cap, "Free checklist: link in bio.")
    assert out == "Line one.\nLine two.\n\nFree checklist: link in bio.\n\n#money #personalfinance"
    assert offer.put_in_caption(out, "Free checklist: link in bio.") == out
    assert offer.put_in_caption("#only #tags", "CTA") == "#only #tags\n\nCTA"


def _script(**kw):
    return {"title": "The Subscription Creep", "description": "Small charges add up.", "caption": "Audit your statement. #money #personalfinance",
            "hashtags": ["#money", "#personalfinance"], "first_comment": "Which one will you cancel?", **kw}


@pytest.fixture
def pkg_job(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "output", tmp_path / "out")

    def make(jid="2026-10-08-s1-math-x"):
        job = Job(id=jid, pillar="math", topic="t", day="2026-10-08")
        job.dir.mkdir(parents=True, exist_ok=True)
        return job
    return make


def test_package_puts_the_offer_in_the_caption_and_the_description_and_the_gate_passes(pkg_job):
    meta = package.run(pkg_job(), _script())
    assert "Free money reset checklist: link in bio." in meta["caption"] and meta["caption"].rstrip().endswith("#personalfinance")
    assert meta["description"].count("http") == 1 and "utm_content=2026-10-08-s1-math-x" in meta["description"]
    assert meta["offer"]["status"] == "draft" and meta["first_comment"] == "Which one will you cancel?"
    gate = next(g for g in gauntlet.check_package(meta) if g.name == "offer_cta")
    assert gate.passed and not gate.hard


def test_the_gate_flags_a_missing_offer_or_a_second_link_but_never_holds_the_video():
    base = {"description": "x. Educational content, not financial advice. AI-assisted.", "caption": "x #a"}
    missing = next(g for g in gauntlet.check_package(base) if g.name == "offer_cta")
    assert not missing.passed and not missing.hard
    two = {**base, "offer": {"status": "draft", "pinned_comment": "p", "caption_line": "c", "description_line": "d"},
           "description": base["description"] + " https://a.example https://b.example"}
    gate = next(g for g in gauntlet.check_package(two) if g.name == "offer_cta")
    assert not gate.passed and not gate.hard and "more than one link" in gate.detail
    promise = {**base, "offer": {"status": "draft", "pinned_comment": "Guaranteed freedom", "caption_line": "c", "description_line": "d"}}
    assert not next(g for g in gauntlet.check_package(promise) if g.name == "offer_cta").passed


def test_a_failure_in_the_offer_layer_falls_back_to_the_plain_link_line(monkeypatch, pkg_job):
    def boom(*a, **k):
        raise RuntimeError("ledger unreadable")
    monkeypatch.setattr(offer, "build", boom)
    meta = package.run(pkg_job("v2"), _script())
    assert "Free 7-day Money Reset checklist + calculators: " + config.load()["channel"]["link_in_bio"] in meta["description"] and "offer" not in meta


def test_post_md_pins_the_offer_comment_and_names_the_profile_link():
    meta = {"title": "T", "description": "D", "caption": "C #a", "offer": {"pinned_comment": "Free checklist in my bio."}}
    md = publish.render_post(0, "2026-10-08 07:30 EDT", meta)
    assert "- [ ] Pin this comment: Free checklist in my bio." in md and "hub page" in md and md.startswith("# Slot 1: T")
    assert "Pin a comment with the link-in-bio CTA" in publish.render_post(2, "x", {k: v for k, v in meta.items() if k != "offer"})


# ---------------------------------------------------------------- the ledger

def test_record_writes_the_pack_and_one_row_once_and_never_regresses_a_pin(tmp_path):
    folder = tmp_path / "queue" / "2026-10-08" / "slot1-math"
    o = offer.build("v1", "math", "T", history=[], post_day="2026-10-08")
    first = offer.record("v1", folder, o)
    again = offer.record("v1", folder, o)
    assert first["written"] and not again["written"] and len(offer.rows()) == 1
    assert (folder / "OFFER.md").read_text(encoding="utf-8").startswith("# Offer:")
    offer.mark("v1", "pinned")
    assert offer.record("v1", folder, o)["written"] is False                              # a draft never overwrites a pin
    assert [r["status"] for r in offer.rows()] == ["draft", "pinned"] and offer.latest()[0]["status"] == "pinned"
    with pytest.raises(KeyError):
        offer.mark("nope", "pinned")
    with pytest.raises(ValueError):
        offer.mark("v1", "posted")


def test_the_ledger_skips_damaged_lines_and_the_latest_row_wins(tmp_path):
    offer.OFFERS.write_text('{"video_id": "a", "slug": "checklist", "status": "draft"}\nnot json\n[1]\n{"video_id": "a", "slug": "checklist", "status": "pinned"}\n',
                            encoding="utf-8")
    assert [r["status"] for r in offer.rows()] == ["draft", "pinned"] and offer.latest() == [{"video_id": "a", "slug": "checklist", "status": "pinned"}]
    assert offer.status()["pinned"] == 1 and offer.status()["draft"] == 0


def _packed_job(tmp_path, monkeypatch, jid="2026-10-08-s1-math-x", day="2026-10-08", legacy=True):
    jobs, queue = tmp_path / "jobs", tmp_path / "queue"
    monkeypatch.setattr(Paths, "jobs", jobs)
    monkeypatch.setattr(Paths, "queue", queue)
    monkeypatch.setattr(Paths, "output", tmp_path / "out")
    folder = queue / day / "slot1-math"
    folder.mkdir(parents=True)
    meta = {"title": "T", "description": "Desc.\n\nFree 7-day Money Reset checklist + calculators: " + config.load()["channel"]["link_in_bio"] + "\n\nEducational content.",
            "caption": "Cap #money", "post_at": "2026-10-08T07:30:00-04:00"}
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (folder / "POST.md").write_text("old", encoding="utf-8")
    job = Job(id=jid, pillar="math", topic="t", day=day, status="published", scores={"gauntlet": 95, "passed": True},
              artifacts={"publish": {"local": {"folder": str(folder)}}})
    job.save()
    return job, folder


def test_batch_repairs_a_pack_made_before_the_offer_layer_and_is_idempotent(tmp_path, monkeypatch):
    job, folder = _packed_job(tmp_path, monkeypatch)
    res = offer.batch("2026-10-08")
    assert res["videos"] == 1 and res["with_offer"] == 1 and res["written"] == 1 and res["problems"] == [] and res["repaired"] == 1
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    assert "link in bio" in meta["caption"] and meta["description"].count("http") == 1 and "utm_content=2026-10-08-s1-math-x" in meta["description"]
    assert "Educational content." in meta["description"]                                   # the rest of the description is untouched
    post = (folder / "POST.md").read_text(encoding="utf-8")
    assert "Post at: 2026-10-08 07:30 EDT" in post and "Pin this comment:" in post
    before = (offer.OFFERS.read_text(encoding="utf-8"), (folder / "POST.md").read_text(encoding="utf-8"))
    again = offer.batch("2026-10-08")
    assert again["written"] == 0 and again["with_offer"] == 1 and "repaired" not in again
    assert (offer.OFFERS.read_text(encoding="utf-8"), (folder / "POST.md").read_text(encoding="utf-8")) == before
    assert offer.unoffered("2026-10-08") == []


def test_unoffered_lists_a_passed_video_with_no_row_and_a_held_one_is_ignored(tmp_path, monkeypatch):
    job, folder = _packed_job(tmp_path, monkeypatch)
    assert offer.unoffered("2026-10-08") == [job.id]
    held = Job(id="h1", pillar="math", topic="t", day="2026-10-08", status="held", scores={"passed": False}, artifacts={"publish": {"local": {"folder": str(folder)}}})
    held.save()
    assert offer.unoffered("2026-10-08") == [job.id]


# ---------------------------------------------------------------- the hub page and the signup form

def test_the_hub_lists_the_free_checklist_first_and_no_product_that_is_not_live():
    html = site.hub_page()
    assert html.index('data-o="checklist"') < html.index('data-o="tools"') < html.index('data-o="rules"')
    assert "Paid" not in html and "noindex" in html and "utm_source=hub" in html and "not financial advice" in html
    assert "<form" not in html                                                              # no signup form until the owner sets one


def test_a_live_product_gets_a_paid_card_with_an_outbound_utm_link_and_no_price(live):
    html = site.hub_page()
    assert 'data-o="debt-payoff-planner"' in html and "https://shop.example/debt?utm_source=quietmoney" in html and 'class="badge">Paid' in html
    assert "$19" not in html


def test_the_hub_is_not_in_the_sitemap_or_the_llms_file(tmp_path, monkeypatch):
    monkeypatch.setattr(site, "SITE", tmp_path / "site")
    monkeypatch.setattr(site, "all_jobs", lambda: [])
    site.build()
    assert (tmp_path / "site" / "links" / "index.html").exists()
    assert "/links/" not in (tmp_path / "site" / "sitemap.xml").read_text(encoding="utf-8")
    assert "/links/" not in (tmp_path / "site" / "llms.txt").read_text(encoding="utf-8")


def test_the_signup_form_exists_only_with_an_https_action_and_goes_on_both_pages(tmp_path, monkeypatch):
    nl = config.load().setdefault("newsletter", {})
    monkeypatch.setitem(nl, "form_action", "http://insecure.example/sub")
    assert site.signup_form() == "" and "<form" not in site.hub_page()
    monkeypatch.setitem(nl, "form_action", 'https://esp.example/subscribe/abc"onmouseover="x')
    form = site.signup_form()
    assert 'action="https://esp.example/subscribe/abc&quot;onmouseover=&quot;x"' in form and 'type="email"' in form and "Unsubscribe any time" in form
    monkeypatch.setitem(nl, "form_email_field", "email<script>")
    assert 'name="emailscript"' in site.signup_form()
    assert "<form" in site.hub_page()
    monkeypatch.setattr(site, "SITE", tmp_path / "site")
    monkeypatch.setattr(site, "all_jobs", lambda: [])
    site.build()
    assert "<form" in (tmp_path / "site" / "money-reset" / "index.html").read_text(encoding="utf-8")


def test_the_owners_analytics_tag_is_inserted_as_written_on_every_page_or_not_at_all(tmp_path, monkeypatch):
    assert "analytics-test" not in site.hub_page()
    snippet = tmp_path / "snippet.html"
    snippet.write_text('<script defer src="https://stats.example/analytics-test.js"></script>', encoding="utf-8")
    monkeypatch.setattr(Paths, "root", tmp_path)
    monkeypatch.setitem(config.load()["site"], "head_snippet", "snippet.html")
    assert "analytics-test.js" in site.hub_page()
    monkeypatch.setitem(config.load()["site"], "head_snippet", "missing.html")
    assert "analytics-test" not in site.hub_page()


def test_a_query_value_cannot_break_out_of_the_hub_script():
    js = site.HUB_JS
    assert "replace(/[^a-z0-9._-]/g,'')" in js and "innerHTML" not in js and "eval(" not in js


# ---------------------------------------------------------------- the orchestrator step

def test_after_publishing_the_orchestrator_writes_the_offer_pack_and_one_ledger_row(tmp_path, monkeypatch, pkg_job):
    from faceless import orchestrator
    job = pkg_job("2026-10-08-s1-math-x")
    meta = package.run(job, _script())
    folder = tmp_path / "queue" / "2026-10-08" / "slot1-math"
    job.artifacts["publish"] = {"local": {"folder": str(folder)}}
    orchestrator._offer(job, meta)
    assert (folder / "OFFER.md").exists() and [r["video_id"] for r in offer.rows()] == [job.id]
    orchestrator._offer(job, meta)                                                           # a re-run adds nothing
    assert len(offer.rows()) == 1
    job.artifacts["publish"] = {"local": {}}
    orchestrator._offer(job, meta)                                                           # no pack folder: nothing to do, nothing breaks
    orchestrator._offer(job, {k: v for k, v in meta.items() if k != "offer"})                # no offer on this video: same
    assert len(offer.rows()) == 1


def test_a_failure_while_recording_an_offer_never_costs_the_video_its_slot(tmp_path, monkeypatch, pkg_job):
    from faceless import events, orchestrator
    job = pkg_job("2026-10-08-s2-math-y")
    meta = package.run(job, _script())
    job.artifacts["publish"] = {"local": {"folder": str(tmp_path / "queue" / "2026-10-08" / "slot2-math")}}
    monkeypatch.setattr(offer, "record", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    orchestrator._offer(job, meta)
    assert any("offer skipped" in n for n in job.notes) and any(e["type"] == "OFFER_FAILED" for e in events.read())
