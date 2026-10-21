# Lead magnet: The Monthly Money Snapshot (free, one page)

DRAFT for the owner. Nothing here is published or hosted. File name when built: `Monthly-Money-Snapshot.pdf` (US Letter, A4 copy optional). One printable page, meant to be copied once a month.

**What it is.** One page that answers four questions in about fifteen minutes: what came in, where it went, what is left, and whether the debt and net worth lines moved. It is a monthly companion to the planner's weekly check-in pages.

**Who it is for.** Someone who has never looked at a whole month at once. It asks for no software, no account and no bank login.

**How it differs from what exists.** The 60-Second Money Reset (`channel/offers/money-reset-checklist.md`) is a seven-day list of one-off tasks. The Money Reset Printables (`channel/shop/catalog.json`, id `money-reset-printables`, paid) are six separate pages. This is one free page you repeat monthly, so it never overlaps a one-off task.

**Numbers on the page.** None are computed. The page only has blanks and the arithmetic written as words (in minus out). The one reference figure, in the bridge, is the planner's own page count and price from `channel/shop/catalog.json`.

Footer on the page: `Quiet Money | Educational content, not financial advice. | Designed by Quiet Money with AI assistance.`

---

## Page 1 (the only page)

Layout: US Letter portrait. Black-and-gold header band (the planner's page style: Anton title with a gold rule), white body, one picture-free page so it prints cheaply (no large black areas). Six numbered blocks, then two lines of reflection, then the bridge. Print one page per month.

### Header
- Small line: QUIET MONEY
- Title: MONTHLY MONEY SNAPSHOT
- Right of the title: Month ______________   Year ________
- Under the title, one italic line: One page. About fifteen minutes. Round to the nearest $10 and do not judge any of it.

### Block 1: Money in
- Label: 1. MONEY IN THIS MONTH
- Line: Take-home pay (after tax)  $__________
- Line: Other money in (side income, refunds, gifts)  $__________
- Line: TOTAL IN  $__________
- Hint (small grey): Use what actually arrived in your account, not what you expected.

### Block 2: Where it went
- Label: 2. WHERE IT WENT
- A table with three columns: Category | $ spent | % of take-home pay
- Rows, one per line:
  - Housing (rent or mortgage, utilities)
  - Food (groceries and eating out)
  - Transport
  - Bills and subscriptions
  - Debt payments (minimums and extra)
  - Everything else
  - TOTAL OUT
- Hint (small grey): The percent column is the amount divided by your take-home pay, times 100. Do the big lines first.

### Block 3: The three numbers
- Label: 3. THE THREE NUMBERS
- Line: Total in minus total out = left over  $__________
- Line: Saved or invested this month  $__________
- Line: Debt paid above the minimums  $__________
- Hint (small grey): A negative "left over" is information, not a failure. Write it down anyway.

### Block 4: Net worth in one line
- Label: 4. NET WORTH IN ONE LINE
- Line: What I own  $__________   minus   what I owe  $__________   =   $__________
- Line: Last month's number  $__________   Up / Down / Same (circle one)
- Hint (small grey): Net worth is what you own minus what you owe. It can be negative.

### Block 5: One biggest line
- Label: 5. THE BIGGEST LINE
- Prompt: Which category in Block 2 was biggest, and was that your choice?
- Two ruled lines.

### Block 6: One change
- Label: 6. ONE CHANGE FOR NEXT MONTH
- Prompt: Pick one small change. Write it as an action with a number.
- Two ruled lines, then a tick box: [ ] I put this in my calendar.

### Closing strip
- Left: Money mood this month (circle one): 1  2  3  4  5
- Right: Date I did this: ____ / ____ / ____

### Bridge line (the one line)
- Small box at the bottom of the page: **Want the habit behind this page? The Quiet Money Daily Planner gives you one short lesson and one small action a day, and every Saturday a check-in with the same four numbers you just filled in: money in, spent, saved or invested, debt paid. 427 printable pages in US Letter and A4, $17, with a 30-day refund: https://chrisclassroom4.gumroad.com/l/utwsfs**

### Fine print
- Educational content, not financial advice. This sheet organises your own numbers; it does not tell you what to do with them.
- Designed by Quiet Money with AI assistance.

---

## Notes for the owner and the builder

1. **No invented numbers.** There are no example figures on the page. If the owner wants a filled example, build it from `faceless/moneymath.py` and label it as an example.
2. **Print-friendly.** No full-page dark areas. The planner's black-and-gold style is kept only in the header band.
3. **Hosting.** The file must be hosted before the delivery email can link to it. The emails use the merge field `{{snapshot_url}}`.
4. **Categories.** The five spending boxes (housing, food, transport, bills, everything else) are the same five boxes the planner uses in week 2 (`channel/products/daily-quiet-money-planner/content/q1.txt`, Day 8); this sheet adds a debt row so the three numbers can include debt paid above the minimums.
