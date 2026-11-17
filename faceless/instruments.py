"""The instrument panel: one snapshot of what the machine, the crew, the models and the money are doing right now.

    python -m faceless instruments              # a short reading for a person
    python -m faceless instruments --json       # the whole snapshot (what GET /instruments.json serves)
    python -m faceless instruments --for hermes # an agent's pre-flight: its budget, who has what, who is better placed
    python -m faceless instruments --probe      # ask each key's service whether the key still works (free, read-only), then print

Every number carries a source tag, and the three are never mixed up:
    read      taken from a provider's API or a local file that is the record itself (an agent's own session store, crew.toml, studio.toml)
    estimate  counted by us (ledger rows, transcript lines, an agent's own beats) or worked out from a rule (a burn rate, a reset clock)
    unknown   nobody told us and nothing says; the board draws it grey with the reason and never a guess
A limit is `unknown` until crew.toml says what it is or a provider's API reports it.

Two lanes. The fast lane is read on every call and is cheap: beats, the ledger, claims, the journal's tail, each agent's own store,
the key-health file. The slow lane is the overview (jobs, missions, alerts), which takes many seconds to build; its last copy is kept in
state/tmp/instruments-slow.json and the snapshot says how old it is. Nothing here starts, stops or prompts anything, and a key's
value never leaves this process: only its variable name, where it was found and what its service answered.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faceless import config, events, missions, team
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic

SLOW = Paths.state / "tmp" / "instruments-slow.json"
KEYHEALTH = Paths.state / "tmp" / "keyhealth.json"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
HERMES_DB = Path.home() / ".hermes" / "state.db"
OPENCODE_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
CLAUDE_CONFIG = Path.home() / ".claude.json"                 # Claude Code's own account record: which plan (never the name or the address)
LIMIT_STALE_MIN = 90                                         # a provider's own limit reading older than this is shown with its age, not as current
WINDOW_LABEL = {"five_hour": "5-hour window", "seven_day": "7-day window", "spend_limit": "spend limit"}
WINDOW_HOURS = {"five_hour": 5.0, "seven_day": 168.0}
KEY_FILES = [Paths.root / ".env", config.MACHINE_ENV]         # where the studio's own keys live; read for health, never shown
KEY_TTL_MIN = 10                                             # a key's health is asked again at most this often
SLOW_TTL_MIN = 10                                            # a pre-flight older than this rebuilds the overview itself
LIVE_MIN = 5                                                 # token use this recent counts as "live" even without a beat
BURN_WINDOW_MIN = 60
EVENT_KEY = "CC_KEY"
BAD_KEY = ("rejected", "missing", "placeholder", "no-credit")
DEFAULT_USAGE = {"claude": "claude-transcripts", "hermes": "hermes-db", "opencode": "opencode-db"}
# The studio's own keys the board watches. An agent's key comes from its crew.toml block (key_env, key_file, provider).
STUDIO_KEYS = (
    {"id": "openrouter", "label": "OpenRouter (engine)", "env": "OPENROUTER_API_KEY", "probe": "openrouter"},
    {"id": "dash-token", "label": "Command center token", "env": "QM_DASH_TOKEN", "probe": None, "min": 16},
    {"id": "composio", "label": "Composio", "env": "COMPOSIO_API_KEY", "probe": "composio"},
    {"id": "elevenlabs", "label": "ElevenLabs", "env": "ELEVENLABS_API_KEY", "probe": "elevenlabs"},
)
PROBES = {"openrouter": ("https://openrouter.ai/api/v1/key", "Authorization", "Bearer {k}")}   # others come from faceless/keys.py
_FILE_CACHE: dict[str, tuple[tuple, list]] = {}
_RUN_CACHE: dict[str, tuple[float, object]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | float | None) -> str | None:
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        dt = datetime.fromtimestamp(float(dt), timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts(value) -> float | None:
    """Seconds since the epoch from an ISO string, seconds or milliseconds."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value) / 1000 if value > 1e11 else float(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _num(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").replace("_", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------- usage: each reader returns token events with their own times

def _empty(source: str, where: str, error: str | None = None) -> dict:
    return {"events": [], "source": source, "from": where, "error": error}


def _usage_claude(since: float) -> dict:
    """Claude Code's own transcripts (every project: a subscription is shared). Counted by us line by line, so always `estimate`.
    One reply is written several times as it streams; it is counted once, by its message id. Cache reads are kept apart."""
    out = {**_empty("estimate", "~/.claude/projects/*/*.jsonl (usage lines, counted by us)"), "grain": "request"}
    if not CLAUDE_PROJECTS.exists():
        out["error"] = "no transcripts folder"
        return out
    seen: dict[str, tuple] = {}
    for f in CLAUDE_PROJECTS.glob("*/*.jsonl"):
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_mtime < since:
            continue
        key = (st.st_mtime_ns, st.st_size)
        hit = _FILE_CACHE.get(str(f))
        if hit and hit[0] == key:
            rows = hit[1]
        else:
            rows = []
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if '"usage"' not in line:
                            continue
                        try:
                            d = json.loads(line)
                        except ValueError:
                            continue
                        msg = d.get("message") if isinstance(d.get("message"), dict) else None
                        u = (msg or {}).get("usage")
                        t = _ts(d.get("timestamp"))
                        if not isinstance(u, dict) or t is None:
                            continue
                        rows.append((msg.get("id") or d.get("uuid") or f"{f.name}:{len(rows)}", t,
                                     int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0),
                                     int(u.get("output_tokens") or 0), int(u.get("cache_read_input_tokens") or 0), msg.get("model") or ""))
            except OSError:
                continue
            _FILE_CACHE[str(f)] = (key, rows)
        for r in rows:
            seen[r[0]] = r                                   # the last copy of a streamed reply holds its final counts
    out["events"] = sorted(({"t": r[1], "in": r[2], "out": r[3], "usd": 0.0, "cacheRead": r[4], "model": r[5]} for r in seen.values() if r[1] >= since),
                           key=lambda e: e["t"])
    return out


def _sqlite(path: Path, sql: str, args: tuple = ()) -> list[tuple] | None:
    if not path.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return None
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.Error:
        return None
    finally:
        con.close()


def _usage_hermes(since: float) -> dict:
    """Hermes's own session store: tokens per session as Hermes recorded them (`read`), timed by the session's last message."""
    out = _empty("read", "~/.hermes/state.db (sessions.input_tokens, output_tokens)")
    rows = _sqlite(HERMES_DB, "select s.started_at, s.ended_at, s.input_tokens, s.output_tokens, s.model, "
                              "(select max(m.timestamp) from messages m where m.session_id = s.id) from sessions s "
                              "where coalesce(s.ended_at, s.started_at) >= ? or s.ended_at is null", (since - 86400,))
    if rows is None:
        out["error"] = "session store missing or unreadable"
        return out
    for started, ended, tin, tout, model, last in rows:
        t = max(x for x in (_ts(last), _ts(ended), _ts(started), 0.0) if x is not None)
        if t >= since:
            out["events"].append({"t": t, "in": int(tin or 0), "out": int(tout or 0), "usd": 0.0, "model": model or ""})
    out["events"].sort(key=lambda e: e["t"])
    replies = _sqlite(HERMES_DB, "select timestamp from messages where role = 'assistant' and timestamp >= ? order by timestamp", (since,))
    if replies is not None:                                  # one assistant message is one model reply: the request count for a requests-per-day cap
        out["requests"] = [_ts(r[0]) or 0.0 for r in replies]
    return out


def _usage_opencode(since: float) -> dict:
    """OpenCode's own store, one row per model reply with the tokens and cost OpenCode recorded for it (`read`). When the reply
    rows cannot be read the per-session totals stand in, and then requests cannot be counted."""
    out = {**_empty("read", "~/.local/share/opencode/opencode.db (message.data: tokens, cost per reply)"), "grain": "request"}
    rows = _sqlite(OPENCODE_DB, "select time_created, data from message where time_created >= ?", (int(since * 1000),))
    if rows is None:
        sess = _sqlite(OPENCODE_DB, "select time_updated, tokens_input, tokens_output, cost from session where time_updated >= ?", (int(since * 1000),))
        if sess is None:
            out["error"] = "session store missing or unreadable"
            return out
        out.update(grain="session", events=sorted(({"t": _ts(r[0]) or 0.0, "in": int(r[1] or 0), "out": int(r[2] or 0), "usd": float(r[3] or 0)} for r in sess), key=lambda e: e["t"]))
        out["from"] = "~/.local/share/opencode/opencode.db (session totals)"
        return out
    for created, data in rows:
        try:
            d = json.loads(data)
        except (TypeError, ValueError):
            continue
        if d.get("role") != "assistant":
            continue
        tk = d.get("tokens") or {}
        out["events"].append({"t": _ts(created) or 0.0, "in": int(tk.get("input") or 0) + int((tk.get("cache") or {}).get("write") or 0),
                              "out": int(tk.get("output") or 0) + int(tk.get("reasoning") or 0), "usd": float(d.get("cost") or 0),
                              "cacheRead": int((tk.get("cache") or {}).get("read") or 0), "model": "/".join(x for x in (d.get("providerID"), d.get("modelID")) if x)})
    out["events"].sort(key=lambda e: e["t"])
    return out


def _usage_beats(agent: str, since: float) -> dict:
    """What the agent said about itself with `agent beat --tokens-in/--tokens-out/--usd`: its own count, so `estimate`."""
    out = _empty("estimate", "state/agents/beats.jsonl (the agent's own beats)")
    for b in read_jsonl(team.BEATS) if team.BEATS.exists() else []:
        t = _ts(b.get("t"))
        if b.get("agent") == agent and t and t >= since and (b.get("tokens_in") or b.get("tokens_out") or b.get("usd")):
            out["events"].append({"t": t, "in": int(b.get("tokens_in") or 0), "out": int(b.get("tokens_out") or 0), "usd": float(b.get("usd") or 0), "model": b.get("model") or ""})
    return out


def usage(agent: dict, since: float) -> dict:
    kind = str(agent.get("usage") or DEFAULT_USAGE.get(agent.get("kind") or agent["id"]) or "beats")
    if kind == "claude-transcripts":
        return _usage_claude(since)
    if kind == "hermes-db":
        return _usage_hermes(since)
    if kind == "opencode-db":
        return _usage_opencode(since)
    return _usage_beats(agent["id"], since)


# ---------------------------------------------------------------- limits

def _window(spec: dict, now: datetime) -> dict:
    """When the current limit window began and when it resets, from crew.toml's `limit_window` and `reset`. Unknown stays unknown."""
    win, reset = str(spec.get("limit_window") or "unknown").strip().lower(), str(spec.get("reset") or "unknown").strip().lower()
    hours = {"day": 24.0, "week": 168.0, "month": 720.0}.get(win)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)h", win)
    if m:
        hours = float(m.group(1))
    if hours is None:
        return {"start": None, "resetAt": None, "hours": None, "rolling": False, "reason": "limit_window is \"unknown\" in crew.toml"}
    if reset == "rolling":
        return {"start": now - timedelta(hours=hours), "resetAt": None, "hours": hours, "rolling": True, "reason": None}
    m = re.fullmatch(r"(?:(mon|tue|wed|thu|fri|sat|sun)\s+)?(\d{1,2}):(\d{2})", reset)
    if not m:
        return {"start": None, "resetAt": None, "hours": hours, "rolling": False, "reason": "reset is \"unknown\" in crew.toml"}
    nxt = now.replace(hour=int(m.group(2)) % 24, minute=int(m.group(3)) % 60, second=0, microsecond=0)
    if m.group(1):
        nxt += timedelta(days=(("mon", "tue", "wed", "thu", "fri", "sat", "sun").index(m.group(1)) - nxt.weekday()) % 7)
    step = timedelta(days=7 if m.group(1) else 1)
    while nxt <= now:
        nxt += step
    return {"start": nxt - timedelta(hours=hours), "resetAt": nxt, "hours": hours, "rolling": False, "reason": None}


def limit_reading(spec: dict, use: dict, now: datetime, provider_limit: dict | None = None) -> dict:
    """One limit: how much, how much is used, when it resets, how fast it burns and when it would run dry.
    `source` is the weakest link: unknown without a limit, estimate when we did the counting, read only when every part was read."""
    unit = str(spec.get("limit_unit") or "tokens").lower()
    w = _window(spec, now)
    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = w["start"] or day0
    ev = [e for e in use["events"] if e["t"] >= start.timestamp()]

    # requests are counted from the store's own per-reply rows: a list of times beside the token events, or the events themselves
    calls = use["requests"] if "requests" in use else [e["t"] for e in use["events"]] if use.get("grain") == "request" else None
    countable = unit != "requests" or calls is not None

    def amount(rows):
        if not countable:                                    # a store that keeps one row per session cannot say how many requests were made
            return None
        if unit == "requests":
            return sum(1 for t in calls if t >= (rows[0]["t"] if rows else float("inf"))) if rows is not ev else sum(1 for t in calls if t >= start.timestamp())
        return sum(e["in"] + e["out"] for e in rows) if unit == "tokens" else round(sum(e["usd"] for e in rows), 6)
    used = amount(ev)
    limit = _num(spec.get("limit"))
    limit_source, reason = ("read", None) if limit is not None else ("unknown", None)
    if limit is None and provider_limit and _num(provider_limit.get("limit")) is not None:
        limit, unit, limit_source = _num(provider_limit["limit"]), "usd", "read"
        used = _num(provider_limit.get("usage")) or 0.0
        use = {**use, "source": "read", "from": provider_limit.get("from") or "provider API"}
    if limit is None:
        reason = (f"limit is \"{spec.get('limit', 'unknown')}\" in crew.toml: nobody has said what this plan allows. "
                  "Set limit, limit_unit, limit_window and reset in the agent's block and this arc fills in.")
    cut = now.timestamp() - BURN_WINDOW_MIN * 60
    recent = [e for e in use["events"] if e["t"] >= cut]
    if unit == "requests":
        burn = sum(1 for t in calls if t >= cut) * (60 / BURN_WINDOW_MIN) if calls is not None else None
    else:
        burn = amount(recent) * (60 / BURN_WINDOW_MIN) if use["events"] else None
    if unit == "requests" and countable and use["source"] == "read":
        use = {**use, "source": "estimate", "from": use["from"] + "; replies counted by us"}
    reset_at = w["resetAt"]
    if w["rolling"] and ev:
        reset_at = datetime.fromtimestamp(ev[0]["t"], timezone.utc) + timedelta(hours=w["hours"])   # the oldest use falls out of the window then
    out = {"unit": unit, "limit": limit, "limitSource": limit_source, "used": used, "usedSource": use["source"], "usedFrom": use["from"],
           "usedSince": _iso(start), "usedScope": "this window" if w["start"] else f"today (UTC); {w['reason'] or 'the window is unknown'}",
           "window": spec.get("limit_window") or "unknown", "windowHours": w["hours"], "resetAt": _iso(reset_at),
           "resetSource": "estimate" if reset_at else "unknown", "resetReason": w["reason"],
           "burnPerHour": round(burn, 4) if burn is not None else None, "burnSource": "estimate" if burn is not None else "unknown",
           "burnWindowMin": BURN_WINDOW_MIN, "pct": None, "projectedEmptyAt": None, "projectedPctAtReset": None, "reason": reason,
           "error": use.get("error")}
    if not countable:
        out["usedSource"], out["usedReason"] = "unknown", "its store keeps tokens per session, not a count of requests; set limit_unit = \"tokens\" or have it report with beats"
    if limit and used is not None:
        out["pct"] = round(100 * used / limit, 1)
        if burn and burn > 0 and used < limit:
            out["projectedEmptyAt"] = _iso(now + timedelta(hours=(limit - used) / burn))
        if burn is not None and reset_at:
            out["projectedPctAtReset"] = round(100 * (used + burn * max(0.0, (reset_at - now).total_seconds() / 3600)) / limit, 1)
    out["source"] = "unknown" if limit is None or used is None else "read" if (limit_source == "read" and out["usedSource"] == "read") else "estimate"
    return out


def provider_windows(agent: dict, now: datetime) -> list[dict]:
    """Limits the provider itself reported, saved by a hook into the file `limit_file` names (Claude Code's status line gives the
    5-hour and 7-day percentages and reset times). These are `read`. The burn is ours, from the file's own history: `estimate`.
    A reading whose window has since reset, or that is old, is not shown as current: it is `unknown` with what was last seen."""
    if not agent.get("limit_file"):
        return []
    path = Path(str(agent["limit_file"])).expanduser()
    where = str(agent["limit_file"])
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [{**_blank_window("five_hour", where), "reason": f"{where} does not exist yet: it is written by the agent's status line after its first reply "
                 "(for Claude Code: the statusLine command in ~/.claude/settings.json, tools/command-center/claude-statusline.py)."}]
    out = []
    for key, w in (doc.get("windows") or {}).items():
        row = _blank_window(key, where)
        read_at = _ts(w.get("stale_since")) or max(_ts(doc.get("t")) or 0.0, float(w["samples"][-1][0]) if w.get("samples") else 0.0)
        reset = _ts(w.get("resets_at"))
        pct = _num(w.get("used_percentage"))
        age_min = (now.timestamp() - read_at) / 60
        row.update(readAt=_iso(read_at), resetAt=_iso(reset) if reset else None, resetSource="read" if reset else "unknown")
        if pct is None:
            row["reason"] = "the last reading held no percentage"
        elif reset and reset <= now.timestamp():
            row["reason"] = f"the window reset at {_iso(reset)}; the last reading before that was {pct:.0f}%. A new one arrives with the agent's next reply."
            row["resetAt"], row["resetSource"] = None, "unknown"
        elif age_min > LIMIT_STALE_MIN:
            row["reason"] = f"last read {int(age_min)} min ago ({pct:.0f}% then); it refreshes with the agent's next reply."
        else:
            samples = [x for x in w.get("samples") or [] if isinstance(x, list) and len(x) == 2]
            burn = None
            recent = [x for x in samples if x[0] >= now.timestamp() - BURN_WINDOW_MIN * 60]
            if len(recent) >= 2 and recent[-1][0] - recent[0][0] >= 120:
                burn = max(0.0, (recent[-1][1] - recent[0][1]) / ((recent[-1][0] - recent[0][0]) / 3600))
            row.update(limit=100.0, limitSource="read", used=round(pct, 1), usedSource="read", pct=round(pct, 1), source="read",
                       burnPerHour=round(burn, 2) if burn is not None else None, burnSource="estimate" if burn is not None else "unknown")
            if burn and pct < 100:
                row["projectedEmptyAt"] = _iso(now + timedelta(hours=(100 - pct) / burn))
            if burn is not None and reset:
                row["projectedPctAtReset"] = round(pct + burn * max(0.0, (reset - now.timestamp()) / 3600), 1)
        out.append(row)
    order = list(WINDOW_LABEL)
    return sorted(out, key=lambda r: order.index(r["id"]) if r["id"] in order else 9)


def _blank_window(key: str, where: str) -> dict:
    return {"id": key, "label": WINDOW_LABEL.get(key, key.replace("_", " ")), "unit": "percent", "limit": None, "limitSource": "unknown", "used": None,
            "usedSource": "unknown", "usedFrom": f"{where} (the provider's own reading)", "usedSince": None, "usedScope": "this window",
            "window": key, "windowHours": WINDOW_HOURS.get(key), "resetAt": None, "resetSource": "unknown", "resetReason": None, "burnPerHour": None,
            "burnSource": "unknown", "burnWindowMin": BURN_WINDOW_MIN, "pct": None, "projectedEmptyAt": None, "projectedPctAtReset": None,
            "reason": None, "error": None, "source": "unknown"}


def plan_detail(agent: dict) -> dict | None:
    """Which plan the agent's own account record names. Only Claude Code keeps one we know how to read; two fields, nothing personal."""
    if (agent.get("kind") or agent.get("id")) != "claude":
        return None
    try:
        acct = json.loads(CLAUDE_CONFIG.read_text(encoding="utf-8")).get("oauthAccount") or {}
    except (OSError, ValueError):
        return None
    bits = [str(acct[k]) for k in ("organizationType", "organizationRateLimitTier") if acct.get(k)]
    return {"text": " · ".join(bits), "source": "read", "from": "~/.claude.json (oauthAccount.organizationType, organizationRateLimitTier)"} if bits else None


# ---------------------------------------------------------------- keys: health only, never a value

def _env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2).strip().strip("\"'")
    except OSError:
        pass
    return out


def key_specs(roster: list[dict] | None = None) -> list[dict]:
    specs = [{**k, "files": list(KEY_FILES), "usedBy": []} for k in STUDIO_KEYS]
    for a in roster or []:
        if a.get("key_env") and not a.get("ghost"):
            specs.append({"id": f"agent-{a['id']}", "label": f"{a['name']} key ({a.get('provider') or 'provider not named'})", "env": str(a["key_env"]),
                          "probe": a.get("provider"), "files": [Path(str(a["key_file"])).expanduser()] if a.get("key_file") else list(KEY_FILES),
                          "usedBy": [a["id"]], "own_file": bool(a.get("key_file"))})
    return specs


def _key_value(spec: dict) -> tuple[str | None, str]:
    """The key and where it was found (a file name or "environment"). An agent with its own key file is read from that file only."""
    if not spec.get("own_file") and (os.environ.get(spec["env"]) or "").strip():
        return os.environ[spec["env"]].strip(), "environment"
    for f in spec["files"]:
        v = _env_file(f).get(spec["env"])
        if v:
            return v, str(f).replace(str(Path.home()), "~")
    return None, ""


def _probe(spec: dict, key: str, session) -> dict:
    name = spec.get("probe")
    target = PROBES.get(name)
    if not target:
        from faceless import keys as keysmod
        p = next((p for p in keysmod.PROBES if p["service"] == name), None)
        target = (p["url"], p["auth"][0], p["auth"][1]) if p else None
    if not target:
        return {"state": "present", "detail": "set; no free read-only check is known for this service", "source": "read"}
    url, header, template = target
    try:
        r = session.get(url, headers={header: template.format(k=key)}, timeout=12)
        code = r.status_code
        try:
            body = r.json()
        except ValueError:
            body = {}
    except Exception as e:  # noqa: BLE001 - an unreachable service is a state, not a crash
        return {"state": "unknown", "detail": f"service unreachable ({type(e).__name__})", "source": "unknown"}
    text = json.dumps(body).lower() if body else ""
    state = ("ok" if code == 200 else "no-credit" if code == 402 or (code == 403 and "credit" in text) else "rejected" if code in (400, 401, 403)
             else "unknown")
    out = {"state": state, "detail": f"the service answered {code}", "source": "read" if state != "unknown" else "unknown", "http": code}
    data = body.get("data") if isinstance(body, dict) and isinstance(body.get("data"), dict) else None
    if code == 200 and name == "openrouter" and data:        # the key's own account facts: numbers only, never the key or its label
        facts = {k: data.get(k) for k in ("limit", "usage", "limit_remaining", "is_free_tier") if isinstance(data.get(k), (int, float, bool))}
        if facts:
            out["facts"] = {**facts, "from": "openrouter.ai/api/v1/key"}
    return out


def keyhealth(roster: list[dict] | None = None, refresh: bool | str = False, session=None, now: datetime | None = None) -> list[dict]:
    """One row per watched key: present / ok / rejected / missing / placeholder / no-credit / unknown. Without `refresh` this only
    reads files (is the variable set, is it a masked paste) and the last saved answers; `refresh=True` asks each service one free
    question, `refresh="stale"` only when the saved answers are older than KEY_TTL_MIN. A change of state is one CC_KEY journal line."""
    now = now or _now()
    try:
        saved = json.loads(KEYHEALTH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    if roster is None:
        roster = missions.crew({"herdr": {"agents": []}})
    age = (now.timestamp() - (_ts(saved.get("checkedAt")) or 0)) / 60
    ask = refresh is True or (refresh == "stale" and age > KEY_TTL_MIN)
    if ask and session is None:
        from faceless.providers import http
        session = http()
    rows, before = [], {r["id"]: r for r in saved.get("keys") or []}
    for spec in key_specs(roster):
        key, where = _key_value(spec)
        row = {"id": spec["id"], "label": spec["label"], "var": spec["env"], "where": where, "usedBy": spec["usedBy"]}
        if not key:
            row.update(state="missing", detail=f"{spec['env']} is not set in " + " or ".join(str(f).replace(str(Path.home()), "~") for f in spec["files"]), source="read")
        elif set(key) <= set("*•.xX") or len(key) < int(spec.get("min", 8)):
            row.update(state="placeholder", detail=f"{spec['env']} holds a masked or too-short value, not a key", source="read")
        elif ask and spec.get("probe"):
            row.update(_probe(spec, key, session))
            row["checkedAt"] = _iso(now)
        else:
            old = before.get(spec["id"]) or {}
            if spec.get("probe") and old.get("where") == where and old.get("state") in ("ok", "rejected", "no-credit", "unknown") and old.get("checkedAt"):
                row.update({k: old[k] for k in ("state", "detail", "source", "checkedAt", "http", "facts") if k in old})
            else:
                row.update(state="present", detail="set" + ("" if not spec.get("probe") else "; not checked against the service yet (run `python -m faceless instruments --probe`)"),
                           source="read")
        row["detail"] = config.redact(str(row.get("detail") or "")).replace(key or "\0", "[key]")
        rows.append(row)
    if ask:
        for r in rows:
            old = (before.get(r["id"]) or {}).get("state")
            if old != r["state"] and (old or r["state"] in BAD_KEY):
                events.emit(EVENT_KEY, actor="instruments", key=r["id"], var=r["var"], state=r["state"], was=old or "never checked", agents=r["usedBy"])
        KEYHEALTH.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(KEYHEALTH, json.dumps({"checkedAt": _iso(now), "keys": rows}, indent=1))
    return rows


# ---------------------------------------------------------------- the crew

def _beat_rows() -> dict[str, dict]:
    """The newest beat of each agent, any day: a sign of life does not stop at midnight."""
    out: dict[str, dict] = {}
    for b in read_jsonl(team.BEATS) if team.BEATS.exists() else []:
        if b.get("agent"):
            out[b["agent"]] = b
    return out


def silent_minutes(agent_id: str, now: datetime | None = None) -> float:
    """Minutes since this agent last showed life: a beat, or tokens recorded in its own store. Infinity when it never has."""
    now = now or _now()
    last = _ts((_beat_rows().get(agent_id) or {}).get("t")) or 0.0
    try:
        a = next((a for a in missions.crew({"herdr": {"agents": []}}) if a["id"] == agent_id), None)
        if a and not a.get("ghost"):
            ev = usage(a, now.timestamp() - 86400)["events"]
            if ev:
                last = max(last, ev[-1]["t"])
    except Exception:   # noqa: BLE001 - an unreadable store counts as silence, not as a crash
        pass
    return (now.timestamp() - last) / 60 if last else float("inf")


def crew_state(roster: list[dict] | None = None, now: datetime | None = None, keys: list[dict] | None = None) -> list[dict]:
    """One row per agent in crew.toml (commented-out blocks included): plan, lamp, task, last sign of life, tokens, limit."""
    now = now or _now()
    cfg = missions.settings()
    if roster is None:
        roster = missions.crew()
    keys = keyhealth(roster, now=now) if keys is None else keys
    beats, held = _beat_rows(), missions.claims()
    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_board = {r["agent"]: r for r in team.board()["agents"]}
    out = []
    for a in roster:
        row = {"id": a["id"], "name": a["name"], "kind": a.get("kind"), "jobs": a.get("jobs") or [], "cost": a.get("cost"), "costLabel": a.get("costLabel"),
               "plan": str(a.get("plan") or "unknown"), "planSource": "read" if a.get("plan") and a.get("plan") != "unknown" else "unknown",
               "provider": a.get("provider"), "installed": bool(a.get("installed")), "model": next((x for i, x in enumerate(a.get("args") or []) if i and a["args"][i - 1] == "--model"), None)}
        if a.get("ghost") or not a.get("installed"):
            row.update(lamp="not-installed", lampReason=("its block in crew.toml is commented out" if a.get("ghost") else f"`{a.get('kind')}` is not on this machine's PATH"),
                       task="", lastBeatAt=None, beatAgeSec=None, tokensIn=None, tokensOut=None, usd=None, usageSource="unknown", limit=None, key=None, claims=[])
            out.append(row)
            continue
        mine = [c for c in held.values() if c["agent"] == a["id"]]
        b, tb = beats.get(a["id"]) or {}, today_board.get(a["id"]) or {}
        w = _window(a, now)
        since = min(day0.timestamp(), (w["start"] or day0).timestamp(), now.timestamp() - 86400)
        try:
            use = usage(a, since)
        except Exception as e:  # noqa: BLE001 - one unreadable store must not blank the crew
            use = _empty("unknown", "", f"usage could not be read ({type(e).__name__})")
        today = [e for e in use["events"] if e["t"] >= day0.timestamp()]
        key = next((k for k in keys if a["id"] in k["usedBy"]), None)
        last_use = use["events"][-1]["t"] if use["events"] else None
        last_beat = _ts(b.get("t"))
        life = max([x for x in (last_beat, last_use, *(_ts(c["t"]) for c in mine)) if x] or [0.0])
        silent = (now.timestamp() - life) / 60 if life else None
        beat_status = b.get("status") if last_beat and now.timestamp() - last_beat < 86400 else None
        panes = [p["status"] for p in a.get("panes") or []]
        active = bool(mine) or beat_status in ("running", "refreshing") or "working" in panes
        if a.get("benched"):
            lamp, why = "benched", "took a mission today and went idle without a report; it sits out until tomorrow"
        elif key and key["state"] in BAD_KEY:
            lamp, why = "key-rejected", f"{key['var']}: {key['state']} ({key['detail']})"
        elif beat_status in ("blocked", "error") or "blocked" in panes:
            lamp, why = "blocked", b.get("note") or b.get("task") or "its pane is waiting on something"
        elif active and silent is not None and silent > float(cfg["dormant_minutes"]):
            lamp, why = "dormant", f"holding work and silent for {int(silent)} min (limit {cfg['dormant_minutes']})"
        elif active and silent is not None and silent > float(cfg["stale_minutes"]):
            lamp, why = "stale", f"holding work and silent for {int(silent)} min (amber after {cfg['stale_minutes']})"
        elif active:
            lamp, why = "live", "holding a mission" if mine else "reported running"
        elif last_use and now.timestamp() - last_use < LIVE_MIN * 60:
            lamp, why = "live", f"its own store recorded tokens in the last {LIVE_MIN} min"
        else:
            lamp, why = "idle", "no mission and no recent beat"
        task = (b.get("task") if active or lamp == "blocked" else "") or (f"mission {mine[0]['mission']}" if mine else "")
        if not task and lamp == "live":
            task = "working in a session the board did not start"
        row.update(lamp=lamp, lampReason=why, task=task, lastBeatAt=_iso(last_beat), beatAgeSec=int(now.timestamp() - last_beat) if last_beat else None,
                   lastSeenAt=_iso(life) if life else None, silentMin=round(silent, 1) if silent is not None else None,
                   tokensIn=sum(e["in"] for e in today), tokensOut=sum(e["out"] for e in today),
                   requests=(sum(1 for t in use["requests"] if t >= day0.timestamp()) if "requests" in use else len(today) if use.get("grain") == "request" else None), usd=round(sum(e["usd"] for e in today), 6),
                   cacheRead=sum(e.get("cacheRead", 0) for e in today) or None, models=sorted({e.get("model") for e in today if e.get("model")})[:6],
                   usageSource=use["source"], usageFrom=use["from"], usageError=use.get("error"), done=tb.get("done"), total=tb.get("total"),
                   key={"var": key["var"], "state": key["state"], "detail": key["detail"], "checkedAt": key.get("checkedAt")} if key else None,
                   claims=[{"mission": c["mission"], "since": c["t"]} for c in mine],
                   limit=limit_reading(a, use, now, (key or {}).get("facts") if key and key["state"] == "ok" else None))
        row["limit"].update(id="own", label="crew.toml limit" if row["limit"]["limit"] is not None else "our own count")
        read = provider_windows(a, now)
        if any(w["pct"] is not None for w in read):          # the provider's own reading leads; a limit typed into crew.toml stays beside it
            row["limits"] = read + ([row["limit"]] if row["limit"]["limit"] is not None else [])
            row["limit"] = max((w for w in row["limits"] if w["pct"] is not None), key=lambda w: w["pct"])
        else:
            row["limits"] = [row["limit"]] + read
        detail = plan_detail(a)
        if detail:
            row["planDetail"] = detail
            if row["plan"] == "unknown":
                row["plan"], row["planSource"] = detail["text"], "read"
        out.append(row)
    return out


def fitness(roster: list[dict]) -> dict[str, str]:
    """agent -> the reason Autopilot must not start it now. Empty for an agent that is fine. (Too dear is the board's own rule.)"""
    hold = float(missions.settings()["hold_percent"])
    out = {}
    for r in crew_state(roster):
        lim = r.get("limit") or {}
        if r["lamp"] == "key-rejected":
            out[r["id"]] = "its key is not accepted: " + r["lampReason"]
        elif r["lamp"] == "dormant":
            out[r["id"]] = r["lampReason"]
        elif lim.get("pct") is not None and lim["pct"] >= hold:
            out[r["id"]] = f"{lim['pct']:.0f}% of its {lim.get('label') if lim.get('unit') == 'percent' else 'limit'} is used (Autopilot holds at {hold:.0f}%)"
    return out


# ---------------------------------------------------------------- the rest of the panel

def _run(key: str, args: list[str], ttl: float = 30.0) -> str | None:
    hit = _RUN_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=4)
        text = (r.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        text = None
    _RUN_CACHE[key] = (time.monotonic(), text)
    return text


def system(now: datetime, server: dict | None = None) -> dict:
    from faceless import safety
    cfg, pause = missions.settings(), safety.paused()
    timer = _run("timer", ["systemctl", "--user", "is-active", "qm-autopilot.timer"])
    try:
        from zoneinfo import ZoneInfo
        pt = now.astimezone(ZoneInfo("America/Los_Angeles"))
        yt = (pt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).astimezone(timezone.utc)
    except Exception:   # noqa: BLE001 - no zone database: the winter rule, said as such
        yt = now.replace(hour=8, minute=0, second=0, microsecond=0)
        yt += timedelta(days=1) if yt <= now else timedelta(0)
    day_end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return {"autopilot": {"state": "paused" if pause else "on" if cfg["enabled"] else "off", "enabled": bool(cfg["enabled"]), "maxParallel": cfg["max_parallel"],
                          "maxCost": cfg["max_cost"], "timer": timer or "unknown", "source": "crew.toml [autopilot], systemctl --user is-active qm-autopilot.timer"},
            "pause": pause, "pauseSource": "state/PAUSE, studio.toml [safety]",
            "server": server or {"state": "unknown", "reason": "asked from the command line, not through the server"},
            "clocks": {"now": _iso(now),
                       "resets": [{"id": "youtube-quota", "label": "YouTube quota", "at": _iso(yt), "source": "estimate", "rule": "midnight Pacific time (08:00 UTC in winter)"},
                                  {"id": "spend-day", "label": "Spend day", "at": _iso(day_end), "source": "estimate", "rule": "the ledger's day is the UTC day"}]}}


def _ledger_rows(day: str) -> list[dict]:
    from faceless import ledger
    return [r for r in (read_jsonl(ledger.LEDGER) if ledger.LEDGER.exists() else []) if r.get("day") == day]


def core(slow: dict | None, now: datetime) -> dict:
    from faceless import safety
    day = now.strftime("%Y-%m-%d")
    rows = _ledger_rows(day)
    usd = round(sum(float(r.get("usd") or 0) for r in rows), 6)
    ceiling = safety.ceiling()
    timed = [r for r in rows if _ts(r.get("t"))]
    burn = round(sum(float(r.get("usd") or 0) for r in timed if _ts(r["t"]) >= now.timestamp() - 3600), 6) if timed else None
    spend = {"usd": usd, "ceilingUsd": ceiling, "pct": round(100 * usd / ceiling, 1) if ceiling else None, "source": "estimate", "ceilingSource": "read",
             "burnPerHour": burn, "burnSource": "estimate" if burn is not None else "unknown",
             "burnReason": None if burn is not None else "no ledger row of today carries a time yet (rows written before this panel have only a day)",
             "projectedEmptyAt": _iso(now + timedelta(hours=(ceiling - usd) / burn)) if burn and usd < ceiling else None,
             "from": "state/ledger.jsonl (rows of today, summed by us); studio.toml [safety] daily_usd_ceiling"}
    cfg = missions.settings()
    m, j = (slow or {}).get("missions"), (slow or {}).get("jobs")
    why = None if slow else "the overview has not been built yet"
    load = {"running": len(m["running"]) if m else None, "maxParallel": cfg["max_parallel"], "source": "read" if m else "unknown", "reason": why,
            "missions": [{"id": x["id"], "title": x["title"], "agent": (x.get("run") or {}).get("agent"), "since": (x.get("run") or {}).get("since")} for x in (m or {}).get("running", [])],
            "from": "state/journal.jsonl (CC_MISSION), state/agents/claims, crew.toml [autopilot] max_parallel"}
    target = (config.load().get("production") or {}).get("videos_per_day")
    queue = {"ready": j["passedToday"] if j else None, "held": j["heldToday"] if j else None, "posted": j["postedToday"] if j else None,
             "made": j.get("madeToday") if j else None, "target": target, "source": "read" if j else "unknown", "reason": why,
             "from": "state/jobs/*.json, state/phone/receipts.jsonl; studio.toml [production] videos_per_day"}
    return {"spend": spend, "load": load, "queue": queue}


def providers(now: datetime) -> dict:
    """Every provider and model in today's ledger. Counted by us from ledger rows, so every figure here is an `estimate`."""
    g = team.gauges(now.strftime("%Y-%m-%d"))
    out = {"providers": [], "models": [], "source": "estimate", "from": "state/ledger.jsonl (rows of today)"}
    for p in g["providers"]:
        plan = "free" if p["provider"] in team.FREE_PROVIDERS else "paid" if p["usd"] > 0 else "unknown"
        out["providers"].append({"provider": p["provider"], "plan": plan, "planSource": "read" if plan == "free" else "estimate" if plan == "paid" else "unknown",
                                 "planReason": {"free": "on the engine's list of free providers", "paid": "the ledger shows money spent on it today",
                                                "unknown": "no money spent today and not on the free list; its plan is not recorded"}[plan],
                                 "calls": p["calls"], "usd": p["usd"], "units": p["units"], "source": "estimate"})
    for m in g["models"]:
        plan = "free" if m["model"].endswith(":free") else "paid" if m["usd"] > 0 else "unknown"
        out["models"].append({"model": m["model"], "provider": m["provider"], "plan": plan, "planSource": "read" if plan == "free" else "estimate" if plan == "paid" else "unknown",
                              "calls": m["calls"], "tokensIn": m["tokensIn"], "tokensOut": m["tokensOut"], "usd": m["usd"], "source": "estimate"})
    return out


def _journal_tail(window: int = 600_000) -> list[dict]:
    try:
        with open(events.JOURNAL, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - window))
            chunk = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    rows = []
    for line in chunk.splitlines()[(1 if size > window else 0):]:
        if "CC_MISSION" not in line and "CC_ACTION" not in line and EVENT_KEY not in line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def feed(names: dict[str, str], limit: int = 40) -> list[dict]:
    """The newest things that happened between the crew, one line each, newest first."""
    out = []

    def who(x):
        return names.get(x, x or "someone")
    for i, e in enumerate(_journal_tail()):
        t, ev, mid = e.get("ts"), e.get("event"), e.get("mission") or ""
        if e.get("type") == "CC_MISSION":
            note = str(e.get("note") or "")
            kind, text = {"claim": ("claim", f"{who(e.get('agent'))} claimed {mid}"),
                          "release": ("claim", f"{who(e.get('agent'))} released {mid}"),
                          "requeue": ("requeue", f"{mid} back on the board: {note}"),
                          "skip": ("skip", f"{mid} held because {who(e.get('agent'))}: {note}"),
                          "ask": ("handoff", f"{who(e.get('agent'))} asked for {e.get('tag')}: {note}"),
                          "dispatched": ("action", f"{mid} sent to {who(e.get('agent'))}"),
                          "picked": ("action", f"Autopilot picked {mid}"),
                          "done": ("done", f"{who(e.get('agent'))} finished {mid}: {note}"),
                          "blocked": ("blocked", f"{who(e.get('agent'))} blocked on {mid}: {note}")}.get(ev, (None, None))
        elif e.get("type") == EVENT_KEY:
            kind, text = "key", f"key {e.get('key')} ({e.get('var')}) is {e.get('state')}; was {e.get('was')}"
        else:
            if str(e.get("actor") or "").startswith("mission:") or e.get("state") == "running":
                continue
            kind, text = "action", f"{e.get('label') or e.get('action')}: {e.get('summary') or ('ok' if e.get('ok') else e.get('refused') or 'failed')}"
            if e.get("ok") is False:
                kind = "blocked"
        if kind:
            out.append({"id": f"{e.get('t') or t}-{i}", "t": t, "kind": kind, "text": " ".join(str(text).split()), "agent": e.get("agent") or e.get("actor")})
    folded: list[dict] = []
    for row in out[::-1]:                                    # newest first; the same line many times over becomes one line with a count
        same = next((f for f in folded[-6:] if f["kind"] == row["kind"] and f["text"] == row["text"]), None)
        if same:
            same["count"] = same.get("count", 1) + 1
            same["firstT"] = row["t"]
        else:
            folded.append(row)
    out = folded[:limit]
    for row in out:                                          # the journal is already scrubbed on write; this is the second lock, on the few lines shown
        row["text"] = config.redact(row["text"])[:220]
    return out


def handoffs(roster: list[dict], hours: int = 48) -> list[dict]:
    """`crew ask` chains: who asked, for which job, and who the board would give it to. Open until someone reports on it."""
    rows = missions.log()
    closed = {e["mission"] for e in rows if e.get("event") in ("done", "blocked")}
    out = []
    for e in rows:
        if e.get("event") == "ask" and missions._minutes(e.get("ts")) < hours * 60:
            to = missions.route(e.get("tag") or "", [a for a in roster if a["id"] != e.get("agent")])
            out.append({"mission": e["mission"], "from": e.get("agent"), "to": to["id"] if to else None, "tag": e.get("tag"), "note": str(e.get("note") or "")[:160],
                        "at": e.get("ts"), "open": e["mission"] not in closed})
    return out[-12:]


def you(slow: dict | None, crew_rows: list[dict], keys: list[dict], sysd: dict) -> list[dict]:
    """Everything that waits for the owner, each with the one action that clears it. The board never does these itself."""
    out = []

    def add(iid, text, action, level="warn", href=None, src="", do=None):
        # `do` is a button the display may press itself: one allowlisted action (faceless/actions.py) that sends, posts and uploads nothing
        out.append({"id": iid, "text": text, "action": action, "level": level, "href": href, "source": src, **({"do": do} if do else {})})
    if sysd.get("pause"):
        add("pause", f"The studio is paused: {sysd['pause']}", "Resume when ready: python -m faceless pause --resume", "stop", None, "state/PAUSE")
    for k in keys:
        if k["state"] in BAD_KEY:
            users = f" ({', '.join(k['usedBy'])} cannot work without it)" if k["usedBy"] else ""
            add(f"key-{k['id']}", f"{k['label']}: {k['var']} is {k['state']}{users}", f"Paste a working key as {k['var']} in {k['where'] or 'the env file'}",
                "stop" if k["usedBy"] else "warn", None, "state/tmp/keyhealth.json", {"name": "keys_probe", "args": {}, "label": "Re-check keys now"})
    m = (slow or {}).get("missions") or {}
    for x in m.get("todo") or []:
        b = x.get("blocked")
        if b and re.search(r"(?i)verif|login|log in|captcha|play services|2fa|password|sign in", b.get("note") or ""):
            add(f"screen-{x['id']}", f"{x['title']} stopped at a screen only you can clear: {b['note'][:140]}", "Clear it on the device, then send the mission again from the desk",
                "stop", "desk#mission", "state/journal.jsonl (CC_MISSION blocked)")
        if x.get("kind") == "owner":
            add(x["id"], x["title"], {"dms": "Open the DM desk and send by hand", "money": "Open Money and approve a price", "alerts": "Open Alerts for the steps"}.get(x.get("tab"), "Open the desk"),
                "warn", f"desk#{x.get('tab') or 'mission'}", "overview (derived mission)")
        elif x.get("held") and "send it yourself" in x["held"]:
            add(f"send-{x['id']}", f"{x['title']} waits for your click: {x['held']}", "Send it, or leave it", "info", "desk#mission", "crew.toml [autopilot] max_cost",
                {"name": "mission", "args": {"mission": x["id"]}, "label": f"Send to {(x.get('route') or {}).get('name') or 'the agent'}", "confirm": True})
    for r in crew_rows:
        if r["lamp"] == "dormant":
            add(f"dormant-{r['id']}", f"{r['name']} went silent: {r['lampReason']}", "Look at its terminal; its mission goes back on the board by itself", "warn", None, "state/agents/beats.jsonl",
                {"name": "crew_reap", "args": {}, "label": "Take its mission back now"} if r.get("claims") else None)
    return out


def held(slow: dict | None) -> list[dict]:
    return [{"mission": x["id"], "title": x["title"], "reason": x["held"], "skipped": x.get("skipped") or []} for x in ((slow or {}).get("missions") or {}).get("todo", []) if x.get("held")]


# ---------------------------------------------------------------- the snapshot

def slim(doc: dict) -> dict:
    """The part of the overview the panel needs, small enough to save."""
    return {"generatedAt": doc.get("generatedAt"), "day": doc.get("day"), "jobs": {k: v for k, v in (doc.get("jobs") or {}).items() if not isinstance(v, (list, dict))} or None,
            "missions": doc.get("missions"), "alerts": doc.get("alerts")}


def save_slow(doc: dict) -> dict:
    s = slim(doc)
    try:
        SLOW.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(SLOW, json.dumps(s, ensure_ascii=False))
    except OSError:
        pass
    return s


def load_slow() -> dict | None:
    try:
        return json.loads(SLOW.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build(slow: dict | None = None, server: dict | None = None, now: datetime | None = None) -> dict:
    """The whole snapshot. `slow` is a (slimmed) overview; without one the last saved copy is used and its age is stated."""
    now = now or _now()
    if slow is None:
        slow = load_slow()
    roster = ((slow or {}).get("missions") or {}).get("crew") or missions.crew()
    keys = keyhealth(roster, now=now)
    crew_rows = crew_state(roster, now, keys)
    sysd = system(now, server)
    names = {r["id"]: r["name"] for r in crew_rows}
    roster_ids = set(names)
    lanes = [{"agent": r["agent"], "status": r["status"], "task": r.get("task") or "", "lastBeatAt": r.get("lastBeat"), "done": r.get("done"), "total": r.get("total"),
              "note": r.get("note") or ""} for r in team.board()["agents"] if r["agent"] not in roster_ids]
    slow_at = _ts((slow or {}).get("generatedAt"))
    y = you(slow, crew_rows, keys, sysd)
    return {"generatedAt": _iso(now), "day": now.strftime("%Y-%m-%d"),
            "slow": {"at": (slow or {}).get("generatedAt"), "ageSec": int(now.timestamp() - slow_at) if slow_at else None,
                     "state": "ok" if slow_at else "warming", "what": "jobs, missions and alerts come from the overview, which is rebuilt in the background"},
            "system": sysd, "you": y, "youCount": len(y), "core": core(slow, now), "crew": crew_rows, "engine": lanes,
            "handoffs": handoffs(roster), "claims": list(missions.claims().values()), "held": held(slow),
            "keys": [{k: v for k, v in r.items() if k != "facts"} for r in keys], **{"ledger": providers(now)},
            "feed": feed(names), "thresholds": {k: missions.settings()[k] for k in ("stale_minutes", "dormant_minutes", "hold_percent", "max_cost", "max_parallel")},
            "sources": {"read": "a provider's API or a local file that is the record itself", "estimate": "counted or worked out by us", "unknown": "not known; never guessed"}}


def _left(lim: dict | None) -> str:
    if not lim:
        return "no gauge"
    if lim["unit"] == "percent" and lim["pct"] is not None:
        return f"{lim['pct']}% of the {lim['label']} used ({lim['source']})" + (f", resets {lim['resetAt']}" if lim["resetAt"] else "")
    if lim["limit"] is None:
        return "limit unknown" + (f" ({lim['used']:,} {lim['unit']} used {lim['usedScope']}, {lim['usedSource']})" if lim["used"] is not None else "")
    return f"{lim['pct']}% used: {lim['used']:,} of {lim['limit']:,.0f} {lim['unit']} ({lim['source']})" + (f", resets {lim['resetAt']}" if lim["resetAt"] else "")


def preflight(agent_id: str, snap: dict) -> tuple[int, str]:
    """What an agent reads before it picks work: its own state and budget, who has what, and where another agent is better placed."""
    me = next((r for r in snap["crew"] if r["id"] == agent_id), None)
    if me is None:
        return 2, f"`{agent_id}` is not in crew.toml. The crew: " + ", ".join(r["id"] for r in snap["crew"])
    L = [f"PRE-FLIGHT for {me['name']} ({agent_id}) at {snap['generatedAt']}",
         f"You: {me['lamp']} ({me['lampReason']}); plan {me['plan']}; cost {me.get('costLabel')}; jobs {', '.join(me['jobs']) or 'none'}",
         f"Budget: {_left(me.get('limit'))}"]
    if me.get("key"):
        L.append(f"Key: {me['key']['var']} is {me['key']['state']}")
    lim = me.get("limit") or {}
    stop = None
    if me["lamp"] in ("key-rejected", "not-installed"):
        stop = f"Do not start work: {me['lampReason']}."
    elif lim.get("pct") is not None and lim["pct"] >= snap["thresholds"]["hold_percent"]:
        stop = f"Do not start new work: {lim['pct']}% of your limit is used. Hand over with `python -m faceless crew ask <job-tag> \"what is needed\" --agent {agent_id}`."
    if snap["system"]["pause"]:
        stop = f"The studio is paused ({snap['system']['pause']}). Start nothing."
    L.append("Others:")
    for r in snap["crew"]:
        if r["id"] != agent_id:
            L.append(f"  {r['name']:12} {r['lamp']:13} {r.get('costLabel') or '':5} {(r.get('task') or '')[:70]}" + (f"  [{_left(r['limit'])}]" if r.get("limit") else ""))
    L.append("Taken (do not start these): " + (", ".join(f"{c['mission']} by {c['agent']}" for c in snap["claims"]) or "nothing"))
    todo = ((load_slow() or {}).get("missions") or {}).get("todo") or []
    mine = [m for m in todo if (m.get("route") or {}).get("agent") == agent_id]
    L.append("Open and routed to you: " + ("; ".join(f"{m['id']} ({m['title']})" for m in mine[:5]) or "nothing"))
    better = []
    for m in todo:
        rt = m.get("route") or {}
        if m.get("kind") == "agent" and rt.get("agent") not in (None, agent_id) and m.get("tag") in me["jobs"]:
            better.append(f"{m['id']}: {rt.get('name')} is better placed ({rt.get('why')}, {rt.get('cost')})")
    L.append("Better placed than you: " + ("; ".join(better[:5]) or "nobody for the open work you could do"))
    for h in snap["held"]:
        L.append(f"Held: {h['mission']} because {h['reason']}")
    L.append(stop or f"Before you start: python -m faceless crew claim <mission> --agent {agent_id}   (refused if another agent holds it)")
    L.append(f"While you work: python -m faceless agent beat {agent_id} running --task \"...\" every few minutes; silent for {snap['thresholds']['dormant_minutes']} min and the mission is taken back.")
    return (1 if stop else 0), "\n".join(L)


def summary(snap: dict) -> str:
    c, s = snap["core"], snap["system"]
    L = [f"Instruments at {snap['generatedAt']} (overview {snap['slow']['state']}" + (f", {snap['slow']['ageSec']} s old)" if snap["slow"]["ageSec"] is not None else ")"),
         f"Autopilot {s['autopilot']['state']} (timer {s['autopilot']['timer']}); pause: {s['pause'] or 'no'}; waiting for you: {snap['youCount']}",
         f"Spend today ${c['spend']['usd']:.4f} of ${c['spend']['ceilingUsd']:.2f} (estimate); load {c['load']['running']}/{c['load']['maxParallel']}; "
         f"queue ready {c['queue']['ready']} held {c['queue']['held']} posted {c['queue']['posted']} of {c['queue']['target']}"]
    for r in snap["crew"]:
        L.append(f"  {r['name']:12} {r['lamp']:13} plan {r['plan']:12} {_left(r.get('limit'))}" + (f" | {r['task'][:60]}" if r.get("task") else ""))
    for k in snap["keys"]:
        L.append(f"  key {k['id']:16} {k['var']:22} {k['state']}")
    for y in snap["you"]:
        L.append(f"  YOU [{y['level']}] {y['text']} -> {y['action']}")
    for h in snap["held"]:
        L.append(f"  held {h['mission']} because {h['reason']}")
    return "\n".join(L)


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="python -m faceless instruments")
    p.add_argument("--json", action="store_true", help="print the whole snapshot")
    p.add_argument("--for", dest="agent", help="an agent's pre-flight (exit 1 when it should not start work)")
    p.add_argument("--probe", action="store_true", help="ask each key's service whether the key works (free, read-only) before printing")
    p.add_argument("--fast", action="store_true", help="never rebuild the overview; use the last saved copy however old")
    a = p.parse_args(argv)
    config.load_keys()
    slow = load_slow()
    age = (time.time() - (_ts((slow or {}).get("generatedAt")) or 0)) / 60
    if not a.fast and (slow is None or age > SLOW_TTL_MIN):
        from faceless import overview
        slow = save_slow(overview.build())
    if a.probe:
        keyhealth(refresh=True)
    snap = build(slow)
    if a.agent:
        code, text = preflight(a.agent.strip().lower(), snap)
        print(text, file=sys.stderr if code == 2 else sys.stdout)
        return code
    print(json.dumps(snap, indent=1, ensure_ascii=False) if a.json else summary(snap))
    return 0
