---
name: faceless-panel
description: Put one decision to several models through OpenRouter (for example Microsoft Phi-4 against Claude Haiku 5.5), tally their answers, adjudicate them against the facts, and record the approved result. Use when the owner asks to get a decision from two models, to compare models on a business or design question, to settle one option against another, or says to approve the best result.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/panel.py
---

# Model panel

`python -m faceless panel brief.txt --models microsoft/phi-4,anthropic/claude-haiku-5.5 --runs 3` asks each model the same brief several times and prints votes, confidence, failures and cost; the raw answers are saved in `state/panels/`.

## Rules
1. **The brief carries the facts.** Pull them from the studio's own files (catalog, prices, rules, what already exists) and mark anything unverified as unverified. Models are not asked to know the business.
2. **Ask for JSON** with `choice`, `confidence`, `reasons` (4 or fewer), `risks`, `first_test`, `what_would_change_my_mind`, and say "do not invent sales numbers or rates".
3. **Agreement is not correctness.** Read the reasons. A model that votes the same way every time can be repeating a generic answer. Check each reason against a fact in the brief; credit the model that used the facts that matter.
4. **A close call goes to the reversible, cheaper option.**
5. **Approval has a scope.** The owner may give permission in advance to approve the best result. That covers the decision named in the task (a structure, a design direction). It never covers publishing, listing, pricing, spending past a cap, or anything on a public account (CLAUDE.md rule 9). Say what was and was not approved.
6. **Record it:** `channel/empire/decisions/<date>-<slug>.md` with the method, the table of what each model said, the adjudication, the actions it sets and what would change it, plus the brief next to it. Keep the raw answers in `state/panels/`.
7. Spend is capped by `[panel]` in `studio.toml` ($0.10 a day, $0.01 a call, 5 runs); the studio ceiling and `state/PAUSE` still apply. Keys stay in the environment.

## Choosing models
Which models exist: `GET https://openrouter.ai/api/v1/models` (public). The only Microsoft model currently there besides the older WizardLM-2 is `microsoft/phi-4` (14B, 16k context): cheap, so a useful second voice, but weak at using a long fact sheet. `anthropic/claude-haiku-5.5` is the studio's cheap strong reader. `typesafe/jev-router` picks its own model per request and measured worse on a locating job (skill `faceless-bench`). To trust a model for a recurring job, benchmark it on ground truth; a panel is for one-off judgement calls.

## Troubleshooting
- **A run fails with no JSON:** a reasoning model ran out of tokens; the panel already sends `max_tokens` 2000 and low reasoning effort. Count failures; do not drop them silently.
- **All models agree and the reasons are generic:** add the missing fact to the brief and run again.
- **Models split:** that is information. Write the split into the decision and pick by rule 4.
