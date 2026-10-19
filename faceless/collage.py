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
visual: ONE paper-collage scene that SHOWS the idea as a visual metaphor (stacked paper coins growing, a torn calendar, a paper clock splitting). Describe ONE scene only; the paper-collage look is added by code. No faces and no real people. Explanatory motion only. facts: list of {{claim, basis}} using the fact sheet as basis.
"""


def fact_sheet(rates=(4, 6, 8, 10, 12)) -> str:
    """Every number a script may use, all from `moneymath`. Wide on purpose: a fresh topic needs fresh true numbers."""
    from faceless import moneymath as m
    lines = [f"Rule of 72 at {r}% = {m.rule_of_72(r):.1f} years to double" for r in rates]
    lines.append(f"$200 a month at 7% for 30 years grows to {m.money(m.future_value_monthly(200, 0.07, 30))}; the same $200 a month paid in only totals {m.money(200 * 12 * 30)}")
    lines.append(f"$10,000 lump sum at 7% for 30 years grows to {m.money(m.lump_sum_growth(10000, 0.07, 30))}")
    lines.append(f"$100 loses value to 3% inflation: worth {m.money(m.inflation_value(100, 0.03, 20))} in today's money after 20 years")
    n, paid = m.card_payoff(5000, 0.24, 150)
    lines.append(f"A $5,000 card at 24% APR paid at $150 a month takes {n} months and costs {m.money(paid)} in total")
    lines.append(f"To live on $3,000 a month at the 4% rule you need {m.money(m.capital_for_income(3000))} invested")
    lines.append(f"$500 a month at 7% reaches $500,000 in {m.months_to_target(500, 0.07, 500000) / 12:.1f} years")
    lines.append(f"$1,000 a month at 7% reaches $500,000 in {m.months_to_target(1000, 0.07, 500000) / 12:.1f} years")
    return "\n".join(lines)


def covered(limit: int = 150) -> str:
    """Titles already made, so a new video takes a fresh angle instead of repeating one."""
    from faceless.pipeline import ideate
    return "\n".join(f"- {t[:70]}" for t in ideate.history_texts()[-limit:])


def used_numbers() -> str:
    """Figures already said in earlier collage videos: a new video must not lean on the same ones."""
    nums = set()
    for f in Paths.final.glob("_collage-*.json"):
        try:
            nums |= {n.strip(",.") for b in json.loads(f.read_text(encoding="utf-8"))["beats"] for n in re.findall(r"\$?\d[\d,.]{2,}", b["say"])}
        except (OSError, ValueError, KeyError):
            continue
    return ", ".join(sorted(nums))


def write(topic: str = "", angle: str = "", *, out: str | None = None, tries: int = 2) -> dict:
    """One Opus call (a second only if the engine's own script gates reject the first). With no topic, Opus picks one that no earlier video covers."""
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    safety.guard("collage script", 0.15)
    if not ledger.allow("collage", "usd", 0.15, CAP_USD):
        raise ProviderUnavailable(f"collage daily cap ${CAP_USD:.2f} reached")
    pick = topic or "YOU CHOOSE: the most surprising true angle that none of the covered videos below uses, on a topic the fact sheet can support"
    user = (f"Topic: {pick}\nAngle: {angle or 'a fresh angle, never a repeat'}\nALREADY COVERED (do not repeat any title, hook or angle, even reworded):\n{covered()}\n"
            f"FIGURES ALREADY USED IN EARLIER VIDEOS (do not use any of them again): {used_numbers() or 'none'}\n"
            f"FACT SHEET (the only numbers allowed):\n{fact_sheet()}")
    from faceless import gauntlet
    from faceless.pipeline import ideate, script as script_stage
    from faceless.providers.llm import _extract_json
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    spent = 0.0
    for attempt in range(tries):
        body = {"model": MODEL, "messages": msgs, "response_format": {"type": "json_object"},
                "max_tokens": 5000, "usage": {"include": True}, "reasoning": {"effort": "low"}}
        r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=240, headers={"Authorization": f"Bearer {key}"})
        if r.status_code != 200:
            raise ProviderError(f"openrouter {r.status_code}")
        d = r.json()
        cost = float((d.get("usage") or {}).get("cost") or 0)
        spent += cost
        ledger.spend("collage", "usd", cost, usd=cost)
        text = d["choices"][0]["message"]["content"]
        script = _extract_json(text)
        script["source"] = "opus-collage"
        script["look"] = LOOK
        norm = script_stage.normalize(script)
        bad = [f"{g.name}: {g.detail}" for g in gauntlet.check_script(norm, ideate.history_texts()) if not g.passed]
        if not bad:
            break
        msgs += [{"role": "assistant", "content": text[:7000]}, {"role": "user", "content": "The studio's script gates refused it: " + "; ".join(bad)[:900] + ". Return the complete corrected JSON object."}]
    script["_gates_failing"] = bad
    words = sum(len(b["say"].split()) for b in script["beats"])
    allowed = set(re.findall(r"\d[\d,.]*", fact_sheet()))
    stray = sorted({n.strip(",.") for b in script["beats"] for n in re.findall(r"\d[\d,.]*", b["say"] + " " + b.get("callout", ""))} - {a.strip(",.") for a in allowed})
    script["_check"] = {"words": words, "numbers_not_in_fact_sheet": stray, "gates_failing": bad, "usd": round(spent, 4)}
    path = Paths.final / (out or "_collage-" + re.sub(r"[^a-z0-9]+", "-", (topic or script["title"]).lower()).strip("-")[:40] + ".json")
    write_atomic(path, json.dumps(script, indent=1, ensure_ascii=False))
    script["_path"] = str(path)
    return script


def check_frames(job_dir) -> dict:
    """Ask the decision layer (Jev with composable images when TYPESAFE_API_KEY is set, else Clef, else the heuristic) whether each drawn still keeps the paper look
    and is free of text and faces. One picture per question, simple yes or no, because image skill is weaker than text. Writes frames-check.json beside the video."""
    from pathlib import Path

    from faceless import decide
    job_dir = Path(job_dir)
    rows = json.loads((job_dir / "images.json").read_text(encoding="utf-8"))
    out = []
    for r in rows:
        if not r.get("path"):
            continue          # a card, drawn in code
        q = {"paper_look": decide.Q("choice", "Is `still` a torn-paper collage illustration with paper texture and cut-out shapes, not a photograph?", "yes",
                                    options={"yes": "paper collage illustration", "no": "photograph or 3D render"}),
             "clean": decide.Q("choice", "Is `still` free of readable words, letters, numbers and human faces?", "yes",
                               options={"yes": "no text and no face", "no": "text or a face is visible"})}
        d = decide.ask(q, {"task": "check one still of a video frame", "still": "the attached picture"}, job=job_dir.name, images={"still": r["path"]})
        out.append({"beat": r["beat"], "paper_look": d["paper_look"].value, "clean": d["clean"].value, "backend": d["paper_look"].backend,
                    "jev_said": [d["paper_look"].jev_value, d["clean"].jev_value]})
    rep = {"frames": len(out), "not_paper": [o["beat"] for o in out if o["paper_look"] == "no"], "dirty": [o["beat"] for o in out if o["clean"] == "no"], "rows": out}
    write_atomic(job_dir / "frames-check.json", json.dumps(rep, indent=1))
    return rep
