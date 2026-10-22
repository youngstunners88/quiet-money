"""The service desk's client hunt: it must never contact anyone, never queue a draft that promises a result or names a price, never invent a
fact about a project, and never pad a batch to hit a target. Nothing here touches the network."""

import json

import pytest

from faceless import decide, outbound


@pytest.fixture
def desk(tmp_path, monkeypatch):
    for name, sub in (("DESK", ""), ("LEADS", "leads"), ("PACKAGES", "outbound"), ("REVIEWS", "reviews")):
        monkeypatch.setattr(outbound, name, tmp_path / sub if sub else tmp_path)
    monkeypatch.setattr(outbound, "OUTCOMES", tmp_path / "outcomes.jsonl")
    monkeypatch.setattr(outbound, "SEEN", tmp_path / "seen.json")
    monkeypatch.setattr(outbound, "LOG", tmp_path / "durable.jsonl")
    monkeypatch.setattr(outbound, "MODELS", tmp_path / "models.json")
    (tmp_path / "PROOF.md").write_text("- `volume`: \"38 Web3 projects, 130 posts, 123 live X links as of 1 Oct 2026.\"\n", encoding="utf-8")
    (tmp_path / "models.json").write_text(json.dumps({"jobs": {j: {"slug": ["vendor/stand-in:free"]} for j in
                                                      ("research", "first_touch", "followups")}}), encoding="utf-8")
    return tmp_path


PROTOCOLS = [
    {"name": "Right Size", "category": "Lending", "chain": "Base", "chains": ["Base"], "tvl": 120_000_000, "twitter": "rightsize",
     "url": "https://rightsize.example", "description": "lending", "listedAt": None, "change_7d": 4.0},
    {"name": "Too Small", "category": "Dexs", "chain": "Base", "tvl": 10_000, "twitter": "small", "url": "https://small.example"},
    {"name": "Mega Cap", "category": "CEX", "chain": "Multi", "tvl": 90_000_000_000, "twitter": "mega", "url": "https://mega.example"},
    {"name": "No Handle", "category": "Dexs", "chain": "Base", "tvl": 50_000_000, "url": "https://nohandle.example"},
]

CARD_FIELDS = {"what_it_is": "a lending protocol", "posts_video": False, "cadence": "5 posts a week",
               "last_posts": ["v3 fee change", "audit published"], "content_gap": "no video at all, active text feed",
               "dated_event": {"what": "mainnet", "when": "2026-11-10", "source": "https://rightsize.example"},
               "budget_signal": {"what": "raise", "source": "https://rightsize.example"},
               "contact": {"route": "partnerships email", "value": "partners@rightsize.example",
                           "source": "https://rightsize.example", "public": True}, "unknown": []}


def _ask(out):
    """A stand-in for one free-model call: panel.ask's shape, no network."""
    return lambda slug, brief: {"out": dict(out), "usd": 0.0, "model_used": slug}


# ------------------------------------------------------------------ discovery

def test_candidates_keep_the_size_band_and_need_a_public_handle_and_site(desk):
    names = [c["name"] for c in outbound.candidates(10, protocols=PROTOCOLS)]
    assert names == ["Right Size"]


def test_a_project_already_in_the_desk_is_never_researched_twice(desk):
    outbound.save_lead({"slug": "right-size", "name": "Right Size", "status": "skip"})
    assert outbound.candidates(10, protocols=PROTOCOLS) == []


def test_a_freshly_listed_project_is_screened_before_a_bigger_quiet_one(desk):
    import time
    fresh = {**PROTOCOLS[0], "name": "Fresh Launch", "tvl": 6_000_000, "twitter": "fresh",
             "url": "https://fresh.example", "listedAt": time.time() - 86400}
    order = [c["name"] for c in outbound.candidates(10, protocols=[PROTOCOLS[0], fresh])]
    assert order == ["Fresh Launch", "Right Size"]


# ------------------------------------------------------------------ research: a card is pitchable or it is a skip

def test_with_no_published_address_the_route_is_the_project_s_own_public_account(desk, monkeypatch):
    """A crypto project is approached on the account it published itself. That is public and theirs - unlike a guessed address."""
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page about the project" * 30)
    cand = outbound.candidates(1, protocols=PROTOCOLS)[0]
    card = outbound.research(cand, ask=_ask({**CARD_FIELDS, "contact": {"route": None, "value": None}}))
    assert card["status"] == "researched"
    assert card["contact"] == {"route": "DM-open X account", "value": "https://x.com/rightsize",
                               "source": outbound.PROTOCOLS, "public": True}


def test_an_invented_address_is_dropped_for_the_public_account(desk, monkeypatch):
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page" * 100)
    cand = outbound.candidates(1, protocols=PROTOCOLS)[0]
    for guess in ({"route": "partnerships email", "value": "partnerships@example.com"},
                  {"route": "guessed", "value": "team"}):
        card = outbound.research(cand, ask=_ask({**CARD_FIELDS, "contact": guess}))
        assert card["contact"]["route"] == "DM-open X account", guess


def test_a_project_with_nothing_specific_to_say_about_it_is_a_skip(desk, monkeypatch):
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page" * 100)
    cand = outbound.candidates(1, protocols=PROTOCOLS)[0]
    card = outbound.research(cand, ask=_ask({**CARD_FIELDS, "last_posts": [], "dated_event": None}))
    assert card["status"] == "skip" and card["skip_reason"] == "nothing_specific_to_say"


def test_a_card_with_no_content_gap_is_a_skip(desk, monkeypatch):
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page" * 100)
    cand = outbound.candidates(1, protocols=PROTOCOLS)[0]
    card = outbound.research(cand, ask=_ask({**CARD_FIELDS, "content_gap": None}))
    assert card["status"] == "skip" and card["skip_reason"] == "no_content_gap"


def test_a_project_whose_pages_cannot_be_read_is_a_skip_not_a_guess(desk, monkeypatch):
    monkeypatch.setattr(outbound, "fetch_text", lambda url: None)
    cand = outbound.candidates(1, protocols=PROTOCOLS)[0]
    card = outbound.research(cand, ask=_ask(CARD_FIELDS))
    assert card["status"] == "skip" and card["skip_reason"] == "pages_unreadable"
    assert card["signals"]["content_gap"] is None


def test_a_good_card_keeps_its_sources_and_the_sized_signal(desk, monkeypatch):
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page" * 100)
    card = outbound.research(outbound.candidates(1, protocols=PROTOCOLS)[0], ask=_ask(CARD_FIELDS))
    assert card["status"] == "researched"
    assert card["identity"]["size_signal"]["source"] == outbound.PROTOCOLS
    assert "$120,000,000" in card["identity"]["size_signal"]["value"]


# ------------------------------------------------------------------ scoring

def test_a_score_answer_is_scaled_off_the_level_index_before_a_threshold_sees_it():
    q = outbound.lead_questions()["fit"]
    assert len(q.levels) == 5
    assert outbound._norm(q, 4) == 1.0 and outbound._norm(q, 2) == 0.5
    assert outbound._norm(outbound.lead_questions()["budget"], 0.49) == pytest.approx(0.49)


def test_an_unconfident_jev_answer_leaves_the_code_deciding(desk, monkeypatch):
    def unsure(questions, state, job=None, images=None, backend=None):
        return {n: decide.Decision(n, q.fallback, 1.0, "heuristic", jev_value=4, jev_confidence=0.55) for n, q in questions.items()}

    monkeypatch.setattr(decide, "ask", unsure)
    card = {"slug": "x", "name": "X", "identity": {"category": "lending", "size_signal": {"value": "TVL $120,000,000"}},
            "social": {"x": {"posts_video": False}}, "signals": {"dated_event": {"when": "2026-11-10"}, "budget_signal": {"what": "raise"}},
            "contact": {"value": "partners@x.example"}}
    out = outbound.score(card)
    assert out["backend"] == "heuristic" and out["fit_confidence"] is None and out["verdict"] in ("pursue", "review")


def test_a_cap_or_an_outage_while_scoring_does_not_stop_the_run(desk, monkeypatch):
    monkeypatch.setattr(decide, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("daily cap reached")))
    out = outbound.score({"slug": "x", "name": "X", "identity": {}, "social": {}, "signals": {}, "contact": {}})
    assert out["backend"] == "heuristic" and out["verdict"] == "review"


# ------------------------------------------------------------------ the gates

def _pkg(body, personalization=(("their v3 fee change", "https://rightsize.example"),)):
    return {"slug": "x", "first_touch": {"subject": None, "body": body},
            "followups": [{"step": 1, "days_after": 3, "body": "one example closest to your niche."}],
            "personalization": [{"claim": c, "source": s} for c, s in personalization]}


def test_a_promised_result_holds_a_draft_however_the_model_scored_it(desk, monkeypatch):
    monkeypatch.setattr(decide, "ask", lambda *a, **k: {n: decide.Decision(n, 1.0, 1.0, "jev", jev_value=1.0, jev_confidence=0.99)
                                                        for n in ("personalization", "spam_risk", "promise_free")})
    g = outbound.gate(_pkg("Your v3 fee change deserves video. We guarantee 100k views."))
    assert g["verdict"] == "hold" and g["banned_language"] is True


def test_a_price_in_a_draft_holds_it(desk, monkeypatch):
    monkeypatch.setattr(decide, "ask", lambda *a, **k: {})
    assert outbound.gate(_pkg("Your v3 fee change deserves video. $500 per clip."))["verdict"] == "hold"


def test_a_draft_that_names_nothing_sourced_is_held_not_softened(desk, monkeypatch):
    monkeypatch.setattr(decide, "ask", lambda *a, **k: {})
    assert outbound.gate(_pkg("I love what you are building. Want some video?", personalization=()))["verdict"] == "hold"


def test_a_clean_specific_draft_passes(desk, monkeypatch):
    monkeypatch.setattr(decide, "ask", lambda *a, **k: {})
    body = ("Your last two posts were the v3 fee change and the audit, both text. One 20-second cut of the fee change would travel. "
            "38 Web3 projects, 130 posts, 123 live X links as of 1 Oct 2026. Worth sending two examples closest to your niche?")
    assert outbound.gate(_pkg(body))["verdict"] == "pass"


# ------------------------------------------------------------------ the loop and its limits

def test_the_run_queues_a_package_and_sends_nothing(desk, monkeypatch):
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page" * 100)
    monkeypatch.setattr(decide, "ask", lambda *a, **k: {})
    body = ("Your last two posts were the v3 fee change and the audit, both text. One 20-second cut of the fee change would travel. "
            "38 Web3 projects, 130 posts, 123 live X links as of 1 Oct 2026. Worth sending two examples closest to your niche?")
    draft = {"channel": "email", "angle": "content gap", "tier_pitched": "monthly retainer", "proof_block": "volume",
             "personalization": [{"claim": "their v3 fee change", "source": "https://rightsize.example"}],
             "first_touch": {"subject": "short video for Right Size", "body": body},
             "followups": [{"step": 1, "days_after": 3, "body": "one example closest to your niche."}]}
    r = outbound.run(protocols=PROTOCOLS, ask=lambda slug, brief: {"out": dict(CARD_FIELDS if "research assistant" in brief else draft),
                                                                   "usd": 0.0, "model_used": slug})
    assert [q["name"] for q in r["queued"]] == ["Right Size"]
    pkg = outbound.load_package("right-size")
    assert pkg["approval"] == {"owner_approved": False, "approved_on": None, "sent_on": None}
    assert pkg["gates"]["verdict"] == "pass"
    assert (desk / "reviews" / f"batch-{r['day']}.md").exists()


def test_a_batch_that_produces_nothing_is_reported_as_nothing(desk, monkeypatch):
    monkeypatch.setattr(outbound, "fetch_text", lambda url: None)
    monkeypatch.setattr(decide, "ask", lambda *a, **k: {})
    r = outbound.run(protocols=PROTOCOLS, ask=_ask(CARD_FIELDS))
    assert r["queued"] == [] and r["skipped"] == {"pages_unreadable": 1}
    assert "Nothing passed the gates today" in outbound.report_md(r)


def test_the_kill_switch_stops_the_hunt(desk, monkeypatch):
    monkeypatch.setattr(outbound.safety, "paused", lambda: "owner paused")
    r = outbound.run(protocols=PROTOCOLS)
    assert r["paused"] == "owner paused" and r["queued"] == [] and r["screened"] == 0


def test_the_engine_refuses_to_run_in_any_send_mode_but_owner(desk, monkeypatch):
    monkeypatch.setattr(outbound, "cfg", lambda: {**base_cfg(), "send": "auto"})
    with pytest.raises(RuntimeError, match="never contacts anyone"):
        outbound.run(protocols=PROTOCOLS)


def base_cfg() -> dict:
    from faceless import config
    return {"daily_candidates": 40, "daily_cards": 16, "daily_packages": 8, "tvl_min_usd": 5_000_000, "tvl_max_usd": 5_000_000_000,
            "fit_floor": 0.6, "personalization_floor": 0.7, "spam_ceiling": 0.4, "promise_floor": 0.9, "firecrawl_pages_per_day": 0,
            "send": "owner", "page_chars": 6000, "dead_days": 90, **config.load().get("outbound", {})}


# ------------------------------------------------------------------ models and outcomes

def test_only_free_slugs_are_accepted_for_a_generative_job(desk):
    (desk / "models.json").write_text(json.dumps({"jobs": {"research": {"slug": ["vendor/paid-model", "vendor/ok:free"]}}}), encoding="utf-8")
    assert outbound.models("research") == ["vendor/ok:free"]
    assert outbound.models("missing") == []


def test_an_outcome_is_recorded_with_the_choices_that_produced_the_message(desk):
    outbound.save_lead({"slug": "x", "name": "X", "status": "queued", "decisions": {"fit": 0.8, "pursue": "pursue"}})
    outbound.save_package({"slug": "x", "channel": "email", "angle": "content gap", "tier_pitched": "monthly retainer",
                           "proof_block": "volume", "first_touch": {"body": "hi"}, "followups": [], "gates": {}, "contact": {}})
    outbound.record("x", "reply-positive", note="asked for examples")
    row = json.loads((desk / "outcomes.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["angle"] == "content gap" and row["scores"]["fit"] == 0.8 and row["note"] == "asked for examples"
    assert outbound.load_lead("x")["status"] == "replied"


def test_a_negative_reply_ends_the_lead(desk):
    outbound.save_lead({"slug": "x", "name": "X", "status": "sent", "decisions": {}})
    outbound.record("x", "reply-negative")
    assert outbound.load_lead("x")["status"] == "dead"


def test_a_review_says_when_the_numbers_are_too_small_to_act_on(desk):
    outbound.save_lead({"slug": "x", "name": "X", "status": "sent", "decisions": {}})
    outbound.save_package({"slug": "x", "channel": "email", "angle": "content gap", "tier_pitched": "test drop", "proof_block": "volume",
                           "first_touch": {"body": "hi"}, "followups": [], "gates": {}, "contact": {}})
    outbound.record("x", "sent")
    outbound.record("x", "reply-positive")
    r = outbound.review()
    assert r["sent"] == 1 and r["actionable"] is False and "too small to act on" in r["note"]
    assert r["per"]["angle"]["content gap"] == {"sent": 1, "positive": 1}


# ------------------------------------------------------------------ memory that survives a fresh checkout

def test_the_committed_memory_holds_hashes_not_company_names(desk):
    outbound.save_lead({"slug": "right-size", "name": "Right Size", "status": "queued", "decisions": {}})
    text = (desk / "seen.json").read_text(encoding="utf-8")
    assert "right-size" not in text and "Right Size" not in text
    assert outbound.fingerprint("right-size") in text


def test_a_project_seen_on_an_earlier_day_is_not_screened_again_after_the_cards_are_gone(desk, monkeypatch):
    outbound.remember("right-size", "queued")
    monkeypatch.setattr(outbound, "LEADS", desk / "gone")                 # a fresh container: the cards are not there any more
    assert outbound.candidates(10, protocols=PROTOCOLS) == []


def test_the_durable_outcome_log_carries_the_signal_without_the_words_a_person_wrote(desk):
    outbound.save_lead({"slug": "x", "name": "X", "status": "sent", "decisions": {"fit": 0.8}})
    outbound.save_package({"slug": "x", "channel": "email", "angle": "content gap", "tier_pitched": "test drop", "proof_block": "volume",
                           "first_touch": {"body": "hi"}, "followups": [], "gates": {}, "contact": {}})
    outbound.record("x", "reply-positive", note="they said the fee change post flopped")
    durable = json.loads((desk / "durable.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert durable["slug"] == outbound.fingerprint("x") and "note" not in durable
    assert durable["angle"] == "content gap" and durable["scores"]["fit"] == 0.8


def test_the_code_s_own_fit_follows_the_configured_band_not_a_hard_coded_size(desk):
    """The band in studio.toml is the band the heuristic uses: a project inside it is not failed for being under some other number."""
    def card(tvl):
        return {"slug": "x", "name": "X", "identity": {"category": "lending", "size_signal": {"tvl_usd": tvl}},
                "social": {"x": {"posts_video": False, "last_posts": ["the v3 fee change"]}},
                "signals": {}, "contact": {"value": "https://x.com/x"}}

    assert outbound._heuristic("fit", card(120_000_000)) == 0.8
    assert outbound._heuristic("fit", card(9_000_000)) == 0.65          # inside the band, under fit_strong_usd
    assert outbound._heuristic("fit", card(1_000)) == 0.35              # outside the band
    assert outbound._heuristic("pursue", card(9_000_000)) == "pursue"
    assert outbound._heuristic("pursue", card(1_000)) == "skip"


def test_a_lead_with_nothing_sourced_to_say_is_not_pursued_by_the_code_either(desk):
    quiet = {"slug": "x", "name": "X", "identity": {"category": "lending", "size_signal": {"tvl_usd": 120_000_000}},
             "social": {"x": {"posts_video": False, "last_posts": []}}, "signals": {}, "contact": {"value": "https://x.com/x"}}
    assert outbound._heuristic("pursue", quiet) == "review"


def test_a_rewrite_tells_the_model_which_check_failed(desk, monkeypatch):
    """One rewrite, and it is told what to fix. Asking the same question again and hoping for a different answer is not a rewrite."""
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page" * 100)
    monkeypatch.setattr(decide, "ask", lambda *a, **k: {})
    seen = []

    def ask(slug, brief, max_tokens=None):
        seen.append(brief)
        return {"out": dict(CARD_FIELDS) if "research assistant" in brief else
                {"first_touch": {"subject": None, "body": "I love what you are building."}, "followups": [], "personalization": []},
                "usd": 0.0, "model_used": slug}

    card = outbound.research(outbound.candidates(1, protocols=PROTOCOLS)[0], ask=ask)
    first = outbound.draft(card, ask=ask)
    assert first["gates"]["verdict"] == "hold"                            # nothing sourced: held, not queued
    again = outbound.draft(card, ask=ask, failed=first)
    assert "THE LAST DRAFT FAILED" in seen[-1] and "name something specific" in seen[-1]
    assert again["gates"]["verdict"] == "hold"


def test_the_gate_a_rewrite_is_told_about_is_the_worst_one(desk):
    assert "no promised results" in outbound._worst_gate({"gates": {"banned_language": True, "personalization": 0.1}})
    assert "name something specific" in outbound._worst_gate({"gates": {"personalization": 0.1, "promise_free": 1.0, "spam_risk": 0.9}})
    assert "mass-sent" in outbound._worst_gate({"gates": {"personalization": 0.9, "promise_free": 1.0, "spam_risk": 0.9}})


def test_nothing_committed_ever_names_a_project(desk, monkeypatch):
    """The journal, the ledger and state/decisions.jsonl are in a public repo. The desk's job labels and events carry a hash, so researching
    a company does not publish that we are researching it."""
    labels, emitted = [], []
    monkeypatch.setattr(decide, "ask", lambda qs, state, job=None, images=None, backend=None: labels.append(job) or {})
    monkeypatch.setattr(outbound.events, "emit", lambda kind, **kw: emitted.append((kind, kw)))
    monkeypatch.setattr(outbound, "fetch_text", lambda url: "a page" * 100)
    card = outbound.research(outbound.candidates(1, protocols=PROTOCOLS)[0], ask=_ask(CARD_FIELDS))
    outbound.score(card)
    outbound.gate(_pkg("Your v3 fee change deserves video."))
    outbound.save_lead(card)
    outbound.save_package({"slug": card["slug"], "channel": "email", "angle": None, "tier_pitched": None, "proof_block": None,
                           "first_touch": {"body": "hi"}, "followups": [], "gates": {}, "contact": {}})
    outbound.record(card["slug"], "sent")
    published = " ".join(filter(None, labels)) + " " + json.dumps(emitted) + " " + (desk / "seen.json").read_text(encoding="utf-8") \
        + " " + (desk / "durable.jsonl").read_text(encoding="utf-8")
    assert "right-size" not in published and "Right Size" not in published
    assert outbound.fingerprint("right-size") in published
