---
name: faceless-craft
description: The learning loop for Quiet Money's creative work: assess every finished video, edit, script or prompt against what the owner has taught so far, turn each piece of owner feedback into a measured rule, and update the owning skill in the same change. Use after producing any creative deliverable, whenever the owner gives feedback on one ("too quiet", "cut off", "boring", "not clean"), and before shipping a reel.
---

# Faceless craft: the learning loop

## What this is, honestly
Nothing here retrains a model. The improvement lives in two places that persist between sessions: the **checks** in `faceless/craftcheck.py` and the **skills** that write prompts, scripts and edits. So the loop only works if every lesson lands in one of them. A lesson kept in a chat reply is lost; a lesson written into a skill or a check is kept for every future piece.

## The loop (run it on every creative deliverable)
1. **Measure.** `python -m faceless craftcheck <video> --report <build.json>`. Every confirmed rule is a gate; provisional rules are reported as `WATCH` and never block.
2. **Look and listen.** A number is not taste. Read a contact sheet (`ffmpeg -i v.mp4 -vf "fps=1,scale=200:-1,tile=14x2" -frames:v 1 sheet.png`) and the loudness curve over the ending. Ask what the owner would say first, using `LESSONS.md`: if a past lesson would have caught it, it is a regression.
3. **Fix the cause, not the instance.** A defect goes back to the code or the skill that produced it. Re-rendering with a hand tweak teaches nothing.
4. **Record.** Append the lesson to `LESSONS.md` (format below), add a check to `craftcheck.py` when it can be measured, and update the skill that owns the decision. All three go in the same commit as the fix.
5. **Ship only when nothing blocks.** Then tell the owner what the checks caught that they would otherwise have heard.

## Turning owner feedback into a rule
The owner speaks in effects ("the end is low", "it feels cut off", "the slow-mo isn't clean"). The job is to find the measurable cause behind the effect before changing anything:
- **Reproduce it in numbers.** "Low at the end" became a momentary-loudness trace that showed a 12.5 LU hole at the last cut and a closing line sagging 4 LU. "Cut off" became 0.55 s between the last word and a hard stop on a rising music bed.
- **Write the rule as the cause, not the symptom.** Not "make the end louder" but "the card is its own act: the bed swells under it and it holds 1.3 s after the last word."
- **Check the checker.** Run the new check on the piece the owner complained about: it must fail. Then on the fixed piece: it must pass. A check that passes the bad version is miscalibrated (this happened with the first hole-at-the-cut threshold).

## Confirmed and provisional rules
- **Confirmed** = the owner said it, or it is a platform fact (loudness standard). These are gates.
- **Provisional** = a rule inferred from a measurement the owner has not reacted to. Report it as `WATCH`; promote it only when the owner confirms or a later complaint traces back to it. Never block a piece on a rule the owner has not validated.
- Never weaken or delete a confirmed rule without the owner. Tighten freely when a check proves too lenient.

## Updating skills autonomously
When a lesson is confirmed, update the owning skill without asking: `faceless-flow` (prompts), `faceless-script` (narration), `faceless-rhythm` (pacing and the script-edit link), `faceless-cineedit` (per-clip edit), `faceless-reel` (compile, mix, ending). Write the rule where the decision is made, cite the lesson number, and keep the skill short: replace an old rule rather than stacking a contradicting one under it. `python -m faceless skills` must stay clean.

## LESSONS.md format
`## Ln: short name` then four lines: **Owner said** (the words or the effect), **Measured cause**, **Rule**, **Enforced in** (file and check, or the skill line). Keep the newest at the bottom; never rewrite history, add a later lesson that supersedes it instead.

## The ledger
Every craftcheck run appends to `state/craft.jsonl` (piece, passed, blocking failures, watch items). Fewer blocking failures per piece over time is the measure of whether this loop is working.
