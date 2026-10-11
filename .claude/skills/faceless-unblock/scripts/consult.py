"""Ask other models on OpenRouter for a second opinion, with a hard spend cap. Secrets are redacted before anything is sent.

    python .claude/skills/faceless-unblock/scripts/consult.py "question" [--file brief.md ...] [--model id ...] [--max-cost 0.25]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from faceless import config, events  # noqa: E402

DEFAULT_MODELS = ["google/gemini-3.1-pro-preview", "microsoft/phi-4"]
URL = "https://openrouter.ai/api/v1"


UNKNOWN_PRICE = (15e-6, 75e-6)   # routers report -1 (price depends on the model they pick): plan for a top-tier model


def prices(model: str) -> tuple[float, float]:
    """(prompt, completion) USD per token, read live so the cap uses today's price."""
    for m in requests.get(f"{URL}/models", timeout=40).json()["data"]:
        if m["id"] == model:
            p = m.get("pricing", {})
            a, b = float(p.get("prompt") or 0), float(p.get("completion") or 0)
            return UNKNOWN_PRICE if a < 0 or b < 0 else (a, b)
    raise SystemExit(f"unknown model {model!r}")


def worst_case(prompt_chars: int, max_tokens: int, price: tuple[float, float]) -> float:
    return (prompt_chars / 3) * price[0] + max_tokens * price[1]   # 3 characters per token is deliberately pessimistic


def consult(brief: str, models: list[str], max_cost: float, max_tokens: int = 1200) -> list[dict]:
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    brief = config.redact(brief)
    plan = [(m, worst_case(len(brief), max_tokens, prices(m))) for m in models]
    if sum(c for _, c in plan) > max_cost:
        raise SystemExit(f"worst-case cost ${sum(c for _, c in plan):.3f} is over the ${max_cost:.2f} cap; shorten the brief or lower --max-tokens")
    out = []
    for model, _ in plan:
        r = requests.post(f"{URL}/chat/completions", timeout=240, headers={"Authorization": f"Bearer {key}"},
                          json={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": brief}]})
        d = r.json()
        if "choices" not in d:
            out.append({"model": model, "error": config.redact(str(d))[:300]})
            continue
        cost = float(d.get("usage", {}).get("cost") or 0)
        events.emit("CONSULT", model=model, cost=cost)
        out.append({"model": model, "text": d["choices"][0]["message"]["content"], "cost": cost})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--model", action="append")
    ap.add_argument("--max-cost", type=float, default=0.25)
    ap.add_argument("--max-tokens", type=int, default=1200)
    a = ap.parse_args()
    brief = "\n\n".join([a.question] + [f"<file {f}>\n{Path(f).read_text(encoding='utf-8')}\n</file>" for f in a.file])
    for o in consult(brief, a.model or DEFAULT_MODELS, a.max_cost, a.max_tokens):
        print("=" * 60, o["model"], f"${o.get('cost', 0):.4f}")
        print(o.get("text") or o.get("error"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
