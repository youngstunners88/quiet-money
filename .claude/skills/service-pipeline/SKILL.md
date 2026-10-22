---
name: service-pipeline
description: The backlog and feedback loop for Quiet Money's Web3 video and KOL service: what state each lead is in, the batch report the owner reads, how replies, calls, quotes and closes are recorded as outcomes, and the weekly review that re-weights which categories, angles and proof blocks the next batch uses. Use when the owner reports back on outreach, when asking what is in the outbound pipeline or what a lead's status is, for the weekly outbound review, when deciding whether a threshold or a model should change, or as steps 6 and 7 of the service-outbound loop.
---

# The pipeline and the feedback loop

Without this step the engine never gets better: free models would write the same draft forever. The loop's only
training signal is what the owner reports back, recorded as outcomes.

Files in `channel/services/web3-video/`, all gitignored because the repo is public: `leads/<slug>.json` (one card per
project), `outbound/<slug>.json` (one package per pursued lead), `outcomes.jsonl` (readable events, with the words a
person wrote), `reviews/` (batch reports and the weekly review).

Two files are **committed**, because the loop's memory has to survive a fresh checkout, and they hold no company
names: `state/outbound-seen.json` (hashed project index - what has already been looked at) and
`state/outbound-outcomes.jsonl` (hashed outcome log - the signal `review` reads). Never put a name or a prospect's
words in either.

## Lead states
`researched -> scored -> drafted -> queued -> sent -> replied -> call -> closed`, with `skip` (never pursued) and
`dead` (sequence over, 90-day cool-off) as ends. The state lives in the card's `status`; nothing else tracks it.

```bash
python -m faceless outbound status     # leads per state, packages waiting on the owner, outcomes so far, resolved models
python -m faceless outbound review     # the aggregate per angle, proof block, channel and tier
```

## The batch report (what the owner actually reads)
The format is in the `service-outbound` skill's run-loop reference. Keep it to: the counts, the queued leads strongest
first with their angle and contact route, what was held and why, what was skipped and why, and the one owner action
(review, send, report back). Never paste draft bodies into the report - they are in the package files.

## Recording outcomes
`python -m faceless outbound outcome <slug> <event> [note]` writes the line and moves the lead's status. The events: `sent`, `no-reply-14d`,
`reply-positive`, `reply-negative`, `reply-question`, `call-booked`, `quoted`, `closed`, `lost`, `unsubscribe`,
`complaint`. Carry the scores and the choices that produced the message (`fit`, `angle`, `tier_pitched`,
`proof_block`, `channel`, `step`) on the line - **an outcome without them teaches nothing**, because the review works
by comparing those choices against what came back.

An unrecorded reply is worse than a lost lead: it is a lesson the engine will never learn. When the owner reports
back informally ("two replied, one wants examples"), write the lines first, then answer them.

## The weekly review
Run it once a week, write it to `reviews/<week>.md`, and keep it to what the numbers support. The exact procedure -
the rates to compute, the minimum volume before anything moves, which knob to turn for which pattern, and the review
format - is in `references/weekly-review.md`.

What may change from a review, in this order:
1. **Which categories and signals get researched** - the cheapest, safest change, and usually the right one.
2. **Which angle and which proof block the drafter reaches for first** - update `PACKAGES.md`'s angle table or the
   drafting brief's examples.
3. **A scoring threshold** - only on at least 30 sent messages, and only when two weeks point the same way
   (`service-scoring`).
4. **A model slug** - when one model's drafts reply measurably worse, or it keeps failing gates.

What never changes from a review: the send gate, the hard `promise_free` gate, the public-sources rule, the caps.
Those are not performance knobs (CLAUDE.md rules 9, 10, 11).

## Honest reporting
Reply rates on tiny samples are noise, and this desk will have tiny samples for weeks. Report the raw counts, say
when a number is too small to act on, and label an assumption as an assumption (CLAUDE.md rule 1 - every number is
true, including these). A batch that produced nothing is reported as a batch that produced nothing.
