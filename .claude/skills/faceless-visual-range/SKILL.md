---
name: faceless-visual-range
description: Expand and rotate the image range of Quiet Money stills so videos stop looking alike. Use whenever you write or review beat visuals (the `visual` and `look` fields), plan Flow stills, or when the owner says the images repeat, feel the same, or lack creativity and diversity. Gives a library of 24 look packs, subject and camera families, banned stock frames and a linter.
metadata:
  author: quiet-money
  version: 1.0.0
  code: tools/visual_range.py
  owner-order: 2026-11-04, "stop using the same kind of images ... create a skill to expand our prompt image range"
---

# Visual range

## Why the videos looked the same
`build_prompt` gives every video its pillar style plus one shared suffix (Kodak Portra, amber and teal). Then the beats reused the same stock frames: stormy sea with a lighthouse for every "honest catch", an empty highway for every closing beat, kitchen tables, coffee cups, old maps, stacks of gold coins. Different topics, one picture. A script's own `look` field **replaces** the style and suffix, so each video can have its own world.

## Rules
1. **One look pack per video.** Pick it with `.venv/bin/python tools/visual_range.py pick`, copy the text from `looks.json` into the script's `look` and its key into `look_pack`. Never the same pack as the last 8 scripts. A pack changes the medium (blueprint, clay, cut paper, woodblock, aerial, macro, neon night, stained glass...), not only the colors.
2. **Concrete subject per beat.** A beat's visual names a specific object, place or scene that carries that beat's idea (Blakely beat: a beige fax machine in a cramped cubicle, not "a desk"). If it could sit under any finance video it is too generic.
3. **No stock frames.** The linter fails the banned list (stormy sea, lighthouse, empty highway, kitchen table, coffee cup, notepad, magnifying glass, old paper map, brass calculator, ledgers, banker lamp, steel safe, open wallet, gold coin stacks, jars of coins, wooden table). The "honest catch" beat, the closing beat and the "not advice" beat each get a **new** image every video.
4. **Vary the camera inside a video.** Alternate scale and angle: extreme wide, macro, overhead, low angle, silhouette, long lens compression, aerial. Never three beats in a row at the same scale.
5. **Vary the subject family** across the 13 beats (see references/families.md): object, place, miniature, nature, architecture, machine, weather, craft, animal, abstract light. At most 3 beats of any one family.
6. **Brand guard rails stay:** no readable text or numbers inside the image, no real faces (backs, silhouettes, clay or felt figures are fine), gold is an accent not the whole palette, tension over noise ([[faceless-visual-charge]] rules still apply).
7. **Hook still** gets the strongest, most surprising image of the video. Closing beat is a new, quiet image, never the same sunrise road.
8. **Metaphor budget:** at most 4 literal-money images (coins, bills) per video; the rest are metaphors or settings from the story.

## Steps
1. `visual_range.py pick` for the look, write `look` + `look_pack` into the script.
2. Write 13 visuals using references/families.md: each a different subject, camera and scale.
3. `visual_range.py lint SCRIPT.json` must PASS before `tools/flow_stills_plan.py`.
4. Make the stills (faceless-flow-stills). Look at the contact sheet: if two stills could swap places, regenerate one with a new subject.
5. After shipping, nothing to log: the pack is read back from the script's `look_pack`, so `visual_range.py looks` shows how recently each was used.

## Check on the Flow model
Nano Banana follows medium words well ("cyanotype blueprint", "layered cut paper", "tilt-shift clay diorama"). It ignores long palette lists. Put the medium first, one subject second, one light or lens word last. Keep prompts under about 60 words so the suffix does not dilute the subject.

## Extending the range
Add a pack to `looks.json` (key, one sentence, medium first). Test one still in Flow before adding. Retire a pack the owner dislikes by deleting its line and noting it in memory.
