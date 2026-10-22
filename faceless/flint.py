"""Flint: free extra hands for work that is NOT on the daily critical path.

Recursive's Flint (OpenRouter `recursive/flint-v1.0:free`, open weights, 262K context, released 2026-10-21) costs nothing and is built for coding
agents, but OpenRouter shows ~20% tool-call and ~50% structured-output errors and the free pool is shared and rate-limited. So it is capacity for
side work (topic and seed expansion, Brain note drafts, intake dossiers, code and skill exploration), never for the 5-video path.

    from faceless import flint
    flint.ask(prompt, task="seeds", want_json=True)       # the answer, or ProviderError (nothing falls back unless fallback=True)
    python -m faceless flint status                       # success rates measured on the jobs we gave it
    python -m faceless flint seeds -n 12 --pillar escape  # high-novelty backlog seeds, filtered for distinct meaning

Hard rules (a test enforces the first two):
1. Flint is not in `[llm].chain` or `[llm].openrouter_models`, and no pipeline, gauntlet, script, offer or publish code imports this module.
2. Only `:free` model ids are accepted: a paid id is refused here, so this module can never spend.
3. Every call is logged to state/flint.jsonl (task, ok, json_ok, latency, tokens) so promotion can be decided on measured rates, not on a listing page.
4. Output is data to be checked; it never reaches a script, an offer, a post or a price without the normal gates.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from faceless import config, ledger, safety
from faceless.config import Paths
from faceless.fsutil import read_jsonl
from faceless.providers import ProviderError, ProviderUnavailable, http
from faceless.providers.llm import _extract_json

LOG = Paths.state / "flint.jsonl"
URL = "https://openrouter.ai/api/v1/chat/completions"


def cfg() -> dict:
    return {"enabled": True, "model": "recursive/flint-v1.0:free", "daily_calls": 60, "retries": 3, "backoff_s": 8, "timeout_s": 240,
            **config.load().get("flint", {})}


def model() -> str:
    m = str(cfg()["model"])
    if not m.endswith(":free"):
        raise ProviderError(f"flint model {m!r} is not a :free id: this module only ever uses free models")
    return m


def _log(row: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": cfg()["model"], **row}) + "\n")


def ask(prompt: str, *, task: str, system: str | None = None, want_json: bool = False, temperature: float = 0.9, fallback: bool = False):
    """One request to Flint. Retries a rate limit (429) with a pause; one extra try if JSON was wanted and not returned. With fallback=True a final
    failure is answered by the normal chain instead (only for side work that can use it); otherwise it raises and the caller carries on without Flint."""
    c = cfg()
    if not c["enabled"]:
        raise ProviderUnavailable("flint is switched off ([flint] enabled = false)")
    safety.guard("flint")                                              # a pause stops this too
    if ledger.used("flint", "calls") >= int(c["daily_calls"]):
        raise ProviderUnavailable(f"flint: daily call allowance ({c['daily_calls']}) used")
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": model(), "messages": msgs, "temperature": temperature, "usage": {"include": True}}
    if want_json:
        body["response_format"] = {"type": "json_object"}
    err, t0, json_ok = "", time.time(), None
    for attempt in range(int(c["retries"])):
        try:
            r = http().post(URL, json=body, timeout=int(c["timeout_s"]), headers={"Authorization": f"Bearer {key}"})
        except Exception as e:                                         # noqa: BLE001 - network trouble is a measured failure, not a crash
            err = type(e).__name__
            time.sleep(int(c["backoff_s"]))
            continue
        if r.status_code == 429:
            err = "429"
            time.sleep(int(c["backoff_s"]) * (attempt + 1))
            continue
        if r.status_code != 200:
            err = str(r.status_code)
            break
        d = r.json()
        ledger.spend("flint", "calls", 1)
        usage = d.get("usage") or {}
        try:
            text = d["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError):
            err = "empty"
            continue
        if want_json:
            try:
                out = _extract_json(text)
                json_ok = True
            except ProviderError:
                err, json_ok = "bad-json", False
                continue
        else:
            out = text.strip()
        _log({"task": task, "ok": True, "json_ok": json_ok, "attempts": attempt + 1, "ms": int((time.time() - t0) * 1000), "tokens": usage.get("total_tokens", 0)})
        return out
    _log({"task": task, "ok": False, "json_ok": json_ok, "error": err, "attempts": int(c["retries"]), "ms": int((time.time() - t0) * 1000)})
    if fallback:
        from faceless.providers import llm
        return llm.complete(prompt, system=system, want_json=want_json, temperature=temperature)
    raise ProviderError(f"flint: {err or 'failed'}")


def status() -> dict:
    """Measured success on the jobs we gave Flint: the evidence for or against ever giving it more."""
    rows = list(read_jsonl(LOG)) if LOG.exists() else []
    by: dict[str, dict] = {}
    for r in rows:
        t = by.setdefault(r.get("task", "?"), {"calls": 0, "ok": 0, "json_wanted": 0, "json_ok": 0, "errors": {}})
        t["calls"] += 1
        t["ok"] += bool(r.get("ok"))
        if r.get("json_ok") is not None:
            t["json_wanted"] += 1
            t["json_ok"] += bool(r.get("json_ok"))
        if not r.get("ok"):
            t["errors"][r.get("error", "?")] = t["errors"].get(r.get("error", "?"), 0) + 1
    n = len(rows)
    return {"calls": n, "ok_rate": round(sum(bool(r.get("ok")) for r in rows) / n, 3) if n else None, "model": cfg()["model"],
            "used_today": ledger.used("flint", "calls"), "daily_calls": cfg()["daily_calls"], "by_task": by,
            "promotion": "none: Flint stays off the critical path until 50+ measured calls on a task reach 95% success and the owner says so"}


# ------------------------------------------------------------------ extra hands: backlog seeds

SEED_PROMPT = """You help a faceless money-education channel (YouTube Shorts, calm, honest, 18-40 year olds who feel behind with money) avoid repeating itself.
Write {n} NEW topic seeds for the pillar "{pillar}" ({what}). They must be about different ideas from each other and from these recent titles:
{recent}
Source material you may build on (our own research briefs, paraphrase only, never quote, never name a person in the hook):
{briefs}
Style: concrete beats abstract. Our abstract titles ("The X Effect", "The Y Lens", "The Z Paradox") get the fewest views; a specific situation, object or number-free claim gets the most ("Why your gym membership is the cheapest lesson in sunk cost"). The hook names a real, ordinary moment (a Tuesday, a payslip, a text from a landlord), not a concept.
Rules: education only, never advice; no promised returns or income; no invented statistics or named real people; if a number is needed leave it out
(a code library computes numbers later). Each seed has: topic (a title, 4-12 words), angle (one sentence: the idea and its honest catch), hook (one spoken
opening line that is true and specific).
Return JSON only: {{"seeds": [{{"topic": "...", "angle": "...", "hook": "..."}}]}}"""

PILLARS = {"escape": "business-ownership and asset-building frameworks, with their catches", "psychology": "money behaviour and biases",
           "playbook": "do-this-today money tasks", "myth": "common money myths, corrected", "story": "documented true money stories"}


def seeds(n: int = 12, pillar: str = "escape", dry_run: bool = False) -> dict:
    """Ask Flint for seeds, keep only those distinct in meaning (and phrase-clean), append them to the backlog. Returns counts and the kept rows."""
    from faceless import embed, offer
    from faceless.pipeline import ideate
    recent = ideate.recent_scripts(60)
    briefs = ""
    for name in ("pena", "kiyosaki", "hormozi"):
        p = Paths.root / "channel" / "research" / f"{name}.md"
        if p.exists():
            briefs += f"\n[{name}]\n" + "\n".join(x for x in p.read_text(encoding="utf-8").splitlines() if x.startswith("- "))[:2500]
    prompt = SEED_PROMPT.format(n=n, pillar=pillar, what=PILLARS.get(pillar, pillar), recent="\n".join("- " + t.split(". ")[0] for t in recent[-40:]),
                                briefs=briefs if pillar == "escape" else "(none for this pillar)")
    if embed.embed(["probe"]) is None:                               # without embeddings the meaning check cannot run: write nothing
        raise ProviderUnavailable("no embedding provider: seeds cannot be checked for repetition, so none are written")
    res = ask(prompt, task="seeds", want_json=True)
    raw = res.get("seeds", res) if isinstance(res, dict) else res
    items = [{"pillar": pillar, "topic": str(s.get("topic", "")).strip(), "angle": str(s.get("angle", "")).strip(), "hook": str(s.get("hook", "")).strip(),
              "source": f"flint-{config.today_utc().isoformat()}"} for s in raw if isinstance(s, dict) and s.get("topic") and s.get("hook")]
    clean = [i for i in items if not offer.violations(ideate._item_text(i))]
    kept: list[dict] = []
    limit = float(config.load()["gauntlet"].get("topic_dup", 0.5))
    existing = [ideate._item_text(i) for i in ideate.load_backlog()]
    for it in clean:                                                   # one at a time: each kept seed joins the "already covered" set for the next
        pick = ideate.first_distinct([it], recent + existing + [ideate._item_text(k) for k in kept], limit)
        if pick is not None:
            kept.append(it)
    if kept and not dry_run:
        ideate.append_backlog(kept)
    return {"asked": n, "returned": len(items), "phrase_clean": len(clean), "kept": len(kept), "rows": kept, "written": bool(kept and not dry_run)}
