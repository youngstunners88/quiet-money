# Lead magnet: Spending Awareness 30 (free, a 30-day tracker, 4 pages)

DRAFT for the owner. Nothing here is published or hosted. File name when built: `Spending-Awareness-30.pdf` (US Letter, A4 copy optional).

**What it is.** A 30-day, one-line-a-day record of what you spend. The only goal is to see it. There is nothing to cut and nothing to judge until day 31.

**Who it is for.** Someone who suspects money "just disappears" but has never written it down for more than a few days.

**How it differs from what exists.** The Monthly Money Snapshot (the sister magnet) looks at a whole month after the fact. This one is a daily habit with a built-in guess-versus-real check. The planner's week 2 (`channel/products/daily-quiet-money-planner/content/q1.txt`, "Where it goes") is one week of tracking inside a 365-day book; this is a standalone 30-day sheet. It does not repeat the 60-Second Money Reset (`channel/offers/money-reset-checklist.md`), which is a seven-day list of one-off tasks, or the planner's 30-day wish list (week 4).

**Numbers on the pages.** Two worked examples on page 4, both from `python -m faceless.moneymath` (the fact sheet): "$5/day habit = $1,825/year" and "A $15/month subscription for 10 years = $1,800". Everything else is a blank.

Footer on every page: `Quiet Money | Educational content, not financial advice. | Designed by Quiet Money with AI assistance.`

---

## Page 1: How it works

Layout: US Letter portrait, header band in the planner's black and gold, then short blocks.

- Small line: QUIET MONEY
- Title: SPENDING AWARENESS 30
- Subtitle: Thirty days. One line a day. Just look.
- Block "The idea" (paragraph): Most people can name their rent. Few can name what they spent last Tuesday. For 30 days you write down what you spend, once a day, and mark whether it was planned. At the end you compare the real number with your guess.
- Block "Before day 1: your guess" (fill-in):
  - On an average day I think I spend  $__________
  - In a month I think I spend (not counting rent or loan payments)  $__________
  - Date I start: ____ / ____ / ____
- Block "The three rules" (numbered):
  1. Write it down the same day, at a time you pick (for example, before bed).
  2. Write everything, including the small stuff. Do not leave out things you are embarrassed about.
  3. Change nothing yet. This month is for looking, not for cutting.
- Block "What counts" (bullets):
  - Count: cards, cash, taps, one-click orders, subscriptions that charged you that day.
  - Leave out for now: rent or mortgage, loan payments and bills you set up long ago. (Add them up once, on page 4.)
- Block "How to fill a row" (small example, no numbers): Amount spent today, biggest purchase in a few words, P if you planned it or I if it was an impulse, and a 1 to 5 mood (1 = low, 5 = good).

## Page 2: Days 1 to 15

Layout: one table, 15 rows, large enough to write in. Column widths: Day (narrow), Date, Amount spent today $, Biggest purchase (a few words), P or I, Mood 1 to 5.

- Table heading: DAYS 1 TO 15
- Column headings: Day | Date | Spent today $ | Biggest purchase | P / I | Mood (1-5)
- Rows: 1, 2, 3 ... 15 in the Day column; the rest blank.
- Row 7 and row 14 are shaded and carry a small note in the Biggest purchase cell: Week check: circle the purchase you would make again. (Row 7 for week 1, row 14 for week 2.)
- Bottom of the page: Total for days 1 to 15  $__________   Number of I rows  ______

## Page 3: Days 16 to 30

Layout: same table, 15 rows.

- Table heading: DAYS 16 TO 30
- Column headings: same as page 2.
- Rows: 16 through 30 in the Day column; the rest blank.
- Row 21 and row 28 are shaded: Week check: circle the purchase you would make again. (Row 21 for week 3, row 28 for week 4.)
- Row 30 cell: Last day! Now turn the page.
- Bottom of the page: Total for days 16 to 30  $__________   Number of I rows  ______

## Page 4: The look back (do this on day 31)

Layout: header band, five short blocks, then the bridge.

- Title: DAY 31: THE LOOK BACK
- Block 1 "Real versus guess":
  - Total for 30 days (page 2 total + page 3 total)  $__________
  - Divide by 30 = my real average per day  $__________
  - My guess from page 1  $__________   Real minus guess  $__________
  - Hint (small grey): A big gap is the most useful result of the month. It is not a score.
- Block 2 "Planned or impulse":
  - Number of I rows in 30 days  ______  Total spent on I rows  $__________
  - Hint: Impulse is not bad. It is just the part you did not plan.
- Block 3 "Small things add up" (two worked examples, labelled as examples):
  - A $5 a day habit is $1,825 a year (5 x 365).
  - A $15 a month subscription for 10 years is $1,800.
  - Your turn: my real average per day  $__________  x 365 =  $__________ a year
  - Hint (small grey): These are examples of arithmetic, not predictions. Your own number is the one that counts.
- Block 4 "The fixed stuff" (the bills you left out): Rent or mortgage $______  Loan payments $______  Other fixed bills $______  Total fixed per month $______
- Block 5 "Three questions" (ruled lines under each):
  1. Which three purchases would I make again without a thought?
  2. Which three would I skip if I could redo the month?
  3. What is one small thing I will change next month, and when will I start?
- Closing strip: Money mood over the month (circle): 1  2  3  4  5

### Bridge line (the one line)
- Small box at the bottom of the page: **Every daily page of the Quiet Money Daily Planner keeps the habit you just used for 30 days in a small tracker (spent today, saved or paid down, how you feel about money 1 to 5) and adds a short lesson and one small action. 427 printable pages in US Letter and A4, $17, with a 30-day refund: https://chrisclassroom4.gumroad.com/l/utwsfs**

### Fine print
- Educational content, not financial advice. This tracker organises your own numbers; it does not tell you what to do with them.
- The examples use plain arithmetic. No result is a promise.
- Designed by Quiet Money with AI assistance.

---

## Notes for the owner and the builder

1. **Numbers.** $1,825 is 5 x 365; $1,800 is 15 x 12 x 10. Both appear in the `python -m faceless.moneymath` fact sheet ("$5/day habit = $1,825/year; ..." and "A $15/month subscription for 10 years = $1,800"). The 30 and 31 are days in the design, not data.
2. **No behavioural claims.** The page does not say tracking makes people spend less; I have no source for that. It says the goal is to look.
3. **Hosting.** The file must be hosted before the delivery email can link to it. The emails use the merge field `{{tracker_url}}`.
4. **Check:** page 2 and page 3 together have 30 rows (15 + 15).
