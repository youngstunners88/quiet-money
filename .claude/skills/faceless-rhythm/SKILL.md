---
name: faceless-rhythm
description: Rhythmic flow for Quiet Money's videos, and the two-way link between writing and editing. Use when planning, scripting, editing or compiling any video (Flow prompts, narration, the reel, the daily batch), when a cut, a pause or an ending feels wrong, or when choosing how long a line, an act or a hold should be.
---

# Faceless rhythm

## The principle
Writing, editing and the mix are one instrument played in three passes. An edit can only be as good as the material it is given, so the script is written for the cut, and what the edit learns changes how the next script is written. When a piece feels wrong, look for the rhythm fault first: a beat that arrives too early, a breath that is missing, a line that is still talking when the picture has moved on.

## Rhythm in the edit
- **Every act has a curve:** establish, build, the hit, release. The hit is the most emphasised beat, never in passing (`faceless-cineedit`).
- **The piece has a curve too.** Acts escalate, and the piece ends at a high point, not a dip. The ending is its own act with its own energy: it needs sound under it, a line that lands, and a held beat (lesson L3, L4).
- **Cut on the beat, speak after it.** A cut lands on an action or just after a hit; narration starts about 0.45 s after the cut, never on it, so the eye arrives before the ear.
- **Breaths are short and deliberate.** A dip to black between acts is about 0.2 s: a breath, not a transition anyone notices.
- **Silence is a beat, an empty gap is not.** A short drop before the biggest hit makes it land; a gap with nothing in it after the last hit reads as the piece dying. Put a sound on every cut that has no clip sound behind it (L3).
- **Hold after the last word.** At least a second of held frame and sound after the final line, then picture and sound fade out together. A hard stop on a live bed reads as a chopped sentence (L4).
- **Speed changes are rhythm, not decoration.** Slow into the hit, snap through it, ease out. Keep slowed footage clean (L1) and keep ramps inside 0.5x to 2x.

## Writing for the edit (the script side)
Write knowing how the piece will be cut:
- **Budget every line by its slot.** `craftcheck.word_budget(seconds)` gives the most words a line can carry in a slot of that length at a calm pace (2.6 words a second, after the lead-in and before the next cut). A line that does not fit is rewritten shorter, never sped up.
- **The last line is written to be held.** Eight words or fewer, ending on a strong word, with nothing after it that needs saying. The card holds on it.
- **The CTA is an act,** written with the other lines, not bolted on: the act lines make one argument, and the CTA is its conclusion.
- **Narration is the thread, not the show.** It says what the picture cannot: the meaning, not the action.
- **Prompts are written for the ramp.** Ask the generator for the peak between 7 and 9 seconds of a 10-second clip, so there is room to build into it and release after it. In a set of three, each act's peak should be bigger than the last.

## The order of work
1. Write the three prompts as acts (`faceless-flow`), with the peak placed for the ramp.
2. When the clips arrive, find each real peak from a contact sheet (the generator rarely puts it where the prompt asked).
3. Size the narration from the actual act lengths after the ramp (`word_budget`), then write it.
4. Edit and compile (`faceless-cineedit`, `faceless-reel`).
5. Assess (`faceless-craft`): measure, look, listen. Whatever the edit had to fight goes back into steps 1 and 3 as a rule.

## What the edit has taught the script so far
- The closing line needs room after it, so it is short (L4).
- The ending has no clip sound under it, so the narration there must be the strongest read of the piece (L3).
- Lines that run past their cut feel rushed even when their pace is fine; size them to the act, not to the sentence you want to say (L4, L5).
