# Conversion review: The Quiet Money Daily Planner (live Gumroad page)

Reviewed 2026-10-20. Draft for the owner. Nothing here changes the live page; every fix needs the owner's yes (CLAUDE.md rule 9) and, per the marketing plan, listing changes go one per 7 days through experiment X1 (`channel/empire/MARKETING.md` C1).

What was reviewed (all repo files, no live fetch):
- Copy: `channel/shop/daily-quiet-money-planner/gumroad/description.md`, `summary.txt`, `name.txt`, `tags.txt`, `after-purchase.txt`, and the catalog entry `channel/shop/catalog.json` (id `daily-quiet-money-planner`).
- Pictures: `gumroad/cover.jpg` (1920x1080, opened and looked at), `gumroad/thumbnail.jpg`, `etsy/images/01-hero.jpg` to `09-notes.jpg` and `etsy/video.mp4` (file names and the build report `report.md` only; not opened one by one).
- Facts: `channel/products/daily-quiet-money-planner/CONTEXT.md`, `faceless/planner_wellness.py`.
- Live URL given in the brief: https://chrisclassroom4.gumroad.com/l/utwsfs. I did not fetch it, so this scores the repo copy, which the brief says is the live description.

Scale: 0 = missing or wrong, 1 = present but weak, 2 = does the job.

## Scorecard

| # | Criterion | Score | Why |
|---|---|---|---|
| 1 | Clarity of the promise | 1 | The first sentence is good and true: "One picture, one short lesson and one small action for every day of the year." But the second sentence is a 14-topic list that buries it, and nothing says what changes for the reader after a month. The summary line repeats the same promise, which is fine, but the page never says "start on any day" until the last clause of the second paragraph. |
| 2 | What is inside (true counts) | 1 | Has two PDFs, 427 pages, 365 daily pages, a weekly check-in, a reflect page, a glossary. But it still says "52 wellness-break pages" next to nothing that explains them, and the brief notes the older description said 40; the count is now 52 (`planner_wellness.POSTERS` has 52 entries, `check()` accounts for positions 1-56 minus 4 duplicates). It never shows what one daily page looks like in words (picture, lesson, a "Try this" box, notes, a spent/saved tracker). It does not say the net worth snapshot has five check-in columns, which the catalog does. |
| 3 | Who it is for (and not for) | 0 | No sentence names a reader. The first-screen question "is this for me?" is unanswered. It also never says who it is not for (people wanting investment picks, tax or country-specific advice, a spreadsheet, or a digital app). |
| 4 | Objections answered (FAQ) | 0 | No FAQ. Open objections a buyer has: "is 427 pages too much?", "do I have to print it?", "what if I start mid-year or skip days?", "is this US only?", "is it advice?", "can I use it on a tablet?", "what do I get, one file or two?", "what if I do not like it?". The refund is stated in two words ("30-day refund") and is the only objection handled. |
| 5 | Proof without fake proof | 1 | There is no review, sales count or quote from a buyer, which is correct: the product has no sales yet (`MARKETING.md` section 1). But there is also no honest proof at all. True proof we can show: the real Day 1 page text, the real first weekly check-in, a free sample week, the plain statement that every number comes from code (`faceless/moneymath.py`, quoted in the catalog as "Every example figure comes from tested money math"). The page uses none of them. |
| 6 | Visuals | 1 | The 16:9 cover is clear: title, the three chips (365 days, Letter + A4, Undated PDF), three real page mock-ups. Two problems. (a) The cover shows Quinton, the AI host. Decision D11 in `MARKETING.md` C1 says any cover, thumbnail or pin that shows him carries a conspicuous "AI-generated person" mark; the cover file has the face and no mark on the image (the disclosure is only in the description text). (b) On the cover the side pages are cropped; a buyer cannot read the lesson. Nine product images and a silent video exist for Etsy; the Gumroad create step uses images 2 to 6 as previews, so check that a "what is not inside" picture exists (the plan asks for one; I did not find one in the file list). |
| 7 | Price and refund | 1 | $17 is owner-approved on Gumroad (`MARKETING.md` section 3). The description says "30-day refund" but not how to ask, and does not say what $17 buys per page in plain words. The price is never mentioned in copy (Gumroad shows it), so there is nothing to fix there; the missing piece is one calm line that the refund is no questions asked (`catalog.json` `refund`: "30 days, no questions") and where to ask. |
| 8 | Disclosures (AI, not advice) | 2 | Both are present and in the right words: "educational tool, not financial advice; every number is an example with its assumptions stated" (plus a returns disclaimer) and "Designed by Quiet Money with AI assistance. The man on the cover is Quinton, the Quiet Money host, a virtual AI-generated character." Add: the 52 wellness pages are education, not medical advice (the pages carry that note in `planner_wellness.NOT_MEDICAL`; the listing should say so too). |

Total: 8 of 16.

Two further checks I made that are not scored:
- Phrase gate. At the time of the review (`faceless/offer.py` as committed, unchanged from 0117401 to HEAD ce50b38) the gate refused the disclaimer "returns are never guaranteed". The working-tree `offer.py` now exempts "never/not guaranteed", and `description.md` and `autoresponder/1-day1.md` both check clean. See "Gate finding" at the end (resolved).
- Scannability. The live description is three paragraphs and no subheads. A source note in the Brain (`brain/sources/2026-10-20-mindvori-claude-gumroad-spreadsheet.md`, claim 5) says short descriptions with subheads convert better. That is one creator's opinion, not data; treat it as a test, not a fact.

## Fixes in order of value

Order follows the plan's X1 rule (description first, then cover). Fixes 1, 2, 3, 4, 6 and 7 are all description text and ship together as one change. Value is my judgment of which gap loses the most buyers; it is not measured.

1. **Add "who it is for" and "who it is not for" as the first thing under the promise.** (criterion 3, score 0 to 2). A buyer decides quickly, on the first screen, whether the page is about them. The Brain note `2026-10-20-earningisnoweasy-claude-gumroad-basics.md` makes the same point for the first screen. v2 does this in two short paragraphs.
2. **Add an 8-question FAQ.** (criterion 4, 0 to 2). It answers the 427-pages worry, paper or tablet, mid-year start, US versus other countries, advice, files, refund and wellness pages. Written in `GUMROAD-PAGE-v2.md`.
3. **Replace the topic list with a "what a day looks like" block and a true "what's inside" list.** (criteria 1 and 2, 1 to 2). Uses the counts in the catalog and the 52 wellness pages. Drops the 14-topic run-on.
4. **Add honest proof: the free first-week sample.** (criterion 5, 1 to 2). The lead magnet `first-quiet-week` (written this sprint, `channel/offers/lead-magnets/first-quiet-week/CONTENT.md`) is the real Day 1 to 7 text and the first weekly check-in. A page that lets the buyer read the actual product is stronger than any adjective. The magnet is not hosted yet; the v2 page has a placeholder and an honest note that the link goes in only when it exists.
5. **Put the AI-person mark on the cover image.** (criterion 6). Needed by decision D11 regardless of conversion. This is a picture change for the owner to approve, not copy.
6. **Make the refund route and the price plain.** (criterion 7). One line: 30 days, no questions, reply to the Gumroad receipt or message the shop. Do not add a compare-at price or a "was" price: that would be a fake anchor (`brain/topics/never.md`).
7. **Add the wellness-pages medical-advice note to the listing.** (criterion 8). The pages already carry the note; the listing should match.
8. **Add one "what is not inside" image** (no investment picks, no tax filing, no app, no spreadsheet), per the marketing plan C1. Picture work for the owner.
9. **Check the cover's side pages are readable at thumbnail size**, or swap in one full Day 1 page as the second image. Lowest value, easiest to test later.

## Honest limits of this review
- No view or conversion data exists. The plan cannot read Gumroad page views through the API (`MARKETING.md` section 4, Measurement), so no score here is a measured conversion effect. It is a checklist against what a page needs.
- I did not fetch the live page. If the live text differs from `description.md`, rescore criteria 1 to 4.
- Traffic, not the page, is the stated binding constraint (`MARKETING.md` section 1). Fix 1 to 3 are cheap and safe, but do not expect them to move sales without visitors.
- `planner_wellness.REVIEW` is not complete. Owner posters outside it and outside the softened set also print health claims on the picture (for example poster 1, "reduces cortisol and boosts recovery"; poster 3, "yawning cools your brain"; poster 6, skipping "is gentler on your knees"). All 40 owner posters need the owner's read, or a swap for typeset posters, before the listing describes them. The code comment says the owner chose to keep the 10 `REVIEW` posters with the not-medical-advice note on every page. The v2 page does not describe any wellness claim; it says only that the pages are illustrated wellness posters, education only. That is an owner risk decision, not mine.

## Gate finding to pass to the CEO (resolved)
Resolved before the CEO review: the working-tree `faceless/offer.py` now exempts "never/not guaranteed" in the first rule of `offer.CLAIMS`, and `channel/shop/daily-quiet-money-planner/gumroad/description.md` and `channel/offers/autoresponder/1-day1.md` both check clean. No change to `FOOTER` or the live description is needed for the gate.
