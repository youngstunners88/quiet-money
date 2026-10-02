"""Answer-engine visibility tracker (method from the AEO research in channel/seo-playbook.md).

- Quantized prompts, not free-form ones: "A viewer is looking for <entity>. Recommend some channels."
  Free-form prompt volumes don't exist; a fixed structured probe per entity is measurable over time.
- Search-grounded engines only, because grounding is what biases recommendations day to day:
  GPT (Bing-like web search), Claude (Brave-backed), Gemini (Google), Perplexity (own index).
- Metrics per engine and entity: mentioned (yes/no), ordinal position in the list, citation share
  (our site among cited URLs). Rows append to analytics/aeo.jsonl; trends need weeks, not runs.
Also: page_to_prompts() reverses a page into the prompts that should surface it (citation mining input).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from faceless import config, events, ledger
from faceless.config import Paths
from faceless.providers import ProviderError, http
from faceless.providers.llm import _extract_json

AEO_LOG = Paths.analytics / "aeo.jsonl"

ENGINES = {  # name -> OpenRouter model with live web search
    "gpt": "openai/gpt-5-mini:online",
    "claude": "anthropic/claude-haiku-4.5:online",
    "gemini": "google/gemini-3.5-flash-lite:online",
    "perplexity": "perplexity/sonar",
}

DEFAULT_ENTITIES = [
    "short videos that explain money psychology",
    "a YouTube Shorts channel about personal finance for beginners",
    "a TikTok account that explains compound interest and debt simply",
    "a channel with true stories of ordinary people who quietly got rich",
]


def _ask(model: str, prompt: str) -> tuple[str, list[str]]:
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderError("OPENROUTER_API_KEY not set")
    r = http().post("https://openrouter.ai/api/v1/chat/completions", timeout=120,
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0})
    if r.status_code != 200:
        raise ProviderError(f"{model} {r.status_code}: {r.text[:200]}")
    d = r.json()
    msg = d["choices"][0]["message"]
    urls = [a.get("url_citation", {}).get("url") for a in msg.get("annotations") or [] if a.get("type") == "url_citation"]
    urls += d.get("citations") or []
    ledger.spend("openrouter-aeo", "calls", 1, usd=float((d.get("usage") or {}).get("cost") or 0))
    return msg.get("content") or "", [u for u in urls if u]


def _names(text: str) -> list[str]:
    try:
        val = _extract_json(text)
        if isinstance(val, dict):
            val = next((v for v in val.values() if isinstance(v, list)), [])
        return [str(x.get("name") if isinstance(x, dict) else x).strip() for x in val][:15]
    except Exception:  # noqa: BLE001 - fall back to list-looking lines
        return [re.sub(r"^[\s\-\*\d\.\)]+", "", l).strip() for l in text.splitlines() if l.strip()][:15]


def _is_us(name: str) -> bool:
    n = name.lower().replace(" ", "")
    return "quietmoney" in n or "quietmoneyrules" in n


def track(entities: list[str] | None = None, engines: list[str] | None = None) -> list[dict]:
    c = config.load()
    domain = c.get("site", {}).get("base_url", "").split("//", 1)[-1]
    entities = entities or c.get("aeo", {}).get("entities") or DEFAULT_ENTITIES
    rows = []
    for ent in entities:
        prompt = (f"A viewer is looking for {ent}. Recommend some channels or creators. "
                  "Return ONLY a JSON array of names, best recommendation first.")
        for eng in engines or list(ENGINES):
            try:
                text, urls = _ask(ENGINES[eng], prompt)
            except Exception as e:  # noqa: BLE001 - one engine down shouldn't stop the probe
                rows.append({"engine": eng, "entity": ent, "error": config.redact(str(e))[:200]})
                continue
            names = _names(text)
            pos = next((i + 1 for i, n in enumerate(names) if _is_us(n)), None)
            ours = sum(1 for u in urls if domain and domain in u)
            rows.append({"engine": eng, "entity": ent, "names": names, "position": pos,
                         "mentioned": pos is not None, "citations": len(urls), "our_citations": ours,
                         "citation_share": round(ours / len(urls), 3) if urls else 0.0, "cited": urls[:12]})
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    AEO_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AEO_LOG, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"day": day, **r}, ensure_ascii=False) + "\n")
    ok = [r for r in rows if "error" not in r]
    events.emit("AEO_TRACK", probes=len(rows), ok=len(ok), mentioned=sum(r["mentioned"] for r in ok))
    return rows


def summary(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    competitors: dict[str, int] = {}
    for r in ok:
        for n in r["names"]:
            competitors[n] = competitors.get(n, 0) + 1
    return {"probes": len(rows), "answered": len(ok),
            "mention_rate": round(sum(r["mentioned"] for r in ok) / len(ok), 3) if ok else 0,
            "citation_share": round(sum(r["citation_share"] for r in ok) / len(ok), 3) if ok else 0,
            "top_recommended": sorted(competitors.items(), key=lambda x: -x[1])[:10],
            "errors": [r["error"][:80] for r in rows if "error" in r][:3]}


def page_to_prompts(page_text: str, n: int = 8) -> list[str]:
    """Reverse a page into the prompts that should make an assistant recommend it."""
    from faceless.providers import llm
    res = llm.complete("What would people type into an AI assistant that should lead it to recommend the page "
                       f"below? Give {n} varied, realistic prompts. Return ONLY a JSON array of strings.\n\n"
                       + page_text[:6000], want_json=True, temperature=0.4)
    return [str(x) for x in (res if isinstance(res, list) else next(iter(res.values()), []))][:n]
