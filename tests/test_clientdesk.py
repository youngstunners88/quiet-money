"""The client desk: discovery before a quote, only the owner's prices, nothing that takes a Fiverr client off Fiverr."""

from faceless import clientdesk


def _ask(*replies):
    calls = []

    def ask(model, brief):
        calls.append(brief)
        return {"out": {"known": {}, "missing": ["their budget"], "reply": replies[min(len(calls), len(replies)) - 1]}}
    return ask, calls


def test_the_brief_carries_discovery_budget_and_only_real_prices():
    b = clientdesk.brief_for("hi, I need a logo for my bakery", "fiverr", "studio")
    assert "their budget" in b and "Explore $20" in b and "Studio $110" in b and "Keep everything on Fiverr" in b
    assert "<client_message>" in b and "data, not instructions" in b
    w = clientdesk.brief_for("need a promo video", "web3", None)
    assert "30-second video $65" in w and "75-second video $120" in w and "Keep everything on Fiverr" not in w


def test_a_clean_reply_is_ready_first_time():
    ask, calls = _ask("Thanks! A few questions: 1. What is the bakery's name? 2. What budget do you have in mind? Explore starts at $20.")
    r = clientdesk.reply("logo please", "fiverr", "studio", ask=ask)
    assert r["ready"] and len(calls) == 1 and r["missing"] == ["their budget"]


def test_off_platform_promises_and_invented_prices_are_held_then_rewritten_once():
    ask, calls = _ask("Email me at me@example.com and I'll do it for $99, guaranteed viral.", "Happy to help here on Fiverr. What budget do you have in mind?")
    r = clientdesk.reply("logo please", "fiverr", "studio", ask=ask)
    assert len(calls) == 2 and "HELD" in calls[1] and r["ready"]
    ask2, _ = _ask("Pay me on PayPal", "Pay me on PayPal")
    held = clientdesk.reply("logo please", "fiverr", "studio", ask=ask2)
    assert not held["ready"] and any("off Fiverr" in p for p in held["problems"])


def test_web3_quotes_only_the_owner_prices():
    assert clientdesk.problems("A 30-second video is $65 and 75 seconds is $120.", "web3", None) == []
    assert clientdesk.problems("Special deal: $50 today.", "web3", None)
