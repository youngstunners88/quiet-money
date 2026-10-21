# Sprint 01, Lane B manifest: content and Brain (2026-10-20)

**Status: tasks 1, 2 and 4 done. Task 3 (the three skills) is drafted but NOT installed: the harness denied every write under `.claude/skills/`.**

## What was blocked, and why it matters
- The first write to `.claude/skills/faceless-product-hunter/references/scoring-rubric.md` was denied ("this session has no approval surface"), and the denial said that anything needing approval would be denied for the rest of the session. I did not retry it or write there another way (shell copy, heredoc), because that would route around the block.
- Also denied in this session: chained shell commands (`a && b`, pipes with a second command, heredocs), running a Python script I had written (`python -I state/brain/lane-b-scratch/gen_cal.py`), `python -c`, and quoted multi-line arguments. Each time I switched to single commands and the Write/Edit tools. Nothing was lost except the scratch script, which is unused (see below).
- Result: `python -m faceless skills` says `48 skills, 0 failure(s)`, which is the state without the three new skills. It cannot pass "for the new skills" until they are copied in.

## Files written
Brain (task 1, 2):
- `brain/sources/2026-10-20-unknown-starknet-repo-dive-starnet-skills-recipe.md` (the StarNet dive; speaker unknown)
- `brain/sources/2026-10-20-unknown-if-i-started-gumroad-from-zero-today-i-d.md` (Gumroad video 1, `#video-1`)
- `brain/sources/2026-10-20-unknown-this-new-claude-ai-method-makes-10k-a-mo.md` (Gumroad video 2, `#video-2`)
- `brain/sources/2026-10-20-levanto-video-maker--sagecut-cutting-video-qa-cost-with-the-s.md` (SageCut; speaker works for the vendor, stated in frontmatter and claims)
- `brain/topics/product-and-pricing.md`, `demand-research.md`, `organic-traffic.md`, `paid-traffic.md`, `tools.md` (new)
- `brain/topics/never.md` (10 rows added, each naming the note and timestamp where seen and the rule broken)
- `brain/INDEX.md` (rebuilt by `brain index`; the hand-written "This week" section was kept as is)
- `state/brain/raw/` (the four raw captures stored by `brain ingest`; git-ignored)

Content (task 4):
- `script-lab/ideas/calendar-2026-10-21.md` (30 days, 2026-10-21 to 2026-11-19)
- `script-lab/ideas/backlog.jsonl` (30 rows appended, source `calendar-2026-10-21`; 190 lines became 220)

Skills (task 3), not installed:
- `analytics/product-hunt/README.md` (written; what lands there and the file naming)
- Drafts in `state/brain/skill-drafts/` (git-ignored; copy them in): `faceless-product-hunter/SKILL.md` and `references/scoring-rubric.md`, `faceless-lead-magnet/SKILL.md`, `faceless-conversion-review/SKILL.md` and `references/rubric.md`.
- Scratch: `state/brain/lane-b-scratch/gen_cal.py` was a generator I could not run; the calendar and rows were written by hand instead. Safe to delete.

Side effect: `state/journal.jsonl` shows as modified; I believe `brain ingest` appended its line. I did not edit it.

## Gates and exact results
| Gate | Result |
|---|---|
| `python -m faceless brain check` | `9 note(s), 0 with problems` (run after all four notes and the topic pages) |
| `python -m faceless brain index` | `9 note(s) indexed in brain/INDEX.md` |
| `python -m faceless offer check script-lab/ideas/calendar-2026-10-21.md` | `clean` (first run refused the phrase "passive income" in one hook; I changed the hook, topic, description and keywords to "from investments" and re-ran) |
| `python -m faceless skills` | `48 skills, 0 failure(s)`; the three new skills are not in it yet (blocked). One existing warning, not mine: `faceless-keys` has no "use when" trigger |
| Skill drafts linted | NOT run (the linter reads only `.claude/skills/`). By reading: `name` equals the folder, each description has trigger words and no angle brackets, every `references/` file named exists in the draft folder, and every `python -m faceless COMMAND` named is in the CLI list (`brain`, `monid`, `offer`, `marketing`, `intake`). Please run `python -m faceless skills` after copying |
| `offer check` on the backlog rows | not run separately (blocked quoting); the hooks and angles are the same text as the clean calendar, except the passive-income row, which I changed in both |
| JSON validity of the 30 new backlog rows | checked by eye and by `Grep` (30 rows with the source tag, 220 lines in total); `python -c` was denied |
| `context`, `ci` | not run (outside this lane) |

To install the skills (needs write access to `.claude/skills/`):
`cp -r state/brain/skill-drafts/faceless-product-hunter state/brain/skill-drafts/faceless-lead-magnet state/brain/skill-drafts/faceless-conversion-review .claude/skills/` then `python -m faceless skills`. If the lint complains, the fix is in the draft text.

## Where each number comes from
- Calendar and backlog figures are all from the fact sheet, `python -m faceless.moneymath` with no arguments (run twice; the output was identical). Two escape rows also use facts from `channel/research/`: about 1 in 5 US businesses close in the first year (`hormozi.md`, BLS) and the 2012 bankruptcy (`kiyosaki.md`).
- In the Brain notes, every figure is the source's own and labelled S or U. Three figures come from repo files: $17 and the roughly $14 net per sale and the Etsy $1 to $13 prices (`channel/empire/MARKETING.md`), and "$20 spent per sale, $124.97" (the existing Humanoid-gpt note). No new arithmetic of my own is printed.
- SageCut's "$127 to 16 cents" and "1/10 the cost" are the vendor employee's claims, labelled U, and the note points out they do not match each other.

## Decisions I made (defaults, say if you disagree)
1. Gumroad video 1 is the same video as the earlier Humanoid-gpt note (same title, same $60 / three sales / $124 figures). I still wrote its own note because the owner's doc is a separate source with a 5-minute cut, and cross-referenced the old one instead of repeating its analysis. The channel is not named in this doc; I did not assert the earlier channel name.
2. Video 2 is cut at the 8,000-word cap (the last words of the outro). Frontmatter says so; `fetch_quality: full` because nothing relevant is missing. Change it to `partial` if you prefer.
3. Story days in the calendar are labelled hypotheticals ("imagine two coworkers"), not true stories, so no real person and no brief is needed. This departs from the story pillar's "true story" format; the writer must keep the "imagine" label. If you want real-person stories, they need briefs first.
4. Escape days (5) point only at free magnets and never at the planner, following the Rat Race rules in MARKETING.md. Hormozi and Kiyosaki appear only as the credited source of a framework, never in a hook, with briefs.
5. Planner days (7) are a proposal: the offer layer decides the real destination, and a paid link needs the listing URL in `[offer] shop_urls` (rule 13). Until the email service is live, "lead magnet: SLUG" is a note.
6. Backlog rows use the six keys `pillar, topic, angle, hook, brief, source` (no `demand`), which is what scout-made rows minus the score look like. If the engine needs `demand`, add it.

## Open questions
- Skills: can write access to `.claude/skills/` be granted to this lane, or should the CEO install the drafts? Which one?
- Is the Levanto Sage idea worth a measured test on a labelled frame set? It needs an owner-issued key (none is set), so I did not ask for one.
- The StarNet doc calls the planner "365-day"; the catalog says 427 pages. The Brain note says to use the catalog. The doc may want a correction on the owner's side.
- Lane A's `channel/offers/sprint-01/CONVERSION-REVIEW.md` records that the existing live description and the autoresponder footers end with a word that `offer check` refuses. The `faceless-conversion-review` draft says to report that rather than edit it. Not mine to fix.

## What I would do next
1. Install the three skills and run `python -m faceless skills`.
2. Run `faceless-product-hunter` once on one niche (budget printables) using only free sources, to test the rubric and fill `analytics/product-hunt/`.
3. Let `faceless-trends` read the calendar, and link the "lead magnet: SLUG" tie-ins once the email service is live (owner queue U04/U05).
4. Next Brain week: Wednesday routine (`brain watch`), and write the "This week" proposals in INDEX.md from the new notes: (a) keep Meta ads parked, (b) test the Ad Library as a free signal inside `faceless-product-hunter`, (c) measure Sage on labelled frames before any gate.

## CEO review (2026-10-21)
32 review findings checked against the raw transcripts, `python -m faceless.moneymath`, `faceless memory` and the repo; all 32 were real and all were fixed (two of them differently from the reviewer's suggested text, see below). Nothing committed.
- Brain notes and topics: misquotes in the four 2026-10-20 notes made verbatim or turned into paraphrase; claim 18 of Gumroad video 1 corrected (the 5:15 cut is a condensed version of the whole video); timestamps added to the Evidence quotes of both Gumroad notes, marking the cut or the full video; SageCut claims 6 and 8 and its Evidence quote 3 credited to the owner's summary of the vendor's skill, the null rule narrowed to yes/no, choice and tags, topics set to `[tools]` (there is no quality-gates page); never.md's mis-citations of MARKETING never-do 7 and 11 replaced with brain/CONTEXT.md Rules and ORCHESTRATOR.md section 2 (the same never-do 7 mis-citation was also fixed in the Reject sections of both Gumroad notes); its timestamps corrected; organic-traffic no longer ranks the five paths "by effort"; tools.md and the video 1 open question no longer say TokConnect has Ad Library tools.
- Calendar and backlog: decision 3 above is reversed. Story days are true stories that need a research brief (rule 8), so the four "Imagine" rows are gone. Those days now point at existing backlog story rows (lines 112, 152, 117, 156), each waiting on a `faceless-research` brief. Of the other 26 rows, 6 could never be picked (their topics score 0.8 or more against job history) and 17 repeated made videos. All of them were dropped, and the two that stayed (11-02, 11-07) got new hooks. The calendar now has 17 rows of its own, each under 0.55 against history and the rest of the backlog and checked with `faceless memory`. Nine days are open: four math, four escape and one myth. The reviewer's suggested fills for those slots ($500 a month for 20 years, the Value Equation's bottom half, OPR, the $900,000 rows) are already in made videos. The fact sheet and the three briefs have no fresh angle left for those pillars. One row uses numbers (11-14, from the fact sheet). No row says "guarantee" any more, and no row says "passive income".
- Skills: product-hunter gets the TokConnect tools it can actually call, how to read Gumroad, Etsy and the Meta Ad Library, and corrected rule citations. Lead-magnet must read the three existing magnets, never reuse a slug, and only point at a product with a live URL in `[offer] shop_urls`. Conversion-review takes the page count from `planner check` (427), never from `build.json` (365 days), gets exact listing paths and a review path, and follows X1's own start and close rule. In the README, a capped Monid pull no longer reads as needing the owner's yes.
- Left for the CEO (outside this lane's files): briefs for the four story rows; `brain/PROMPTS/ORCHESTRATOR.md` line 120 and the Humanoid-gpt note still mention a TokConnect "EU/UK ad library".
