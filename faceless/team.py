"""The team board: who is working, on what, how far along, and what it cost. One shared file every agent writes to, read by the overview.

Schema (state/agents/beats.jsonl, append-only, one JSON object per line; an append of one short line is atomic, so agents never corrupt each other):
    {"t": ISO-8601 UTC, "agent": "hermes", "status": "running|idle|refreshing|blocked|paused|error|done",
     "task": "one line", "run": "a run id that groups beats", "done": 3, "total": 10,
     "model": "nvidia/...:free", "tokens_in": 1200, "tokens_out": 300, "usd": 0.0, "note": "..."}
Only `agent` and `status` are required. Token and USD fields are what this beat used since the agent's previous beat (deltas), so
the board can sum them per day. Writers: `python -m faceless agent beat <agent> <status> --task ... [--done N --total M] [--tokens-in N] ...`.

The board never invents a number: an agent with no beat today shows its roster state only; a run whose last beat is older than
STALE_MIN while it claims to be running shows "stale", because a silent agent is not a working one.
Two lanes are derived from real state rather than beats: a video batch (jobs made since the batch's first beat, from state/jobs) and
provider usage (state/ledger.jsonl, which the engine already writes per call).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faceless import config
from faceless.config import STUDIO
from faceless.fsutil import read_jsonl

BEATS = STUDIO / "state" / "agents" / "beats.jsonl"
STATUSES = ("running", "idle", "refreshing", "blocked", "paused", "error", "done")
STALE_MIN = 20
FREE_PROVIDERS = {"edge", "pollinations", "cloudflare", "procedural", "openrouter-panel", "composio", "ollama"}
_NUM = ("done", "total", "tokens_in", "tokens_out")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def beat(agent: str, status: str, task: str = "", **kw) -> dict:
    """Append one beat. Refuses an unknown status or a negative count, so a typo never reaches the board."""
    agent = str(agent).strip().lower()
    if not agent or len(agent) > 40:
        raise ValueError("agent must be a short name")
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    row = {"t": _iso(_now()), "agent": agent, "status": status}
    if task:
        row["task"] = " ".join(str(task).split())[:160]
    for k in _NUM:
        if kw.get(k) is not None:
            v = int(kw[k])
            if v < 0:
                raise ValueError(f"{k} cannot be negative")
            row[k] = v
    if kw.get("usd") is not None:
        if float(kw["usd"]) < 0:
            raise ValueError("usd cannot be negative")
        row["usd"] = round(float(kw["usd"]), 6)
    if kw.get("since"):
        since = _parse(kw["since"])
        if not since:
            raise ValueError("since must be an ISO time like 2026-11-15T10:15:13Z")
        row["since"] = _iso(since)
    for k in ("model", "run", "note"):
        if kw.get(k):
            row[k] = " ".join(str(kw[k]).split())[:160]
    BEATS.parent.mkdir(parents=True, exist_ok=True)
    with BEATS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _beats_today(day: str) -> list[dict]:
    return [b for b in (read_jsonl(BEATS) if BEATS.exists() else []) if str(b.get("t", ""))[:10] == day and b.get("agent")]


def _batch_progress(first: dict, jobs_dir: Path) -> dict:
    """Jobs created after the batch started: made (packaged or later), held, failed, still going, and when any of them last changed.
    A job that has not taken its first step yet has no history, so its file's time stands in for when it began."""
    start = _parse(first.get("since") or first["t"])
    counts = {"made": 0, "held": 0, "failed": 0, "inProgress": 0, "lastActivity": None}
    newest = 0.0
    for f in jobs_dir.glob("*.json"):                       # banked slots can carry a later day in their id, so every file is checked
        mtime = f.stat().st_mtime
        if start and mtime < start.timestamp():
            continue
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        hist = j.get("history") or []
        began = _parse(hist[0]["ts"]) if hist and hist[0].get("ts") else datetime.fromtimestamp(mtime, timezone.utc)
        if not began or not start or began < start:
            continue
        s = j.get("status")
        key = "made" if s in ("packaged", "published") else "held" if s == "held" else "failed" if s == "failed" else "inProgress"
        counts[key] += 1
        newest = max(newest, mtime)
    if newest:
        counts["lastActivity"] = _iso(datetime.fromtimestamp(newest, timezone.utc))
    return counts


def board(roster: list[dict] | None = None, jobs_dir: Path | None = None, day: str | None = None) -> dict:
    """One row per agent: the latest beat today wins; token and cost deltas add up across the day."""
    day = day or config.today_utc().isoformat()
    now = _now()
    rows: dict[str, dict] = {}
    for b in _beats_today(day):
        r = rows.setdefault(b["agent"], {"agent": b["agent"], "tokensIn": 0, "tokensOut": 0, "usd": 0.0, "models": [], "startedAt": b["t"], "first": b})
        r["tokensIn"] += b.get("tokens_in", 0)
        r["tokensOut"] += b.get("tokens_out", 0)
        r["usd"] = round(r["usd"] + b.get("usd", 0.0), 6)
        if b.get("model") and b["model"] not in r["models"]:
            r["models"].append(b["model"])
        if b.get("run") != r["first"].get("run"):
            r["first"], r["startedAt"] = b, b["t"]
        r.update(status=b["status"], task=b.get("task", r.get("task", "")), lastBeat=b["t"], note=b.get("note", ""), run=b.get("run"))
        if "total" in b:
            r["done"], r["total"] = b.get("done", 0), b["total"]
    out = []
    for r in rows.values():
        first = r.pop("first")
        last = _parse(r["lastBeat"])
        if (r.get("run") or "").startswith("batch-"):          # a batch shows progress from its jobs, and a job changing is a sign of life
            r["batch"] = _batch_progress(first, jobs_dir or STUDIO / "state" / "jobs")
            r["done"] = r["batch"]["made"]
            act = _parse(r["batch"]["lastActivity"]) if r["batch"]["lastActivity"] else None
            if act and (not last or act > last):
                last = act
        if r["status"] in ("running", "refreshing") and last and now - last > timedelta(minutes=STALE_MIN):
            r["status"], r["note"] = "stale", f"no sign of life for {int((now - last).total_seconds() // 60)} min"
        out.append(r)
    seen = {r["agent"] for r in out}
    for c in roster or []:
        if c.get("id") and c["id"] not in seen:
            out.append({"agent": c["id"], "status": "idle" if c.get("installed", True) else "missing", "task": "", "lastBeat": None,
                        "roster": c.get("status"), "tokensIn": 0, "tokensOut": 0, "usd": 0.0, "models": []})
    order = {"running": 0, "refreshing": 1, "stale": 2, "blocked": 3, "error": 4, "paused": 5, "done": 6, "idle": 7, "missing": 8}
    out.sort(key=lambda r: (order.get(r["status"], 9), r["agent"]))
    return {"day": day, "agents": out, "staleAfterMin": STALE_MIN, "source": "state/agents/beats.jsonl, crew.toml, state/jobs"}


def gauges(day: str | None = None) -> dict:
    """Usage per provider today from the ledger (tokens, characters, images, USD), free vs paid, against the day's ceiling."""
    from faceless import ledger, safety
    day = day or config.today_utc().isoformat()
    per: dict[str, dict] = {}
    models: dict[str, dict] = {}
    for r in read_jsonl(ledger.LEDGER) if ledger.LEDGER.exists() else []:
        if r.get("day") != day or not r.get("provider"):
            continue
        if r.get("model"):
            m = models.setdefault(r["model"], {"model": r["model"], "provider": r["provider"], "calls": 0, "tokensIn": 0, "tokensOut": 0,
                                                "tokens": 0, "usd": 0.0})
            m["calls"] += 1
            m["tokensIn"] += int(r.get("tokens_in") or 0)
            m["tokensOut"] += int(r.get("tokens_out") or 0)
            m["tokens"] += int(r.get("amount") or 0) if r.get("unit") == "tokens" else 0
            m["usd"] = round(m["usd"] + float(r.get("usd") or 0), 6)
        g = per.setdefault(r["provider"], {"provider": r["provider"], "usd": 0.0, "units": {}, "calls": 0})
        g["calls"] += 1
        g["usd"] += float(r.get("usd") or 0)
        if r.get("unit") != "microusd":
            g["units"][r["unit"]] = round(g["units"].get(r["unit"], 0) + float(r.get("amount") or 0), 2)
    rows = []
    for g in per.values():
        g["usd"] = round(g["usd"], 4)
        g["free"] = g["usd"] == 0 or g["provider"] in FREE_PROVIDERS
        rows.append(g)
    rows.sort(key=lambda g: (-g["usd"], -g["calls"]))
    autopilot = (config.load().get("autopilot") or {}) if hasattr(config, "load") else {}
    try:
        crew = __import__("tomllib").loads((STUDIO / "crew.toml").read_text(encoding="utf-8"))
        autopilot = crew.get("autopilot") or autopilot
    except (OSError, ValueError):
        pass
    total = round(sum(g["usd"] for g in rows), 4)
    mrows = sorted(models.values(), key=lambda m: (-m["usd"], -m["tokens"]))
    for m in mrows:
        m["free"] = m["model"].endswith(":free") or m["usd"] == 0
    return {"day": day, "providers": rows, "models": mrows, "usdToday": total, "ceilingUsd": safety.ceiling(),
            "autopilotMaxCost": autopilot.get("max_cost"), "source": "state/ledger.jsonl, studio.toml [safety], crew.toml [autopilot]"}


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="python -m faceless agent")
    p.add_argument("action", choices=["beat", "board", "gauges"])
    p.add_argument("agent", nargs="?")
    p.add_argument("status", nargs="?")
    p.add_argument("--task", default="")
    p.add_argument("--run")
    p.add_argument("--model")
    p.add_argument("--note")
    p.add_argument("--since", help="a batch: count jobs started at or after this time instead of the beat's own time")
    for k in _NUM:
        p.add_argument("--" + k.replace("_", "-"), type=int, dest=k)
    p.add_argument("--usd", type=float)
    a = p.parse_args(argv)
    if a.action == "board":
        print(json.dumps(board(), indent=1))
        return 0
    if a.action == "gauges":
        print(json.dumps(gauges(), indent=1))
        return 0
    try:
        row = beat(a.agent or "", a.status or "", a.task, run=a.run, model=a.model, note=a.note, usd=a.usd, since=a.since,
                   **{k: getattr(a, k) for k in _NUM})
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(json.dumps(row))
    return 0
