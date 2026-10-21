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


def _item_text(item: dict) -> str:
    return ". ".join(x for x in (item.get("topic", ""), item.get("angle", ""), item.get("hook", "")) if x)


def recent_scripts(n: int = 120) -> list[str]:
    """Title and hook of the latest finished scripts: the short form a backlog topic is compared with."""
    out = []
    for p in sorted(Paths.final.glob("*.json"))[-n:]:
        if p.name.startswith("_"):
            continue
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append(f"{s.get('title', '')}. {s.get('hook_text', '')}")
    return out


def first_distinct(items: list[dict], reserved: list[str], limit: float) -> dict | None:
    """The first item whose meaning is not already covered by a recent video or by a topic taken earlier today: centered embedding
    similarity of topic+angle+hook against recent titles and hooks stays under `limit` (0.5; unrelated pairs sit under 0.34 99 times in 100).
    Lexical checks miss a paraphrase ("start at 25 vs 35" written twice). No embeddings: the first item, as before."""
    from faceless import embed
    past = recent_scripts() + list(reserved)
    texts = [_item_text(i) for i in items]
    vecs = embed.embed(texts + past) if past else None
    if vecs is None:
        return items[0]
    cv = embed.centered(vecs, vecs)
    cands, refs = cv[:len(texts)], cv[len(texts):]
    for item, v in zip(items, cands):
        top = max((embed.cosine(v, r) for r in refs), default=0.0)
        if top < limit:
            return item
        events.emit("TOPIC_TOO_CLOSE", topic=item["topic"][:80], similarity=round(top, 3))
    return None


def next_topic(pillar_id: str, reserved: list[str] | None = None) -> dict:
    """The best unused topic for the pillar: topics with researched demand first (highest score), the rest in the order they were written."""
    cfg = config.load()
    threshold = cfg["gauntlet"]["similarity_max"]
    history = history_texts() + list(reserved or [])
    used = {h.lower() for h in history}
    pool = sorted((i for i in load_backlog() if i["pillar"] == pillar_id), key=lambda i: -demand_score(i))        # stable: ties keep file order
    fresh = [i for i in pool if i["topic"].lower() not in used and is_fresh(i["topic"], history, 0.8)]
    if fresh:
        pick = first_distinct(fresh, list(reserved or []), float(cfg["gauntlet"].get("topic_dup", 0.5)))
        if pick is not None:
            return pick
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
