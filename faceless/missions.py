"""Mission control: the work that makes money, who should do it, and what is in motion. One board for every agent.

Nothing here is a second store. The to-do list is DERIVED from the overview (the same real state the page shows), so a mission
disappears when the thing it names is no longer true. Who was sent what, and what they said when they finished, are `CC_MISSION`
lines in the studio's journal. The crew is `crew.toml`: one block per agent.

Routing is the token rule: an engine command (zero tokens) when one does the job; otherwise the cheapest installed agent whose `jobs`
list the mission's tag; a paid agent only when nothing cheaper lists it. Owner missions (send a DM, set a price) are never dispatched.

Agents talk to each other through the board, not to each other directly:
    python -m faceless crew report <mission> done|blocked "one line"     # close what you were sent
    python -m faceless crew ask <job-tag> "what you need"                # open a mission for a better-suited agent
Dispatch reaches an agent through herdr (`herdr agent start`, `herdr agent prompt`), so any agent kind herdr knows can join.
"""

from __future__ import annotations

import json
import re
import secrets
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone

from faceless import config, events, safety
from faceless.config import Paths

EVENT = "CC_MISSION"
ROSTER = Paths.root / "crew.toml"
DEFAULTS = {"enabled": False, "max_parallel": 2, "phone": False, "agent_ttl_minutes": 180, "max_cost": 1}
TAG = re.compile(r"^[a-z][a-z0-9-]{1,24}$")
MISSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,180}$")
COST = {0: "free", 1: "cheap", 2: "paid"}
COST_OF = {v: k for k, v in COST.items()}


def _now() -> str:
    return events.now_iso()


def _minutes(iso: str | None) -> float:
    try:
        then = datetime.strptime(str(iso), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return 1e9
    return (datetime.now(timezone.utc) - then).total_seconds() / 60


def settings() -> dict:
    try:
        with open(ROSTER, "rb") as f:
            return {**DEFAULTS, **(tomllib.load(f).get("autopilot") or {})}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def crew(agents_doc: dict | None = None) -> list[dict]:
    """The roster with what is true right now: installed or not, and each live herdr pane with its status."""
    try:
        with open(ROSTER, "rb") as f:
            raw = tomllib.load(f).get("agents") or {}
    except (OSError, ValueError):
        raw = {}
    if agents_doc is None:
        from faceless import agents
        agents_doc = agents.build()
    panes = (agents_doc.get("herdr") or {}).get("agents") or []
    out = []
    for aid, a in raw.items():
        if a.get("enabled") is False:                        # benched by the owner (a dead key, a trial that ran out)
            continue
        kind = str(a.get("kind") or aid)
        live = [{"pane": p.get("id"), "status": p.get("status") or "unknown"} for p in panes if p.get("agent") == kind]
        out.append({"args": [str(x) for x in a.get("args") or []], "outside": _outside(kind, len(live)),
                    "id": aid, "name": a.get("name") or aid, "kind": kind, "jobs": list(a.get("jobs") or []), "cost": int(a.get("cost", 1)),
                    "costLabel": COST.get(int(a.get("cost", 1)), "paid"), "installed": bool(shutil.which(str(a.get("bin") or kind))), "panes": live,
                    "status": ("working" if any(p["status"] == "working" for p in live) else "blocked" if any(p["status"] == "blocked" for p in live)
                               else "idle" if live else "asleep")})
    return sorted(out, key=lambda a: (a["cost"], a["id"]))


def _outside(kind: str, in_herdr: int) -> bool:
    """Is this agent also running somewhere the board cannot see (a terminal of the owner's)? True when more processes exist than panes."""
    try:
        r = subprocess.run(["pgrep", "-x", kind], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return len(r.stdout.split()) > in_herdr


def made_unposted(day: str, days: int = 3) -> list[str]:
    """Passed, packaged videos of the last few days that have no TikTok receipt and no phone job yet: made, and reaching nobody."""
    from faceless import phone
    from faceless.state import scan_jobs
    seen = {r.get("key") for r in phone.receipts() if r.get("kind") == "tiktok"} | {j.get("key") for j in phone.jobs() if j.get("kind") == "tiktok"}
    return sorted(j.id for j in scan_jobs()[0] if j.day > _days_ago(day, days) and j.status == "packaged" and (j.scores or {}).get("passed")
                  and j.id not in seen and j.artifacts.get("video"))


def route(tag: str, roster: list[dict]) -> dict | None:
    """The cheapest installed agent that lists this job; among equals, one that is already awake and idle."""
    fit = [a for a in roster if a["installed"] and tag in a["jobs"]]
    return min(fit, key=lambda a: (a["cost"], 0 if a["status"] == "idle" else 1 if a["status"] == "asleep" else 2), default=None)


def log(limit: int = 400, window: int = 900_000) -> list[dict]:
    """The newest mission lines and mission-run engine actions from the journal's tail, oldest first."""
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
        if EVENT not in line and '"mission:' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == EVENT:
            rows.append(e)
        elif e.get("type") == "CC_ACTION" and str(e.get("actor") or "").startswith("mission:"):
            rows.append({"ts": e.get("ts"), "type": EVENT, "mission": e["actor"][8:], "event": "done" if e.get("ok") else "blocked",
                         "agent": "engine", "note": e.get("summary") or ""})
    return rows[-limit:]


def derive(doc: dict) -> list[dict]:
    """What needs doing, in the order it pays: straight from the overview, so nothing is listed that is not true right now."""
    out: list[dict] = []
    j, ph, ob, of = doc.get("jobs"), doc.get("phone"), doc.get("outbound"), doc.get("offers")
    day = doc.get("day") or config.today_utc().isoformat()

    def add(mid, title, why, kind, **kw):
        out.append({"id": mid, "title": title, "why": why, "kind": kind, "auto": kind != "owner", **kw})
    if ob and ob.get("blockedOnOwner"):
        add(f"send-dms-{day}", f"Send {ob['blockedOnOwner']} DM drafts", "The shortest road to a first receipt: a conversation with one person.", "owner", tab="dms")
    if ob and ob.get("followUpsDue"):
        add(f"follow-ups-{day}", f"Send {ob['followUpsDue']} follow-ups", "Most replies come on the second message.", "owner", tab="dms")
    pr = doc.get("prospects")
    if pr and not pr.get("draftedToday") and (pr.get("ready") or pr.get("youtube")):
        n = pr.get("ready") or 0
        add(f"prospect-{day}", f"Turn {n} new comment(s) into DM drafts" if n else "Read today's comments for people to write to",
            "Someone who already wrote to us is the warmest person there is.", "engine", action="prospect", args={})
    if pr and not pr.get("addedToday") and ph is not None:
        add(f"harvest-comments-{day}", "Collect today's comments from the TikTok inbox", "The prospect machine can only draft for people it has been shown.",
            "agent", tag="phone", auto=bool(settings()["phone"]),
            brief=("Use the faceless-prospect skill. On the phone, open TikTok > Inbox > Activity and read the comments left on our videos in the last three days. "
                   "For each real comment (skip emoji-only and promotion) run `python -m faceless prospect add --handle @their_handle --text \"their exact words\" "
                   "--video \"the video title\" --platform tiktok`. Read only: never reply, like, follow or message. When done run `python -m faceless prospect` "
                   "and report how many were added. Stop at a login wall or a verification screen and report blocked."))
    if j:
        if not j["ranToday"] or j["passedToday"] < 5:
            add(f"daily-{day}", "Make today's five videos", "No videos, no reach; reach is what every offer rides on.", "engine", action="daily", args={})
        for r in [r for r in j["failed"] if r["day"] > _days_ago(day, 7)][:3]:
            add(f"retry-{r['id']}", f"Retry: {r['title']}", f"Stopped at {r['step']}; a finished video is a post.", "engine", action="job_retry", args={"job": r["id"]})
        held = [r for r in j["held"] if r["day"] > _days_ago(day, 7)]
        if held:
            ids = [r["id"] for r in held[:6]]
            add(f"held-review-{day}", f"Fix and release {len(held)} held videos", "Finished videos sitting behind a gate earn nothing.", "agent", tag="writing",
                brief=("These videos are held by the gauntlet: " + ", ".join(ids) + ". For each: read gauntlet/reports/<id>.md, and when the failed gate is a script "
                       "fault (word count, duration, originality, duplicate) fix script-lab/final/<id>.json so the gate would pass, keeping every number true; "
                       "then run `python -m faceless retry <id>`. Leave a video held when the fix needs a person. Never publish or upload."))
    if ph and ph.get("mediaMissing"):
        add("phone-park", f"Clear {ph['mediaMissing']} phone jobs that lost their video", "They jam the head of the posting queue.", "engine", action="phone_park", args={})
    elif ph and ph.get("next"):
        n = ph["runnable"]
        add("phone-lane", f"Post through the phone: {n} job(s) ready", "A passed video only reaches people once it is posted.", "agent", tag="phone", auto=bool(settings()["phone"]),
            brief=("Use the faceless-phone skill. Run every job `python -m faceless phone next --push` hands out, one at a time, following its recipes, and record "
                   "each with `python -m faceless phone done`. AI label on for every post. Stop at a login wall or a verification screen and report blocked."))
    try:
        made = made_unposted(day)
    except Exception:   # noqa: BLE001 - a damaged job file must not blank the board
        made = []
    if made:
        add(f"post-made-{day}", f"Post {len(made)} finished video(s) to TikTok", "Made and passed, but nobody has seen them yet.", "agent", tag="phone", auto=bool(settings()["phone"]),
            brief=("These videos passed the gauntlet and are not posted: " + ", ".join(made[:5]) + ". Post up to five today to TikTok through the phone, one at a time, "
                   "oldest first. Use the faceless-phone skill and its TikTok recipe (stage with tools/stage_local.py DAY --jobs ID,ID then post each pack; "
                   "tools/tt-phone-post.py is the scripted route). Lint every caption with the faceless-tiktok-policy skill first. The AI-generated label must be ON "
                   "for every post. Record each one with `python -m faceless phone done` or a receipt as the skill says, so nothing is posted twice. "
                   "No YouTube. Stop at a login wall, a verification screen or a missing AI-label switch and report blocked."))
    if of and of["built"] > of["live"]:
        waiting = [i["name"] for i in of["items"] if not i["live"]]
        add("list-" + "-".join(i["id"] for i in of["items"] if not i["live"])[:60], f"Set a price for {waiting[0]}", "Built and not on sale earns nothing; the price is yours to say.", "owner", tab="money")
    if not (config.load().get("newsletter") or {}).get("form_action"):
        add("newsletter-form", "Connect an email form to the hub", "The hub gives the checklist away and keeps no address to sell to later.", "owner", tab="alerts")
    return out


def _days_ago(day: str, n: int) -> str:
    from datetime import timedelta
    return (datetime.fromisoformat(day) - timedelta(days=n)).date().isoformat()


def board(doc: dict) -> dict:
    """To do, in motion, done today: the derived missions joined with what the journal says was sent and reported."""
    roster = crew(doc.get("agents"))
    cfg = settings()
    rows = log()
    last: dict[str, dict] = {}
    for e in rows:
        if e.get("mission"):
            last[e["mission"]] = e
    asks = {}
    for e in rows:                                           # a request one agent left for another stays open until someone reports on it
        if e.get("event") == "ask":
            asks[e["mission"]] = e
    missions = derive(doc)
    known = {m["id"] for m in missions}
    for mid, e in asks.items():
        if last[mid].get("event") in ("ask", "dispatched") and mid not in known and _minutes(e.get("ts")) < 60 * 48:
            missions.append({"id": mid, "title": str(e.get("note") or "Request")[:120], "why": f"Asked for by {e.get('agent') or 'an agent'}.", "kind": "agent",
                             "tag": e.get("tag") or "bulk", "auto": True, "brief": str(e.get("note") or "")})
    by_pane = {p["pane"]: p["status"] for a in roster for p in a["panes"]}
    todo, running, today = [], [], _now()[:10]
    # An agent that took a mission today and went idle without reporting cannot be trusted with the next one (a dead key, a login
    # wall): it sits out for the day and its mission is offered to the next cheapest agent.
    quiet = {mid: e for mid, e in last.items() if e.get("event") == "dispatched" and e.get("agent") not in (None, "engine")
             and str(e.get("ts"))[:10] == today and by_pane.get(e.get("pane")) in ("idle", "done", None) and _minutes(e.get("ts")) > 3}
    benched = {e["agent"] for e in quiet.values()}
    for a in roster:
        if a["id"] in benched:
            a["status"], a["benched"] = "no answer", True
    roster_fit = [a for a in roster if a["id"] not in benched]
    for m in missions:
        if m["kind"] == "agent":
            a = route(m["tag"], roster_fit)
            if a and m["tag"] == "phone" and a.get("outside"):
                m["auto"], m["note"] = False, f"{a['name']} is already working in a terminal the board cannot see; Autopilot waits for it rather than put two drivers on one phone."
            m["route"] = ({"agent": a["id"], "name": a["name"], "cost": a["costLabel"], "why": f"cheapest installed agent that does {m['tag']}"} if a
                          else {"agent": None, "name": "nobody", "cost": "", "why": f"no installed agent lists {m['tag']} in crew.toml"})
        elif m["kind"] == "engine":
            m["route"] = {"agent": "engine", "name": "Engine", "cost": "0 tokens", "why": "a command does this; no model is needed"}
        else:
            m["route"] = {"agent": "owner", "name": "You", "cost": "", "why": "money and the outside world are yours"}
        m.pop("brief", None) if m["kind"] != "agent" else None
        e = last.get(m["id"])
        age = _minutes(e.get("ts")) if e else None
        if m["id"] in quiet:
            m["note"] = f"{quiet[m['id']].get('agent')} took this and went idle without a report (check its model key or login); offered to the next agent."
            todo.append(m)
        elif e and e.get("event") == "picked" and age < 2:
            m["run"] = {"agent": "autopilot", "pane": None, "since": e.get("ts"), "status": "starting"}
            running.append(m)
        elif e and e.get("event") == "dispatched" and age < (cfg["agent_ttl_minutes"] if m["kind"] == "agent" else 300):
            pane = by_pane.get(e.get("pane"))
            m["run"] = {"agent": e.get("agent"), "pane": e.get("pane"), "since": e.get("ts"), "status": pane or ("running" if m["kind"] == "engine" else "unknown")}
            running.append(m)
        else:
            if e and e.get("event") == "blocked" and str(e.get("ts"))[:10] == today:
                m["blocked"] = {"note": e.get("note") or "", "agent": e.get("agent"), "at": e.get("ts")}
            todo.append(m)
    sent = {e["mission"]: e.get("agent") for e in rows if e.get("event") == "dispatched"}
    done = [{"id": e["mission"], "event": e["event"], "agent": sent.get(e["mission"]) or e.get("agent"), "note": e.get("note") or "", "at": e.get("ts")}
            for e in rows if e.get("event") in ("done", "blocked") and str(e.get("ts"))[:10] == today][::-1][:12]
    for m in todo + running:
        m.pop("brief", None)
    return {"crew": roster, "todo": todo, "running": running, "done": done, "autopilot": cfg, "source": "state/overview (derived), crew.toml, state/journal.jsonl (CC_MISSION), herdr api snapshot"}


def plan_auto(doc: dict | None = None) -> dict:
    """What Autopilot should start now, or why not. Reads only. One mission per tick, never an owner's, never one blocked today."""
    if why := safety.paused():
        return {"state": "paused", "text": f"Paused: {why}. Autopilot does nothing until you resume."}
    if doc is None:
        from faceless import overview
        doc = overview.build()
    b = doc.get("missions") or board(doc)
    if len(b["running"]) >= int(b["autopilot"]["max_parallel"]):
        return {"state": "busy", "text": f"{len(b['running'])} mission(s) in motion; the limit is {b['autopilot']['max_parallel']}."}
    rendering = any(m["kind"] == "engine" and m.get("action") in ("daily", "job_retry") for m in b["running"])
    for m in b["todo"]:
        if rendering and m["kind"] == "engine" and m.get("action") in ("daily", "job_retry"):
            continue                                         # one render at a time: the machine has one GPU and the batch refills its own slots
        if COST_OF.get(m["route"].get("cost"), 0) > int(b["autopilot"].get("max_cost", 1)):
            continue                                         # a paid agent is started by a person's click, never by the timer
        if m["auto"] and not m.get("blocked") and m["route"]["agent"] not in (None, "owner"):
            return {"state": "run", "mission": m["id"], "text": f"Starting: {m['title']} ({m['route']['name']}, {m['route']['cost']})"}
    waiting = sum(1 for m in b["todo"] if m["kind"] == "owner")
    return {"state": "idle", "text": (f"Nothing left that a machine may do; {waiting} thing(s) wait for you." if waiting else "Nothing needs doing right now.")}


def tick() -> dict:
    """One Autopilot step with no page open (the systemd timer runs this). The mission is started detached so a long batch does not
    hold the next tick; `[autopilot] enabled` in crew.toml is the switch and state/PAUSE the kill switch."""
    if not settings()["enabled"]:
        return {"state": "off", "text": "[autopilot] enabled = false in crew.toml"}
    plan = plan_auto()
    if plan.get("state") != "run":
        return plan
    log_file = Paths.state / "tmp" / "autopilot.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "ab") as out:
        subprocess.Popen([sys.executable, "-m", "faceless", "crew", "dispatch", plan["mission"], "autopilot"], cwd=Paths.root, stdout=out, stderr=out,   # noqa: S603
                         stdin=subprocess.DEVNULL, start_new_session=True)
    return plan


def _herdr(*args: str, timeout: int = 60) -> dict:
    r = subprocess.run(["herdr", *args], capture_output=True, text=True, timeout=timeout)
    try:
        doc = json.loads(r.stdout or "{}")
    except ValueError:
        doc = {}
    if r.returncode != 0 or "error" in doc:
        raise RuntimeError(f"herdr {' '.join(args[:2])}: {((doc.get('error') or {}).get('message') or r.stderr or r.stdout).strip()[:240]}")
    return doc.get("result") or {}


def _pane_for(agent: dict) -> str:
    """An idle pane already running this agent, else a new herdr workspace with the agent started in it."""
    idle = next((p["pane"] for p in agent["panes"] if p["status"] in ("idle", "done")), None)
    if idle:
        return idle
    label = f"qm-{agent['id']}"
    made = _herdr("workspace", "create", "--cwd", str(Paths.root), "--label", label)
    found = re.search(r'"pane_id":\s*"([^"]+)"', json.dumps(made))
    if not found:
        snap = json.dumps(_herdr("api", "snapshot"))
        ws = re.search(r'"label":\s*"' + re.escape(label) + r'".{0,400}?"workspace_id":\s*"([^"]+)"|"workspace_id":\s*"([^"]+)".{0,400}?"label":\s*"' + re.escape(label) + '"', snap)
        wid = ws and (ws.group(1) or ws.group(2))
        found = wid and re.search(r'"pane_id":\s*"(' + re.escape(wid) + r':p[^"]+)"', snap)
    if not found:
        raise RuntimeError(f"herdr made the {label} workspace but its pane id could not be read")
    pane = found.group(1)
    _herdr("agent", "start", label, "--kind", agent["kind"], "--pane", pane, "--timeout", "90000", *(["--", *agent["args"]] if agent.get("args") else []), timeout=120)
    return pane


def dispatch(mission_id: str, by: str = "owner") -> dict:
    """Send one mission to whoever the board routes it to. Engine: run its command. Agent: prompt it through herdr. Owner: refuse."""
    from faceless import actions, overview
    if why := safety.paused():
        raise RuntimeError(f"the studio is paused ({why})")
    doc = overview.build()
    b = board(doc)
    brief = {m["id"]: m.get("brief") for m in derive(doc)}
    for e in log():
        if e.get("event") == "ask":
            brief.setdefault(e["mission"], str(e.get("note") or ""))
    m = next((x for x in b["todo"] if x["id"] == mission_id), None)
    if m is None:
        state = "already in motion" if any(x["id"] == mission_id for x in b["running"]) else "not on the board (it may already be done)"
        raise RuntimeError(f"{mission_id} is {state}")
    if m["kind"] == "owner":
        raise RuntimeError("this one is yours; no agent is sent to do it")
    if m["kind"] == "engine":
        events.emit(EVENT, actor=by, mission=m["id"], event="dispatched", agent="engine", note=m["title"])
        r = actions.run(m["action"], m.get("args") or {}, actor=f"mission:{m['id']}")
        return {"mission": m["id"], "agent": "engine", "ok": r["ok"], "summary": r["summary"]}
    if not m["route"]["agent"]:
        raise RuntimeError(m["route"]["why"])
    agent = next(a for a in b["crew"] if a["id"] == m["route"]["agent"])
    pane = _pane_for(agent)
    text = (f"[Quiet Money mission {m['id']}] {m['title']}. {brief.get(m['id']) or ''} "
            f"Work in {Paths.root}; CLAUDE.md there is the law (no publishing, no spending past the caps, no key in any file). "
            f"When you finish run: python -m faceless crew report {m['id']} done \"one line on what changed\" "
            f"(or: ... report {m['id']} blocked \"why\"). If part of it suits another specialist better, hand it over with: "
            f"python -m faceless crew ask <writing|research|bulk|code|review|hard> \"what you need\".")
    _herdr("agent", "prompt", pane, re.sub(r"\s+", " ", text).strip())
    events.emit(EVENT, actor=by, mission=m["id"], event="dispatched", agent=agent["id"], pane=pane, note=m["title"])
    return {"mission": m["id"], "agent": agent["id"], "pane": pane, "ok": True, "summary": f"{agent['name']} has it (pane {pane})"}


def report(mission_id: str, result: str, note: str = "", agent: str = "agent") -> dict:
    if result not in ("done", "blocked") or not MISSION.match(mission_id):
        raise ValueError("usage: crew report <mission> done|blocked \"one line\"")
    return events.emit(EVENT, actor=agent, mission=mission_id, event=result, agent=agent, note=config.redact(note)[:300])


def ask(tag: str, note: str, agent: str = "agent") -> dict:
    if not TAG.match(tag) or not note.strip():
        raise ValueError("usage: crew ask <job-tag> \"what you need\"")
    return events.emit(EVENT, actor=agent, mission=f"ask-{secrets.token_hex(3)}", event="ask", agent=agent, tag=tag, note=config.redact(note.strip())[:400])


def main(argv: list[str]) -> int:
    """`python -m faceless crew board|dispatch <id>|report <id> done|blocked "note"|ask <tag> "note"|plan`."""
    act = argv[0] if argv else "board"
    try:
        if act == "board":
            from faceless import overview
            b = board(overview.build())
            for a in b["crew"]:
                print(f"{a['name']:12} {a['status']:8} {a['costLabel']:5} {'installed' if a['installed'] else 'missing':9} {', '.join(a['jobs'])}")
            for label, rows in (("TO DO", b["todo"]), ("IN MOTION", b["running"])):
                print(f"\n{label}")
                for m in rows:
                    print(f"  [{m['route']['name']:8}] {m['title']}  ({m['id']})")
            print("\nDONE TODAY")
            for d in b["done"]:
                print(f"  {d['event']:7} {d['id']}  {d['note'][:90]}")
        elif act == "tick":
            print(json.dumps(tick()))
        elif act == "plan":
            print(json.dumps(plan_auto()))
        elif act == "dispatch":
            r = dispatch(argv[1], by=argv[2] if len(argv) > 2 else "owner")
            print(json.dumps(r))
            return 0 if r["ok"] else 2
        elif act == "report":
            print(json.dumps(report(argv[1], argv[2], " ".join(argv[3:]))))
        elif act == "ask":
            print(json.dumps(ask(argv[1], " ".join(argv[2:]))))
        else:
            print(main.__doc__)
            return 1
    except (IndexError, ValueError, RuntimeError, OSError, subprocess.SubprocessError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    return 0
