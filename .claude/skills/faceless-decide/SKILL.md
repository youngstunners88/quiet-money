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

## Images in the state (Jev 1.14, read 2026-10-15)
Sources: typesafe.ai/blog/jev-1-14, docs.typesafe.ai/images, docs.typesafe.ai/models#context-length.
- `decide.ask(questions, state, job, images={"name": path})` puts pictures in front of the model. Jev (SDK): each becomes an `Image` in the state and the request carries `TypeSafe-Danger-Zone-Images: true`. Laya: the pictures go in a top-level `assets` map (base64 PNG) and the state names them by reference. Clef (Cloudflare): up to 4 images, no header. Whichever backend `[decide]` selects gets them; `dry_run` still applies.
- Limits (never resized for you): PNG or JPEG, still only; each side 256-1568 px; 78,400-2,458,624 pixels; 16 MiB a file; 32 MiB a request. `decide.prepare_image` makes every picture fit. Images cost ordinary input tokens.
- Image skill is weaker than text skill (the authors say so): one picture and a simple yes/no or choice per question. Never use an image answer for compliance.
- Other 1.14 items, not used yet: the `box` question type (where something is in a picture), long context (per-request 64k tokens, 262k with `TypeSafe-Danger-Zone-Long-Context: true`; less reliable), and the opt-in data sharing. Danger-zone features are the vendor's own warning: calibrate against gauntlet results before anything acts.
- First use: `collage.check_frames(job_dir)` asks whether each drawn still keeps the paper look and has no text or face, and writes `frames-check.json`. No `TYPESAFE_API_KEY` is set here, so it runs on Clef; the Jev path is tested with a stand-in SDK, not live.
