---
name: faceless-panel
description: Put one decision to several models through OpenRouter (for example Microsoft-Decision-1 against Jev and Claude Haiku 5.5), tally their answers, adjudicate them against the facts, and record the approved result. Use when the owner asks to get a decision from two models, to compare models on a business or design question, to settle one option against another, or says to approve the best result.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/panel.py
---

# Model panel

`python -m faceless panel brief.txt --models anthropic/claude-haiku-5.5 --runs 3` asks each model the same brief several times and prints votes, confidence, failures and cost; the raw answers are saved in `state/panels/`.

## Rules
1. **The brief carries the facts.** Pull them from the studio's own files (catalog, prices, rules, what already exists) and mark anything unverified as unverified. Models are not asked to know the business.
2. **Ask for JSON** with `choice`, `confidence`, `reasons` (4 or fewer), `risks`, `first_test`, `what_would_change_my_mind`, and say "do not invent sales numbers or rates".
3. **Agreement is not correctness.** Read the reasons. A model that votes the same way every time can be repeating a generic answer. Check each reason against a fact in the brief; credit the model that used the facts that matter.
4. **A close call goes to the reversible, cheaper option.**
5. **Approval has a scope.** The owner may give permission in advance to approve the best result. That covers the decision named in the task (a structure, a design direction). It never covers publishing, listing, pricing, spending past a cap, or anything on a public account (CLAUDE.md rule 9). Say what was and was not approved.
6. **Record it:** `channel/empire/decisions/<date>-<slug>.md` with the method, the table of what each model said, the adjudication, the actions it sets and what would change it, plus the brief next to it. Keep the raw answers in `state/panels/`.
7. Spend is capped by `[panel]` in `studio.toml` ($0.10 a day, $0.01 a call, 5 runs); the studio ceiling and `state/PAUSE` still apply. Keys stay in the environment.

## Two kinds of panel
- **Chat models** (`python -m faceless panel brief.txt --models anthropic/claude-haiku-5.5,... --runs 3`): the brief asks for JSON with a `choice`; good for open judgement and for reading the reasons.
- **Decision models** (OpenRouter Decisions API, `POST /api/alpha/decisions`, `faceless/panel.py` `run_decisions`): the facts go in as `state`, the questions as typed `choice`, `noul` (yes/no) and `score`; the model returns a calibrated **probability per option** instead of text, in about 0.3 s for a few thousandths of a cent. 19 are served (list them: `GET https://openrouter.ai/api/v1/models?output_modalities=decisions`): `microsoft/microsoft-decision-1` (Azure), `typesafe/jev-1.13` (Jev), `upstage/solar-decide-flash`, `openai/gpt-6-luna-decisions`, `perplexity/pplx-decider-v1.1-27b`, `cloudflare/clef`, `liquid/d1`, `inception/mercury-decide`, and more. **A decision model is not a chat model** (`microsoft/phi-4` is a chat model; sending a decision model to chat completions is refused).

## Gate in code, and check coherence
1. Ask the headline `choice` **and** yes/no questions about its consequences ("would this overlap an existing bundle", "is there data", "is a third listing justified"). Independent questions over the same state go in one request.
2. **A pick must agree with the same model's answers about what the pick implies.** In the bundle decision Microsoft-Decision-1 chose "bundle" at 0.86 while rating "a third listing is justified" at 0.07: the pick is overruled by its own answer.
3. Treat the models as voters on the sub-questions first; the headline split is information, not a verdict. A near-0.5 probability means unsure, not "medium".
4. Pin the exact build (`response.model`, e.g. `microsoft/microsoft-decision-1-20261009`), never an alias; record it with the answer.

## Choosing models
`anthropic/claude-haiku-5.5` is the studio's cheap strong reader for open questions and for vision. For a recurring typed job, benchmark candidates on ground truth first (skill `faceless-bench`); a panel is for one-off judgement calls. In the studio, `[decide] decisions_model` pins the decision model behind the `openrouter-decisions` backend (Jev 1.13 today).

## Troubleshooting
- **A run fails with no JSON:** a reasoning model ran out of tokens; the panel already sends `max_tokens` 2000 and low reasoning effort. Count failures; do not drop them silently.
- **All models agree and the reasons are generic:** add the missing fact to the brief and run again.
- **Models split:** that is information. Write the split into the decision and pick by rule 4.
