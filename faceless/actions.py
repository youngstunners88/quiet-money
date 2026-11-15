"""The command center's action desk: the few things a click on the page may do, and nothing else.

Every action is a name on an allowlist that maps to ONE existing command (`python -m faceless ...` or `herdr ...`), run as a child
process with a timeout and no shell. The desk owns no state of its own:

  * what happened is one `CC_ACTION` line in the studio's journal (`state/journal.jsonl`, the same log every stage writes), and the
    page's activity strip is a projection of those lines;
  * what is running right now lives in the server's memory only and is gone when the server stops;
  * the jobs, the phone queue, the DM record and the receipts change only because the command that owns them ran.

The kill switch is honoured before anything that moves the pipeline: with `state/PAUSE` (or `[safety] paused`) the desk refuses and says
why. A refusal, a non-zero exit and a timeout are all results: they are journaled and shown, never swallowed.

Non-stop (`plan_tick`) is the page asking, while it is open and its toggle is on, "should the phone lane be advanced now?". The rule is
the Non-Stop Operating Spec's rule 3: the moment the staged job is closed, `python -m faceless phone next --push` hands out the next.
It never pushes the same job twice, a job whose media is gone is held with the reason instead of failing for ever, and two failed
tries in a row open a breaker for half an hour.
"""

from __future__ import annotations

import json
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

from faceless import config, events, safety
from faceless.config import Paths

EVENT = "CC_ACTION"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,180}$")       # ids are file names and argv values: no slash, no leading dash, no space
HANDLE = re.compile(r"^@?[A-Za-z0-9_.]{1,40}$")
WORKSPACE, PANE = re.compile(r"^w[0-9A-Za-z]{1,8}$"), re.compile(r"^w[0-9A-Za-z]{1,8}:p[0-9A-Za-z]{1,8}$")
DM_STATUSES = ("sent", "replied", "clicked", "bought", "dead")
OUTCOMES = ("sent", "reply", "closed", "rejected")
BREAKER_FAILS, BREAKER_MINUTES = 2, 30
TAIL = 600


class Refused(Exception):
    """The desk will not run this, and the message is the reason shown to the owner."""


def _py(*args: str) -> list[str]:
    return [sys.executable, "-m", "faceless", *args]


def _name(args: dict, key: str) -> str:
    value = str(args.get(key) or "")
    if not NAME.match(value):
        raise Refused(f"{key} is missing or not a plain id")
    return value


def _video_job(args: dict) -> str:
    jid = _name(args, "job")
    if not (Paths.jobs / f"{jid}.json").is_file():
        raise Refused(f"no job {jid} in state/jobs")
    return jid


def _phone_job(args: dict) -> str:
    from faceless import phone
    jid = _name(args, "job")
    if not phone.job_path(jid).is_file():
        raise Refused(f"no phone job {jid} in state/phone/jobs")
    return jid


def _dm_log(args: dict) -> list[str]:
    status = str(args.get("status") or "")
    if status not in DM_STATUSES:
        raise Refused(f"status is one of {', '.join(DM_STATUSES)}")
    argv = _py("dm", "log", _name(args, "draft"), status)
    handle = str(args.get("handle") or "").strip()
    if handle:
        if not HANDLE.match(handle):
            raise Refused("the handle is letters, digits, dots and underscores, with or without the @")
        argv += ["--handle", handle if handle.startswith("@") else "@" + handle]
    return argv


def _outcome(args: dict) -> list[str]:
    event = str(args.get("event") or "")
    if event not in OUTCOMES:
        raise Refused(f"event is one of {', '.join(OUTCOMES)}")
    return _py("outbound", "outcome", _name(args, "slug"), event)


def _focus(args: dict) -> list[str]:
    target = str(args.get("target") or "")
    if WORKSPACE.match(target):
        return ["herdr", "workspace", "focus", target]
    if PANE.match(target):
        return ["herdr", "agent", "focus", target]
    raise Refused("target is a herdr workspace (w2) or an agent pane (w2:p1)")


def _mission_lane(args: dict) -> str:
    mid = str((args or {}).get("mission") or "")
    return "render" if mid.startswith(("daily-", "retry-")) else "phone" if mid.startswith("phone-") else "crew:" + mid[:40]


def lane_of(spec: dict, args: dict | None) -> str:
    return spec["lane"](args or {}) if callable(spec["lane"]) else spec["lane"]


# name -> what it runs. `moves`: it advances the pipeline, so the kill switch refuses it. `lane`: one at a time per lane.
ACTIONS: dict[str, dict] = {
    "phone_next": {"label": "Advance phone", "lane": "phone", "moves": True, "timeout": 900,
                   "argv": lambda a: _py("phone", "next", "--push"), "shows": "python -m faceless phone next --push"},
    "phone_park": {"label": "Park phone jobs with no media", "lane": "phone", "moves": True, "timeout": 900,
                   "argv": lambda a: _py("phone", "park"), "shows": "python -m faceless phone park"},
    "phone_requeue": {"label": "Release held phone job", "lane": "phone", "moves": True, "timeout": 60,
                      "argv": lambda a: _py("phone", "requeue", _phone_job(a)), "shows": "python -m faceless phone requeue <id>"},
    "job_retry": {"label": "Retry job", "lane": "render", "moves": True, "timeout": 3600,
                  "argv": lambda a: _py("retry", _video_job(a)), "shows": "python -m faceless retry <job_id>"},
    "daily": {"label": "Run today's batch", "lane": "render", "moves": True, "timeout": 4 * 3600,
              "argv": lambda a: _py("daily", "--no-publish"), "shows": "python -m faceless daily --no-publish"},
    "dm_draft": {"label": "Draft today's DMs", "lane": "desk", "moves": True, "timeout": 600,
                 "argv": lambda a: _py("dm"), "shows": "python -m faceless dm"},
    "prospect": {"label": "Find people to write to", "lane": "desk", "moves": True, "timeout": 600,
                 "argv": lambda a: _py("prospect"), "shows": "python -m faceless prospect"},
    "outbound_run": {"label": "Hunt for clients", "lane": "desk", "moves": True, "timeout": 2 * 3600,
                     "argv": lambda a: _py("outbound", "run"), "shows": "python -m faceless outbound run"},
    "dm_log": {"label": "Log DM", "lane": "desk", "moves": False, "timeout": 60, "argv": _dm_log,
               "shows": "python -m faceless dm log <id> <status>"},
    "money_brief": {"label": "Write the money brief", "lane": "desk", "moves": False, "timeout": 300,
                    "argv": lambda a: _py("money"), "shows": "python -m faceless money"},
    "outbound_outcome": {"label": "Record outreach outcome", "lane": "desk", "moves": False, "timeout": 60, "argv": _outcome,
                         "shows": "python -m faceless outbound outcome <slug> <event>"},
    "mission": {"label": "Dispatch mission", "lane": lambda a: _mission_lane(a), "moves": True, "timeout": 4 * 3600,
                "argv": lambda a: _py("crew", "dispatch", _name(a, "mission"), str(a.get("by") or "owner") if str(a.get("by") or "owner") in ("owner", "autopilot") else "owner"),
                "shows": "python -m faceless crew dispatch <mission>"},
    "herdr_focus": {"label": "Focus pane", "lane": "herdr", "moves": False, "timeout": 15, "argv": _focus,
                    "shows": "herdr workspace focus <id> | herdr agent focus <pane>"},
}


def catalog() -> list[dict]:
    return [{"name": k, "label": v["label"], "lane": v["lane"] if isinstance(v["lane"], str) else "per mission", "stoppedByPause": v["moves"], "runs": v["shows"]} for k, v in ACTIONS.items()]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _tail(text: str | None) -> str:
    text = config.redact((text or "").strip())
    return text[-TAIL:]


def _clean_args(args: dict) -> dict:
    """What is kept about a click. A handle is a person: it goes to the command, never to the journal."""
    return {k: str(v)[:160] for k, v in (args or {}).items() if k != "handle" and v not in (None, "")}


def summarize(name: str, code: int | None, stdout: str) -> tuple[str, dict]:
    """One line a person can read, and the ids worth keeping, from the command's own output."""
    extra: dict = {}
    if name == "phone_next":
        try:
            doc = json.loads(stdout)
        except ValueError:
            doc = None
        if isinstance(doc, dict) and isinstance(doc.get("job"), dict):
            job = doc["job"]
            extra["job"] = job.get("id")
            files = len(doc.get("on_phone") or [])
            return (f"{job.get('kind')} job {job.get('id')} is on the phone ({files} file(s))" if files
                    else f"{job.get('kind')} job {job.get('id')} is handed out (it has no file to push); on the phone it is the driver's turn"), extra
        if isinstance(doc, dict) and "next" in doc and not doc["next"]:
            blocked = doc.get("blocked") or []
            return ("no phone job can run: " + (f"{blocked[0].get('why')} (and {len(blocked) - 1} more blocked)" if blocked else "the queue is empty")), extra
    if name == "phone_park":
        try:
            doc = json.loads(stdout)
            return f"{doc['count']} job(s) with no media held; next is {doc.get('next') or 'nothing'}", extra
        except (ValueError, KeyError, TypeError):
            pass
    lines = [ln.strip() for ln in (stdout or "").splitlines() if ln.strip()]
    if name == "mission":
        try:
            doc = json.loads(stdout)
            extra["job"] = doc.get("mission")
            return f"{doc.get('agent')}: {doc.get('summary')}"[:200], extra
        except (ValueError, TypeError):
            pass
    if name in ("job_retry", "phone_requeue", "dm_log"):
        try:
            doc = json.loads(stdout)
            if isinstance(doc, dict):
                extra["job"] = doc.get("job") or doc.get("id") or doc.get("draft_id")
                bits = [str(doc[k]) for k in ("job", "id", "draft_id", "status", "why") if doc.get(k)]
                if bits:
                    return " · ".join(bits)[:200], extra
        except ValueError:
            pass
    if lines:
        return lines[-1][:200], extra
    return ("done" if code == 0 else "no output"), extra


def _record(result: dict) -> dict:
    """One journal line per click: small, redacted, and without the command's full output (the journal is committed)."""
    events.emit(EVENT, actor=result.get("actor") or "owner",
                **{k: result.get(k) for k in ("id", "action", "label", "args", "ok", "exit", "refused", "seconds", "summary", "job", "error")
                   if result.get(k) not in (None, "", {})})
    return result


def _beat_agent(spec: dict, args: dict) -> str:
    """Board actions report on the team board under their lane: render, desk, phone, or the mission's crew lane."""
    lane = lane_of(spec, args)
    return "engine-" + lane.split(":", 1)[0]


def _arg_hint(args: dict) -> str:
    v = next((str(args[k]) for k in ("mission", "job", "id", "slug") if args.get(k)), "")
    return f" ({v[:60]})" if v else ""


def _beat(agent: str, status: str, task: str, **kw) -> None:
    try:
        from faceless import team
        team.beat(agent, status, task, **kw)
    except Exception:   # noqa: BLE001 - the team board is a view; an action never fails over it
        pass


def run(name: str, args: dict | None = None, *, actor: str = "owner", runner=subprocess.run, rid: str | None = None) -> dict:
    """Run one allowlisted action to the end and return what happened. Never raises: a refusal or a failure is a result."""
    args = args or {}
    spec = ACTIONS.get(name)
    base = {"id": rid or secrets.token_hex(4), "action": name, "label": (spec or {}).get("label") or name, "args": _clean_args(args),
            "actor": actor, "at": _now(), "state": "done"}

    def refuse(why: str) -> dict:
        return _record({**base, "ok": False, "exit": None, "refused": why, "summary": "refused: " + why, "seconds": 0})
    if spec is None:
        return refuse(f"unknown action {name!r}")
    try:
        argv = spec["argv"](args)
    except Refused as e:
        return refuse(str(e))
    if spec["moves"] and (why := safety.paused()):
        return refuse(f"the studio is paused ({why}); only you resume it: python -m faceless pause --resume")
    agent = _beat_agent(spec, args)
    if spec["moves"]:
        _beat(agent, "running", base["label"] + _arg_hint(args), run=f"action-{base['id']}")
    t0 = time.monotonic()
    try:
        r = runner(argv, cwd=Paths.root, capture_output=True, text=True, timeout=spec["timeout"])
        code, out, err = r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        code, out, err = None, "", f"timed out after {spec['timeout']} s"
    except OSError as e:
        code, out, err = None, "", f"{type(e).__name__}: {e}"
    summary, extra = summarize(name, code, out)
    ok = code == 0
    error = "" if ok else (_tail(err) or _tail(out) or "failed without a message")[-300:]
    if spec["moves"]:
        _beat(agent, "done" if ok else "error", base["label"] + ": " + (summary if ok else (error.splitlines()[-1] if error else summary))[:120],
              run=f"action-{base['id']}")
    return _record({**base, **extra, "ok": ok, "exit": code, "seconds": round(time.monotonic() - t0, 1),
                    "summary": summary if ok else (error.splitlines()[-1][:200] if error else summary),
                    "error": error, "stdout": _tail(out), "stderr": _tail(err)})


def recent(limit: int = 15, window: int = 600_000) -> list[dict]:
    """The newest clicks, from the journal's tail. A projection: nothing is kept anywhere else."""
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
        if EVENT not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == EVENT:
            rows.append({"id": e.get("id"), "action": e.get("action"), "label": e.get("label") or e.get("action"), "args": e.get("args") or {},
                         "actor": e.get("actor"), "at": e.get("ts"), "ok": bool(e.get("ok")), "exit": e.get("exit"), "refused": e.get("refused"),
                         "seconds": e.get("seconds"), "summary": e.get("summary") or "", "job": e.get("job"), "error": e.get("error") or "",
                         "state": "done"})
    return rows[::-1][:limit]


def _age_minutes(iso: str | None) -> float:
    try:
        then = datetime.strptime(str(iso), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return 1e9
    return (datetime.now(timezone.utc) - then).total_seconds() / 60


def plan_tick(history: list[dict] | None = None) -> dict:
    """What Non-stop should do right now, decided from the kill switch, the phone queue and the journal. Reads only.

    state: paused | idle | tripped | waiting | run. Only `run` means "act now": `do` names the action (phone_next unless the head of
    the queue has lost its media, in which case phone_park holds such jobs with the reason so the lane can move).
    """
    from faceless import phone
    if why := safety.paused():
        return {"state": "paused", "text": f"Paused: {why}. Non-stop does nothing until you resume."}
    nxt = phone.next_job()
    if not nxt:
        queued = sum(1 for j in phone.jobs() if j.get("status") == "queued")
        return {"state": "idle", "text": (f"No phone job can run now ({queued} queued, all blocked by a gate or a cap)." if queued else "The phone queue is empty.")}
    pushes = [e for e in (recent(40) if history is None else history) if e.get("action") in ("phone_next", "phone_park") and not e.get("refused")]
    fails = 0
    for e in pushes:
        if e.get("ok"):
            break
        fails += 1
    if fails >= BREAKER_FAILS and _age_minutes(pushes[0].get("at")) < BREAKER_MINUTES:
        return {"state": "tripped", "next": nxt["id"],
                "text": f"Stopped after {fails} failed tries in a row ({pushes[0].get('summary') or 'see Alerts'}). "
                        f"It tries again {BREAKER_MINUTES} minutes after the last failure, or press Advance phone once it is fixed."}
    if gone := phone.media_missing(nxt):
        return {"state": "run", "do": "phone_park", "next": nxt["id"],
                "text": f"{nxt['id']} cannot be pushed ({', '.join(gone)} is gone from the media branch and this disk): holding it, and every job like it, with the reason."}
    last_ok = next((e for e in pushes if e.get("action") == "phone_next" and e.get("ok") and e.get("job")), None)
    if last_ok and last_ok.get("job") == nxt["id"]:
        return {"state": "waiting", "next": nxt["id"],
                "text": f"{nxt['id']} was handed to the phone {int(_age_minutes(last_ok.get('at')))} min ago. "
                        "Waiting for the phone driver to record it with `phone done`; it is not pushed twice."}
    return {"state": "run", "next": nxt["id"], "text": f"Advancing the phone lane: {nxt['id']}"}


class Desk:
    """Runs actions off the request thread, one per lane, and remembers only what is running (in memory)."""

    def __init__(self, run_action=run, plan=plan_tick, on_done=None, wait: float = 1.5):
        self.run_action, self.plan, self.on_done, self.wait = run_action, plan, on_done, wait
        self.running: dict[str, dict] = {}                   # lane -> the record of the action holding it
        self.finished: dict[str, dict] = {}                  # id -> full result (with stdout/stderr), newest 30
        self.lock = threading.Lock()

    def start(self, name: str, args: dict | None = None, *, actor: str = "owner") -> dict:
        """Start an action; answer within `wait` seconds with either its result or a `running` record the page can poll."""
        spec = ACTIONS.get(name)
        if spec is None:
            return self.run_action(name, args, actor=actor)                  # journals the refusal
        lane = lane_of(spec, args)
        with self.lock:
            busy = self.running.get(lane)
            if busy:
                return {"id": None, "action": name, "label": spec["label"], "state": "done", "ok": False, "exit": None, "busy": True,
                        "refused": f"the {lane} lane is busy with {busy['label']} (started {busy['at']})",
                        "summary": f"not started: the {lane} lane is busy with {busy['label']}"}
            rec = {"id": secrets.token_hex(4), "action": name, "label": spec["label"], "args": _clean_args(args or {}), "actor": actor,
                   "at": _now(), "state": "running", "lane": lane}
            self.running[lane] = rec

        def work() -> None:
            try:
                result = self.run_action(name, args, actor=actor, rid=rec["id"])
            except Exception as e:   # noqa: BLE001 - the page must hear about it, whatever it was
                result = {**rec, "state": "done", "ok": False, "exit": None, "summary": f"{type(e).__name__}: {e}"[:200], "error": str(e)[:300]}
            with self.lock:
                self.running.pop(lane, None)
                self.finished[rec["id"]] = result
                for old in list(self.finished)[:-30]:
                    self.finished.pop(old, None)
            if self.on_done:
                try:
                    self.on_done(result)
                except Exception:   # noqa: BLE001, S110 - a cache refresh must never lose the result
                    pass
        t = threading.Thread(target=work, daemon=True, name=f"qm-action-{name}")
        t.start()
        t.join(self.wait)
        with self.lock:
            return dict(self.finished.get(rec["id"]) or rec)

    def tick(self) -> dict:
        """One Non-stop step, asked for by the open page. Starts phone_next only when the plan says so and the lane is free."""
        with self.lock:
            busy = self.running.get("phone")
        if busy:
            return {"state": "busy", "text": f"The phone lane is busy with {busy['label']}."}
        plan = self.plan()
        if plan.get("state") != "run":
            return plan
        return {**plan, "result": self.start(plan.get("do") or "phone_next", {}, actor="non-stop")}

    def auto(self) -> dict:
        """One Autopilot step, asked for by the open page: start the next mission a machine may do, if there is room."""
        from faceless import missions
        plan = missions.plan_auto()
        if plan.get("state") != "run":
            return plan
        return {**plan, "result": self.start("mission", {"mission": plan["mission"], "by": "autopilot"}, actor="autopilot")}

    def snapshot(self, limit: int = 15) -> dict:
        with self.lock:
            running = [dict(r) for r in self.running.values()]
            full = dict(self.finished)
        rows = recent(limit)
        for r in rows:                                       # this server's own runs carry their output; the journal keeps only the summary
            if r.get("id") in full:
                r["stdout"], r["stderr"] = full[r["id"]].get("stdout", ""), full[r["id"]].get("stderr", "")
        return {"generatedAt": _now(), "paused": safety.paused(), "running": running, "recent": rows}
