"""Spend ledger: tracks free-tier quotas and paid spend per UTC day.

Providers ask `ledger.allow(...)` before spending and `ledger.spend(...)` after.
When a free quota is exhausted the router simply moves to the next provider in the chain.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from faceless.config import Paths
from faceless.fsutil import read_jsonl

LEDGER = Paths.state / "ledger.jsonl"


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _rows(day: str | None = None) -> list[dict]:
    return [r for r in read_jsonl(LEDGER) if day is None or r.get("day") == day]


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):   # a damaged row counts as nothing; it must not stop every provider call
        return 0.0


def used(provider: str, unit: str, day: str | None = None) -> float:
    day = day or today()
    return sum(_num(r.get("amount")) for r in _rows(day) if r.get("provider") == provider and r.get("unit") == unit)


def usd_total(day: str | None = None) -> float:
    """Every dollar spent on `day` (default today) across all providers: the number the daily spend ceiling is checked against."""
    return round(sum(_num(r.get("usd")) for r in _rows(day or today())), 6)


def allow(provider: str, unit: str, amount: float, cap: float) -> bool:
    return used(provider, unit) + amount <= cap


def spend(provider: str, unit: str, amount: float, usd: float = 0.0, job: str | None = None) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row = {"day": today(), "provider": provider, "unit": unit, "amount": round(amount, 4),
           "usd": round(usd, 6), "job": job}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def summary(day: str | None = None) -> dict:
    out: dict = {}
    for r in _rows(day or today()):
        k = f"{r.get('provider')}:{r.get('unit')}"
        out[k] = round(out.get(k, 0) + _num(r.get("amount")), 3)
        out["usd"] = round(out.get("usd", 0) + _num(r.get("usd")), 4)
    return out
