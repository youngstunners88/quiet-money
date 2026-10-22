---
name: faceless-flint
description: Use Flint, a free open-weight coding model on OpenRouter, as extra hands for side work that is not on the daily 5-video path: backlog topic and script seeds, Brain note drafts, intake dossiers, code and skill exploration. Covers what it may and may never do, how to call it, and how its success rate is measured. Use when the owner says Flint, extra hands, extra capacity, free model, or when a side job would burn Gemini or paid tokens; and before ever proposing Flint for anything on the critical path.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/flint.py
---

# Flint: free extra hands

Recursive's Flint (`recursive/flint-v1.0:free`, open weights, 262K context, released 2026-10-21) costs nothing. OpenRouter's own page shows about 20% tool-call and
about 50% structured-output errors and a shared, rate-limited free pool. So it is capacity for side work, never part of the daily run. First live check
(2026-10-22): after one retry on a 429 it returned valid JSON on 8 of 8 seed requests, but the titles were abstract and templated until the prompt asked for
concrete situations, and a person still had to prune the weak seeds. Treat every answer as a draft.

## What it may do
- Backlog seeds: `python -m faceless flint seeds -n 8 --pillar psychology` (`--dry-run` to look first). It asks Flint, drops anything the claim check refuses
  (`offer.violations`), keeps only seeds whose meaning is not within `[gauntlet] topic_dup` of recent videos, the backlog or each other, and appends them to
  `script-lab/ideas/backlog.jsonl` with `source: flint-<date>`. No embeddings means no write. Read the output and prune weak rows by hand; real hooks name an ordinary
  moment, not a concept.
- Drafts for a person or another skill to check: Brain note skeletons (faceless-brain), intake dossiers (faceless-intake), skill and code exploration.
- Any one-off in Python: `from faceless import flint; flint.ask(prompt, task="brain-draft", want_json=True)`. Give each kind of job its own `task` name: the measurement
  is per task.

## What it may never do
- Sit on the critical path: final scripts, gauntlet judging, structured outputs the run needs, offer packs, the daily run, posting, prices, listings. It is not in
  `[llm].chain` or `[llm].openrouter_models`, and `tests/test_flint.py` fails if any pipeline, gauntlet, script, offer or publish module imports it.
- Spend: the code refuses any model id that does not end in `:free`. Do not change that; a paid Flint is a different decision for the owner.
- Write facts about a real person, a number, a claim or a quote: those come from `channel/research/` and `faceless/moneymath.py`.
- Run unreviewed: its answers are data. Nothing it writes reaches a video, an email or a listing without the normal gates.

## Measurement and promotion
Every call is a row in `state/flint.jsonl` (task, ok, json_ok, attempts, ms, tokens). `python -m faceless flint status` shows the rates per task. The rule in the output: no
promotion beyond side work until 50 or more measured calls on one task reach 95% success, and then only the owner moves it (`faceless-bench` for the test, rule 9).
A 429 is retried with a pause (the free pool is shared); after the retries it raises, and the caller carries on without Flint. Use `fallback=True` only for side work
that may use the normal chain instead.

## Switch off or undo
`[flint] enabled = false` in `studio.toml` stops every call; nothing else depends on it. To remove it entirely delete `faceless/flint.py`, `tests/test_flint.py`, this skill, the `[flint]`
section and the `flint` command.

## Troubleshooting
- HTTP 429 "rate-limited upstream": the shared free pool is busy. Wait and retry; do not add a paid key to get around it.
- `bad-json`: Flint answered in prose. Retried once; repeated means the task is wrong for it.
- `no embedding provider`: `python -m faceless keys`; seeds are never written unchecked.
- Daily allowance used (`[flint] daily_calls`): it resets with the UTC day.
