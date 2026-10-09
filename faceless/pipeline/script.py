"""Script stage: hand-written final scripts win; otherwise the LLM drafts from the five-part prompt."""

from __future__ import annotations

import json
import re

from faceless import config, events
from faceless.config import Paths
from faceless.prompts import script_prompt
from faceless.providers import llm
from faceless.fsutil import write_atomic


def narration(script: dict) -> str:
    return " ".join(b["say"].strip() for b in script["beats"])


def word_count(script: dict) -> int:
    return len(narration(script).split())


def _number_words(n: int) -> int:
    """How many words English uses to say n (226000 -> 'two hundred twenty six thousand' = 5)."""
    if n < 20:
        return 1
    if n < 100:
        return 1 if n % 10 == 0 else 2
    if n < 1000:
        return 2 + (_number_words(n % 100) if n % 100 else 0)
    for size, _name in ((10**9, "billion"), (10**6, "million"), (1000, "thousand")):
        if n >= size:
            rest = n % size
            return _number_words(n // size) + 1 + (_number_words(rest) if rest else 0)
    return 1


def spoken_words(text: str) -> int:
    """Words as the voice says them: digits, money, percents, and years expanded."""
    total = 0
    for tok in text.split():
        core = tok.strip(".,!?;:()\"'")
        nums = re.findall(r"\d[\d,]*(?:\.\d+)?", core)
        if not nums:
            total += 1
            continue
        for num in nums:
            whole, _, frac = num.replace(",", "").partition(".")
            n = int(whole or 0)
            if 1100 <= n <= 2099 and len(whole) == 4 and "," not in num and not frac:
                total += 2                                   # years: "twenty fourteen"
            else:
                total += _number_words(n) + (1 + len(frac) if frac else 0)
        total += core.count("$") + core.count("%")           # "dollars", "percent"
        if re.search(r"[A-Za-z]", re.sub(r"\d", "", core)):
            total += 1                                       # "50-plus", "10-year"
    return total


def spoken_word_count(script: dict) -> int:
    return spoken_words(narration(script))


def normalize(script: dict) -> dict:
    beats = []
    for b in script.get("beats") or []:
        if not isinstance(b, dict):
            continue
        say = re.sub(r"\s+", " ", str(b.get("say", ""))).strip()
        if not say:
            continue
        beats.append({"say": say, "callout": re.sub(r"\s+", " ", str(b.get("callout") or "")).strip()[:28],
                      "visual": re.sub(r"\s+", " ", str(b.get("visual") or "")).strip()})
    if beats:
        beats[0]["callout"] = ""  # the hook headline owns the top of the frame in beat 1
    # keep at most 7 callouts, numbers first: too many on-screen phrases dilutes every one of them
    with_callout = [i for i, b in enumerate(beats) if b["callout"]]
    if len(with_callout) > 7:
        keep = sorted(with_callout, key=lambda i: (not re.search(r"\d", beats[i]["callout"]), i))[:7]
        for i in with_callout:
            if i not in keep:
                beats[i]["callout"] = ""
    tags = script.get("hashtags") or re.findall(r"#\w+", str(script.get("caption", "")))
    if isinstance(tags, str):           # "#money #debt" instead of a list
        tags = re.findall(r"#?\w+", tags)
    tags = [t if t.startswith("#") else f"#{t}" for t in (str(x).strip() for x in tags if x) if t][:6]
    facts = [f if isinstance(f, dict) else {"claim": str(f).strip(), "basis": ""}
             for f in (script.get("facts") if isinstance(script.get("facts"), list) else []) if f]
    return {
        "title": str(script.get("title", "")).strip()[:90],
        "hook_text": re.sub(r"\s+", " ", str(script.get("hook_text", ""))).strip().rstrip(".!,;:"),
        "beats": beats,
        "caption": str(script.get("caption", "")).strip(),
        "description": str(script.get("description", "")).strip(),
        "hashtags": tags,
        "first_comment": str(script.get("first_comment", "")).strip(),
        "facts": facts,
        "source": script.get("source", "llm"),
        "pillar": script.get("pillar", ""),
    }


def final_path(job) -> object:
    return Paths.final / f"{job.id}.json"


def recent_titles(limit: int = 25) -> list[str]:
    titles = []
    for p in sorted(Paths.final.glob("*.json"))[-limit:]:
        try:
            titles.append(json.loads(p.read_text(encoding="utf-8")).get("title", ""))
        except json.JSONDecodeError:
            continue
    return [t for t in titles if t]


def write(job, angle: str = "", feedback: list[str] | None = None) -> dict:
    """Return the job's script, drafting one if no final script exists yet."""
    fp = final_path(job)
    if fp.exists() and not feedback:
        script = normalize({"pillar": job.pillar, **json.loads(fp.read_text(encoding="utf-8"))})
        events.emit("SCRIPT_LOADED", job=job.id, source=script["source"])
        return script
    from faceless import research
    pillar = config.pillar(job.pillar)
    prompt = script_prompt(pillar, job.topic, angle or job.artifacts.get("angle", ""), feedback, recent_titles(),
                           brief=research.brief(job.artifacts.get("brief")))
    from faceless.prompts import identity
    raw = llm.complete(prompt, system=identity(), want_json=True, job=job.id)
    raw["pillar"] = job.pillar
    script = normalize(raw)
    rnd = len(list(Paths.drafts.glob(f"{job.id}*.json")))
    write_atomic(Paths.drafts / f"{job.id}.r{rnd}.json", json.dumps(script, indent=2, ensure_ascii=False))
    events.emit("SCRIPT_DRAFTED", job=job.id, words=word_count(script), beats=len(script["beats"]), round=rnd)
    return script


def finalize(job, script: dict) -> None:
    write_atomic(final_path(job), json.dumps(script, indent=2, ensure_ascii=False))
