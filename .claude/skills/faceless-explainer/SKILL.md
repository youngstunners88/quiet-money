---
name: faceless-explainer
description: Make a Quiet Money video in the explainer look, one drawn world with diagrams timed to the spoken words (a fork, bars that grow, a ring that fills, a timeline, a big number), no characters, no generated pictures. Use when the owner asks for a motion-graphics or Showhow-style video, a code-drawn explainer, or to build a story such as the LeBron McDonald's script in this look.
metadata:
  author: quiet-money
  version: 1.0.0
  source: owner's Google Doc "Creating Katana open" (2026-10-31); ideas from sirioberati/showhow credited, no code taken (intake verdict PARK, repo-farm/intake/2026-10-31)
---

# Explainer look

The look the owner asked for on 2026-10-31, replacing the Penny / Fee Gremlin cast (retired: its one measured video got 2 views, median 15.5; `studio.toml` pillar `ledger` is `enabled = false`).
Night navy world, brand gold, Anton and Montserrat Black. One grid drifts under every scene so the video reads as one camera move. Each element appears on the word that names it.
It costs nothing: no image model is called. It renders with HyperFrames like the motion cards (`faceless/pipeline/explainer.py`, Node 22 and ffmpeg).

## Make a video
1. Script by `faceless-script` (and `wealth-neuron-surgery` for a person's story). Set `"look": "explainer"` on the script.
2. Give every beat a `scene` object (below). A beat without one gets a number card (numeric callout) or a phrase card.
3. `python -m faceless make --pillar story --topic "<exact topic>" --script <path> --no-publish`, then read the gauntlet report and look at frames (contact sheet at 3 and 4.7 s into every scene).

## Scene vocabulary
| type | use it for | fields |
|---|---|---|
| `fork` | a choice between two paths (open the video on one) | `left`, `right` each `{label, value, sub, word}`; `pick` = `left` or `right` (the gold path) |
| `stat` | one number, optionally a second | `value`, `label`, `word`; `value2`, `label2`, `word2` |
| `bars` | two or three values compared (heights are to scale) | `items` of `{label, value, text, word}` |
| `ring` | a share of a whole | `percent`, `text`, `label`, `word` |
| `timeline` | dated events on an axis | `events` of `{year, label, word}`, `active` |
| `versus` | a flat line against a rising one | `left`, `right` `{label, sub, word}` |
| `phrase` | the rule, in big type | `lines`, `hl` (words in gold) |
| `catch` | the honest catch | `lines`, `hl` |
| `end` | the closing question and FOLLOW | `text` |
`word` is a spoken word the element waits for; without it the elements spread across the beat. Keep bars honest: never scale a 1% share up to look big.

## Rules
- The first scene is lit on frame zero (the gauntlet's `first_frame_visible` gate is hard): open on `fork` or `stat`, never a fade from black.
- Facts on screen are the brief's facts, with "reported" or "estimate" kept in the label. A number that is an estimate says so on screen.
- No faces, no logos, no text in pictures: nothing is a photograph.
- Keep scenes above the captions (content sits between y 260 and 1100; captions use the band below).
- Add a scene type only when two scripts need it; take new chart types from `repo-farm/intake/2026-10-31/decisions.md` (slope chart, 2x2 matrix, venn).
