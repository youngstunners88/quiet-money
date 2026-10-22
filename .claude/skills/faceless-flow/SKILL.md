---
name: faceless-flow
description: Quiet Money's Google Flow lane: the owner makes 10-second clips in Flow from prompts the engine writes, saves them to channel/flow/inbox/, and the engine uses them as hook shots. Use when asked for Flow prompts, the daily shot list, the prompt standard, or to change the Flow scenes.
---

# Faceless Flow

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
- **No people's faces.** Use silhouettes, visors, helmets, creatures, or objects. This is the lane's rule; it keeps the channel faceless.

The stereotype and ethnicity-based characters in the owner's example document are not used here: they mock groups of people and the channel does not publish that.

## Where the prompts live
`faceless/flow.py`: `SUBJECTS` holds the scenes per series; `RULES` is appended to every prompt. Add scenes there when the pool runs thin, and keep them to this standard. A test checks the shot list format, not the scene quality, so review new scenes by reading them.

## Limits
- Flow's free daily credits set the volume. Do not promise a number of clips.
- The clips are AI output: the post's disclosure covers them.
