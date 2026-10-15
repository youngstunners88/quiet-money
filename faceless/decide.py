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


IMG_MIN, IMG_MAX, IMG_PIXELS = 256, 1568, (78_400, 2_458_624)       # TypeSafe image limits (docs.typesafe.ai/images): never resized for you
IMAGES_HEADER = {"TypeSafe-Danger-Zone-Images": "true"}              # images and box questions are off by default, per request


def prepare_image(path) -> bytes:
    """PNG bytes of a picture that fits Jev's limits: longest side at most 1568, shortest at least 256, pixels in range."""
    import io

    from PIL import Image
    im = Image.open(path).convert("RGB")
    sc = min(1.0, IMG_MAX / max(im.size))
    if min(im.size) * sc < IMG_MIN:
        sc = IMG_MIN / min(im.size)
    im = im.resize((max(IMG_MIN, round(im.width * sc)), max(IMG_MIN, round(im.height * sc))))
    while im.width * im.height > IMG_PIXELS[1]:
        im = im.resize((round(im.width * 0.9), round(im.height * 0.9)))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


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


def _ask_clef(questions: dict[str, Q], state: dict, images: dict | None = None) -> dict:
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
    for name, a in clef.run(json.dumps(state, default=str), qs, images=list((images or {}).values()) or None).items():
        if "choice" in a:
            out[name] = (a["choice"], a.get("confidence", 0.0))
        elif "score" in a:
            out[name] = (a["score"], a.get("confidence", 0.0))
        elif "noul" in a:
            out[name] = (a["noul"], abs(a["noul"] - 0.5) * 2)
    return out


def _ask_laya(questions: dict[str, Q], state: dict, images: dict | None = None) -> dict:
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
    body = {"state": state, "questions": qs}
    if images:       # composable images: each is listed once in `assets`, and the state names it by reference
        import base64
        body["assets"] = {f"img-{n}": {"type": "image", "format": "png", "data_base64": base64.b64encode(prepare_image(p)).decode()} for n, p in images.items()}
        body["state"] = {**state, **{n: f"img-{n}" for n in images}}
        headers = {**headers, **IMAGES_HEADER}
    r = http().post(url, json=body, headers=headers, timeout=60)
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


def _png_path(path):
    """A resized copy in the scratch cache (the SDK takes a file path); never overwrites the original."""
    from pathlib import Path
    out = Paths.cache / "decide-images" / (Path(path).stem + ".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(prepare_image(path))
    return out


def _ask_jev(questions: dict[str, Q], state: dict, images: dict | None = None) -> dict:
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
    kw = {}
    if images:       # the SDK uploads each Image and writes the reference itself; the header turns the feature on
        from typesafe_sdk import Image
        state = {**state, **{n: Image(_png_path(p)) for n, p in images.items()}}
        kw["extra_headers"] = IMAGES_HEADER
    with TypeSafeClient(model=cfg.get("jev_model", "jev-latest")) as client:
        res = client.system_one(state=state, questions=qs, **kw)
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


def ask(questions: dict[str, Q], state: dict, job: str | None = None, images: dict | None = None) -> dict[str, Decision]:
    """Ask all questions that share this moment in one call; return validated decisions.
    `images` ({name: file path}) puts pictures in the state for the model to look at; the state text names them. Jev 1.14 multimodal is weaker than its text
    skill, so ask simple yes/no or choice questions about one picture each."""
    cfg = config.load()["decide"]
    backend = _backend()
    floor = cfg.get("confidence_floor", 0.85)
    decisions = {n: Decision(n, q.fallback, 1.0, "heuristic") for n, q in questions.items()}
    if backend in ("jev", "laya", "clef"):
        t0 = time.time()
        try:
            answers = {"laya": _ask_laya, "jev": _ask_jev, "clef": _ask_clef}[backend](questions, state, images)
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
