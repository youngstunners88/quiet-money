---
name: faceless-weekly-current
description: Weekly research pass that keeps Quiet Money current with accessible, real-world strategies, mechanisms and case studies for earning differently or reducing dependence on a single paycheck. Uses free or cheap models for the bulk research and synthesis, and files the results as Brain notes the Escape the Rat Race series and the daily topic picker can use. Use on the weekly cadence, when the owner asks for current strategies, fresh cases or a rat-race update, or when the content mix feels stale.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/brain.py
---

# Weekly current update

Once a week, gather fresh, accessible, relatable examples of strategies, mechanisms, tools and real cases that help ordinary people earn differently or depend less on one paycheck. Turn them into short tagged Brain notes the daily machine can use, so the channel stays current without turning into a news feed or hype.

This extends `faceless-brain`, `faceless-trends` and `faceless-research`. It does not replace them or the daily machine. (Source: the owner's `UPDATESKILL.md` on Drive, read in full 2026-11-05.)

## Rules
| Rule | Detail |
|---|---|
| Cadence | Once a week, or when the owner asks. Window: the last 7 to 14 days of signal. |
| Audience fit | Only what is accessible to 18-40 year olds who feel behind with money. No "you need $500k to start" stories. |
| Tone and compliance | Education only. No promised returns, no advice, no "get rich" framing (CLAUDE.md rules 1, 2 and 8). |
| Cost | Free or cheap models first for bulk work (Gemini Flash, free OpenRouter models, Flint for drafts, see `faceless-flint`). Stay inside the `[brain]` caps and the $3 daily ceiling. Where a better tool is on hand for a hard source, use it (rule 16). |
| Phone | Only when a source is locked behind a phone-only surface. Web and browser tools and APIs first. |
| Token burn | Claude orchestrates and judges. Bulk search, summary and extraction go to cheaper models. |
| Output | Brain notes in the Brain's own format, never raw dumps. The weekly cap is `weekly_new_max` in studio.toml `[brain]` (6 today). |

## What "current" means
Look for:
- Real cases (named or well documented) of people who used a specific, repeatable method.
- New or newly visible mechanisms (platforms, tools, policy changes, distribution) that lowered a barrier.
- Strategies that work now for ordinary people, with numbers that can be checked.
- Angles that fit the Escape the Rat Race pillar and the money-psychology mix.

Not generic motivation, undated evergreen theory already covered, news with no mechanism, or anything the gauntlet or compliance rules would fail.

## Workflow
0. **Pre-flight.** `python -m faceless preflight` and `python -m faceless doctor`; stop if paused or out of headroom. Read `channel/brand.md` (the Escape the Rat Race pillar), the last 2 to 3 weeks of `brain/sources/` so nothing is repeated (`python -m faceless brain search "words"`), and `analytics/opportunities.md` if present.
1. **Angles.** Write 3 to 5 focused angles for the week, for example: low-capital distribution that produced income; tools that removed a bottleneck; documented cases of skill, then offer, then first clients in the last 90 days; policy or platform changes that opened a side path; mechanisms that turn a skill into cash flow. Save them in `brain/weekly/<YYYY>-W<WW>-angles.md`.
2. **Bulk research.** For each angle, find primary sources, concrete numbers and named or well documented examples with a cheap model. Keep only the mechanism, the numbers, the constraint and the accessibility test. If the best source is in the owner's NotebookLM or on the phone: web version first, API or export second, phone automation last and for the fewest steps, with the session logged so its cost can be judged later (`faceless-phone`). Phone research is never the default path.
3. **Notes.** One note per usable finding, following `faceless-brain` step 3 so `python -m faceless brain check` passes: file `brain/sources/<day>-<speaker>-<slug>.md`, with `current-strategy`, `case-study`, `accessible-method` and `rat-race` among its `topics`. Put these in the note body: Accessibility (low or medium capital, skill or time barrier), Numbers (the checkable figures), Mechanism (one plain paragraph), Why it matters for Quiet Money (one or two sentences), Caveats (honest limits). Keep to `max_words`, quote at most `quote_max_words` words, and label every claim S, V or U. Then link the note from the topic pages it touches and run `python -m faceless brain index`.
4. **Feed the mix.** Add 1 to 3 concrete topic seeds to `script-lab/ideas/` (the backlog), each linking back to its brain note. Do not force every note into a video; the daily machine and the gauntlet decide. Facts about real people still need a research brief first (rule 8).
5. **Report** in this shape and send it to the owner:

```
Weekly current update, week <YYYY-WW>
Angles researched: N
New brain notes: N
Topic seeds added: N
Models used (cheap vs Claude): ...
Spend this run: $X.XX
Notable finds: <3 to 5 one-liners>
Next recommended follow-up: ...
```

Commit text, state and reports only, never media.

## Integration
| Piece | Use |
|---|---|
| `/brain` | where the notes go; `brain check` and `brain index` gate them |
| `faceless-trends`, `faceless-research` | complement; this is the weekly current layer |
| `faceless-scout` | its output is a source of opportunity signals |
| `faceless-flint` | free drafts for note skeletons; you still read every source and verify claims |
| LLM chain in studio.toml | respect its free-first order; every call goes through the ledger |
| Escape the Rat Race (`faceless-rat-race`) | main beneficiary of the notes |

## Never
- Turn the channel into a news feed.
- Seed topics that fail compliance or the gauntlet.
- Use a paid model for bulk research when a free or cheap one will do.
- Let Claude do heavy phone tapping when a cheaper model and structured tools can.
- Raise a spend ceiling or resume a paused studio without the owner's instruction.
- Commit media.

## Success
A handful of high-signal, accessible, tagged notes; fresh relatable examples for the Escape the Rat Race pillar and the wider mix; low Claude token burn; spend inside the ceilings; better raw material for the daily machine, not more noise.
