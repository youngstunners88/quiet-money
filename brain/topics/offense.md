# Offense: why the George Foreman Short worked, and what to copy

Our own brain surgery, written 2026-10-30 from the 2026-10-29 snapshot (68 Shorts). Numbers come from
`analytics/snapshots/youtube-2026-10-29.json`; the posture labels are hand-assigned in `tools/posture-audit.py`
(run it to reproduce). Small samples are signals, not facts. No retention data exists yet, so every "why" below is
a reading of the script, not a measurement of viewer attention.

## The finding
A video puts the viewer on **offense** (someone makes a move that creates upside) or **defense** (avoid, cancel,
protect, escape a trap). 59% of our Shorts are defense, and they do worse.

| Posture | Shorts | Median views | Mean | At 5 views or fewer |
|---|---|---|---|---|
| Offense | 13 | 25 | 41 (26 without Foreman) | 2 |
| Neutral / explainer | 15 | 16 | 27 | 3 |
| Defense | 40 | 13 | 18 | 11 |

The backlog repeats the skew: a rough keyword read of the 249 queued ideas finds about 85 defense, 12 offense, the
rest mixed. Left alone, the engine keeps making more of what works worst.

What the numbers do not say: offense might simply be correlated with a number or a named person in the title, which
we already know helps. The honest test is the mix in `channel/CONTENT-MIX.md`, measured at the checkpoints there.

## Autopsy: "How George Foreman Turned a Kitchen Appliance Into $138M" (229 views, more than double our best defense Short at 104)
Read from `script-lab/final/2026-10-26-s10-story-george-foreman-s-royalty-play-th.json`.
1. **A named person at a fork, in the first line.** "In 1994, a retired boxer chose between upfront cash and a 45%
   profit share." Character, a year, a risk and two priced options before second 3.
2. **The fork is already a forced choice.** Cash or equity. The viewer picks a side before the script answers, which
   is the same move as the ending question we want comments on.
3. **A head fake.** "You'd assume guaranteed cash is safer." The script says the obvious answer out loud, then
   reverses it (Kallaway step 3 in `sources/2026-10-20-kallaway-addiction-loop.md`).
4. **The protagonist acts.** He "took zero dollars upfront, demanding a 45% split". The viewer rides along on a bet.
   In defense videos the viewer is the victim and nobody acts.
5. **A number ladder on screen.** 45%, then 100M units, then $138M, then $200M+. Each callout is larger than the last,
   so the picture keeps paying off even with the sound off.
6. **A second payoff after the first.** The $138M buyout lands, then "his total royalty bet paid over $200 million".
   A re-hook near the end, not one reveal.
7. **One transferable rule, in offense wording.** "Always seek equity and upside." Defense endings say "stop
   losing"; this one says "take the bet".

## Counter-evidence we must respect
- A named person is not enough. Ruin stories flop: Nicolas Cage 6, the $100M fortune that froze 4, William Post
  19 (n = 3, median 6). Win stories do better: Foreman 229, the 1993 Volvo billionaire 176, Grace Groner 16, the
  janitor 17 (n = 4). Both are signals. The pattern is "someone makes a bold move and it pays", not "a famous name".
- Grace Groner's "$180 move" (16) is patience, not attack. Offense here means a bet or a negotiation, not waiting.
- Foreman has no research brief, so its facts rest on the judge alone. New named-person offense videos need a brief
  in `channel/research/` first (CLAUDE.md rule 8).

## What "attack" means here, and what it never means
Offense is the viewer's own bold move: take equity over a fee, ask for the raise, build the asset, make the
offer, buy the thing that compounds. It is never attacking another person or business. `topics/never.md` already
bans pick-on-the-little-guy, review attacks and cloning small sellers; this page does not reopen that.
Risk stays on screen: every offense script keeps its honest catch and promises no result.

## The offense recipe (use in script-lab)
1. Open on a person, a year, a fork and a price on each side.
2. Say the safe answer, then break it.
3. Show what they did, in the active voice.
4. Callouts climb: each number bigger or sharper than the last.
5. Land the payoff, then open a second one.
6. Close on one offense rule and a question the viewer can answer in a comment.
7. Keep the catch: what it cost, what could have gone wrong, why most people would not.

## Next experiments
- E1: 2 offense Shorts a day for two weeks against the 13-video baseline (median 25). Pass: median above 25 on at
  least 20 posts. Kill: no lift, return to the old mix.
- E2: flip test on defense backlog items. Rewrite "avoid the X trap" as "the move that makes X work for you".
  Compare the flipped pairs.
- E3: when retention exports exist, check whether offense wins in the first 3 seconds or in the second payoff.
