# Craft lessons

Every rule the owner has taught, with the measured cause and where it is enforced. Newest at the bottom. A lesson cited
in `faceless/craftcheck.py` must exist here (a test checks this).

## L1: slow motion must be clean
- **Owner said:** the slow motion is not coming out clean (2026-10-22).
- **Measured cause:** slowing 24 fps footage repeated every second frame; per-frame change alternated 0.0, 10.3, 0.0, 7.6.
- **Rule:** slowed segments are rebuilt with optical flow, and the slow is 0.65, not 0.5. Jitter 4.4 to 1.5.
- **Enforced in:** `faceless/cineedit.py` (`SMOOTH`, `SLOW`); `tests/test_cineedit.py::test_slow_motion_is_interpolated_not_frame_doubled`.

## L2: master to the channel's loudness
- **Owner said:** (caught before the owner heard it) the first reel came out at -21.2 LUFS.
- **Measured cause:** no loudness pass on the reel mix; every other post is -14 LUFS.
- **Rule:** master to -14 LUFS, true peak -1.5, in two passes so the gain is linear.
- **Enforced in:** `faceless/reel.py` (`_master`); craftcheck L2.

## L3: the ending must not lose energy
- **Owner said:** the volume at the end is low (2026-10-22).
- **Measured cause:** at the cut into the CTA card the level fell to -27 LUFS against -14.6 in the acts (the card has no clip sound), and the closing line sagged 4 LU as it finished.
- **Rule:** the ending is its own act. Every narration line is levelled to the same loudness before the mix, the closing line gets +1.6 dB, the music bed swells under the card, and the card lands on a sound (a whoosh into the cut, a low impact on it, a coin ping as the coin appears).
- **Learned on the fix:** levelling and the bed swell alone still left a 10 LU hole for a breath at the cut, before the closing line began. The checker caught it on the second render; the sting closed it. A gap with nothing in it reads as an ending; a gap with a hit in it reads as a beat.
- **Enforced in:** `faceless/reel.py` (`VO_LUFS`, `CTA_VO_GAIN`, `CTA_BED_GAIN`, `card_sting`); craftcheck L3 (no hole at the cut, closing line as present as the act lines, ending within 4 LU of the acts).

## L4: the last sentence must land, not be cut off
- **Owner said:** it feels like the sentence got cut off (2026-10-22).
- **Measured cause:** 0.55 s between the last word and the end of the file; the music bed swelled back up as the duck released, then stopped dead on the last frame with no fade.
- **Rule:** the card lasts lead-in + the whole line + a 1.3 s hold; picture and sound fade out together over 0.7 s. Every act's line ends before its cut. (The same lesson as the daily videos' complete-ending gate.)
- **Enforced in:** `faceless/reel.py` (`card_seconds_for`, `END_FADE`); craftcheck L4.

## L5 (provisional): narration pace
- **Owner said:** nothing yet.
- **Measured cause:** the first reel's lines ran 3.1 to 4.1 words a second.
- **Rule:** a calm read is at most about 3.2 words a second; `craftcheck.word_budget` sizes lines at 2.6 a second.
- **Enforced in:** craftcheck L5 as WATCH only. Promote to a gate if the owner says the voice is rushed.

## L6: grade by brightness
- **Owner said:** (caught in frames before shipping) a night clip crushed to black and the impact flash blew it out.
- **Measured cause:** one grade for every clip; a 53-luma night scene crushed like a 105-luma day scene.
- **Rule:** the grade and the flash opacity are chosen from the clip's mean luma (day, dusk, night).
- **Enforced in:** `faceless/cineedit.py` (`grade_for`); `tests/test_cineedit.py`.

## L7: prompts need story, not scenery
- **Owner said:** the prompts were generic, static, no subject, no antagonist, no action, no drama (2026-10-22).
- **Measured cause:** prompts described a place and a camera move; nothing happened to anyone.
- **Rule:** every prompt has a protagonist with a goal, an antagonist or force against them, timed beats with one action each, explicit camera moves per beat, and a payoff in the last frame. See the owner's example document for the bar.
- **Enforced in:** `faceless-flow` skill, prompt standard.

## L8: the three daily clips are one film
- **Owner said:** compile the three into one video with a subtle voiceover leading to a CTA, and write future prompts knowing they will be joined (2026-10-22).
- **Rule:** the day's prompts are three acts (the loss, the wrong fight, the turn), escalating and ending brighter, with one visual thread. Narration and CTA are planned with the prompts, not after.
- **Enforced in:** `faceless-flow`, `faceless-reel`, `faceless-rhythm`.

## L9: faces are allowed
- **Owner said:** faces are allowed, every time (2026-10-22).
- **Rule:** write real characters with expression and bearing; a face carries the reaction that makes a 10-second beat land.
- **Enforced in:** `faceless-flow` skill.
