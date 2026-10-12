---
name: faceless-song-art
description: Write the cover-image prompts for Quiet Money's daily song packs: one absurd, impossible, Inception-level scene per song that makes a viewer stop and drift. Covers the creative method, the variety rules (no repeated motifs, no repeated framing), the banned-motif list, and the prompt template with the safety tail. Use when writing or rewriting a song cover image prompt, when a morning batch needs new art, or when the owner says the artwork is trash or repetitive.
---

# Faceless song art

Every song pack gets one cover scene. The scene is the first thing a stranger sees, so it has to hold attention for three seconds and then reward a second look. The bar: someone should drift and stare, and want to know how it was made.

## The method
1. Start from one idea from the song, then push it past physics. Ask what the impossible version of the feeling looks like: a house on a whale's back, a painting that paints itself, a sea held in a hand.
2. Pick one impossibility and commit to it. Good impossibilities: scale (a whole city on an animal), nesting (a world inside a breath, a canvas inside a canvas), gravity turned over, a loop with no seam, time running backward in one corner, a reflection that disagrees with the thing it reflects.
3. Add two or three small true details the eye can rest on: a streetlamp between ribs, a moth in a corridor, paint drips floating upward. Specific beats generic.
4. Give the light a source and a mood, and limit the palette to two or three named colours.
5. Name the camera (lens and angle) so the image has a composition, not just a subject.

## Variety rules
- Never repeat a motif already used in `music/packs/` (check the folder first). Each pack must differ from the others in subject, scale, and impossibility type.
- Rotate impossibility types: scale, nesting, gravity, loop, time, reflection. Do not use the same type twice in one day.
- Rotate camera distance: one wide, one macro, one from below or above.
- Keep it bold and specific. A prompt that could be a stock photo is rejected.

## Banned motifs (already used; do not reuse)
Kitchen table in a flood; lantern in a black-glass desert; broken chain at dawn; a runner on a frozen highway; a mountain staircase in clouds; a rain street with a split skyscraper; a floorboard Penrose loop; a gravity-flipped city under a sea; a salt plain of mirror shards with a swing; a folding city; a pocket watch of gears; a bathtub of stars; a blue whale carrying a city; a glass hand holding a sea; a recursive painting.

## Safety tail (every prompt, exactly)
End with: `No text, no letters, no logos, no visible faces.`
Faces are never shown. Silhouettes from behind, hands, objects and places are allowed.

## Template
```
[Impossibility, one sentence, 9:16]. [Two or three specific details]. [Light source and mood, 2-3 colours]. [Lens and camera angle]. 8K, [print/poster]. No text, no letters, no logos, no visible faces.
```

## Checks before a prompt ships
- Could a viewer name the impossibility in one sentence? If not, sharpen it.
- Does it differ from every pack in the same day and the banned list? If not, change the subject and the impossibility type.
- Does it end with the safety tail?
- Does the image do something a photo could not? If not, push further.

## Where it goes
The songs desk (`faceless/songs.py`) writes the cover prompt into `image-prompt.txt`, `pack.json` and `SUNO.md` block 4. This skill is the standard the writer follows; when the owner rejects art, rewrite the prompt here first, then the pack files.
