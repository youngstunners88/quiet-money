"""Decision layer: "the LLM creates the work, Jev decides what happens next, code executes."

Every routing / scoring / approval question goes through `ask()` with a code-computed
fallback. Backends:
  heuristic  - the fallback itself (always available, free, deterministic)
  jev        - TypeSafe's System One model (needs TYPESAFE_API_KEY + `pip install typesafe-sdk`)
  clef       - Cloudflare's open (Apache 2.0) decision model hosted on Workers AI: no new account, uses the Cloudflare key we already
               have (auto-selected when no Jev/Laya is configured; counts against the free neuron budget)
  laya       - open-source (Apache 2.0) Jev-compatible engine you host yourself (needs LAYA_URL, optional
               LAYA_API_KEY); same choice/score/noul questions over POST /v1/systemone

Rules borrowed from keel: the host validates every choice; an invalid, low-confidence,
or failed answer falls back to the ordinary (heuristic) route. In dry_run the Jev answer
is logged next to the heuristic one but never acted on, so you can compare a day of
decisions before switching it on (studio.toml [decide].dry_run = false).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass

from faceless import config, events
from faceless.config import Paths

RECORDS = Paths.state / "decisions.jsonl"


@dataclass
class Q:
    """A typed question. kind: choice | score | noul."""
    kind: str
    instructions: str
    fallback: object                      # code's answer: option key / score float / probability
    options: dict | None = None           # choice: {key: description}
    levels: list | None = None            # score: ordered descriptions, index = score


@dataclass
class Decision:
    name: str
    value: object
    confidence: float
    backend: str
    jev_value: object = None
    jev_confidence: float | None = None


def _backend() -> str:
    cfg = config.load()["decide"]
    b = cfg.get("backend", "auto")
    if b == "auto":
        if config.env("LAYA_URL"):
            return "laya"
        if config.env("TYPESAFE_API_KEY"):
            return "jev"
        from faceless.providers import clef
        return "clef" if clef.available() else "heuristic"
    return b


def _ask_clef(questions: dict[str, Q], state: dict) -> dict:
    """Cloudflare Clef (open weights, Jev-API compatible) on Workers AI. Counts against the free neuron budget; skipped when it is spent."""
    from faceless.providers import clef
    qs = {}
    for name, q in questions.items():
        if q.kind == "choice":
            qs[name] = {"type": "choice", "instructions": q.instructions, "criteria": dict(q.options)}
        elif q.kind == "score":
            qs[name] = {"type": "score", "instructions": q.instructions, "criteria": list(q.levels)}
        else:
            qs[name] = {"type": "noul", "instructions": q.instructions}
    out = {}
    for name, a in clef.run(json.dumps(state, default=str), qs).items():
        if "choice" in a:
            out[name] = (a["choice"], a.get("confidence", 0.0))
        elif "score" in a:
            out[name] = (a["score"], a.get("confidence", 0.0))
        elif "noul" in a:
            out[name] = (a["noul"], abs(a["noul"] - 0.5) * 2)
    return out


def _ask_laya(questions: dict[str, Q], state: dict) -> dict:
    """Same questions over HTTP to a self-hosted Laya server. Returns {name: (value, confidence)}."""
    import random

    from faceless.providers import http
    url = config.env("LAYA_URL").rstrip("/") + "/v1/systemone"
    qs = {}
    for name, q in questions.items():
        if q.kind == "choice":
            keys = list(q.options)
            random.Random(name).shuffle(keys)    # Laya shows position bias: don't always put our favourite first
            qs[name] = {"type": "choice", "instructions": q.instructions, "criteria": {k: q.options[k] for k in keys}}
        elif q.kind == "score":
            qs[name] = {"type": "score", "instructions": q.instructions, "criteria": q.levels}
        else:
            qs[name] = {"type": "noul", "instructions": q.instructions}
    headers = {"Authorization": f"Bearer {config.env('LAYA_API_KEY')}"} if config.env("LAYA_API_KEY") else {}
    r = http().post(url, json={"state": state, "questions": qs}, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"laya {r.status_code}")
    body = r.json()
    out = {}
    for name, a in body.get("answers", {}).items():
        if "choice" in a:
            out[name] = (a["choice"], a.get("answer_confidence", a.get("confidence", 0.0)))
        elif "score" in a:
            out[name] = (a["score"], a.get("answer_confidence", a.get("confidence", 0.0)))
        elif "noul" in a:
            out[name] = (a["noul"], abs(a["noul"] - 0.5) * 2)
    events.emit("LAYA_CALL", questions=list(questions), input_tokens=(body.get("usage") or {}).get("input_tokens"))
    return out


def _spec(questions: dict[str, Q]) -> dict:
    """Our typed questions in the Decisions API's shape: choice (criteria = option: description), noul (yes or no), score (criteria = ordered levels)."""
    out = {}
    for name, q in questions.items():
        if q.kind == "choice":
            out[name] = {"type": "choice", "instructions": q.instructions, "criteria": dict(q.options)}
        elif q.kind == "score":
            out[name] = {"type": "score", "instructions": q.instructions, "criteria": list(q.levels)}
        else:
            out[name] = {"type": "noul", "instructions": q.instructions}
    return out


def openrouter_decide(model: str, state, questions: dict[str, Q], *, cap_provider: str = "openrouter-decisions") -> dict:
    """One call to OpenRouter's Decisions API (POST /api/alpha/decisions), for any decision model in its catalog (Microsoft-Decision-1, typesafe/jev-1.13, ...):
    {"answers": {name: raw answer with probabilities}, "model": the exact build, "usd": cost}. A decision model reads the state and returns a calibrated probability
    for each option instead of text. Capped by [decide] decisions_daily_usd, the studio ceiling and state/PAUSE; the key is read from the environment only.
    Docs: https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request"""
    from faceless import ledger, safety
    from faceless.providers import http
    cfg = config.load()["decide"]
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    safety.guard("openrouter-decisions", 0.001)
    if not ledger.allow_usd(cap_provider, 0.001, cfg.get("decisions_daily_usd", 0.05)):
        raise RuntimeError("openrouter decisions daily cap reached")
    r = http().post("https://openrouter.ai/api/alpha/decisions", timeout=60, headers={"Authorization": f"Bearer {key}"},
                    json={"model": model, "state": state, "questions": _spec(questions) if questions and isinstance(next(iter(questions.values())), Q) else questions})
    if r.status_code != 200:
        raise RuntimeError(f"openrouter decisions {r.status_code}")
    d = r.json()
    cost = float((d.get("usage") or {}).get("cost") or 0.0)
    ledger.spend_usd(cap_provider, cost)
    return {"answers": d.get("answers") or {}, "model": d.get("model", model), "usd": cost}


def _ask_openrouter_decisions(questions: dict[str, Q], state: dict) -> dict:
    """Backend `openrouter-decisions` (alias `jev-openrouter`): Jev, or whichever decision model `[decide] decisions_model` pins, through OpenRouter with only OPENROUTER_API_KEY.
    Returns {name: (value, confidence)}; the confidence is the model's own probability for the answer it picked. Opt in with `backend = "openrouter-decisions"` (auto never picks it)."""
    cfg = config.load()["decide"]
    res = openrouter_decide(cfg.get("decisions_model", "typesafe/jev-1.13"), state, questions)
    out = {}
    for name, a in res["answers"].items():
        q = questions.get(name)
        if q is None or not isinstance(a, dict) or a.get("type") != ("noul" if q.kind == "noul" else q.kind):
            continue                                         # an answer to a question we did not ask, or of the wrong type, is ignored
        try:
            if q.kind == "noul":
                out[name] = (float(a["noul"]), abs(float(a["noul"]) - 0.5) * 2)
            elif q.kind == "score":
                out[name] = (float(a["score"]), float(a.get("confidence", 0.0)))
            else:
                probs = a.get("probabilities") or {}
                out[name] = (a["choice"], float(probs.get(a["choice"], a.get("confidence", 0.0))))
        except (KeyError, TypeError, ValueError):
            continue
    events.emit("JEV_CALL", questions=list(questions), via="openrouter-decisions", model=res["model"])
    return out


def _ask_jev(questions: dict[str, Q], state: dict) -> dict:
    from typesafe_sdk import Choice, Noul, Score, TypeSafeClient  # optional dependency

    cfg = config.load()["decide"]
    qs = {}
    for name, q in questions.items():
        if q.kind == "choice":
            qs[name] = Choice(instructions=q.instructions, criteria=q.options)
        elif q.kind == "score":
            qs[name] = Score(instructions=q.instructions, criteria=q.levels)
        else:
            qs[name] = Noul(instructions=q.instructions)
    with TypeSafeClient(model=cfg.get("jev_model", "jev-latest")) as client:
        res = client.system_one(state=state, questions=qs)
    out = {}
    for name, a in res.answers.items():
        if a.type == "choice":
            out[name] = (a.choice, a.confidence)
        elif a.type == "score":
            out[name] = (a.score, a.confidence)
        else:
            out[name] = (a.noul, abs(a.noul - 0.5) * 2)
    tokens = getattr(res.usage, "input_tokens", None)
    events.emit("JEV_CALL", questions=list(questions), input_tokens=tokens)
    return out


def ask(questions: dict[str, Q], state: dict, job: str | None = None, backend: str | None = None) -> dict[str, Decision]:
    """Ask all questions that share this moment in one call; return validated decisions. `backend` overrides studio.toml for one call (the planner review uses it)."""
    cfg = config.load()["decide"]
    backend = backend or _backend()
    floor = cfg.get("confidence_floor", 0.85)
    decisions = {n: Decision(n, q.fallback, 1.0, "heuristic") for n, q in questions.items()}
    if backend == "jev-openrouter":
        backend = "openrouter-decisions"
    if backend in ("jev", "laya", "clef", "openrouter-decisions"):
        t0 = time.time()
        try:
            answers = {"laya": _ask_laya, "jev": _ask_jev, "clef": _ask_clef, "openrouter-decisions": _ask_openrouter_decisions}[backend](questions, state)
        except Exception as e:  # noqa: BLE001 - on any Jev error keep the ordinary route
            events.emit("JEV_ERROR", job=job, backend=backend, error=str(e)[:300])
            answers = {}
        ms = int((time.time() - t0) * 1000)
        for n, (val, conf) in answers.items():
            if n not in decisions:      # the host validates: an answer to a question we never asked is ignored
                continue
            d, q = decisions[n], questions[n]
            d.jev_value, d.jev_confidence = val, conf
            valid = q.kind != "choice" or val in (q.options or {})
            if valid and conf >= floor and not cfg.get("dry_run", True):
                d.value, d.confidence, d.backend = val, conf, "jev"
        events.emit("DECISIONS", job=job, backend=backend, ms=ms, dry_run=cfg.get("dry_run", True))
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECORDS, "a", encoding="utf-8") as f:
        for d in decisions.values():
            f.write(json.dumps({"ts": events.now_iso(), "job": job, **asdict(d),
                                "state_keys": sorted(state)}, default=str) + "\n")
    return decisions
