# Lead magnet: The First Quiet Week (free PDF, 9 pages, a true sample of the planner)

DRAFT for the owner. Nothing here is published or hosted. The file name when built: `The-First-Quiet-Week.pdf` (US Letter; an A4 copy if the owner wants one, built the same way as the planner).

**What it is.** The first seven days of The Quiet Money Daily Planner, word for word, plus the planner's first weekly check-in. A reader gets a real sample of the product, not a teaser.

**Where the words come from.** Week 1 of `channel/products/daily-quiet-money-planner/content/q1.txt`, read by `faceless.planner_content.load()` (the function that returns the 365 `Day` records). Days 1 to 7 are `load()[0]` to `load()[6]`:

| Day | Kind (`planner_content.KINDS`) | Title in the data |
|---|---|---|
| 1 | L, Learn | Start with the truth |
| 2 | N, By the numbers | The $5 rounding error |
| 3 | D, Do it | Find every account |
| 4 | M, Mindset | The ostrich effect |
| 5 | A, Action | Pick your tracking day |
| 6 | S, Weekly check-in (the first one) | prompt only |
| 7 | R, Reflect and reset | prompt only |

Day 2 has two computed numbers. In `q1.txt` they are the placeholders `{x:5,365}` and `{fv:5*365/12,8,30}`, which `planner_content.fill()` resolves with `faceless/moneymath.py`. I resolved them with the same code: `python -m faceless.moneymath future_value_monthly 152.0833333333333 0.08 30` returned 226658.83, which the planner prints as $226,659 (the fact sheet from `python -m faceless.moneymath` lists the same: "$5/day habit = $1,825/year; invested monthly at 8% for 30 years = $226,659"). `{x:5,365}` is 5 x 365 = $1,825 (same fact sheet line).

**Which page is "the first weekly check-in".** In the planner, the weekly check-in is the Saturday page, so the first one is Day 6 (kind S). It is inside days 1 to 7. The sample shows it as it is built in `faceless/product_planner.py` `checkin_page()`: the prompt, four money boxes, three wins, one thing to fix. Nothing extra is invented; the page after it is Day 7 (reflect and reset, `reflect_page()`).

**Rules for the builder.** Quote the quoted blocks below exactly. Do not edit a word inside a "Planner text" block. Text outside those blocks (the cover, the sample notes, the last page) is new copy written for this magnet. Page layout, fonts, colors and pictures follow the planner's own style lock (`channel/products/daily-quiet-money-planner/CONTEXT.md`, "The picture style lock"). The pictures are the planner's own Week 1 day pictures; the builder takes them from the same source the planner uses. No day picture contains text or a real person, and no wellness poster is used.

**Disclosures on this file.** The AI line ("Designed by Quiet Money with AI assistance.") is on page 1 and the last page; the not-advice line is in every footer. No AI-person mark is needed because no picture shows Quinton.

---

## Page 1: Cover and how to use it

Footer on every page of this file: `Quiet Money | Educational content, not financial advice. | The First Quiet Week`

Layout: black-and-gold cover (the planner's cover style, without Quinton, so no AI-person mark is needed on the picture; see note at the end). Title block, three short paragraphs, a "what is inside" strip.

Copy:

- Small line above the title: QUIET MONEY
- Title: THE FIRST QUIET WEEK
- Subtitle: Seven days. Seven small pages. The first week of the Quiet Money Daily Planner, exactly as it appears in the book.
- Paragraph 1: **How to use this.** Print it, or keep it open next to a notebook. Do one page a day. Each page takes about ten minutes. You do not need to start on a Monday: the book is undated, and so is this.
- Paragraph 2: **What you will find.** Day 1 to Day 5 are the five daily pages: Learn, By the numbers, Do it, Mindset, Action. Day 6 is the weekly check-in. Day 7 is the reflect-and-reset page. These are the real pages, not a mock-up.
- Paragraph 3: **A note on the numbers.** Every number in this week is a worked example with its assumptions stated. Rates in the examples are hypothetical. None of it is a promise about what money will do, and none of it is advice about your situation.
- Strip: DAY 1 LEARN | DAY 2 NUMBERS | DAY 3 DO IT | DAY 4 MINDSET | DAY 5 ACTION | DAY 6 CHECK-IN | DAY 7 RESET
- Small print at the bottom: Designed by Quiet Money with AI assistance. Educational content, not financial advice.

## Page 2: Day 1 (Learn)

Layout: the planner's day page (`day_page()`): header line, picture, kind chip, title, lesson, TRY THIS box, "My notes" ruled lines, tracker row.

Copy:

- Header left: DAY 001
- Header middle: WEEK 1 | WHERE YOU STAND
- Header right: Date ______ / ______ / ______
- Picture: the planner's Day 1 picture (motif `coin`).
- Chip: LEARN
- Title: START WITH THE TRUTH
- Planner text (lesson, exact):
  > Net worth is what you own minus what you owe. It can be negative, and that is a starting line, not a verdict. Most people have never written it down, so doing it once already puts you ahead of yesterday.
- Box label: TRY THIS
- Planner text (task, exact):
  > Fill in the Net Worth Snapshot at the front of this book. Round every number to the nearest $10 and do not judge any of it.
- Sample note (new copy, printed in small grey italics under the box): In the full planner the snapshot is page 3. In this sample, use the notes lines below: write what you own, what you owe, and the difference.
- Notes area label: My notes (ruled lines)
- Tracker boxes: Spent today $ | Saved or paid down $ | How I feel about money (1-5)

Source: `load()[0]` (`Day.title`, `Day.lesson`, `Day.task`).

## Page 3: Day 2 (By the numbers)

Layout: same day page.

Copy:

- Header: DAY 002 | WEEK 1 | WHERE YOU STAND | Date ______ / ______ / ______
- Picture: the planner's Day 2 picture (motif `stack`).
- Chip: BY THE NUMBERS
- Title: THE $5 ROUNDING ERROR
- Planner text (lesson, exact, numbers as filled by `planner_content.fill()`):
  > A $5 a day habit is $1,825 a year. Put the same money into an investment every month for 30 years at a hypothetical 8% a year and it becomes $226,659. Small and daily is how both costs and savings grow.
- Box label: TRY THIS
- Planner text (task, exact):
  > Write down one small thing you buy almost every day. Multiply its price by 365.
- Sample note (new copy, printed in small grey italics under the box): Illustration, not a promise. 8% is a hypothetical rate; real investments can earn less or lose money.
- Notes area and tracker: as Day 1.

Source: `load()[1]`. Numbers: `faceless/moneymath.py` (fact sheet line for the $5 a day habit).

## Page 4: Day 3 (Do it)

Copy:

- Header: DAY 003 | WEEK 1 | WHERE YOU STAND | Date ______ / ______ / ______
- Picture: the planner's Day 3 picture (motif `coin`; for kind D the motif is the week's first motif, `coin`).
- Chip: DO IT
- Title: FIND EVERY ACCOUNT
- Planner text (lesson, exact):
  > Money hides in places you forgot: an old savings account, a work retirement plan, a prepaid card, a refund you never claimed. You cannot manage what you cannot see.
- Box label: TRY THIS
- Planner text (task, exact):
  > Log into every account you have. Write each name and balance on one page so nothing hides from you.
- Notes and tracker: as Day 1.

Source: `load()[2]`.

## Page 5: Day 4 (Mindset)

Copy:

- Header: DAY 004 | WEEK 1 | WHERE YOU STAND | Date ______ / ______ / ______
- Picture: the planner's Day 4 picture (motif `grid`, the third motif of week 1 for kind M).
- Chip: MINDSET
- Title: THE OSTRICH EFFECT
- Planner text (lesson, exact):
  > Researchers use the name ostrich effect for the habit of not checking your accounts when you fear the news. Avoiding the number does not change the number. It only removes your chance to change it.
- Box label: TRY THIS
- Planner text (task, exact):
  > Check one balance you have been avoiding. Write the number here, then take one slow breath.
- Notes and tracker: as Day 1.

Source: `load()[3]`.

## Page 6: Day 5 (Action)

Copy:

- Header: DAY 005 | WEEK 1 | WHERE YOU STAND | Date ______ / ______ / ______
- Picture: the planner's Day 5 picture (motif `coin`).
- Chip: ACTION
- Title: PICK YOUR TRACKING DAY
- Planner text (lesson, exact):
  > Money work sticks when it has a time. Pick one weekday and a time, such as Sunday at 6 pm, and treat it like a standing appointment with yourself.
- Box label: TRY THIS
- Planner text (task, exact):
  > Choose your weekly money hour. Put it in your calendar with a repeating reminder.
- Notes and tracker: as Day 1.

Source: `load()[4]`.

## Page 7: Day 6, the first weekly check-in

Layout: the planner's check-in page (`checkin_page()`): header line with a "Week ending" date, picture, WEEKLY CHECK-IN heading with a gold rule, the prompt, a 2 x 2 grid of boxes, three-wins lines, one-thing lines.

Copy:

- Header left: DAY 006
- Header middle: WEEK 1 | WHERE YOU STAND
- Header right: Week ending ______ / ______ / ______
- Picture: the planner's Day 6 picture (motif `grid`, progress dots).
- Heading: WEEKLY CHECK-IN
- Planner text (prompt, exact; `load()[5].lesson`, which is the S line with its "Weekly check-in:" prefix removed and the first letter capitalised by `planner_content.parse()`):
  > How did looking at the real numbers feel, and which number surprised you most?
- Four boxes, each labelled: Money in this week $ | Spent this week $ | Saved or invested $ | Debt paid $
- Lines label: Three wins (any size) (three lines)
- Lines label: One thing to fix next week (two lines)

Source: `load()[5]` and `faceless/product_planner.py` `checkin_page()`.

## Page 8: Day 7, reflect and reset

Layout: the planner's reflect page (`reflect_page()`): header, picture, heading, italic prompt, ruled lines, "Next week I will" with three tick boxes, "Money mood this week" with circles 1 to 5.

Copy:

- Header left: DAY 007
- Header middle: WEEK 1 | WHERE YOU STAND
- Header right: Date ______ / ______ / ______
- Picture: the planner's Day 7 picture (motif `road`).
- Heading: REFLECT AND RESET
- Planner text (prompt, exact; `load()[6].lesson`):
  > What is one thing you now know about your money that you did not know seven days ago?
- Ruled lines for the answer.
- Label: Next week I will (tick when done) with three tick boxes and three lines.
- Label: Money mood this week with five circles numbered 1, 2, 3, 4, 5.

Source: `load()[6]` and `reflect_page()`.

## Page 9: What comes next (the bridge)

Layout: dark page, short text, one line to the planner.

Copy:

- Heading: YOU JUST DID WEEK 1 OF 52
- Paragraph: That is how the whole book works: one page, one small action, a check-in on Saturday and a reset on Sunday. If you did even two of the seven days, you know more about your own numbers than you did last week.
- Bridge line (the one bridge line): **If you want the other 51 weeks, the full Quiet Money Daily Planner is 427 printable pages in US Letter and A4, $17, with a 30-day refund: https://chrisclassroom4.gumroad.com/l/utwsfs**
- Small print: Designed by Quiet Money with AI assistance. Educational content, not financial advice. Every number is a worked example; rates are hypothetical.

(The URL is the live product URL given in the lane brief. If the owner adds a tracking tag, use the one the offer layer produces; do not type a tag by hand.)

---

## Notes for the owner and the builder

1. **No Quinton.** This sample does not use the planner's cover (it has Quinton, an AI-generated host). Using the coin cover avoids the need for the AI-person mark on the image (decision D11 in `channel/empire/MARKETING.md`). If the owner wants Quinton on it, the mark goes on the image.
2. **Day 1 mentions a page that is not in the sample.** The quoted task says "the front of this book". I kept the quote exact and added a labelled sample note instead of editing the planner's words.
3. **Hosting.** The file has to be hosted somewhere the owner controls before the delivery email can link to it. I wrote the link as the merge field `{{first_quiet_week_url}}` in the emails and the v2 page; nothing was invented.
4. **What is not here.** No review, sales count or buyer quote. No wellness poster: the Week 1 poster (wellness-001) prints cortisol and inflammation claims on the picture itself that nobody has checked, so the sample leaves it out until the owner has read it. If the owner wants a wellness example later, use only a studio-typeset poster (positions 45-56, `planner_wellness.MADE`) after reading the rendered image.
