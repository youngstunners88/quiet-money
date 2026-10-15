"""Paper-collage explainer: Claude Opus 5.5 (OpenRouter) writes one whole video; the free pipeline renders it.

Method taken from the Vox Explainer Method study (holy-templar/vox-animated-ad-mcp, AGPL, so ideas only, no code or text copied): a researched cold open,
one idea per line, a curiosity gap that escalates, an insight at the end, one keyword on screen per beat, one locked look in every shot (torn paper,
hand-cut cutouts, warm off-white ground, one or two accents), and motion that explains rather than decorates. The paid generation service it drives is not used.
Numbers come only from `moneymath`, so rule 1 (every number is true) holds. Output is a script JSON for `python -m faceless make --script`.
Skill: .claude/skills/faceless-paper-collage.
"""

from __future__ import annotations

import json
import re

from faceless import config, ledger, safety
from faceless.config import Paths
from faceless.fsutil import write_atomic
from faceless.providers import ProviderError, ProviderUnavailable, http

MODEL = "anthropic/claude-opus-5.5"          # $4 in, $20 out per million tokens on OpenRouter; one script is about 3000 tokens, so about $0.07
CAP_USD = 0.50
LOOK = ("torn-paper collage, hand-cut paper cutouts with drop shadows, visible paper fibre and torn white edges, warm off-white background, "
        "black ink, one burnt-orange accent and one teal accent, flat editorial illustration, no photorealism, no text, no letters, no faces")

SYSTEM = f"""You write one 61-72 second vertical explainer for Quiet Money (money psychology for 18-40 year olds who feel behind), in the Vox paper-collage style.
Return ONLY a JSON object with keys: title, hook_text (max 6 words, caps), beats (12 to 14 objects: say, callout, visual), caption, description, hashtags (5), first_comment, facts.
Script: 175-200 spoken words in total, short comma-separated clauses, one idea per beat, about 14 words per beat. Open cold on the strangest concrete detail, create a curiosity gap,
escalate every beat, end on one insight the viewer can use today. Education only: no buy or invest calls, no promised returns, no income claims.
Every number you say must appear in the FACT SHEET; never invent a number, date, person or study. callout: one keyword or 1-3 words in caps, or empty; never a full sentence.
visual: ONE paper-collage scene that SHOWS the idea as a visual metaphor (stacked paper coins growing, a torn calendar, a paper clock splitting). Start each visual with
"{LOOK}:" then the scene. No faces and no real people. Explanatory motion only. facts: list of {{claim, basis}} using the fact sheet as basis.
"""


def fact_sheet(rates=(4, 6, 8, 10, 12)) -> str:
    from faceless import moneymath as m
    lines = [f"Rule of 72 at {r}% = {m.rule_of_72(r):.1f} years to double" for r in rates]
    lines.append(f"$200 a month at 7% for 30 years grows to {m.money(m.future_value_monthly(200, 0.07, 30))}; the same $200 a month paid in only totals {m.money(200 * 12 * 30)}")
    lines.append(f"$10,000 lump sum at 7% for 30 years grows to {m.money(m.lump_sum_growth(10000, 0.07, 30))}")
    lines.append(f"$100 loses value to 3% inflation: worth {m.money(m.inflation_value(100, 0.03, 20))} in today's money after 20 years")
    return "\n".join(lines)


def write(topic: str, angle: str = "", *, out: str | None = None) -> dict:
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    safety.guard("collage script", 0.15)
    if not ledger.allow("collage", "usd", 0.15, CAP_USD):
        raise ProviderUnavailable(f"collage daily cap ${CAP_USD:.2f} reached")
    user = f"Topic: {topic}\nAngle: {angle or 'find the most surprising true angle'}\nFACT SHEET (the only numbers allowed):\n{fact_sheet()}"
    body = {"model": MODEL, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], "response_format": {"type": "json_object"},
            "max_tokens": 5000, "usage": {"include": True}, "reasoning": {"effort": "low"}}
    r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=240, headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        raise ProviderError(f"openrouter {r.status_code}")
    d = r.json()
    spent = float((d.get("usage") or {}).get("cost") or 0)
    ledger.spend("collage", "usd", spent, usd=spent)
    from faceless.providers.llm import _extract_json
    script = _extract_json(d["choices"][0]["message"]["content"])
    script["source"] = "opus-collage"
    words = sum(len(b["say"].split()) for b in script["beats"])
    allowed = set(re.findall(r"\d[\d,.]*", fact_sheet()))
    stray = sorted({n.strip(",.") for b in script["beats"] for n in re.findall(r"\d[\d,.]*", b["say"] + " " + b.get("callout", ""))} - {a.strip(",.") for a in allowed})
    script["_check"] = {"words": words, "numbers_not_in_fact_sheet": stray, "usd": round(spent, 4)}
    path = Paths.final / (out or "_collage-" + re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40] + ".json")
    write_atomic(path, json.dumps(script, indent=1, ensure_ascii=False))
    script["_path"] = str(path)
    return script
