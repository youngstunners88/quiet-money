"""Watchdog: a dead-man's switch that needs no session, no key and no network.

The studio's work happens in scheduled Claude sessions. If one fails to start, or stalls, nothing inside it can say so. This module reads
only what is committed to the repo and says whether the operation is alive: the last daily batch, the kill switch, held and failed
videos, spend against the ceiling, damaged state files, broken skills and stale rule pages. `.github/workflows/watchdog.yml` runs it
every six hours on GitHub's own scheduler (it needs nothing but the built-in token), keeps ONE issue titled "Ops alert" in sync with
the findings, and closes it when everything is healthy again. Locally: `python -m faceless watchdog`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from faceless import config, events, ledger, safety
from faceless.config import Paths

CRITICAL, WARN, INFO = "critical", "warn", "info"


def _finding(level: str, what: str, detail: str, action: str = "") -> dict:
    return {"level": level, "what": what, "detail": detail, "action": action}


def evaluate(now: datetime | None = None) -> list[dict]:
    """Every problem visible in the repository right now, worst first. An empty list means healthy."""
    now = now or datetime.now(timezone.utc)
    out: list[dict] = []
    days = sorted(p.stem.replace("daily-", "") for p in Paths.reports.glob("daily-*.md"))
    if not days:
        out.append(_finding(WARN, "no daily batch yet", "gauntlet/reports has no daily report", "run the daily routine once"))
    else:
        last = datetime.strptime(days[-1], "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
        age = (now - last).total_seconds() / 3600
        if age > 54:
            out.append(_finding(CRITICAL, "the daily batch has stopped", f"the newest report is for {days[-1]}, about {age:.0f} hours old", "open the routine's last session: did it start, did it fail, did it push?"))
        elif age > 34:
            out.append(_finding(WARN, "the daily batch is late", f"the newest report is for {days[-1]}, about {age:.0f} hours old", "check that today's routine is running"))
    why = safety.paused()
    if why:
        f = Paths.state / "PAUSE"
        age_h = (now.timestamp() - f.stat().st_mtime) / 3600 if f.exists() else 0
        out.append(_finding(WARN if age_h > 24 or not f.exists() else INFO, "the studio is paused", f"{why} (for about {age_h:.0f} hours)", "`python -m faceless pause --resume` when the reason is dealt with"))
    spent, cap = ledger.usd_total(), safety.ceiling()
    if spent >= cap:
        out.append(_finding(CRITICAL, "the spend ceiling was reached", f"${spent:.2f} of ${cap:.2f} today", "find what spent it (`python -m faceless status`) before raising anything"))
    elif spent >= 0.8 * cap:
        out.append(_finding(WARN, "spend is near the ceiling", f"${spent:.2f} of ${cap:.2f} today", ""))
    recent = {(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(2)}
    slots: dict[tuple, list] = {}
    for p in Paths.jobs.glob("*.json"):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if j.get("day") in recent:
            slots.setdefault((j.get("day"), j.get("slot")), []).append(j.get("status"))
    # a held or failed attempt only matters while its slot has no finished video: a refill resolves it
    open_slots = [k for k, v in slots.items() if not any(s in ("packaged", "published") for s in v) and any(s in ("held", "failed") for s in v)]
    if len(open_slots) >= 2:
        out.append(_finding(CRITICAL if len(open_slots) >= 4 else WARN, "slots are open after a held or failed video",
                            f"{len(open_slots)} slot(s) in the last two days have no finished video: {sorted(open_slots)[:4]}",
                            "read gauntlet/reports for the failing gates; use the faceless-gauntlet skill; `python -m faceless daily` refills open slots"))
    for path in (Paths.state / "journal.jsonl", Paths.state / "ledger.jsonl"):
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(line.startswith(("<<<<<<<", ">>>>>>>")) for line in text.splitlines()):
                out.append(_finding(CRITICAL, f"{path.name} has merge conflict markers", "a merge left the file unreadable by tools that expect one JSON object a line", "union-merge both sides by timestamp, keep every line"))
    try:
        from faceless import skilllint
        bad = skilllint.failures(skilllint.lint_all())
        if bad:
            out.append(_finding(CRITICAL, "skills are broken", f"{bad} lint failure(s): the scheduled routines follow these files", "`python -m faceless skills` lists them"))
    except Exception as e:  # noqa: BLE001 - the watchdog itself must never crash
        out.append(_finding(WARN, "the skill check could not run", f"{type(e).__name__}", ""))
    try:
        from faceless import policy
        late = policy.stale()
        if len(late) > 8:
            out.append(_finding(WARN, "platform rule pages are stale", f"{len(late)} pages unread or older than 14 days", "the weekly session fetches them through Exa and records them"))
    except Exception:  # noqa: BLE001
        pass
    order = {CRITICAL: 0, WARN: 1, INFO: 2}
    return sorted(out, key=lambda f: order[f["level"]])


def failing(findings: list[dict], fail_on: str | None) -> bool:
    """True when a finding is at or above the level named (`critical`, or `warn` which also counts critical). No level named: never fails."""
    if not fail_on:
        return False
    bar = {CRITICAL: {CRITICAL}, WARN: {CRITICAL, WARN}}[fail_on]
    return any(f["level"] in bar for f in findings)


def summary(findings: list[dict]) -> str:
    if not findings:
        return "healthy"
    worst = findings[0]["level"]
    return f"{worst}: " + "; ".join(f["what"] for f in findings[:3])


def render_md(findings: list[dict], now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if not findings:
        return f"Quiet Money is healthy as of {now.strftime('%Y-%m-%d %H:%M UTC')}.\n"
    lines = [f"Watchdog findings as of {now.strftime('%Y-%m-%d %H:%M UTC')}. This issue closes itself when every finding clears.", ""]
    for f in findings:
        lines.append(f"- **{f['level'].upper()}: {f['what']}.** {f['detail']}." + (f" Next: {f['action']}." if f["action"] else ""))
    return "\n".join(lines) + "\n"


def emit(findings: list[dict]) -> None:
    events.emit("WATCHDOG", actor="watchdog", status=summary(findings), findings=len(findings))
