# Content mix: what we dispense, and how we stop sounding the same

Hand-written. The generated sameness score is `analytics/variety.md` (it measures wording, openers and formats and is
overwritten each run); this file is the rule for what the channel is *about* each day. Evidence and the full autopsy:
`brain/topics/offense.md`. Written 2026-10-30.

## Status: enforced in code (2026-10-30)
`faceless/mix.py` applies the daily rules when the engine picks a topic (`[mix]` in `studio.toml`): at most 2 defense, at least 2 offense, a lead word once a day. If a day's pillar has no offense left it moves the slot to story, escape or playbook; if nothing fits it falls back to the old order and logs `MIX_RELAXED`, so a run is never stopped. `python -m faceless mix` shows the split of the unused backlog. Backlog items carry a hand `posture`; without one a keyword read of the title is used, which agreed with hand labels on 44 of 68 titles, so label new items.

## The problem
Too many videos teach the same lesson in the same posture: a trap, a leak, a hidden fee, a bias, and a "stop doing
X". 40 of 68 Shorts are defense; the best defense Short got 104 views and the median is 13. Offense, the viewer
watching a bold move pay off, has a median of 25. The backlog is worse: about 85 defense ideas to 12 offense.

## The daily mix (five slots)
| Slot | Posture | Examples of the move | Pillars that fit |
|---|---|---|---|
| 1 | Offense, a person's bet | equity over a fee, a negotiated deal, a bold purchase that compounded | story, escape |
| 2 | Offense, the viewer's move | the raise ask, the offer, the asset, the side income | escape, playbook |
| 3 | Neutral | a number explained with a clear verdict | math, myth |
| 4 | Defense | a trap or fee, in the form "do this today" | psychology, myth, playbook |
| 5 | Wildcard | a new format: comparison, challenge, Part 2 of a winner | any |

Hard limits: at most two defense videos a day, never back to back in the schedule, and no more than two titles a day
built on the same word ("trap", "hidden", "cost", "why your").
If the batch has to drop to three Shorts (owner decision 1 in `STRATEGY.md`), keep slots 1, 2 and 4.

## Variation axes (change at least two from yesterday's batch)
- **Posture:** offense, neutral, defense.
- **Protagonist:** a named person with a bet, the viewer, a company, a number as the character.
- **Shape:** fork (A or B), ladder (numbers climbing), before and after, myth then break, challenge, Part 2.
- **Money stage:** broke to first $1,000, saver to investor, earner to owner.
- **Ending:** a forced choice, a rule, a dare, a cliffhanger into Part 2.

## Titles
Number or named thing, plus a consequence (rule in `brand.md`). Do not open more than one title a day with "Why".
Weak patterns so far: "Hidden / Silent / Quiet" (median 3, n = 8), "Why your..." (median 10, n = 6).

## The flip test (run on every defense idea before it is scripted)
Ask: who makes a move here, and what did it win? If nobody wins anything, rewrite the idea as the bet or the
move, or drop it to slot 4. "Avoid the subscription trap" becomes "The $X a month a person redirected into an index
fund, and what it became", with the catch stated.

## Guardrails
Offense never means attacking people or businesses (`brain/topics/never.md`). No promised results, no income claims,
no "quit your job". Named people need a research brief first (CLAUDE.md rule 8). Every offense script keeps its
honest catch.

## Checkpoints (pre-registered)
| By | Check | Pass |
|---|---|---|
| 2026-11-13 | Offense share of new Shorts | 40% or more |
| 2026-11-13 | Median views, offense Shorts posted after 10-30 | above 25 on 20 or more posts |
| 2026-11-13 | Defense share of the backlog queue | below 50% |
| 2026-11-13 | Pairs of titles sharing a lead word on one day | 0 |
If the offense median does not beat 25 after 20 posts, this file is wrong: revert the mix and say so in `STRATEGY.md`.
