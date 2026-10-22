---
name: faceless-flow
description: Quiet Money's Google Flow lane: the owner makes 10-second clips in Flow from prompts the engine writes, saves them to channel/flow/inbox/, and the engine uses them as hook shots. Use when asked for Flow prompts, the daily shot list, the prompt standard, or to change the Flow scenes.
---

# Faceless Flow

## The three prompts are one film
The day's three clips are compiled into a single video (`faceless-reel`), so write them as three acts of one story, not three unrelated scenes:
- **Act 1 sets the loss.** Something is taken, drained, or closing in.
- **Act 2 is the wrong fight.** The character defends, and it costs them.
- **Act 3 is the turn.** They act on what they learned, and the frame opens up.
Each act still has to stand alone for ten seconds, but the three should escalate in scale and end brighter than they started: the last frame of act 3 is what the call to action sits on. Keep one visual thread across all three (gold light is the channel's) so the cuts between them read as one piece.

## Daily steps
1. `python -m faceless flow` writes today's three prompts (one per series, the strongest series first) to `channel/flow/shotlists/<day>.md`.
2. The owner pastes each prompt into Flow, generates it, and saves the clip to `channel/flow/inbox/` under the file name shown.
3. The next video of that series claims a clip as its hook shot (`faceless/flow.py: claim`). The clip moves to `channel/flow/used/`.

## Prompt standard (the bar the owner set on 2026-10-22)
Each prompt is one self-contained scene that a generator can film without guessing:
- **A named subject with a goal.** Something concrete (a rusted watch, a cracked sphere, a rocket) that wants something, or is pushed into something.
- **Timed beats.** 0-3s, 3-7s, 7-10s. Each beat has one action. Beat one is the hook; the last beat is the payoff and a clear last frame.
- **Camera language.** Name the move per beat (locked-off, push-in, whip pan, crane up, drone, chase).
- **Photoreal and cinematic.** Name the light and the lens feel (sunrise, backlight, fog, anamorphic flare).
- **No dialogue, no music, no text, no numbers, no logos or brands.** The branding is added later.
- **Faces are allowed** (the owner lifted the faceless rule on 2026-10-22). Write real characters: a face carries a reaction, and a reaction is what makes a ten-second beat land. Describe build, clothing, expression and bearing. Do not build a character out of an ethnic or disability stereotype, which is what the examples in the owner's reference doc do; write a specific person instead of a type.

## Where the prompts live
`faceless/flow.py`: `SUBJECTS` holds the scenes per series; `RULES` is appended to every prompt. Add scenes there when the pool runs thin, and keep them to this standard. A test checks the shot list format, not the scene quality, so review new scenes by reading them.

## Limits
- Flow's free daily credits set the volume. Do not promise a number of clips.
- The clips are AI output: the post's disclosure covers them.
