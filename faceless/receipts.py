"""Receipts: the only proof of income. Money counts here when a real receipt exists, and never before.

Two sources, both real:
  * `analytics/sales.jsonl`  what `python -m faceless shop sales` pulled from Gumroad (needs the owner's read connection)
  * `state/receipts.jsonl`   what the owner records by hand from a payout or order email: `python -m faceless receipts add ...`

A row holds a day, a rail, a product, the gross, the fee and a reference. It never holds a buyer's name, handle or email (the repo is
public); `add` refuses anything shaped like one. Views, clicks, replies and "potential" are not income and are never added in here.
"""

from __future__ import annotations

import json
import re

from faceless import config, events
from faceless.config import Paths
from faceless.fsutil import read_jsonl

RECEIPTS = Paths.state / "receipts.jsonl"
SALES = Paths.analytics / "sales.jsonl"
RAILS = ("gumroad", "etsy", "fiverr", "service", "affiliate", "other")
_PERSONAL = re.compile(r"@|\b[\w.+-]+\s?\(at\)\s?[\w-]+")


def add(rail: str, gross: float, fee: float | None = None, product: str = "", ref: str = "", day: str | None = None, note: str = "") -> dict:
    """Record one real receipt. `fee` is what the platform kept; when it is not given for a Gumroad card sale it is estimated and marked so."""
    if rail not in RAILS:
        raise ValueError(f"rail must be one of {', '.join(RAILS)}")
    gross = float(gross)
    if gross <= 0:
        raise ValueError("a receipt has a positive gross amount; a free download is not income")
    for text in (product, ref, note):
        if _PERSONAL.search(text or ""):
            raise ValueError("no buyer names, handles or emails in a receipt: use the order number as the reference")
    day = day or config.today_utc().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("day is YYYY-MM-DD")
    if ref and any(r.get("ref") == ref and r.get("rail") == rail for r in read_jsonl(RECEIPTS)):
        raise ValueError(f"receipt {ref} on {rail} is already recorded")
    estimated = fee is None
    if estimated:
        from faceless import marketing
        fee = round(gross - marketing.net_per_sale(gross), 2) if rail == "gumroad" else 0.0
    row = {"t": events.now_iso(), "day": day, "rail": rail, "product": product, "gross": round(gross, 2), "fee": round(float(fee), 2),
           "net": round(gross - float(fee), 2), "fee_estimated": estimated, "ref": ref, "note": note}
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def rows() -> list[dict]:
    """Every receipt from both sources, one shape, each counted once (a Gumroad sale also typed in by hand under the same id counts once)."""
    from faceless import marketing
    out, seen = [], set()
    for r in read_jsonl(RECEIPTS):
        try:
            gross, fee = float(r.get("gross") or 0), float(r.get("fee") or 0)
        except (TypeError, ValueError):
            continue
        if gross <= 0 or r.get("refunded"):
            continue
        key = (r.get("rail"), r.get("ref")) if r.get("ref") else None
        if key:
            seen.add(key)
        out.append({"day": str(r.get("day") or "")[:10], "rail": r.get("rail") or "other", "product": r.get("product") or "", "gross": gross,
                    "net": round(gross - fee, 2), "ref": r.get("ref") or "", "source": "state/receipts.jsonl"})
    for r in read_jsonl(SALES):
        try:
            usd = float(r.get("usd") or 0)
        except (TypeError, ValueError):
            continue
        if usd <= 0 or r.get("refunded") or ("gumroad", r.get("id")) in seen:
            continue
        out.append({"day": str(r.get("at") or r.get("day") or r.get("date") or "")[:10], "rail": "gumroad", "product": r.get("product") or "",
                    "gross": usd, "net": marketing.net_per_sale(usd), "ref": str(r.get("id") or ""), "source": "analytics/sales.jsonl"})
    return sorted(out, key=lambda r: r["day"])


def summary(today: str | None = None) -> dict:
    today = today or config.today_utc().isoformat()
    every = rows()
    mtd = [r for r in every if r["day"][:7] == today[:7]]
    by: dict[str, dict] = {}
    for r in mtd:
        b = by.setdefault(r["rail"], {"receipts": 0, "gross": 0.0, "net": 0.0})
        b["receipts"] += 1
        b["gross"] = round(b["gross"] + r["gross"], 2)
        b["net"] = round(b["net"] + r["net"], 2)
    return {
        "revenueMTD": round(sum(r["gross"] for r in mtd), 2), "netMTD": round(sum(r["net"] for r in mtd), 2), "receipts": len(mtd),
        "receiptsAllTime": len(every), "revenueAllTime": round(sum(r["gross"] for r in every), 2), "byRail": by,
        "lastReceiptDay": every[-1]["day"] if every else None,
        "note": "no receipts yet" if not every else ("no receipts this month" if not mtd else ""),
        "sources": {"state/receipts.jsonl": RECEIPTS.exists(), "analytics/sales.jsonl": SALES.exists()},
        "source": "state/receipts.jsonl (typed in from payout emails), analytics/sales.jsonl (Gumroad pull)",
    }
