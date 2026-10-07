"""The Money Reset as an email sequence: a welcome plus one email a day for seven days.

The same seven boxes as the free checklist, one per email, with every number computed by faceless.moneymath (no number is
typed by hand). `python -m faceless autoresponder` writes channel/offers/autoresponder/: one markdown file per email and
sequence.json for importing into any email service. Nothing is sent from here: the owner picks the service, adds the
postal address and unsubscribe link (the law requires both), and turns the sequence on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from faceless import config, moneymath as mm
from faceless.config import Paths
from faceless.prompts import BANNED, COMPLIANCE_BANNED

OUT = Paths.root / "channel" / "offers" / "autoresponder"
FOOTER = ("Educational content, not financial advice. Examples use assumed returns that are never guaranteed.\n\n"
          "{{postal_address}}\nYou joined the free Money Reset. Unsubscribe any time: {{unsubscribe_url}}")
SIGN = "Quiet Money"


def numbers() -> dict:
    """Every figure the emails quote, computed once."""
    mo, interest = mm.card_minimum_payoff(6000, 0.24)
    return {"sub10": mm.money(15 * 120), "sub10_inv": mm.money(mm.future_value_monthly(15, 0.08, 10)),
            "pay25": mm.money(mm.future_value_monthly(25, 0.08, 30)), "put25": mm.money(25 * 12 * 30),
            "needs": mm.money(4000 * 0.5), "wants": mm.money(4000 * 0.3), "future": mm.money(4000 * 0.2),
            "min_years": f"{mo / 12:.0f}", "min_interest": mm.money(interest), "card600": mm.money(600 * 0.24), "fee4": mm.money(35 * 4),
            "half_raise": mm.money(3000 / 2 / 12), "raise20": mm.money(mm.future_value_monthly(3000 / 2 / 12, 0.08, 20))}


def emails() -> list[dict]:
    n = numbers()
    cfg = config.load()
    link = cfg["channel"].get("link_in_bio", "")
    planner = cfg.get("newsletter", {}).get("planner_url", "")
    d7_cta = (f"If you want the numbers laid out for you, the Rat Race Escape Planner is a spreadsheet that does it: {planner}\n\n"
              if planner else "")
    rows = [
        ("welcome", 0, "Your 7-day Money Reset starts now",
         "One small box a day. Day 1 arrives tomorrow.",
         f"Welcome.\n\nThis is the Money Reset: seven boxes, one a day, about 10 minutes each. In a week your money runs on rules instead of willpower.\n\n"
         f"The whole checklist is here if you like to see it all at once: {link}\n\nTomorrow's box: find the leaks. Hit reply if you get stuck."),
        ("day1", 1, "Day 1: find the leaks",
         f"A $15 subscription is {n['sub10']} over 10 years.",
         f"Open last month's bank and card statements. Highlight every subscription and recurring charge. Cancel at least one you forgot about.\n\n"
         f"Why it matters: a $15 a month subscription costs {n['sub10']} over 10 years. Invested instead at an assumed 8% a year, that same $15 a month "
         f"would be about {n['sub10_inv']}. Small leaks are not small.\n\nToday's box: one cancellation. That is the whole job."),
        ("day2", 2, "Day 2: pay yourself first",
         "Saving what's left is why nothing is left.",
         f"Open a separate savings account and set an automatic transfer for payday. Even $25.\n\n"
         f"Why it matters: $25 a month for 30 years at an assumed 8% a year grows to about {n['pay25']}, and you only put in {n['put25']}. "
         f"The amount matters less than the habit and the time.\n\nToday's box: the automatic transfer, set once."),
        ("day3", 3, "Day 3: split every paycheck",
         "50 / 30 / 20 in five minutes.",
         f"Write your take-home pay. Then split it: 50% needs, 30% wants, 20% future.\n\n"
         f"On $4,000 a month that is {n['needs']} for needs, {n['wants']} for wants and {n['future']} for your future. "
         f"If your needs are over 50%, circle the biggest one. That is next month's project, not today's.\n\nToday's box: the three numbers on one piece of paper."),
        ("day4", 4, "Day 4: attack the expensive debt first",
         "Minimums are designed to last.",
         f"List every debt with its interest rate. Put every extra dollar on the highest rate (avalanche) or the smallest balance (snowball). Pick one and stick to it.\n\n"
         f"Why it matters: $6,000 at 24% paid at a typical minimum takes about {n['min_years']} years and costs {n['min_interest']} in interest. "
         f"The minimum is not a plan.\n\nToday's box: the list, and one choice of method."),
        ("day5", 5, "Day 5: build the $1,000 buffer",
         "A surprise bill should not become a debt.",
         f"Sell one thing you do not use, do a no-spend weekend, and park the cash in savings labeled emergencies only.\n\n"
         f"Why it matters: a $600 surprise put on a 24% card costs about {n['card600']} a year in interest while you carry it. "
         f"A buffer turns a crisis into an inconvenience.\n\nToday's box: the first $100 of the $1,000. Start there."),
        ("day6", 6, "Day 6: stop fee bleeding",
         "Banks waive fees when you ask.",
         f"Turn on low-balance and large-purchase alerts in your banking app. Then look at the last 90 days of fees and ask your bank: "
         f"\"Can you waive this as a courtesy?\"\n\nWhy it matters: one $35 fee a quarter is {n['fee4']} a year. Alerts stop most of them before they happen.\n\n"
         f"Today's box: alerts on, and one phone call."),
        ("day7", 7, "Day 7: lock in your raises",
         "Decide now, while it is easy.",
         f"Write this rule down: when income goes up, half the raise goes to savings before I see it. Put your money rules on one index card and keep it in your wallet.\n\n"
         f"Why it matters: on a $3,000 a year raise, half is {n['half_raise']} a month. Invested at an assumed 8% a year for 20 years it grows to about {n['raise20']}, "
         f"and you never felt it leave.\n\n{d7_cta}You finished the Money Reset. Reply and tell me which box changed the most for you."),
    ]
    return [{"key": k, "day": d, "subject": s, "preview": p, "body": b, "footer": FOOTER, "sign": SIGN} for k, d, s, p, b in rows]


def text(e: dict) -> str:
    return f"Subject: {e['subject']}\nPreview: {e['preview']}\nSend: day {e['day']} after signup\n\n{e['body']}\n\n{e['sign']}\n\n--\n{e['footer']}\n"


def problems(es: list[dict] | None = None) -> list[str]:
    """Rule check: short subjects, short bodies, no banned phrases, a footer, and no leftover template braces in the body."""
    out = []
    for e in es or emails():
        words = len(e["body"].split())
        if len(e["subject"]) > 60:
            out.append(f"{e['key']}: subject over 60 characters")
        if words > 190:
            out.append(f"{e['key']}: {words} words (limit 190)")
        low = (e["subject"] + " " + e["body"]).lower()
        out += [f"{e['key']}: banned phrase '{p}'" for p in BANNED + COMPLIANCE_BANNED if p in low]
        if re.search(r"\{\{|\}\}", e["body"]):
            out.append(f"{e['key']}: template braces in body")
        if "{{unsubscribe_url}}" not in e["footer"] or "{{postal_address}}" not in e["footer"]:
            out.append(f"{e['key']}: footer lacks unsubscribe or postal address")
    return out


def write() -> list[Path]:
    es = emails()
    bad = problems(es)
    if bad:
        raise ValueError("autoresponder fails its own rules: " + "; ".join(bad))
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for e in es:
        p = OUT / f"{e['day']}-{e['key']}.md"
        p.write_text(text(e), encoding="utf-8")
        paths.append(p)
    (OUT / "sequence.json").write_text(json.dumps(es, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Money Reset autoresponder\n\nEight emails (a welcome and days 1-7), generated by `python -m faceless autoresponder` with every number computed.\n\n"
        "## To turn it on (owner)\n1. Pick an email service with a free tier (MailerLite, Kit, Beehiiv, Buttondown all accept pasted emails or an import).\n"
        "2. Add your real postal address and the service's unsubscribe link in the footer merge tags. The law requires both; the service may supply them for you.\n"
        "3. Paste each email, set the delays in the file names (welcome at signup, then day 1 to day 7 at one day apart).\n"
        "4. Point the 'link in bio' signup form at the sequence.\n5. Replies go to the sending mailbox: use one you actually read.\n\nMerge tags differ per service: replace `{{postal_address}}` and `{{unsubscribe_url}}` with the service's own.\n"
        "Set `[newsletter] planner_url` in studio.toml after the planner is live and day 7 will mention it.\n", encoding="utf-8")
    return paths
