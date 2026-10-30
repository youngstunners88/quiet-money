---
name: wealth-neuron-surgery
description: Write Quiet Money video scripts built on one wealth-building "neuron" (a single ownership, cash-flow, equity, IP or resilience decision) shown through a real person. Use for wealth-vs-riches scripts about athletes, entertainers, historical figures, equity, IP, franchises or cash flow, or when the owner names a neuron ID such as W1.
argument-hint: "[neuron-ID or subject] [platform/runtime]"
metadata:
  author: quiet-money
  version: 1.1.0
  source: owner's skill draft plus the research report "From Riches to Resilience" (2026-10-30)
---

# Wealth Neuron Surgery

## Purpose
Write calm, concrete, source-checked scripts for the Quiet Money series. "Neuron" is a **content metaphor** for one
high-leverage wealth decision. Never present it as a literal claim about brains or AI model internals.

## Input
A neuron ID (`W1`), a subject (`LeBron James and equity`), or both (`W1 - LeBron James`), plus an optional platform
and runtime. The engine is autonomous, so never stop to ask: if the neuron is unclear, pick the closest one, state the
assumption in the output, and carry on. With no runtime, use the default below.

## Core distinction
- **Riches:** high income, visible spending, labor-dependent earnings, fragile status.
- **Wealth:** ownership, cash flow, control, optionality, and resilience after income changes.

A video isolates **one switch**: what happens when it is turned up, what happens when it is ignored, one practical move.

## Lead with the move that paid (offense first)
Our own numbers (`brain/topics/offense.md`, `channel/CONTENT-MIX.md`): a person making a bold move that pays has a
median of 25 views against 13 for avoid-the-trap videos, and ruin stories flop (6, 4 and 19 views). So:
- W1, W2, W3, W4 and W7 are offense neurons. Use them for the offense slots.
- W5, W6 and W8 are neutral. Use them in the explainer slot, never two in a row.
- "Dose down" is a short contrast, one or two beats. The video is about the move, not the collapse.
- Keep the honest catch: what it cost, what could have gone wrong, why most people would not.

## Non-negotiables
1. One neuron per video.
2. Every factual claim is sourced or marked `UNVERIFIED`. An `UNVERIFIED` claim never ships (the gauntlet's facts judge is a hard gate).
3. Never invent quotes, net worths, contract values, career lengths, bankruptcy rates or business details.
4. Prefer filings, interviews, autobiographies, reputable journalism and academic research over aggregators.
5. Never imply the viewer should copy a celebrity's exact strategy.
6. Calm, specific, no hype. Ban: "unlock", "game-changer", "mindset is everything", guru language, get-rich-quick.
7. No causation without support: "associated with", "contributed to", "in this case", not "because".
8. Real people never appear as faces in the visuals; no endorsement is implied (CLAUDE.md rules).

## High-risk claims (verify independently)
Net worth, contract value, equity percentage or ownership stake, career length, bankruptcy or distress rates, business
counts and franchise details, direct quotes, and causal claims ("this decision made them wealthy").

## Roster
These scripts are additional. Hormozi, Kiyosaki and Peña stay the core of the `escape` pillar; whom this skill covers, and the growing queue, is in `channel/ROSTER.md`. Researched so far: LeBron James (W1), Jay-Z (W2, W1) and Taylor Swift (W2), each with a brief and backlog topics. Add posture to every new backlog line (`"posture": "offense"`); `python -m faceless mix` shows the split.

## Neuron library
| ID | Neuron | Dose up | Dose down | Posture |
|----|--------|---------|-----------|---------|
| W1 | Equity over wages | Trade some cash pay for ownership | Optimize only for the biggest paycheck | offense |
| W2 | Ownership of IP / masters | Keep rights that compound | Sell rights for immediate cash | offense |
| W3 | Cash-flow businesses | Build repeatable cash engines | Depend entirely on personal labor | offense |
| W4 | Conversion window | Turn peak income into assets in a defined window | Assume high income will continue | offense |
| W5 | Quiet vs loud signal | Prioritize privacy and compounding | Use display spending as proof | neutral |
| W6 | Stewardship vs hoarding | Treat capital as responsibility | Optimize only for private accumulation | neutral |
| W7 | System leverage | Build systems that earn beyond personal hours | Sell only personal time | offense |
| W8 | Autonomy definition | Measure freedom of time and choice | Measure only net worth | neutral |

## Research gate
Our rule 8 (CLAUDE.md): facts about a real person in a script come only from `channel/research/<person>.md`, in the
format of `channel/research/hormozi.md` (researched date, "Verified facts", "Do not say"). So:
1. List the files you checked: `channel/research/`, `brain/sources/`, `brain/topics/wealth-neurons.md`.
2. For each material claim, find a primary or reputable source. The owner's report "From Riches to Resilience" is a
   **lead list, not a source**: most of its citations are search-engine redirect links and a few are social posts
   (`brain/topics/wealth-neurons.md` has the count and the leads).
3. Write what you verified into `channel/research/<person>.md` (claim, source, date checked, confidence, counterpoint).
   Mark anything unsupported `UNVERIFIED` and leave it out of the script.
4. No brief, no script. Return a research plan instead.

## Completion states
- `RESEARCH COMPLETE`: enough verified evidence for a full script.
- `RESEARCH INCOMPLETE`: research plan, source gaps, proposed angle; **no final script**.
- `DRAFT ONLY`: only when the owner explicitly asks for a draft despite gaps. Every unverified claim is labelled inline
  and the draft is never queued or posted.

## Script structure (seven beats)
1. **Hook: the switch exists.** The first line carries a named person and a number (title rule in
   `channel/brand.md`; vague hooks have a median of 2-3 views). The AI analogy is optional and goes second at best:
   "Some AI researchers can steer a model by changing a few internal signals. With money, the useful version is simpler:
   find the one decision that changes the trajectory."
2. **Name the neuron:** one line, optional ID.
3. **Dose up:** what they did, what they owned, what compounded. Active voice; the protagonist acts.
4. **Dose down:** the opposite path, real patterns only, short.
5. **Definition:** riches vs wealth, in verified practice rather than invented quotes.
6. **Transferable move:** one realistic action for an ordinary viewer this week.
7. **Close on the loop:** the last line returns to the switch and gives a forced choice the viewer can answer in a comment.
Follow `brain/topics/offense.md` (recipe) and `faceless-script` for the JSON format, then the gauntlet.

## Output format
Produce exactly: 1 Title options (3, each with a number or a named thing); 2 Target platform and runtime (state
assumption); 3 Neuron (ID, one-line definition, posture); 4 Hook; 5 Full voiceover script; 6 On-screen text;
7 Visual direction; 8 Transferable move; 9 Closing line; 10 Source table (claim | source | status Verified / Estimate /
UNVERIFIED | notes); 11 Self-check (one neuron, factual status, banned words, tone); 12 Completion state.

## Visual direction
Use `faceless-visual-charge`: large-scale environments, isolation, edge-of-city imagery, hard light. Avoid soft stock,
generic desks, smiling handshakes, luxury clichés. Preferred metaphor: a switch, circuit, control panel or mechanical
system changing state.

## Default runtime
- Short (YouTube Shorts, TikTok, Reels): 45-60 seconds. The engine's gate is 175-200 spoken words in 11-14 beats; follow the gate.
- YouTube video: 3-5 minutes, about 500-850 words.

## Content map (backlog queue only; verify every claim first)
| # | Neuron | Subject | Lead in the report? |
|---|---|---|---|
| 1 | W1 | LeBron: equity versus immediate cash | thin: only his funds; the equity deals need fresh research |
| 2 | W4 | Short careers and the conversion window | yes, but the statistics are high-risk |
| 3 | W5 | Jay-Z: quiet wealth and ownership | yes |
| 4 | W3 | Shaq: franchises and cash flow | no: the report covers his endorsements only |
| 5 | W2 | Music masters and catalog ownership | yes (Taylor Swift) |
| 6 | W6 | Carnegie: stewardship and giving | yes |
| 7 | W1 + W4 | Jordan Brand versus endorsement income | yes, but the ownership claim looks wrong: verify first |
| 8 | W8 | Oprah: autonomy | no |
| 9 | W7 | Franklin: systems and printing franchises | no |
| 10 | W5 | Why quietly wealthy people may avoid visible spending | none; needs academic sources |
| 11 | W3 | Cash flow versus flex after income stops | none |
| 12 | W1 | The ownership question: "Do I own it?" | general; pair with a verified person |
Offense rows (1, 2, 4, 5, 7, 9, 11, 12) fill the offense slots first; neutral rows (3, 6, 8, 10) go in the explainer slot.

## Brand fit
Quiet Money does not teach people to shout about money. It teaches which switches change the outcome.

## Invocation
`/wealth-neuron-surgery W1 LeBron James YouTube 4 minutes`
