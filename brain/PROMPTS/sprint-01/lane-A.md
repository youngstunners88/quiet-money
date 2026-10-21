# Lane A manifest: offer and funnel (sprint 01, 2026-10-20)

Worker: Lane A. All five tasks done. Nothing was committed, pushed, published, posted or sent. No ad spend is assumed anywhere. No API key was seen or copied.

## Files written (all inside the lane's paths)

| Task | File |
|---|---|
| 1 | `channel/offers/sprint-01/CONVERSION-REVIEW.md` |
| 2 | `channel/offers/sprint-01/GUMROAD-PAGE-v2.md` |
| 3 | `channel/offers/lead-magnets/first-quiet-week/CONTENT.md` |
| 3 | `channel/offers/lead-magnets/monthly-money-snapshot/CONTENT.md` |
| 3 | `channel/offers/lead-magnets/spending-awareness-30/CONTENT.md` |
| 4 | `channel/offers/sprint-01/emails/1-delivery-first-quiet-week.md` |
| 4 | `channel/offers/sprint-01/emails/2-delivery-monthly-money-snapshot.md` |
| 4 | `channel/offers/sprint-01/emails/3-delivery-spending-awareness-30.md` |
| 4 | `channel/offers/sprint-01/emails/4-nurture-weekly-check.md` |
| 4 | `channel/offers/sprint-01/emails/5-nurture-planner-offer.md` (the one soft planner offer) |
| 5 | `channel/empire/PRODUCT-SUITE.md` |
| manifest | `brain/PROMPTS/sprint-01/lane-A.md` (this file) |

Files read first (all named in the brief): `CLAUDE.md`, `brain/PROMPTS/ORCHESTRATOR.md` sections 2, 6, 8; `channel/shop/catalog.json`; `channel/products/daily-quiet-money-planner/CONTEXT.md`; `channel/shop/daily-quiet-money-planner/gumroad/description.md` (and the other gumroad files, `report.md`, and the cover image); `channel/offers/money-reset-checklist.md`; every file in `channel/offers/autoresponder/` (README, sequence.json, emails 0 to 7); `channel/empire/MARKETING.md` (lines 1 to 381 of 615; the rest not needed for this lane); `channel/empire/RANKING.md`; `faceless/planner_content.py`, `faceless/product_planner.py` (day, check-in and reflect pages), `faceless/planner_wellness.py`; `faceless/offer.py` (the phrase rules); `faceless/shop.py` `md_to_html`; `brain/sources/*.md` product and pricing notes (humanoidgpt, mindvori, andrew, earningisnoweasy, kallaway) and `brain/topics/never.md`; `content/q1.txt` (weeks 1 to 4). I did not find `channel/empire/PLAN.md` content I needed beyond what MARKETING.md and RANKING.md give; I did not read it in full.

## Gates (exact results, run last after the final edit of each file)

Command: `python -m faceless offer check FILE`

| File | Result |
|---|---|
| `channel/offers/sprint-01/CONVERSION-REVIEW.md` | clean |
| `channel/offers/sprint-01/GUMROAD-PAGE-v2.md` | clean |
| `channel/offers/lead-magnets/first-quiet-week/CONTENT.md` | clean |
| `channel/offers/lead-magnets/monthly-money-snapshot/CONTENT.md` | clean |
| `channel/offers/lead-magnets/spending-awareness-30/CONTENT.md` | clean |
| `channel/offers/sprint-01/emails/1-delivery-first-quiet-week.md` | clean |
| `channel/offers/sprint-01/emails/2-delivery-monthly-money-snapshot.md` | clean |
| `channel/offers/sprint-01/emails/3-delivery-spending-awareness-30.md` | clean |
| `channel/offers/sprint-01/emails/4-nurture-weekly-check.md` | clean |
| `channel/offers/sprint-01/emails/5-nurture-planner-offer.md` | clean |
| `channel/empire/PRODUCT-SUITE.md` | clean |
| `brain/PROMPTS/sprint-01/lane-A.md` | refused (it lists the flagged words on purpose; internal manifest, not public copy) |

Several files were refused on the first run and fixed until clean (the gate flagged: the word the disclaimer uses for returns, "testimonial", "passive income", "get-rich", "countdown", and a FAQ question that contained "financial advice" without "not"). The fixes were rewording only.

Gate finding for the CEO (resolved; see CEO review): `offer check` refused the existing disclaimer when this lane ran. I ran it on two existing files and both are refused by the first rule in `offer.CLAIMS`: `channel/shop/daily-quiet-money-planner/gumroad/description.md` and `channel/offers/autoresponder/1-day1.md`. The footer text that causes it is the `FOOTER` constant at `faceless/autoresponder.py` line 21 ("... assumed returns that are never <the past participle of the pledge word>"), so all eight autoresponder emails fail the gate as generated, and the live planner description fails too. I did not touch those files (outside my paths). My new emails use "Examples use assumed returns that are not promised." instead. Suggest the CEO fix `FOOTER` and the description wording and regenerate. Resolved: the working-tree `faceless/offer.py` now exempts "never/not guaranteed", and `description.md` and `autoresponder/1-day1.md` both check clean.

Quote check (not a gate, but I did it): the twelve planner text strings (Day 1 to 5 lesson and task, the Day 6 and Day 7 prompts) were checked: ten match q1.txt exactly; the Day 2 lesson (placeholders filled) and the Day 6 prompt (prefix stripped, capitalised) match `planner_content.load()` output exactly. The wellness page was dropped from the sample (see CEO review).

## Numbers and their sources

Every printed number is traced in the tables at the end of `GUMROAD-PAGE-v2.md` and `PRODUCT-SUITE.md`, and in the header of each magnet file. Summary:
- `$1,825` and `$226,659` (Day 2 of the first-quiet-week sample): `python -m faceless.moneymath` fact sheet line "$5/day habit = $1,825/year; invested monthly at 8% for 30 years = $226,659", and `python -m faceless.moneymath future_value_monthly 152.0833333333333 0.08 30` returned 226658.83 (the planner prints $226,659). These are the same values `planner_content.fill()` produces for `{x:5,365}` and `{fv:5*365/12,8,30}`.
- `$1,800` ($15 a month for 10 years) and `$1,825` in spending-awareness-30: the same fact sheet.
- Page counts, price, refund, structure: `channel/shop/catalog.json`, `CONTEXT.md`, `faceless/planner_content.py`, `faceless/planner_wellness.py` (52 wellness entries), `faceless/product_planner.py`. The 10 front and back pages are 427 - 365 - 52, matching the ten items listed in `CONTEXT.md`.
- Suite net-per-sale figures: the fee formula and the $7.04, $11.39, $14.01, $15.75 nets are from `MARKETING.md` sections 0 and 3; $9.65 for $12 is my arithmetic on that formula (shown in the file).
- Outside figures: the $9.99 spreadsheet price is a creator's claim in a Brain note, labelled **U**. Audio file limits on Gumroad: not checked, labelled **U**.

## Choices I made without asking

1. **"The first weekly check-in" is Day 6.** The planner's weekly check-in is the Saturday page (kind S), which is inside days 1 to 7. The sample therefore has 7 day pages (Days 1 to 5 the daily pages, Day 6 the check-in, Day 7 the reflect page), a cover and a bridge page, 9 pages in all (the Week 1 wellness page was dropped in the CEO review). I did not add a separate check-in page.
2. **I quoted the planner's text exactly and added labelled "sample notes" outside the quotes**, for example Day 1's task refers to "the front of this book" (the net worth snapshot, page 3 of the book), which the sample does not contain.
3. **Added a wellness page to the sample** (week 1, poster position 1, "Time in nature", not in the `REVIEW` list) so the buyer sees what the 52 wellness pages are. Dropped in the CEO review: the poster picture itself prints cortisol and inflammation claims nobody has checked.
4. **Merge fields for the hosted PDFs.** The emails and the v2 page use `{{first_quiet_week_url}}`, `{{snapshot_url}}`, `{{tracker_url}}`. They are placeholders because no hosting URL exists; I invented no link. The only URLs in my files are the two already in the repo or the brief: the Money Reset page (`https://youngstunners88.github.io/quiet-money/money-reset/`, from `autoresponder/0-welcome.md`) and the live planner URL (`https://chrisclassroom4.gumroad.com/l/utwsfs`, from the brief).
5. **Footer.** I kept the autoresponder's tone and merge tags (`{{postal_address}}`, `{{unsubscribe_url}}`) and changed two things: "never <pledge word>" to "not promised" (gate), and the last footer line to name the magnet the person asked for.
6. **Email timing.** Delivery emails take the place of `0-welcome.md` (the welcome would repeat them) and the 7-day Money Reset continues at `1-day1.md` the next day. Nurture 1 is at day 8, nurture 2 (the one soft planner offer) at day 10. `MARKETING.md` C5 describes a single planner-offer email the day after day 7, which would be day 8. Mine puts a lesson first and the offer second, as the brief asked. If the owner prefers the plan's timing, send the offer on day 8 and drop nurture 1. Emails 1-4 and the day-10 offer timing need D9 widened; until then only the 7-day course and a day-8 offer email are inside the exemption.
7. **Nurture 1 is original text** (the ten-minute weekly check), not a planner quote, to avoid repeating the planner lessons that appear in the magnet or the existing sequence.
8. **Suite names.** I proposed renaming the existing Debt planner and Daily Planner to follow one pattern ("Quiet Money + job + Planner or Tracker") in the 4-SKU suite. Renaming a live listing is a change the owner has to approve.
9. **Python limitation.** The environment refused inline Python (`python -c`, heredocs) and compound shell commands. I filled the Day 2 placeholders by running `python -m faceless.moneymath` directly and checking against the fact sheet, and I did not call `planner_content.load()` itself. The quotes were verified by exact-string search of `q1.txt` instead. If the CEO wants belt and braces, run `load()[1].lesson` and compare it to the Day 2 block.

## Open questions for the owner or CEO

1. **Cover image and the AI-person mark.** The live Gumroad cover shows Quinton and has no mark on the picture; decision D11 asks for one. Picture change, owner approval.
2. **Hosting for the three PDFs.** The delivery emails cannot be used until the owner hosts the three files and fills the merge fields.
3. **Wellness posters.** `planner_wellness.REVIEW` (10 posters) is not complete: owner posters outside it and outside the softened set also print health claims on the picture (posters 1, 3 and 6, for example). All 40 owner posters need the owner's read, or a swap for typeset posters, before the listing describes them. The v2 page describes the wellness pages only as illustrated posters tied to a money habit, education only, and does not repeat any claim.
4. **"About ten minutes"** in the v2 page comes from the Etsy copy in the catalog; nobody timed the actions. Keep, or change to "one small action".
5. **"Not form-fillable"** in v2 FAQ 2 is based on finding no form-field code in `faceless/product_planner.py`; I did not test a built PDF.
6. **Gate vs. live copy.** Resolved: the gate now exempts "never/not guaranteed"; the live description and `autoresponder/1-day1.md` check clean.
7. **Suite.** Which of the proposed SKUs, if any, does the owner want built first? After the CEO review: nothing new before the planner's first sales and an X1 read; if a second ask is needed sooner, the already-built Debt planner.
8. **Which email timing** (see choice 6).

## What I would do next

1. (Resolved) The gate now accepts the existing disclaimer; no `FOOTER` or description change is needed for it.
2. Build `first-quiet-week` only (it is the plan's step 0b, `MARKETING.md` section 3) and have the owner host it. Hold the Monthly Money Snapshot and Spending Awareness 30 until the hub and email form show signups: at the 16 to 135 planner-page views the plan expects in 30 days (`MARKETING.md` section 4), more sign-up doors split the traffic too thin to tell which one works.
3. Have the owner read `GUMROAD-PAGE-v2.md` and approve the description as one change, then the cover mark 7 days later (X1).
4. When the owner picks an email service, paste emails 1 to 5 in with the delays above, and set up the suppression of existing buyers before the offer email goes out.
5. Pre-register how the free-to-paid step will be read (clicks on the planner link in email 5 and in the three magnet bridge lines) so it can be measured without guessing.
6. Do not build any of the five new products until the owner decides; the Debt planner (already built) is the second ask before any new build.

## CEO review (2026-10-21)

Review findings applied by the CEO pass, each checked against the file and its source first (poster images opened, `planner_content.load()` run, `python -m faceless.moneymath future_value_monthly 152.0833333333333 0.08 30` re-run: 226658.83). Not committed.

- `first-quiet-week/CONTENT.md`: wellness page removed (poster wellness-001 prints cortisol and inflammation claims on the picture), now 9 pages; picture rule, disclosure line and owner note 4 corrected; Day 2 gets an "Illustration, not a promise" sample note.
- `GUMROAD-PAGE-v2.md`: new first paragraph (no repeat of the summary); Saturday and Sunday pages shown as inside the 365 (no 531-page reading); spreadsheet pointer removed; wellness pages described as illustrated posters; FAQ 2 answers tablets; FAQ 4 drops "credit scores"; FAQ 8 answers "I tried budgeting and quit"; one listing change for the description, cover mark 7 days later; owner notes 1, 2, 3, 5, 8 corrected, note 9 (Week 18 credit wording) added; Day 1 source row corrected.
- `CONVERSION-REVIEW.md`: gate finding marked resolved; unsourced "five seconds" removed; description fixes ship as one change; `REVIEW` stated as incomplete (posters 1, 3, 6).
- Emails 1-4: D9 and consent-scope gate added to each Send line. Email 3: no "change nothing" clash with Money Reset Day 1. Email 5: Saturday-page bridge, sample link merge field, "week 1 of 52" line, commercial-identification footer line.
- `monthly-money-snapshot` and `spending-awareness-30`: bridges now describe what the planner really has; "seven one-off tasks" corrected to a seven-day list (18 tasks).
- `PRODUCT-SUITE.md`: ladder leads only to the $17 planner, Debt planner second; "build first" is nothing new, then the Debt planner; Debt cross-sell has no outcome framing; Start Here page corrected to Welcome page; Goal Planner notes `months_to_target` starts from zero.
- This manifest: gate table includes itself; gate finding, quote check (twelve strings), choices 1, 3, 6, open questions 3, 6, 7 and next steps 1, 2, 3, 6 updated.
