---
name: faceless-flow-cinematic
description: Quiet Money's cinematic Flow lane: three 10-second, captionless, high-energy AI clips a day, written as prompts for the owner's Google Flow (free daily credits), then branded by the engine. Use when asked for the cinematic series, Flow prompts, the daily three clips, or to edit clips the owner saved into channel/flow/cinematic/inbox.
---

# Faceless Flow cinematic

## What it is
Three 10-second vertical clips a day, made by the owner in Google Flow from prompts the engine writes. No captions are added to the clips themselves. Quiet Money branding (gold Q coin, Anton and Montserrat Black, the handle) is added when the engine edits them.

## Daily steps
1. `python -m faceless flowcine` prints today's three prompts and writes `channel/flow/cinematic/shotlists/<day>.md`. `python -m faceless flowcine status` lists what is waiting in the inbox.
2. The owner pastes each prompt into Flow, generates the clip, and saves it to `channel/flow/cinematic/inbox/` as `<NN>-<anything>.mp4`, where NN is the shot number.
3. When clips are waiting, the engine (or you) edits each one: brand overlay, Quiet Money end card, and the disclosure line in the post description. Move the source clip to `channel/flow/cinematic/used/` once it has shipped.

## Rules for prompts (they decide whether the clip is watched)
- **Not boring.** Every prompt needs a hook in the first second, one big reveal or transformation in the middle, and a strong last frame. A slow pan of a still scene fails this test.
- **Ten seconds only.** Each beat has to earn its time. If a prompt cannot show its change within ten seconds, cut it.
- **No text, letters, numbers, logos, brands, human faces, dialogue or music** (the generator would add them; the branding goes on later).
- **Rotate.** `flowcine.pick` never repeats a scene within four days; add new scenes to `SCENES` when the pool runs thin.
- **Theme.** Money as escape: gold, time, distance, the door that opens. Stay on the channel's idea without drawing a person.

## Limits
- Flow's free daily credits set the volume. Do not promise a number of clips.
- The clips are AI output: the post's disclosure covers them, as it does for the other Flow lane (rule in `faceless-flow`).
