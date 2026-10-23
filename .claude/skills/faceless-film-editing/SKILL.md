---
name: faceless-film-editing
description: The master film-editing skill for Quiet Money. Plans or reviews the cut of any video (a Short, a Flow clip, the reel, a long-form vibe, an AI clip) with classical continuity, montage theory and modern impact editing: establish, build, peak, aftermath; speed ramps into the hit, held frames, hard cuts, rhythm that pulses, sound as the invisible partner, grade and grain for weak AI footage. Use when asked to edit, cut, re-cut, pace, punch up, fix a flat or floaty AI clip, plan a timeline, or when a finished video feels flat, soft, or cut in the wrong places.
---

# Master film editing

You are the final author of rhythm, power and emotion. Editing is not cleaning footage: it is the last act of storytelling. Prefer clarity plus force over invisible smoothness when the material needs energy. Sources and the reading behind this skill are in `references/` (read them when a call is hard; the rules below are enough for most cuts).

## Every cut must earn one of five jobs
1. Advance the story or the feeling. 2. Build or release tension. 3. Land an impact. 4. Control rhythm. 5. Steer the eye. If a cut does none of these, remove it. Ask of each one: does this cut make the viewer feel more?

## The principles (apply all, in this order)
1. **Continuity and space.** Keep screen direction (the 180 line) unless breaking it on purpose to disorient. Match action across the cut, keep eyelines (looks left, the next shot implies the looker is off right), establish, then go closer, then return. Longer holds for wide, detailed shots, shorter for close ones: the eye needs time for detail.
2. **Rhythm.** Vary shot length on purpose. Short and sharp for intensity, long holds for awe or emotion. The edit has a pulse that rises and falls with the content. Metric montage: shortening shots shortens the time to absorb them, so tension rises.
3. **Impact framing.** Find the single strongest frame (the hit, the decision, the reveal). Land the cut on it or one beat before. Emphasise with a 2-6 frame freeze, a speed ramp or a push-in.
4. **Speed ramps.** Slow to 40-70% before the hit (anticipation), 150-300% through it, then normal or slightly slow for the reaction. Mandatory for any collision, explosion, fight or power moment. Not for talk.
5. **Montage and juxtaposition.** Meaning comes from the collision of two shots as well as their link (Kuleshov: the same face reads hungry, sad or joyful by what follows it). Use metric, rhythmic, tonal and intellectual montage deliberately; cross-cut parallel lines of action for suspense or a theme; a non-diegetic insert is allowed when it makes a point.
6. **Sound is the invisible partner.** Plan pre-lap and post-lap, impact sounds that land on the cut, silence before the big moment, layered low boom plus high detail. The voice and the bed never fight (see `faceless-rhythm`, `faceless-craft`).
7. **Colour, contrast, texture.** Crush the blacks a little, lift mid-tone contrast, add grain when AI footage looks too clean, split cool shadows and warm highlights for tension.

## Short-clip structure (6-15 s)
1. **Establish** 0.8-1.5 s: the situation or threat, clear. 2. **Build** 1-3 s: approach, stare-down, power-up. 3. **Peak** (the longest or most emphasised beat): hit, reveal, declaration. 4. **Aftermath** 1-2.5 s: reaction, debris, new status quo. Never let energy stay flat.

## Fixing the usual AI-video faults
| Fault | Fix |
|---|---|
| Floaty, weightless motion | ramp hard, cut on the hit |
| Morphing limbs or melting faces | cut away just before it shows |
| No contact, weak impact | freeze the impact frame plus a 2-frame flash |
| Soft, washed-out look | crush blacks, raise contrast, add grain |
| Boring wide framing | digital push-in or a hard crop to tighter |
| Predictable pacing | vary shot length sharply |

## Directives
Hard cuts over dissolves unless the moment is poetic or dreamlike. Jump cuts are allowed when they make energy or a state of mind. Never cut through the middle of a strong spoken line unless interrupting it is the point. An edit succeeds when the viewer forgets the cuts and feels the story.

## How it applies here
- **Shorts (61-72 s):** the hook is the establish and must be the strongest frame; one idea per beat; pace follows the voice; the last beat is aftermath plus the call to action.
- **Long-form vibes** (`faceless-vibe` method, `faceless/vibe.py`): cuts on the bar line, shot length follows the music's energy, a held breath before a peak, dissolves are right here because the form is dreamlike.
- **Flow clips:** run `python -m faceless cineedit` (impact ramp, grade, flash, brand mark); plan the timeline with this skill first.
- **Comics-to-Shorts:** reveal the setup, hold, land the punchline on a beat, a 6-frame hold on the laugh.

## Output format when asked to plan an edit
**Clip analysis** (strengths, weaknesses). **Editorial goal** (one sentence, the effect on the viewer). **Timeline** (beat by beat with seconds: 0.0-1.3 s ...). **Techniques** (ramps, cut types, framing, colour, sound). **Final polish** (grain, vignette, flash frames, particles, title). Then, after any cut, run the check in `faceless-craft` and record the owner's feedback as a rule.

## Never
Edit for smoothness alone. Cut the story's cause-and-effect. Copy text from the source books into a video or post. Use footage the studio has no right to use.
