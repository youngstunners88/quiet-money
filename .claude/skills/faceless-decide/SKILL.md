---
name: faceless-decide
description: Add, test, and safely switch on a typed decision engine (Laya, the open-source Jev alternative, or Jev) for Quiet Money's routing and triage questions. Covers where a fast classifier helps (comment triage, topic scoring, gating LLM calls), where it must not be trusted (compliance), and how to calibrate it against gauntlet results before it acts. Use for Laya, Jev, TypeSafe, InstaCloud, "decision engine", classifier routing, or cutting LLM costs.
---

# Typed decisions (faceless/decide.py)

`decide.ask()` takes typed questions (`choice`, `score`, `noul` = yes/no probability) with a code-computed
fallback. Backends: `heuristic` (default, free), `jev` (TypeSafe API), `laya` (self-hosted, Apache 2.0, no
per-token cost). Pick with `studio.toml [decide].backend`; `auto` uses Laya if `LAYA_URL` is set, else Jev if
`TYPESAFE_API_KEY` is set. `dry_run = true` (default) logs the engine's answer next to the fallback in
`state/decisions.jsonl` and never acts on it.

## What Laya is (checked 2026-10-02)
Open-source, non-autoregressive classifier: one forward pass, no text generated, same Jev question types over
`POST /v1/systemone`. English 421M params (512-token context), multilingual 322M (1K+). ~35 ms on a GPU, 200-460 ms
on CPU. The InstaCloud template is a one-click English-only container (amd64, 842 MB model, input cut at ~1K
tokens); its price is not published (container runtime), so check the InstaCloud dashboard before relying on it.
Self-hosting elsewhere: `pip install "laya[serve]"` then `laya-serve`; set `LAYA_URL=http://host:8000`.

## Where it earns its keep (blind spots worth knowing)
1. **Comment triage** (once accounts exist): is it a question / praise / spam / abuse / buying-intent? Reply
   priority, auto-hide spam, surface questions for the reply-with-video format. High volume, no tokens spent.
2. **Backlog scoring**: score topics for hook strength, number-ability, and risk before spending a render.
3. **Gating LLM calls**: skip the judge on a script a cheap check already rejects; skip rewrites that cannot fix it.
4. **Trend and AEO triage**: is a scraped idea on-niche and checkable; does an AI answer actually recommend us.
5. **Hold-queue triage**: which held videos are one-gate fixes versus rewrites.

## Where NOT to use it
- **Compliance and facts.** The judge, `COMPLIANCE_BANNED`, and the facts gate stay deterministic or LLM-judged.
  A classifier may only hold more videos, never release one (`orchestrator.produce` already forbids shipping a
  failed video whatever the engine says).
- Long inputs (>1K tokens) are truncated: send the hook and key beats, not whole transcripts.
- Many options (dozens of labels): accuracy collapses; keep choice questions to ~8 options.

## Known caveats (from Laya's own docs)
- Checkpoints ship over-confident: fit a temperature before trusting `confidence`; gate on `answer_confidence`.
- Position bias: identical options score differently by slot. `_ask_laya` shuffles option order per question.
- The engine is only as good as the question wording; ask narrow, single-purpose questions.

## Turn it on safely (do this, in order)
1. Deploy (InstaCloud template or `laya-serve`), set `LAYA_URL` (and `LAYA_API_KEY` if the server needs one) as
   environment variables in the Claude Code environment. Never commit them.
2. Leave `dry_run = true`. Run normal batches for a week; every decision logs the fallback and Laya's answer.
3. Measure agreement against ground truth we already have: gauntlet pass/hold (`gauntlet/reports/*.json`) and
   later real metrics. Per question: agreement rate, and for confident answers (`confidence >= confidence_floor`)
   the precision of "publish". Only questions with sustained high precision move to `dry_run = false`.
4. Keep `confidence_floor` at 0.85 or higher; a low-confidence or invalid answer always falls back to the code route.

## Add a new question
```python
from faceless import decide
d = decide.ask({"kind": decide.Q("choice", "What is this comment?", fallback="question",
        options={"question": "asks something", "praise": "compliments", "spam": "ads or links", "abuse": "hostile"})},
        state={"body": comment_text}, job=None)["kind"]
```
Always give a fallback the code can live with, and add a test with a mocked `faceless.providers.http` (see
`test_laya_backend_answers_are_validated_and_dry_run_by_default`).
