---
name: faceless-reel
description: Compile the day's three Flow clips into one video with a voiceover that threads them and lands a call to action. Use when asked to stitch, compile, join or combine the daily clips, to add the CTA, or to put narration over the Flow footage.
---

# Faceless reel

## What it is
The day's three clips are not three posts. They are three acts of one film, joined by `faceless/reel.py`: each clip is edited by `faceless-cineedit`, the acts are dipped through black, and one quiet narration line per act carries the viewer to a CTA card.

## Run it
```python
from faceless import reel
reel.build(
    [{"src": clip, "impact": 8.9, "line": "..."}, ...],
    out, cta_line="One money rule a day. Follow Quiet Money.",
    bed=Path("assets/music/escape-1.mp3"))
```
`impact` is the peak second in each SOURCE clip (see `faceless-cineedit`: read a contact sheet, never guess it from the prompt). Returns the act start times, where the CTA lands, and every spoken line with its length.

## Writing the narration
- **One line per act, and the line is the thread, not the show.** It sits under the action and explains nothing the picture already says.
- **Six to ten words.** Any longer and it is still talking when the next act cuts.
- **The three lines are one sentence of an argument,** ending where the CTA begins: the loss, the mistake, the turn. The CTA line then asks for the follow and nothing else.
- **No claim a number has to back.** The offer claim rules apply here as everywhere (`faceless-offer`): no income promises, no returns.
- The voice is the channel's configured narrator (`[voice] elevenlabs_voice`, currently a deep calm read), kept deliberately low in the mix.

## The ending is an act (lessons L3, L4)
The card has no clip sound, so it lands on a sting (whoosh into the cut, low impact, coin ping as the coin appears), the music bed swells under it, and the closing line is levelled like every other line and lifted 1.6 dB. The card lasts the lead-in, the whole line and a 1.3 s hold (`card_seconds_for`), then picture and sound fade out together. Never let the file end on a live sound.

## The mix
Clip sound keeps the hits at `CLIP_GAIN`, the music bed fills the gaps at `BED_GAIN`, and both duck to let the narration through only while it speaks (`sidechaincompress`). A limiter catches the peaks. Raise `BED_GAIN` before raising the voice: if the voice has to be loud to be heard, the bed is too busy.

## Rules
- **Run the craft loop on every reel** (`faceless-craft`): `python -m faceless craftcheck <reel> --report <build.json>`, look at a contact sheet and listen to the ending. The reel ships regardless; every `FIX` goes into the code or skill before the next one.
- **Size the narration from the act lengths** with `craftcheck.word_budget` (`faceless-rhythm`).
- **Never stretch an act to fit the narration.** Cut the words instead.
- The clips are AI output: the post's disclosure covers them.
