"""Decision layer: "the LLM creates the work, Jev decides what happens next, code executes."

Every routing / scoring / approval question goes through `ask()` with a code-computed
fallback. Backends:
  heuristic  - the fallback itself (always available, free, deterministic)
  jev        - TypeSafe's System One model (needs TYPESAFE_API_KEY + `pip install typesafe-sdk`)

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
        return "jev" if config.env("TYPESAFE_API_KEY") else "heuristic"
    return b


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


def ask(questions: dict[str, Q], state: dict, job: str | None = None) -> dict[str, Decision]:
    """Ask all questions that share this moment in one call; return validated decisions."""
    cfg = config.load()["decide"]
    backend = _backend()
    floor = cfg.get("confidence_floor", 0.85)
    decisions = {n: Decision(n, q.fallback, 1.0, "heuristic") for n, q in questions.items()}
    if backend == "jev":
        t0 = time.time()
        try:
            answers = _ask_jev(questions, state)
        except Exception as e:  # noqa: BLE001 - on any Jev error keep the ordinary route
            events.emit("JEV_ERROR", job=job, error=str(e)[:300])
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
