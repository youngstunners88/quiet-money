---
name: service-scoring
description: The decision layer for Quiet Money's outbound engine: Jev (TypeSafe System One, through OpenRouter's Decisions API) answers typed questions about each Web3 lead and each outreach draft, so code routes on probabilities instead of a model's prose. Covers the question bank (fit, budget signal, content gap, pursue or skip, personalization quality, spam risk, promise-free), the thresholds and confidence gates, which free model does which generative job and how to resolve its OpenRouter slug, and the caps. Use when scoring leads, gating outreach drafts, choosing or changing a model for this desk, when a score looks wrong, or as steps 3 and 5 of the service-outbound loop.
---

# Scoring and gating (Jev)

Free generative models make volume; **Jev decides what is worth pursuing and which drafts are good enough**. Jev
returns a typed answer plus its own probability, so the loop can route without reading prose. It never writes
content, and it never releases anything past the owner's send gate.

## How to call it
`faceless/outbound.py` does this on every run (`outbound.score`, `outbound.gate`), so a normal day needs no code from
you. The call, for a one-off or a new question:

```python
from faceless import decide
qs = {"fit": decide.Q("score", "...", fallback=0.0, levels=[...]),
      "pursue": decide.Q("choice", "...", fallback="skip", options={...})}
d = decide.ask(qs, state=lead_card, job=f"outbound:{slug}", backend="openrouter-decisions")
fit = d["fit"].jev_value          # Jev's answer and its probability
conf = d["fit"].jev_confidence
```

**A `score` answer comes back as the level index, not 0-1.** Jev answered `fit` 3.09 of 4 in the first live call
(2026-10-22), so `outbound._norm` scales every score answer by `len(levels) - 1` before a threshold sees it. A
threshold in this skill is on the 0-1 scale; never compare one against a raw answer.

**Read `jev_value` / `jev_confidence`, not `.value`.** `studio.toml [decide].dry_run` is `true` so that Jev cannot act
on the daily video path, and `.value` therefore holds the heuristic fallback. This desk acts on Jev's own answer and
applies its own thresholds. **Do not flip the global `dry_run`** to make this desk work - that would put Jev on the
daily critical path, which the brief forbids.

`backend="openrouter-decisions"` pins `[decide].decisions_model` (`typesafe/jev-1.13` - a build, never an alias) and
needs only `OPENROUTER_API_KEY`. Every call is logged to `state/decisions.jsonl` with its state and answers.

## The question bank
Atomic, single-purpose questions - one judgement each, never a compound one. Lead questions run on the lead card,
gate questions on the drafted text. The full bank, with exact wording, levels and options, is in
`references/question-bank.md`; copy from there rather than rewording, so scores stay comparable across batches.

| Stage | Question | Type | Used for |
|---|---|---|---|
| Lead | `fit` | score | Does this project match who we sell to |
| Lead | `budget` | noul | Is there a public signal they pay for marketing |
| Lead | `gap` | score | How badly their short-form is missing |
| Lead | `timing` | noul | Is there a dated moment in the next 6 weeks |
| Lead | `pursue` | choice | pursue / review / skip |
| Draft | `personalization` | score | Does it name something only research could know |
| Draft | `spam_risk` | score | Would a marketing lead read this as spam |
| Draft | `promise_free` | noul | Is it free of results claims, prices and token talk |
| Draft | `verdict` | choice | pass / rewrite / hold |

## Thresholds (start here; move them only from recorded outcomes)
| Gate | Rule |
|---|---|
| Pursue | `pursue == "pursue"` and confidence at or above 0.85, **and** `fit >= 0.6`, **and** a public business contact exists |
| Review | `pursue == "review"`, or any confident pursue whose `fit` is 0.4-0.6: listed for the owner, not drafted |
| Skip | everything else, with the score written into the card |
| Draft passes | `personalization >= 0.7` **and** `spam_risk <= 0.4` **and** `promise_free >= 0.9` **and** `verdict == "pass"` |
| Rewrite | one failed draft gate, once; a second failure is a hold |
| Hold | `promise_free` below 0.9 ever, or two failed rounds. Held drafts are reported, never queued |

A low-confidence answer (below `[decide].confidence_floor`, 0.85) is **not** a pursue: it goes to review. Confidence
decides how much autonomy Jev gets, which is the only dial that raises the autonomy level (`service-outbound`).

**What the first live calls actually returned (2026-10-22):** confidences of 0.55 to 0.88, mostly under the 0.85
floor - so Jev abstains and the code heuristics decide most leads today. That is the design working, not a fault, and
it is the honest state to report: the desk is heuristic-first until the outcomes justify a calibrated floor. Measure
before lowering it (`faceless-bench`), and never lower it to make a batch look decided.

`promise_free` is a **hard gate**: a draft that promises results, names a price or talks about a token is held
whatever else it scored. Compliance is never a probability call (CLAUDE.md rules 2 and 9, and `faceless-decide`'s
rule that a classifier may hold but never release).

## Cost and caps
Jev is $0.042 per million input tokens, output free. `[decide].decisions_daily_usd` is $0.05/day - roughly a million
input tokens, far more than a daily batch needs. A lead card is a small state object; keep it that way (send the card,
not the fetched pages). If the cap is reached, stop scoring, queue what already passed, and report. **Never raise it.**
When `OPENROUTER_API_KEY` is unset, `decide.ask` falls back to the heuristics in `references/question-bank.md` and the
batch is reported as heuristically scored.

## The free-model workforce
`channel/services/web3-video/models.json` holds the job-to-model assignment the owner set. The named models are
resolved to live OpenRouter slugs before first use and the resolved slug is written back into that file - never guess
a slug, and never leave a guess in place. `references/model-routing.md` has the job table, the resolution procedure
and the fallbacks.
