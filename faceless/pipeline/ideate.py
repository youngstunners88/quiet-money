"""Topic selection: seeded backlog first, LLM top-ups when a pillar runs low, dedupe against history."""

from __future__ import annotations

import json
import re

from faceless import config, events
from faceless.config import Paths
from faceless.providers import llm
from faceless.prompts import ideas_prompt
from faceless.state import all_jobs

BACKLOG = Paths.ideas / "backlog.jsonl"
STOP = set("a an the and or of to in on for with is are was were be your you it its this that how why what "
           "who when do does did not no i my me we our they their them his her he she at by from as".split())


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9$%]+", text.lower()) if w not in STOP and len(w) > 2}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def history_texts() -> list[str]:
    out = []
    for j in all_jobs():
        out.append(j.topic)
        title = j.artifacts.get("title")
        if title:
            out.append(title)
    return out


def load_backlog() -> list[dict]:
    """Backlog items with a pillar and topic. The file is hand-edited, so a bad line is reported and skipped
    instead of stopping every daily run."""
    if not BACKLOG.exists():
        return []
    items = []
    for n, line in enumerate(BACKLOG.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            item = None
        if isinstance(item, dict) and isinstance(item.get("pillar"), str) and isinstance(item.get("topic"), str):
            items.append(item)
        else:
            events.emit("BACKLOG_BAD_LINE", line=n)
    return items


def append_backlog(items: list[dict]) -> None:
    BACKLOG.parent.mkdir(parents=True, exist_ok=True)
    with open(BACKLOG, "a", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def is_fresh(topic: str, history: list[str], threshold: float) -> bool:
    return all(similarity(topic, h) < threshold for h in history)


def find_topic(topic: str) -> dict | None:
    """The backlog item for a topic, so a hand-picked topic still gets its angle and research brief."""
    return next((i for i in load_backlog() if i["topic"].lower() == topic.lower()), None)


def demand_score(item: dict) -> float:
    """0 to 100: how much audience demand the research session found for this topic (see the faceless-trends skill). No evidence scores 0."""
    d = item.get("demand")
    try:
        return max(0.0, min(100.0, float(d.get("score", 0)))) if isinstance(d, dict) else 0.0
    except (TypeError, ValueError):
        return 0.0


def next_topic(pillar_id: str, reserved: list[str] | None = None) -> dict:
    """The best unused topic for the pillar: topics with researched demand first (highest score), the rest in the order they were written."""
    cfg = config.load()
    threshold = cfg["gauntlet"]["similarity_max"]
    history = history_texts() + list(reserved or [])
    used = {h.lower() for h in history}
    pool = sorted((i for i in load_backlog() if i["pillar"] == pillar_id), key=lambda i: -demand_score(i))        # stable: ties keep file order
    for item in pool:
        if item["topic"].lower() not in used and is_fresh(item["topic"], history, 0.8):
            return item
    # backlog dry for this pillar: ask the LLM for fresh ideas and keep the extras for later
    pillar = config.pillar(pillar_id)
    from faceless import research
    briefs = research.available() if pillar_id == "escape" else None
    res = llm.complete(ideas_prompt(pillar, 8, history, briefs), want_json=True, temperature=1.0)
    raw = res.get("ideas", []) if isinstance(res, dict) else res
    ideas = [dict(pillar=pillar_id, **{k: str(i.get(k) or "") for k in ("topic", "angle", "hook", "brief")})
             for i in (raw if isinstance(raw, list) else []) if isinstance(i, dict) and i.get("topic")
             and (not i.get("brief") or i["brief"] in (briefs or []))]
    fresh = [i for i in ideas if is_fresh(i["topic"], history, threshold)]
    append_backlog(fresh)
    events.emit("IDEAS_GENERATED", pillar=pillar_id, total=len(ideas), fresh=len(fresh))
    if not fresh:
        raise RuntimeError(f"no fresh topics for {pillar_id}")
    return fresh[0]
