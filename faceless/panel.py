"""A model panel: put one decision brief to several models through OpenRouter, several runs each, and tally the answers.

    python -m faceless panel brief.txt --models microsoft/phi-4,anthropic/claude-haiku-5.5 --runs 3

The brief must tell the models to answer with JSON containing a "choice". The panel does not decide anything: it shows where the models agree, how sure they are, and
what each one noticed, so a person (or an agent the owner has given the decision to) can adjudicate. Agreement is not correctness: a model that votes the same way three
times can be repeating a generic answer, so read the reasons, and check each against the facts in the brief. Results are saved to state/panels/ with the raw answers.
Spend: [panel] caps (daily_usd, per_call_usd, max_runs), the ledger, the studio ceiling and state/PAUSE. Keys are read from the environment only.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter

from faceless import config, ledger, safety
from faceless.config import Paths
from faceless.fsutil import write_atomic
from faceless.providers import ProviderUnavailable, http

PROVIDER = "openrouter-panel"


def settings() -> dict:
    return {"daily_usd": 0.10, "per_call_usd": 0.01, "max_runs": 5, "temperature": 0.4, "max_tokens": 2000, **config.load().get("panel", {})}


def ask(model: str, brief: str, max_tokens: int | None = None) -> dict:
    """One answer: {out (parsed JSON or {"error": ...}), usd, model_used}. `max_tokens` raises the answer budget for one call: a reasoning
    model given a long brief and a small budget spends it all on reasoning and returns empty text (seen on the service desk's research
    briefs, 2026-10-22), which reads as an unreadable answer."""
    s, key = settings(), config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    safety.guard("panel", s["per_call_usd"])
    if not ledger.allow_usd(PROVIDER, s["per_call_usd"], s["daily_usd"]):
        raise ProviderUnavailable(f"panel daily cap ${s['daily_usd']} reached")
    body = {"model": model, "max_tokens": max_tokens or s["max_tokens"], "temperature": s["temperature"], "reasoning": {"effort": "low"},      # a reasoning model with a small budget returns empty text
            "messages": [{"role": "user", "content": brief}]}
    r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=120, headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        return {"out": {"error": f"http {r.status_code}"}, "usd": 0.0, "model_used": model}
    d = r.json()
    cost = float((d.get("usage") or {}).get("cost") or 0.0)
    ledger.spend_usd(PROVIDER, cost)
    from faceless.providers.llm import _extract_json
    try:
        out = _extract_json(d["choices"][0]["message"].get("content") or "")
        out = out if isinstance(out, dict) else {"error": "not a JSON object"}
    except Exception as e:  # noqa: BLE001 - an unreadable answer is a failed run, counted as such
        out = {"error": f"unreadable: {type(e).__name__}"}
    return {"out": out, "usd": cost, "model_used": d.get("model", model)}


def run(brief: str, models: list[str], runs: int = 3, label: str = "panel") -> dict:
    runs = max(1, min(runs, settings()["max_runs"]))
    result = {"label": label, "runs": runs, "models": {}}
    for m in models:
        rows = []
        for _ in range(runs):
            try:
                rows.append(ask(m, brief))
            except ProviderUnavailable as e:
                rows.append({"out": {"error": str(e)[:100]}, "usd": 0.0, "model_used": m})
        votes = [str(r["out"].get("choice")) for r in rows if "choice" in r["out"]]
        confs = [float(r["out"]["confidence"]) for r in rows if isinstance(r["out"].get("confidence"), (int, float))]
        result["models"][m] = {"votes": dict(Counter(votes)), "failed": sum(1 for r in rows if "choice" not in r["out"]),
                               "mean_confidence": round(sum(confs) / len(confs), 2) if confs else None, "usd": round(sum(r["usd"] for r in rows), 5), "answers": rows}
    tally = Counter()
    for m in result["models"].values():
        tally.update(m["votes"])
    result["tally"] = dict(tally)
    return result


def save(result: dict) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", result["label"].lower()).strip("-")[:40] or "panel"
    path = Paths.state / "panels" / f"{time.strftime('%Y-%m-%d', time.gmtime())}-{slug}.json"
    write_atomic(path, json.dumps(result, indent=1, default=str) + "\n")
    return str(path.relative_to(Paths.root))


def run_decisions(state, questions: dict, models: list[str], label: str = "decisions") -> dict:
    """The same typed questions (the Decisions API's own shape: choice, noul, score) put to several decision models, with the probability each gives every option.
    Decision models return calibrated probabilities instead of text, so the spread between models is visible directly. Result: {model: {question: answer or error}}."""
    from faceless import decide
    out = {"label": label, "models": {}}
    for m in models:
        try:
            r = decide.openrouter_decide(m, state, questions, cap_provider=PROVIDER)
            out["models"][m] = {"answers": r["answers"], "build": r["model"], "usd": round(r["usd"], 6)}
        except Exception as e:  # noqa: BLE001 - a model that fails is reported, the others still answer
            out["models"][m] = {"error": str(e)[:120]}
    return out
