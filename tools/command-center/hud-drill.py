#!/usr/bin/env python3
"""Rehearse the head-up display's rare states in a throwaway folder, to look at them in a browser before they happen for real.

    .venv/bin/python tools/command-center/hud-drill.py [--port 8899]      # prints the address; Ctrl+C stops it

Everything the display reads is pointed at a temp folder (a crew.toml, beats, claims, a journal, a ledger, key files, agents' stores),
so NOTHING real is read or written and no service is asked anything. The folder is then filled the way the real commands would fill
it: an agent holding a mission and silent for 50 minutes, one at 93% of a provider-reported window, a rejected key, a handoff in
flight, a mission Autopilot holds, a newly installed fourth agent. The page it serves is the real page and the real snapshot code;
only the state is rehearsed. The top of the page says so in its You strip.
"""
import argparse
import json
import os
import stat
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from faceless import cmdcache, events, instruments, ledger, missions, serve, team  # noqa: E402

import secrets  # noqa: E402

TOKEN = secrets.token_urlsafe(18)                            # made for this run only and printed with the address; it guards a temp folder


def ago(minutes: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8899)
    a = ap.parse_args()
    root = Path(tempfile.mkdtemp(prefix="qm-hud-drill-"))
    bins = root / "bin"
    bins.mkdir()
    for name in ("opencode", "hermes", "claude", "agent-zero"):
        f = bins / name
        f.write_text("#!/bin/sh\n")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    os.environ["PATH"] = f"{bins}{os.pathsep}/usr/bin{os.pathsep}/bin"
    for k in [k for k in os.environ if "KEY" in k or "TOKEN" in k]:
        del os.environ[k]
    (root / "hermes.env").write_text("OPENROUTER_API_KEY=drill-value-not-a-key-000000\n")
    (root / "crew.toml").write_text(f'''
[autopilot]
enabled = true
max_parallel = 2
max_cost = 1
[agents.opencode]
name = "OpenCode"
kind = "opencode"
jobs = ["phone", "bulk", "research", "writing"]
cost = 0
plan = "free"
limit = 120000
limit_unit = "tokens"
limit_window = "day"
reset = "00:00"
usage = "beats"
[agents.hermes]
name = "Hermes"
kind = "hermes"
jobs = ["writing", "research", "bulk"]
cost = 0
plan = "free"
provider = "openrouter"
key_env = "OPENROUTER_API_KEY"
key_file = "{root / 'hermes.env'}"
limit = 400000
limit_unit = "tokens"
limit_window = "day"
reset = "00:00"
usage = "beats"
[agents.claude]
name = "Claude Code"
kind = "claude"
jobs = ["code", "review", "hard", "phone", "writing"]
cost = 2
plan = "subscription"
limit = "unknown"
limit_file = "{root / 'claude-limits.json'}"
usage = "beats"
[agents.agent-zero]
name = "Agent Zero"
kind = "agent-zero"
bin = "agent-zero"
jobs = ["research", "bulk"]
cost = 0
plan = "unknown"
limit = "unknown"
''')
    missions.ROSTER, missions.CLAIMS = root / "crew.toml", root / "claims"
    missions._outside = lambda kind, n: False
    team.BEATS, events.JOURNAL, ledger.LEDGER = root / "beats.jsonl", root / "journal.jsonl", root / "ledger.jsonl"
    instruments.KEYHEALTH, instruments.SLOW, instruments.KEY_FILES = root / "keyhealth.json", root / "slow.json", [root / "studio.env"]
    instruments.CLAUDE_PROJECTS, instruments.HERMES_DB, instruments.OPENCODE_DB = root / "none", root / "none.db", root / "none2.db"
    instruments.CLAUDE_CONFIG, cmdcache.PATH = root / "claude.json", root / "cmd.json"
    instruments._run = lambda key, args, ttl=30.0: "active"
    now = time.time()

    def write_beat(agent, status, minutes, task, **kw):
        with team.BEATS.open("a") as f:
            f.write(json.dumps({"t": ago(minutes), "agent": agent, "status": status, "task": task, **kw}) + "\n")
    # Hermes took a mission and went silent 50 minutes ago; its key is then rejected
    missions.CLAIMS.mkdir()
    (missions.CLAIMS / "held-review-drill.json").write_text(json.dumps({"mission": "held-review-drill", "agent": "hermes", "t": ago(52)}))
    write_beat("hermes", "running", 50, "Fixing 6 held videos", tokens_in=250000, tokens_out=38000)
    # OpenCode is at work on the phone lane and beating
    missions.claim("phone-lane", "opencode")
    for m, n in ((40, 60), (20, 55), (2, 50)):
        for _ in range(n // 10):
            write_beat("opencode", "running", m, "Posting to TikTok through the phone (3 of 5)", tokens_in=4000, tokens_out=700, done=3, total=5)
    write_beat("agent-zero", "running", 1, "Researching 12 projects for the service desk", tokens_in=9000, tokens_out=2100)
    write_beat("engine-render", "running", 3, "Rendering today's batch", done=2, total=5)
    # Claude Code: the provider's own readings, 5-hour rising fast, 7-day past the hold line
    (root / "claude-limits.json").write_text(json.dumps({"t": now - 60, "windows": {
        "five_hour": {"used_percentage": 72.0, "resets_at": now + 2.2 * 3600, "samples": [[now - 2400, 55.0], [now - 60, 72.0]]},
        "seven_day": {"used_percentage": 93.0, "resets_at": now + 3.4 * 86400, "samples": [[now - 3000, 92.0], [now - 60, 93.0]]}}}))
    ledger.spend("openrouter", "tokens", 52000, usd=1.31, model="vendor/paid-model", tokens_in=41000, tokens_out=11000)
    ledger.spend("openrouter", "tokens", 9000, usd=0.0, model="vendor/free-model:free", tokens_in=7000, tokens_out=2000)
    ledger.spend("edge", "chars", 6100)

    (root / "studio.env").write_text("".join(f"{k}=drill-value-not-a-key-000000\n" for k in ("OPENROUTER_API_KEY", "QM_DASH_TOKEN", "COMPOSIO_API_KEY", "ELEVENLABS_API_KEY")))

    class Answer:
        def __init__(self, code):
            self.status_code = code

        def json(self):
            return {}

    class Services:                                          # every service says yes, except Composio, which rejects its key
        def get(self, url, **kw):
            return Answer(401 if "composio" in url else 200)
    instruments.keyhealth(missions.crew({"herdr": {"agents": []}}), refresh=True, session=Services())
    # a handoff in flight, and one finished
    missions.main(["ask", "code", "retry", "crashes", "on", "a", "job", "with", "no", "history", "--agent", "opencode"])
    missions.main(["ask", "research", "three", "sources", "for", "the", "janitor", "story", "--agent", "claude"])
    roster = missions.crew({"herdr": {"agents": []}})
    doc = {"agents": {"herdr": {"agents": []}}, "day": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "jobs": None}
    missions.derive = lambda d: [{"id": "held-review-drill", "title": "Fix and release 6 held videos", "why": "", "kind": "agent", "tag": "writing", "auto": True},
                                 {"id": "phone-lane", "title": "Post through the phone: 5 job(s) ready", "why": "", "kind": "agent", "tag": "phone", "auto": True},
                                 {"id": "send-dms-drill", "title": "THIS IS A DRILL: rehearsed state in a temp folder, not the studio", "why": "", "kind": "owner", "auto": False, "tab": "dms"}]

    missions.made_unposted = lambda day, days=3: ["drill-video-1", "drill-video-2"]      # the real one reads the studio's job files

    def overview():
        d = dict(doc, generatedAt=instruments._iso(time.time()))
        d["missions"] = missions.board(d)
        d["jobs"] = {"passedToday": 4, "heldToday": 2, "postedToday": 3, "madeToday": 7}
        missions.log_skips(d["missions"])
        return d
    source = serve.Source(overview, seconds=5)
    httpd = serve.make_server("127.0.0.1", a.port, TOKEN, build=overview, panel=serve.Panel(source, background=False, slow_seconds=5))
    print(f"drill state in {root}\nopen http://127.0.0.1:{a.port}/?t={TOKEN}   (crew: {', '.join(r['id'] for r in roster)})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
