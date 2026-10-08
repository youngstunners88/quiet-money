"""Spend ledger: tracks free-tier quotas and paid spend per UTC day.

Providers ask `ledger.allow(...)` before spending and `ledger.spend(...)` after.
When a free quota is exhausted the router simply moves to the next provider in the chain.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from faceless.config import Paths

LEDGER = Paths.state / "ledger.jsonl"


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _rows(day: str | None = None) -> list[dict]:
    if not LEDGER.exists():
        return []
    rows = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if day is None or r.get("day") == day:
            rows.append(r)
    return rows


def used(provider: str, unit: str, day: str | None = None) -> float:
    day = day or today()
    return sum(r["amount"] for r in _rows(day) if r["provider"] == provider and r["unit"] == unit)


def usd_total(day: str | None = None) -> float:
    """Every dollar spent on `day` (default today) across all providers: the number the daily spend ceiling is checked against."""
    return round(sum(float(r.get("usd") or 0) for r in _rows(day or today())), 6)


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
        k = f"{r['provider']}:{r['unit']}"
        out[k] = round(out.get(k, 0) + r["amount"], 3)
        out["usd"] = round(out.get("usd", 0) + r.get("usd", 0), 4)
    return out
