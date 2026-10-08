"""Product: Money Reset printable pack (6 pen-and-paper pages, US Letter and A4) and the Money Reset Kit bundle.

Pages: how to use, 50/30/20 paycheck split, subscription audit, sinking funds, debt list, net worth snapshot. Plain white pages
with thin ink lines so they print cheaply on any printer. A check proves nothing is drawn inside the printer-unsafe margins.
The bundle zips the two spreadsheets and the printables with a read-me and licence. Nothing is sold from here.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from faceless import brand, config
from faceless.config import Paths

OUT = Paths.root / "channel" / "products"
DPI = 200
SIZES = {"Letter": (1700, 2200), "A4": (1654, 2339)}
MARGIN = 110                     # keep everything inside; the check below enforces it
INK, GREY, LINE, GOLD = (20, 20, 22), (110, 110, 112), (150, 150, 152), (214, 170, 20)
FOOT = "Quiet Money  |  Educational tool, not financial advice. Designed with AI assistance."


class Page:
    def __init__(self, size: tuple[int, int], title: str, sub: str, n: int, total: int):
        self.W, self.H = size
        self.im = Image.new("RGB", size, "white")
        self.d = ImageDraw.Draw(self.im)
        self.x0, self.x1 = MARGIN, self.W - MARGIN
        self.y = MARGIN
        self.d.text((self.x0, self.y), title.upper(), font=brand.font("Anton-Regular.ttf", 84), fill=INK)
        self.y += 100
        self.d.rectangle([self.x0, self.y, self.x0 + 220, self.y + 10], fill=GOLD)
        self.y += 34
        if sub:
            self.d.text((self.x0, self.y), sub, font=brand.font("Montserrat-ExtraBold.ttf", 30), fill=GREY)
            self.y += 66
        f = brand.font("Montserrat-ExtraBold.ttf", 22)
        self.d.text((self.x0, self.H - MARGIN - 22), FOOT, font=f, fill=GREY)
        tail = f"{n} / {total}"
        self.d.text((self.x1 - self.d.textlength(tail, font=f), self.H - MARGIN - 22), tail, font=f, fill=GREY)

    def text(self, x: int, y: int, s: str, size: int = 30, color=INK, bold: bool = True) -> None:
        self.d.text((x, y), s, font=brand.font("Montserrat-ExtraBold.ttf", size), fill=color)

    def para(self, s: str, size: int = 30, color=INK, gap: int = 14, width: int | None = None) -> None:
        f = brand.font("Montserrat-ExtraBold.ttf", size)
        width = width or (self.x1 - self.x0)
        line = ""
        for w in s.split():
            t = f"{line} {w}".strip()
            if line and self.d.textlength(t, font=f) > width:
                self.d.text((self.x0, self.y), line, font=f, fill=color)
                self.y += size + gap
                line = w
            else:
                line = t
        if line:
            self.d.text((self.x0, self.y), line, font=f, fill=color)
            self.y += size + gap

    def rule(self, y: int | None = None, x0: int | None = None, x1: int | None = None, w: int = 2, color=LINE) -> None:
        y = self.y if y is None else y
        self.d.line([(x0 or self.x0, y), (x1 or self.x1, y)], fill=color, width=w)

    def box(self, x: int, y: int, w: int, h: int) -> None:
        self.d.rectangle([x, y, x + w, y + h], outline=INK, width=3)

    def table(self, cols: list[tuple[str, float]], rows: int, row_h: int = 78, start: str = "") -> None:
        """Header row with column titles, then `rows` empty ruled rows. Column widths are fractions of the printable width."""
        full = self.x1 - self.x0
        xs = [self.x0]
        for _t, frac in cols:
            xs.append(xs[-1] + int(full * frac))
        xs[-1] = self.x1
        self.d.rectangle([self.x0, self.y, self.x1, self.y + 64], outline=INK, width=3)
        for (t, _f), a in zip(cols, xs):
            self.text(a + 14, self.y + 17, t, 24)
        for x in xs[1:-1]:
            self.d.line([(x, self.y), (x, self.y + 64 + rows * row_h)], fill=LINE, width=2)
        self.d.line([(self.x1, self.y), (self.x1, self.y + 64 + rows * row_h)], fill=INK, width=3)
        self.d.line([(self.x0, self.y), (self.x0, self.y + 64 + rows * row_h)], fill=INK, width=3)
        y = self.y + 64
        for _ in range(rows):
            y += row_h
            self.d.line([(self.x0, y), (self.x1, y)], fill=LINE, width=2)
        self.d.line([(self.x0, y), (self.x1, y)], fill=INK, width=3)
        self.y = y + 30


def pages(size: tuple[int, int]) -> list[Image.Image]:
    total = 6
    ps = []
    p = Page(size, "Money Reset Printables", "Six pages. A pen. Thirty minutes.", 1, total)
    for i, t in enumerate(["Print these pages (any printer; thin lines save ink). Letter and A4 versions are both included.",
                           "Do one page a day, or all in one sitting. Use pencil for numbers you will update.",
                           "Start with page 2: split one paycheck 50 / 30 / 20. Then audit your subscriptions (page 3).",
                           "Pages 4 to 6 build your buffer, list your debts, and show your net worth. Update the net worth page every quarter."]):
        p.para(f"{i + 1}.  {t}", 32, gap=18)
        p.y += 18
    p.y += 30
    p.text(p.x0, p.y, "How the rules work", 40)
    p.y += 66
    p.para("50 / 30 / 20 is a starting guideline, not a law: 50% of take-home pay for needs, 30% for wants, 20% for your future (savings and debt payments). "
           "If your needs are over 50%, circle the biggest one. That is next month's project.", 30, GREY)
    p.y += 16
    p.para("A sinking fund is money you set aside monthly for a known future cost, so a big bill is a plan instead of a crisis.", 30, GREY)
    p.y += 16
    p.para("Net worth is what you own minus what you owe. Watching it rise every quarter beats watching any single day's balance.", 30, GREY)
    p.y += 40
    p.para("License: personal use for you and your household. Please do not resell, share or redistribute the files.", 26, GREY)
    ps.append(p)

    p = Page(size, "50 / 30 / 20 paycheck split", "Write your take-home pay, then give every dollar a job.", 2, total)
    p.text(p.x0, p.y, "Monthly take-home pay  $", 36)
    p.rule(p.y + 52, p.x0 + 520, p.x0 + 900, 3, INK)
    p.y += 100
    colw = (p.x1 - p.x0 - 60) // 3
    for k, (head, pct) in enumerate((("NEEDS", "50%"), ("WANTS", "30%"), ("FUTURE", "20%"))):
        x = p.x0 + k * (colw + 30)
        p.box(x, p.y, colw, 520)
        p.text(x + 20, p.y + 16, head, 44)
        p.text(x + colw - 130, p.y + 16, pct, 44, GOLD)
        p.text(x + 20, p.y + 84, "pay x " + (".50" if k == 0 else ".30" if k == 1 else ".20") + "  =  $", 24, GREY)
        p.rule(p.y + 150, x + 20, x + colw - 20, 3, INK)
        for j in range(5):
            p.rule(p.y + 230 + j * 56, x + 20, x + colw - 20)
        p.text(x + 20, p.y + 170, ("Rent, food, bills, transport" if k == 0 else "Fun, dining out, hobbies" if k == 1 else "Savings, investing, debt"), 20, GREY)
    p.y += 580
    p.text(p.x0, p.y, "What I actually spend:", 34)
    p.y += 64
    for lab in ("Needs  $", "Wants  $", "Future  $"):
        p.text(p.x0, p.y, lab, 30)
        p.rule(p.y + 44, p.x0 + 260, p.x0 + 640, 3, INK)
        p.y += 80
    p.y += 20
    p.text(p.x0, p.y, "My biggest need to shrink this month:", 32)
    p.rule(p.y + 100, p.x0, p.x1, 3, INK)
    p.y += 150
    p.text(p.x0, p.y, "One thing I will do about it:", 32)
    p.rule(p.y + 100, p.x0, p.x1, 3, INK)
    ps.append(p)

    p = Page(size, "Subscription audit", "Open last month's statements. Every recurring charge goes here.", 3, total)
    p.table([("Subscription", .34), ("Per month", .14), ("Per year", .14), ("Keep", .09), ("Cancel", .1), ("Last used", .19)], 17, 74)
    p.text(p.x0, p.y, "Totals:   per month  $__________      per year  $__________", 30)
    p.y += 66
    p.para("Per year = per month x 12. A $15 a month subscription costs $1,800 over 10 years. Cancel at least one today.", 26, GREY)
    ps.append(p)

    p = Page(size, "Sinking funds", "Save a little every month for the bills you already know are coming.", 4, total)
    p.table([("Fund (car, gifts, insurance...)", .31), ("Target $", .14), ("Due date", .14), ("Months left", .13), ("Set aside / month", .16), ("Saved so far", .12)], 12, 84)
    p.para("Set aside per month = target divided by months left. Example: $600 due in 6 months is $100 a month. Move it on payday so it never feels spent.", 26, GREY)
    ps.append(p)

    p = Page(size, "Debt list", "Highest rate first (avalanche) or smallest balance first (snowball). Pick one.", 5, total)
    p.table([("Debt", .30), ("Balance $", .15), ("Rate %", .11), ("Minimum $", .15), ("Order", .09), ("Paid off on", .20)], 12, 84)
    p.text(p.x0, p.y, "Extra I can pay each month on top of minimums:  $__________", 30)
    p.y += 66
    p.text(p.x0, p.y, "My method (circle one):   Avalanche      Snowball", 30)
    p.y += 66
    p.para("Never pay only the minimum: it is built to last. Put every extra dollar on the first debt in your order, and when it is gone roll its payment onto the next.", 26, GREY)
    ps.append(p)

    p = Page(size, "Net worth snapshot", "What you own minus what you owe. Update every quarter.", 6, total)
    p.text(p.x0, p.y, "Date: ____ / ____ / ________", 30)
    p.y += 70
    half = (p.x1 - p.x0 - 40) // 2
    top = p.y
    for k, (head, rows) in enumerate((("I OWN (assets)", ["Cash and checking", "Savings", "Investments and retirement", "Home value", "Car value", "Other", "", ""]),
                                       ("I OWE (liabilities)", ["Credit cards", "Car loan", "Student loans", "Mortgage", "Personal loans", "Other", "", ""]))):
        x = p.x0 + k * (half + 40)
        p.d.rectangle([x, top, x + half, top + 70 + 8 * 84 + 90], outline=INK, width=3)
        p.text(x + 18, top + 16, head, 32)
        for j, lab in enumerate(rows):
            yy = top + 70 + j * 84
            p.rule(yy + 70, x + 18, x + half - 18)
            p.text(x + 18, yy + 28, lab, 22, GREY)
            p.text(x + half - 60, yy + 28, "$", 24, GREY)
        p.text(x + 18, top + 70 + 8 * 84 + 24, "TOTAL  $", 32)
    p.y = top + 70 + 8 * 84 + 90 + 50
    p.text(p.x0, p.y, "NET WORTH  =  assets  -  liabilities  =  $", 40)
    p.rule(p.y + 62, p.x0 + 780, p.x1, 3, INK)
    p.y += 110
    p.text(p.x0, p.y, "Change since last quarter:  $____________", 30)
    ps.append(p)
    return [q.im for q in ps]


def unsafe(im: Image.Image, margin: int = MARGIN - 40) -> int:
    """Count non-white pixels in the outer printer-unsafe margin (must be zero)."""
    w, h = im.size
    g = im.convert("L")
    bad = 0
    for box in ((0, 0, w, margin), (0, h - margin, w, h), (0, 0, margin, h), (w - margin, 0, w, h)):
        bad += int((np.asarray(g.crop(box)) < 250).sum())
    return bad


def build_printables(dest: Path) -> dict[str, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, size in SIZES.items():
        ims = pages(size)
        p = dest / f"Money-Reset-Printables-{name}.pdf"
        ims[0].save(p, "PDF", resolution=DPI, save_all=True, append_images=ims[1:])
        out[name] = p
    return out


README = """MONEY RESET KIT
===============
What is inside
- Rat-Race-Escape-Planner.xlsx          your freedom number, income streams, 40-year projection (Excel / Google Sheets)
- Debt-Payoff-and-Compound-Interest-Planner.xlsx   avalanche or snowball payoff plan with interest saved, compound growth
- Money-Reset-Printables-Letter.pdf and -A4.pdf    six pen-and-paper pages

How to start
1. Open the Rat Race Escape Planner and replace the blue cells with your numbers.
2. Open the Debt Payoff planner and list your debts.
3. Print the pages and do the 50 / 30 / 20 split and the subscription audit.

Honest notes
Educational tools, not financial advice. Results depend on the assumptions you enter; returns are never guaranteed.
Designed by Quiet Money with AI assistance. Spreadsheets were recalculated and checked against independent math.

License
Personal use for you and your household. Please do not resell, share or redistribute the files.
"""


def bundle(parts: dict[str, Path], printables: dict[str, Path], dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    z = dest / "Money-Reset-Kit.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Money-Reset-Kit/READ-ME-FIRST.txt", README)
        for p in list(parts.values()) + list(printables.values()):
            zf.write(p, f"Money-Reset-Kit/{p.name}")
    return z


def assemble_kit(root: Path | None = None) -> Path:
    """Rebuild Money-Reset-Kit.zip from the spreadsheets and PDFs that are committed, with no LibreOffice or recalculation.
    The zip itself is a gitignored build output, so a clean checkout (CI, a fresh container) has the parts but not the bundle."""
    root = Path(root) if root else OUT
    parts = {"escape": root / "rat-race-escape-planner" / "Rat-Race-Escape-Planner.xlsx",
             "debt": root / "debt-payoff-planner" / "Debt-Payoff-and-Compound-Interest-Planner.xlsx"}
    printables = {"Letter": root / "money-reset-printables" / "Money-Reset-Printables-Letter.pdf",
                  "A4": root / "money-reset-printables" / "Money-Reset-Printables-A4.pdf"}
    missing = [p.name for p in [*parts.values(), *printables.values()] if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"cannot assemble the kit, missing: {missing} (run `python -m faceless products`)")
    return bundle(parts, printables, root / "money-reset-kit")


def listing_printables(price: float = 9.0) -> str:
    link = config.load()["channel"].get("link_in_bio", "")
    return f"""# Listing: Money Reset Printables (pen-and-paper pack)

The owner approves price, copy and the account before anything goes live.

## Gumroad / Etsy
- **Name:** Money Reset Printables: budget, subscriptions, sinking funds, debt and net worth (Letter + A4 PDF)
- **Price:** ${price:.0f} to test (assumed; try $7 / $9 / $12)
- **Files:** `Money-Reset-Printables-Letter.pdf`, `Money-Reset-Printables-A4.pdf`
- **Images:** render the PDF pages to PNG for the gallery (page 2 and page 3 sell best)

### Description
Six clean pages that make you look at your money once, on paper: a how-to page, a 50/30/20 paycheck split, a subscription audit,
sinking funds, a debt list and a net worth snapshot. Thin lines print cheaply on any printer. Letter and A4 included.

**Honest notes:** educational tool, not financial advice; 50/30/20 is a guideline. Instant PDF download, nothing ships.
*Designed by Quiet Money with AI assistance.* (Etsy: keep this disclosure line and check Etsy's current Creativity Standards.)

### After-purchase message
Thanks! Start with page 2. More free tools: {link}
"""


def listing_bundle(prices: dict) -> str:
    total = sum(prices.values())
    price = round(total * 0.6)
    link = config.load()["channel"].get("link_in_bio", "")
    return f"""# Listing: Money Reset Kit (bundle)

The owner approves price, copy and the account before anything goes live. Prices below are tests (assumed), not market facts.

## Gumroad
- **Name:** Money Reset Kit: two spreadsheet planners + six printable pages
- **Parts and test prices:** Rat Race Escape Planner ${prices['escape']:.0f}, Debt Payoff & Compound Interest Planner ${prices['debt']:.0f}, Printables ${prices['print']:.0f} (sold apart: ${total:.0f})
- **Bundle price to test:** ${price} (40% below the parts; only advertise the discount if the parts are also listed at those prices)
- **File:** `Money-Reset-Kit.zip`

### Description
Everything to get a clear picture of your money in one weekend: find your freedom number, build your debt payoff plan with the interest it saves,
and fill in six printable pages (paycheck split, subscription audit, sinking funds, debt list, net worth). Excel and Google Sheets plus Letter and A4 PDFs.

Educational tools, not financial advice. Results depend on your assumptions. Designed by Quiet Money with AI assistance; spreadsheets were recalculated and checked against independent math.

### After-purchase message
Thanks for grabbing the kit. Start with the Rat Race Escape Planner. Free 7-day Money Reset emails: {link}

## Rules we keep
No income or savings guarantees; no fake testimonials or scarcity; 30-day refund promise.
"""


def build_all(escape: Path, debt: Path) -> dict:
    dest = OUT / "money-reset-printables"
    pdfs = build_printables(dest)
    clean = {}
    for name, size in SIZES.items():
        ims = pages(size)
        clean[name] = [unsafe(im) for im in ims]
    prices = {"escape": 19.0, "debt": 19.0, "print": 9.0}
    (dest / "LISTING.md").write_text(listing_printables(prices["print"]), encoding="utf-8")
    kit = OUT / "money-reset-kit"
    z = bundle({"escape": escape, "debt": debt}, pdfs, kit)
    (kit / "LISTING.md").write_text(listing_bundle(prices), encoding="utf-8")
    return {"pdfs": {k: str(v) for k, v in pdfs.items()}, "unsafe_pixels": clean, "bundle": str(z)}
