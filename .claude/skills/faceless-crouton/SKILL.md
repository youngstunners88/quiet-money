---
name: faceless-crouton
description: Use Crouton Alpha, a free stealth model on OpenRouter (1M-token context, image/audio/video in), as extra hands for side work and as a measured advisory pre-screen for scripts. Covers the call template (reasoning effort per kind, 4000-token floor), the free-only and privacy guards, the gate bench, and what it may never do. Use when the owner says Crouton, stealth model, free model for bulk reading, long-context digest, or pre-screening scripts, and before ever proposing Crouton for anything on the critical path.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/crouton.py
---

# Crouton: free extra hands, measured before trusted

`stealth/crouton-alpha` (OpenRouter, checked 2026-11-04): $0 in and out, 1,048,576-token context, text/image/audio/video in, text out, tools and JSON mode work. It is
an anonymous provider's preview: **prompts may be kept by the provider** (not used for training), the price may change and the model may disappear. So it is capacity
for bounded side work, never part of the daily run. Same family of rules as `faceless-flint`; the difference is a pre-screen job that has to be proven on data.

## What it may do
- **Long reads (kind `digest`)**: one call over the whole Brain, a week of `gauntlet/reports/`, or `analytics/metrics.jsonl` to draft the weekly review or a Brain
  topic page. Build the prompt with `crouton.read_files([...])` (labels each file, refuses private paths and missing files).
- **Drafts (kind `draft`)**: backlog seed ideas, Brain note skeletons, intake dossiers. Same checks as Flint's: nothing is written unchecked.
- **Review (kind `review`)**: compliance sweeps over many descriptions or `POST.md` files, skill or CONTEXT.md drift hunting. Deterministic checks stay in code.
- **Advisory pre-screen (kind `classify`)**: `python -m faceless crouton screen FILE` asks whether a script breaks rules 1, 2, 3, 8 or 13 and returns `advise_hold`.
  It can only ADD a reason to look at a script. A "pass" releases nothing and an unreadable answer counts as a hold (`faceless-bench` rule 3).
- **Pictures**: `crouton.ask(..., images=[path])` for a second opinion on a still. Measure before relying on it (`faceless-bench`).

## What it may never do
- Sit on the critical path: final scripts, gauntlet judging, the daily run, offers, posting, prices, listings. It is not in `[llm].chain` or
  `[llm].openrouter_models`, and `tests/test_crouton.py` fails if any pipeline, gauntlet, script, offer or publish module imports it.
- Spend: the id must be a known-free id, the live catalog must say $0 in and out (checked once a UTC day, fail closed), and one call reporting `usage.cost > 0`
  trips `state/crouton.tripped`, which refuses every later call. Read why, fix it, then delete the file by hand; do not script the reset.
- Receive private material: no key-shaped strings or live key values (rule 11), nothing under `state/`, `.env`, `channel/services/studio/orders/`,
  `channel/services/web3-video/leads/` or `outbound/` (client messages, real people). The list is `[crouton] private_prefixes`.
- Write facts about a real person, a number, a claim or a quote: those come from `channel/research/` and `faceless/moneymath.py`.

## The call template (why it exists)
The model reasons by default at `max` effort and the hidden thinking spends `max_tokens`: in the first live test a 400-token budget returned `content: null`,
`finish_reason: length`. So `ask()` always sends `reasoning.effort` by `kind` (classify=minimal, review=low, draft=low, digest=medium) and `max_tokens` of at least
4000; an empty answer with `finish=length` is retried once with double the budget (and logged as `grown`). `minimal` answered 17x23 with 0 reasoning tokens.
Give each kind of job its own `task` name: the measurement is per task.

## Measurement and promotion
- Every call is a row in `state/crouton.jsonl`; `python -m faceless crouton status` shows success, JSON validity, empty-and-grown counts and latency per task.
- **The gate bench**: `python -m faceless crouton cases` (rebuild) and `python -m faceless crouton bench [--runs N] [--limit N] [--dry-run]`. Ground truth is 40
  scripts that shipped through the gauntlet (`gauntlet/corpus/quality`, label pass) and the same 40 with one sentence injected that breaks a rule (label hold; the
  violation is known by construction; 8 types x 5 in `crouton.INJECTIONS`), stored in `gauntlet/bench/crouton_gate.jsonl`. It scores right, wrongly flagged, missed,
  coverage and rule match, then a verdict: no opinion under 40 cases or 95% coverage, eligible only at recall >= 0.9 and false alarms <= 0.1. Reports:
  `analytics/crouton/<day>-gate.json`. Add real held jobs as new cases; the injected set is a floor, not the finish line.
- **Promotion**: a task needs 50+ measured calls at 95% success, and for the pre-screen a passing bench on cases that include real holds. Eligible means it may ADD
  holds as an advisory line in the gauntlet report; the owner decides whether it ever does more (rule 9 of the studio, `faceless-decide`).

### Latest measured results (2026-11-04, `stealth/crouton-alpha`, 1 run per case, temperature 0)
| Prompt | Split | Cases | Caught (recall) | Wrongly flagged | Verdict |
|---|---|---|---|---|---|
| v1 (judged rules 1 and 8 on provenance it cannot see) | dev | 40 hold + 40 pass | 39/40 (0.975) | **34/40 (0.85)** | not eligible: it flagged almost every shipped script |
| v2 (text-only scope: picks, urgency, promises, unnamed authority, private quotes) | dev (tuned on it) | 40 + 40 | 40/40 | 4/40 (0.10) | informational only |
| v2 | **holdout** (unseen scripts and phrasings) | 24 hold + 40 pass | 23/24 (0.958, 95% interval 0.80-0.99) | 4/40 (0.10, interval 0.04-0.23) | eligible to ADD holds, at the bar |
The thresholds (recall >= 0.9, false alarms <= 0.1) were fixed before any run. v2 was written after reading v1's false alarms, which is why the holdout exists. Read this honestly:
the holdout sits exactly on the false-alarm limit and its interval is wide; two of its four "false alarms" flag real promise wording the gauntlet let through ("force the hospital to
lower the balance", "clear every ghost charge in 15 minutes flat"), so they may be good catches, and the owner should read them in `analytics/crouton/2026-11-04-gate-holdout-v2.json`.
The one miss was a soft income promise ("the extra two thousand a month shows up every time"). Calls: 224 of 224 returned valid JSON, 0 empty, average 2.1 s. Scope matters: it does
not and cannot check that a number is true (that is `moneymath.py`) or that a fact about a person is true (that is the research brief). Whether to show its flag in the gauntlet
report is the owner's call; real held jobs should be added as cases first.

## Switch off or undo
`[crouton] enabled = false` in `studio.toml` stops every call; nothing else depends on it. To remove it: delete `faceless/crouton.py`, `tests/test_crouton.py`,
`gauntlet/bench/crouton_gate.jsonl`, `analytics/crouton/`, this skill, the `[crouton]` section and the `crouton` command.

## Troubleshooting
- `crouton is tripped`: a call reported a cost. Open `state/crouton.tripped`, check the catalog price, delete the file only when it is free again.
- `no longer free` / `not in the OpenRouter catalog`: the stealth preview ended or was priced. Stop; tell the owner; do not switch to a paid id here.
- `empty-length` after the retry: the task needs more thinking room than 8000 tokens; narrow the question or use `kind=classify`.
- HTTP 429: the shared free pool is busy; retried with a pause, then reported. Do not add a paid key to get around it.
