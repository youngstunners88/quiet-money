# The cast: how Penny and the Fee Gremlin work

Code: `faceless/pipeline/cast.py`. Reference art from the owner: `channel/brand-kit/character-reference/` (Penny pose sheet, the gremlin eating coins,
a poster of both). The characters are drawn as inline SVG parts and moved by GSAP inside HyperFrames; no image generator of any kind is used.
Every tween is `set`/`fromTo` on opacity, x, y, scale, rotation, width, height, visibility or strokeDashoffset, so any frame can be redrawn alone.

## Penny (the gold Q coin), `penny(pid, x, y)` -> (html, ids)
Local box 420x560, origin bottom centre. Parts you can move: `bd` body+face, `lgL`/`lgR` legs, `aL`/`aR` upper arms with `fL`/`fR` forearms nested inside
(two joints, so pointing, waving, hands-to-cheeks and a cheer are real poses), and inside the face `lk` (look left or right), `pu` pupils, `ey` closed lids,
`eh` half lids, `br` eyebrows (lift for surprise), `sw` sweat drop.
Mouths (word-timed lip sync picks by word length): `m0` closed smile, `m1` talk, `m2` small, `m3` gasp O, `m4` wide cheer, `m5` thinking flat line.
Look: a gold coin with a visible edge on the right, a soft rim and a highlight arc so she does not flatten on gold, big eyes, coral blush, thick rounded
gold limbs with a thin darker outline, a small Q on the rim (readable, secondary).
Helpers: `talk` (lip sync, varied blinks, glances; the blink rhythm differs per scene), `mood` (hold gasp/cheer/think), `arms` (pose both arms),
`walk` (legs and arms in opposition, a bob on each step), `bob`.

## The Fee Gremlin, `gremlin(pid, x, y)`
A hunched, round purple villain (cartoon, not horror) with a huge mouth of coin-shaped gold teeth. Parts: `bd` body+head, `jw` lower jaw, `bl` belly,
`aL`/`aR` grabbing arms. The eating beat has three frames per coin: approach (hops in and leans), bite (jaw opens, a coin leaps in, the jaw snaps),
swallow (belly bulges, the stack drops one coin). At most two gremlin scenes a video (`choose` enforces it).

## The nine scene types (`TEMPLATES`)
hero (Penny talks and waves; also the hook, below the caption band), stack (number counts up while coins stack and Penny cheers), fee (the gremlin eats the
stack; used for money that goes away: DROP, LOSS, COST, FEE), race (two coins race to lengths set by the two amounts), step (Penny presents a numbered board),
years (Penny walks while the years count), shock (hands to cheeks, brows up, shake), think (hand to chin, thought cloud with the phrase), sign (Penny points at
a five-word sign). Layout rule: characters above the caption band (y 360 to 1040), big type below it (1330+), nothing important between y 1070 and 1280.

## Rotation rules (`choose`)
Numbers get a number scene, a numeric face-off a race, `STEP n` a board, `N YEARS` a walk, money-draining words the gremlin (capped at two). Everything else cycles
hero, think, shock, sign. No neighbours share a template or a colour. Five colour schemes (`PALS`): navy, teal, ledger paper, money green, wine red; the gold
wipe between scenes and the coin belt keep it branded. (Gold pages were dropped because gold Penny disappeared on them.)

## Adding a second character
1. Write `newchar(pid, x, y) -> (html, ids)` the same way: parts as `part(...)` divs with `transform-origin` set, ids for everything a template will move.
2. Add its mouth/eye helpers or reuse `talk` by giving it the same ids (`m0`..`m4`, `ey`, `eh`, `lk`, `pu`).
3. Write one template that uses it, register it in `TEMPLATES`, and add it to `choose` with a rule for when it appears and a cap per video.
4. Render with `python -m faceless make --pillar ledger --no-publish`, look at a contact sheet (`ffmpeg -ss T -i final.mp4 -frames:v 1`), and add a test to
   `tests/test_drawn_series.py`. Do not add the character to the daily plan until the owner approves a sample (`[[pillars]] ledger enabled = false`).

## Not built yet
Lottie stickers, a falling curve instead of a rising one for drops (the gremlin now eats those numbers, so the case is covered), a character that stays across a
week of videos, Penny's mouth in more than the six shapes, and sound effects timed to the bite.
