"""Product: the Quiet Money Daily Planner (printable PDF, US Letter and A4, 375 pages, undated).

One picture, one short lesson and one small action for every day of the year: Monday Learn, Tuesday By the numbers, Wednesday Do it, Thursday Mindset,
Friday Action, Saturday weekly check-in, Sunday reflect and reset, 52 weeks plus a bonus Day 365. Front matter: cover, welcome, net worth snapshot,
debt map, year map. Back matter: summary and goals, money words, notes, the licence page.

Pictures: the owner's own artwork when `assets/planner/source/day-NNN.*` exists (cleaned by planner_clean.py), otherwise drawn in code by planner_art.py in
the same black-and-gold language. Text lives in channel/products/daily-quiet-money-planner/content/*.txt and every number in it is computed
(planner_content.py). Nothing here publishes anything: the listing copy and the files are for the owner to approve and upload.

    python -m faceless planner build [--size Letter|A4|both] [--days N]    build the PDFs (and previews) into channel/products/daily-quiet-money-planner/
    python -m faceless planner check                                       the product gauntlet: text, numbers, layout, size, licence, claims
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

from faceless import brand, planner_art, planner_content
from faceless.config import STUDIO, Paths
from faceless.fsutil import write_atomic

PRODUCT = "daily-quiet-money-planner"
OUT = STUDIO / "channel" / "products" / PRODUCT
NAME = "The Quiet Money Daily Planner"
SIZES = {"Letter": (612.0, 792.0), "A4": (595.28, 841.89)}
M = 40.0                                   # page margin in points, inside every printer's unprintable edge
GOLD, DEEP, INK, GREY, LINE, PAPER = "#C9A227", "#8A6D0B", "#141416", "#6A6A6E", "#B9B9BC", "#FFFFFF"
GOLD_BRIGHT = "#FFD23F"
FOOT = "Quiet Money  |  Educational tool, not financial advice. Every number is an example."
AI_LINE = "Designed by Quiet Money with AI assistance."
LICENSE = "Personal use for you and your household. Please do not resell, share or redistribute the files."
ART_RATIO = planner_art.W / planner_art.H
MAX_BYTES = 20 * 2**20                     # Etsy accepts files up to 20 MB each

FRONT, BACK = 5, 5                         # cover, welcome, snapshot, debt map, year map | summary, money words, two notes pages, licence
GLOSSARY = [
    ("APR", "Annual percentage rate: the yearly cost of borrowing, including interest."),
    ("Asset", "Something you own that can put money in your pocket (an investment, a business, a rental)."),
    ("Compound interest", "Interest earned on your earlier interest as well as on your original money."),
    ("Credit utilisation", "How much of your credit limit you are using, as a percentage."),
    ("Deductible", "What you pay yourself on an insurance claim before the insurer pays."),
    ("Diversification", "Spreading money across many investments so one failure does not sink you."),
    ("Emergency fund", "Cash set aside for unplanned, necessary costs, often three to six months of essentials."),
    ("Expense ratio", "The yearly percentage a fund charges to run itself."),
    ("Freedom number", "Yearly spending divided by a withdrawal rate such as 4%: an estimate, not a promise."),
    ("Index fund", "A fund that copies a market index instead of trying to pick winners."),
    ("Inflation", "The rise in prices over time, so the same money buys less."),
    ("Leverage", "Using borrowed money to control a bigger asset. It magnifies gains and losses."),
    ("Liability", "Something that takes money out of your pocket each month."),
    ("Net worth", "What you own minus what you owe."),
    ("Passive income", "Income from assets rather than hours, which usually takes capital or years of work first."),
    ("Rule of 72", "Divide 72 by a yearly rate to estimate the years it takes money to double."),
    ("Sinking fund", "Money set aside monthly for a cost you know is coming."),
    ("Snowball and avalanche", "Two ways to pay debt: smallest balance first, or highest rate first."),
]


# ---------------------------------------------------------------- fonts and drawing helpers

def _rl():
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import simpleSplit
    for name, f in (("Anton", "Anton-Regular.ttf"), ("MontBlack", "Montserrat-Black.ttf"), ("MontXB", "Montserrat-ExtraBold.ttf"),
                    ("Body", "Carlito-Regular.ttf"), ("BodyB", "Carlito-Bold.ttf"), ("BodyI", "Carlito-Italic.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(Paths.fonts / f)))
    return HexColor, simpleSplit


class Overflow(Exception):
    """A page's text does not fit. The builder refuses to ship a page that clips."""


class Pen:
    def __init__(self, c, W: float, H: float):
        self.c, self.W, self.H = c, W, H
        self.hex, self.split = _rl()

    def color(self, h: str) -> None:
        self.c.setFillColor(self.hex(h))
        self.c.setStrokeColor(self.hex(h))

    def text(self, x: float, y: float, s: str, font: str, size: float, color: str = INK, align: str = "l") -> None:
        self.c.setFont(font, size)
        self.c.setFillColor(self.hex(color))
        {"l": self.c.drawString, "r": self.c.drawRightString, "c": self.c.drawCentredString}[align](x, y, s)

    def para(self, x: float, y: float, s: str, font: str, size: float, width: float, color: str = INK, leading: float | None = None, what: str = "") -> float:
        """Draw wrapped text with its first baseline at y. Returns the y below the last line."""
        lead = leading or size * 1.36
        for line in self.split(s, font, size, width):
            self.text(x, y, line, font, size, color)
            y -= lead
        return y

    def lines_needed(self, s: str, font: str, size: float, width: float) -> int:
        return len(self.split(s, font, size, width))

    def rule(self, x0: float, x1: float, y: float, w: float = 0.6, color: str = LINE) -> None:
        self.c.setStrokeColor(self.hex(color))
        self.c.setLineWidth(w)
        self.c.line(x0, y, x1, y)

    def box(self, x: float, y: float, w: float, h: float, stroke: str = INK, lw: float = 0.8, fill: str | None = None, r: float = 0) -> None:
        self.c.setStrokeColor(self.hex(stroke))
        self.c.setLineWidth(lw)
        if fill:
            self.c.setFillColor(self.hex(fill))
        (self.c.roundRect(x, y, w, h, r, stroke=1, fill=1 if fill else 0) if r else self.c.rect(x, y, w, h, stroke=1, fill=1 if fill else 0))

    def footer(self, n: int, total: int) -> None:
        self.text(M, 24, FOOT, "Body", 7.5, GREY)
        self.text(self.W - M, 24, f"{n} / {total}", "Body", 7.5, GREY, "r")

    def title(self, y: float, s: str, sub: str = "") -> float:
        self.text(M, y, s.upper(), "Anton", 30, INK)
        self.c.setFillColor(self.hex(GOLD_BRIGHT))
        self.c.rect(M, y - 12, 70, 4, stroke=0, fill=1)
        y -= 34
        if sub:
            y = self.para(M, y, sub, "BodyI", 12, self.W - 2 * M, GREY)
        return y - 6

    def image(self, im: Image.Image, x: float, y: float, w: float, h: float, radius: float = 7, quality: int = 78) -> None:
        from reportlab.lib.utils import ImageReader
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        buf.seek(0)
        self.c.saveState()
        p = self.c.beginPath()
        p.roundRect(x, y, w, h, radius)
        self.c.clipPath(p, stroke=0, fill=0)
        self.c.drawImage(ImageReader(buf), x, y, w, h)
        self.c.restoreState()
        self.box(x, y, w, h, stroke=GOLD, lw=1.2, r=radius)


# ---------------------------------------------------------------- the day pages

def _tracker(p: Pen, y: float) -> None:
    w = (p.W - 2 * M - 20) / 3
    for i, label in enumerate(("Spent today  $", "Saved or paid down  $", "How I feel about money (1-5)")):
        x = M + i * (w + 10)
        p.box(x, y, w, 36, LINE, 0.8, r=4)
        p.text(x + 8, y + 22, label, "BodyB", 8.5, GREY)


def _ruled(p: Pen, y_top: float, y_bottom: float, step: float = 22) -> int:
    y, n = y_top, 0
    while y >= y_bottom:
        p.rule(M, p.W - M, y, 0.5, LINE)
        y -= step
        n += 1
    return n


def day_page(p: Pen, d: planner_content.Day, art: Image.Image, n: int, total: int) -> None:
    W, H = p.W, p.H
    inner = W - 2 * M
    p.text(M, H - M + 2, f"DAY {d.n:03d}", "MontBlack", 11, INK)
    p.text(M + 62, H - M + 2, f"WEEK {d.week}  |  {d.theme.upper()}", "MontXB", 8.5, GREY)
    p.text(W - M, H - M + 2, "Date  ______ / ______ / ______", "Body", 9.5, GREY, "r")
    ah = inner / ART_RATIO
    ay = H - M - 10 - ah
    p.image(art, M, ay, inner, ah)
    y = ay - 22
    chip = d.label.upper()
    cw = p.c.stringWidth(chip, "MontXB", 8) + 16
    p.box(M, y - 4, cw, 17, INK, 0, fill=INK, r=8.5)
    p.text(M + 8, y + 1, chip, "MontXB", 8, GOLD_BRIGHT)
    y -= 40
    if p.lines_needed(d.title.upper(), "Anton", 27, inner) > 1:
        raise Overflow(f"day {d.n}: title is longer than one line")
    p.text(M, y, d.title.upper(), "Anton", 27, INK)
    y -= 12
    p.rule(M, M + 54, y, 3, GOLD_BRIGHT)
    y -= 22
    y = p.para(M, y, d.lesson, "Body", 12.5, inner, INK, 17)
    y -= 8
    # the action box
    task_lines = p.split(d.task, "BodyB", 11.5, inner - 44)
    bh = 24 + 15 * len(task_lines)
    p.box(M, y - bh, inner, bh, GOLD, 1, fill="#FFF8DC", r=5)
    p.text(M + 10, y - 16, "TRY THIS", "MontXB", 8, DEEP)
    p.box(W - M - 26, y - 22, 14, 14, INK, 1.2)
    ty = y - 33
    for line in task_lines:
        p.text(M + 10, ty, line, "BodyB", 11.5, INK)
        ty -= 15
    y -= bh + 16
    tracker_y = 44
    notes_bottom = tracker_y + 36 + 14
    if y - notes_bottom < 2 * 22:
        raise Overflow(f"day {d.n}: not enough room left for the notes lines ({y - notes_bottom:.0f} pt)")
    p.text(M, y, "My notes", "MontXB", 8, GREY)
    _ruled(p, y - 16, notes_bottom)
    _tracker(p, tracker_y)
    p.footer(n, total)


def checkin_page(p: Pen, d: planner_content.Day, art: Image.Image, n: int, total: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * M
    p.text(M, H - M + 2, f"DAY {d.n:03d}", "MontBlack", 11, INK)
    p.text(M + 62, H - M + 2, f"WEEK {d.week}  |  {d.theme.upper()}", "MontXB", 8.5, GREY)
    p.text(W - M, H - M + 2, "Week ending  ______ / ______ / ______", "Body", 9.5, GREY, "r")
    ah = inner / ART_RATIO
    ay = H - M - 10 - ah
    p.image(art, M, ay, inner, ah)
    y = ay - 36
    p.text(M, y, "WEEKLY CHECK-IN", "Anton", 27, INK)
    y -= 12
    p.rule(M, M + 54, y, 3, GOLD_BRIGHT)
    y -= 22
    y = p.para(M, y, d.lesson, "BodyB", 13, inner, INK, 18)
    y -= 12
    colw = (inner - 15) / 2
    for i, label in enumerate(("Money in this week  $", "Spent this week  $", "Saved or invested  $", "Debt paid  $")):
        x = M + (i % 2) * (colw + 15)
        yy = y - (i // 2) * 44
        p.box(x, yy - 34, colw, 34, LINE, 0.8, r=4)
        p.text(x + 8, yy - 21, label, "BodyB", 10.5, GREY)
    y -= 2 * 44 + 8
    p.text(M, y, "Three wins (any size)", "MontXB", 8, GREY)
    for k in range(3):
        p.rule(M, W - M, y - 22 - k * 22, 0.5, LINE)
    y -= 22 * 3 + 20
    p.text(M, y, "One thing to fix next week", "MontXB", 8, GREY)
    for k in range(2):
        p.rule(M, W - M, y - 22 - k * 22, 0.5, LINE)
    if y - 22 * 2 < 60:
        raise Overflow(f"day {d.n}: check-in page does not fit")
    p.footer(n, total)


def reflect_page(p: Pen, d: planner_content.Day, art: Image.Image, n: int, total: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * M
    p.text(M, H - M + 2, f"DAY {d.n:03d}", "MontBlack", 11, INK)
    p.text(M + 62, H - M + 2, f"WEEK {d.week}  |  {d.theme.upper()}", "MontXB", 8.5, GREY)
    p.text(W - M, H - M + 2, "Date  ______ / ______ / ______", "Body", 9.5, GREY, "r")
    ah = inner / ART_RATIO
    ay = H - M - 10 - ah
    p.image(art, M, ay, inner, ah)
    y = ay - 36
    p.text(M, y, "REFLECT AND RESET", "Anton", 27, INK)
    y -= 12
    p.rule(M, M + 54, y, 3, GOLD_BRIGHT)
    y -= 24
    y = p.para(M, y, d.lesson, "BodyI", 14, inner, INK, 19)
    y -= 10
    bottom = 150
    _ruled(p, y, bottom + 8, 24)
    y = bottom - 6
    p.text(M, y, "Next week I will  (tick when done)", "MontXB", 8, GREY)
    for k in range(3):
        p.box(M, y - 26 - k * 24, 11, 11, INK, 1)
        p.rule(M + 20, W - M, y - 24 - k * 24, 0.5, LINE)
    y -= 26 + 2 * 24 + 22
    p.text(M, y, "Money mood this week", "MontXB", 8, GREY)
    for k in range(5):
        cx = M + 150 + k * 44
        p.c.setStrokeColor(p.hex(INK))
        p.c.setLineWidth(1)
        p.c.circle(cx, y + 3, 11, stroke=1, fill=0)
        p.text(cx, y, str(k + 1), "MontXB", 9, INK, "c")
    p.footer(n, total)


def last_page(p: Pen, d: planner_content.Day, art: Image.Image, n: int, total: int) -> None:
    day_page(p, d, art, n, total)


PAGERS = {"S": checkin_page, "R": reflect_page, "X": last_page}


# ---------------------------------------------------------------- front and back matter

def welcome(p: Pen, n: int, total: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * M
    y = p.title(H - M - 24, "Welcome", "365 days. One picture, one short lesson, one small action. About ten minutes a day.")
    y -= 4
    steps = [
        ("How the week works", "Monday: Learn.  Tuesday: By the numbers.  Wednesday: Do it.  Thursday: Mindset.  Friday: Action.  Saturday: weekly check-in.  Sunday: reflect and reset."),
        ("Start anywhere", "The book is undated. Open to Day 1 whenever you begin. If you miss days, skip ahead to today's page. Never restart: a missed day is only a missed day."),
        ("Do the front pages first", "Fill in the Net Worth Snapshot (page 3) and your Debt Map (page 4) before Day 1. You will come back to both."),
        ("Print it your way", "Print single-sided for a binder, double-sided for a book. Black-and-white or colour both work. The art pages are the heaviest ink, so print them in draft mode if you like."),
        ("What the numbers are", "Every figure in this book is a worked example computed with the same math the Quiet Money channel uses, with its assumptions stated. Investment returns are never guaranteed. Your own numbers are the ones that matter."),
        ("What this is not", "This planner is education, not financial, tax or legal advice. It will never tell you to buy a particular stock, coin or product. Rules differ by country: where a lesson is specific to one, it says so."),
    ]
    for head, body in steps:
        p.text(M, y, head.upper(), "MontXB", 9.5, DEEP)
        y -= 16
        y = p.para(M, y, body, "Body", 12.5, inner, INK, 17)
        y -= 12
    p.box(M, y - 118, inner, 118, GOLD, 1.2, fill="#FFF8DC", r=6)
    p.text(M + 12, y - 20, "WHY I AM DOING THIS", "MontXB", 8.5, DEEP)
    for k in range(3):
        p.rule(M + 12, W - M - 12, y - 48 - k * 24, 0.5, LINE)
    y -= 140
    p.rule(M, W - M, y, 0.6)
    y -= 18
    p.para(M, y, f"{AI_LINE} Illustrations are drawn in code or made with AI image tools. {LICENSE}", "BodyI", 10, inner, GREY, 13)
    if y < 60:
        raise Overflow("welcome page overflow")
    p.footer(n, total)


def _table(p: Pen, y: float, cols: list[tuple[str, float]], rows: list[str], row_h: float = 25, first_col_label: str = "") -> float:
    inner = p.W - 2 * M
    xs = [M]
    for _t, f in cols:
        xs.append(xs[-1] + inner * f)
    xs[-1] = p.W - M
    hh = 24
    p.box(M, y - hh, inner, hh, INK, 1, fill=INK)
    for (t, _f), x in zip(cols, xs):
        p.text(x + 6, y - 16, t, "MontXB", 8.5, GOLD_BRIGHT)
    top = y - hh
    for i, label in enumerate(rows):
        ry = top - (i + 1) * row_h
        p.rule(M, p.W - M, ry, 0.5, LINE)
        if label:
            p.text(M + 6, ry + 8, label, "BodyB", 10.5, INK)
    bottom = top - len(rows) * row_h
    for x in xs[1:-1]:
        p.c.setStrokeColor(p.hex(LINE))
        p.c.setLineWidth(0.5)
        p.c.line(x, top, x, bottom)
    p.box(M, bottom, inner, hh + len(rows) * row_h, INK, 1)
    return bottom - 14


def snapshot(p: Pen, n: int, total: int) -> None:
    W, H = p.W, p.H
    y = p.title(H - M - 24, "Net worth snapshot", "What you own minus what you owe. Fill in a column on Days 1, 91, 182, 273 and 365. Round to the nearest $10.")
    cols = [("WHAT YOU OWN", 0.30)] + [(f"DAY {d}", 0.14) for d in (1, 91, 182, 273, 365)]
    y = _table(p, y, cols, ["Checking", "Savings", "Emergency fund", "Retirement / investments", "Home or car value (if sold)", "Other", "TOTAL OWNED"], 31)
    cols[0] = ("WHAT YOU OWE", 0.30)
    y = _table(p, y - 4, cols, ["Credit cards", "Student loans", "Car loan", "Mortgage", "Other debts", "TOTAL OWED"], 31)
    cols[0] = ("NET WORTH", 0.30)
    y = _table(p, y - 4, cols, ["OWNED minus OWED", "Change since Day 1"], 36)
    p.para(M, y - 4, "A negative number is a starting line, not a verdict. The direction of the line matters more than where it starts.", "BodyI", 11, W - 2 * M, GREY)
    p.footer(n, total)


def debt_map(p: Pen, n: int, total: int) -> None:
    W, H = p.W, p.H
    y = p.title(H - M - 24, "Debt map", "Every debt on one page. Rank them 1 for the highest APR. You will use this in weeks 14 to 16.")
    cols = [("LENDER OR CARD", 0.30), ("BALANCE $", 0.18), ("APR %", 0.12), ("MINIMUM $", 0.16), ("DUE DAY", 0.12), ("RANK", 0.12)]
    y = _table(p, y, cols, [""] * 10, 30)
    y = p.para(M, y - 2, "Total owed:  $______________      Total monthly minimums:  $______________      Highest APR:  ________ %", "BodyB", 11.5, W - 2 * M, INK, 16)
    y = p.para(M, y - 8, "Avalanche: extra money to the highest APR first (usually cheapest). Snowball: extra money to the smallest balance first (quicker wins). Both pay every minimum. Pick one and keep going.", "BodyI", 11, W - 2 * M, GREY, 15)
    p.footer(n, total)


def year_map(p: Pen, weeks: list[tuple[int, str, int]], n: int, total: int) -> None:
    W, H = p.W, p.H
    y = p.title(H - M - 24, "The year at a glance", "52 weeks, four quarters. Tick each week when you finish it.")
    colw = (W - 2 * M - 12) / 2
    q_titles = ["QUARTER 1: FOUNDATIONS", "QUARTER 2: DEBT, CREDIT AND COMPOUNDING", "QUARTER 3: INVESTING AND INCOME", "QUARTER 4: LIFE, PROTECTION AND FREEDOM"]
    top = y
    for q in range(4):
        x = M + (q % 2) * (colw + 12)
        qy = top - (q // 2) * ((top - 60) / 2) - 6
        p.text(x, qy, q_titles[q], "MontXB", 8, DEEP)
        for i in range(13):
            wk, theme, first = weeks[q * 13 + i]
            ly = qy - 20 - i * 21.5
            p.box(x, ly - 2, 9, 9, INK, 0.9)
            p.text(x + 15, ly, f"Wk {wk}", "BodyB", 9.5, GREY)
            p.text(x + 47, ly, theme, "Body", 10.5, INK)
            p.text(x + colw, ly, f"Day {first}", "Body", 8.5, GREY, "r")
    p.footer(n, total)


def summary(p: Pen, n: int, total: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * M
    y = p.title(H - M - 24, "Summary and goals", "Fill this in as you reach weeks 47, 51 and 52.")
    p.box(M, y - 70, inner, 70, GOLD, 1.5, fill="#FFF8DC", r=6)
    p.text(M + 12, y - 20, "MY FREEDOM NUMBER (yearly spending divided by 0.04)", "MontXB", 8.5, DEEP)
    p.text(M + 12, y - 52, "$ ______________________________", "BodyB", 22, INK)
    y -= 90
    p.text(M, y, "MY THREE GOALS  (a number and a date for each)", "MontXB", 8.5, DEEP)
    for i, label in enumerate(("Under 3 months", "Under a year", "Five years or more")):
        yy = y - 26 - i * 30
        p.text(M, yy, label, "BodyB", 11, GREY)
        p.rule(M + 120, W - M, yy - 2, 0.5, LINE)
    y -= 26 + 3 * 30 + 8
    cols = [("MY YEAR IN NUMBERS", 0.55), ("AMOUNT", 0.45)]
    y = _table(p, y, cols, ["Total saved or invested", "Total debt paid", "Change in net worth", "Interest and fees I stopped paying", "Subscriptions cancelled (monthly $)", "Best money decision", "Costliest mistake (and the lesson)"], 30)
    p.footer(n, total)


def money_words(p: Pen, n: int, total: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * M
    y = p.title(H - M - 24, "Money words", "Plain-English definitions of the terms in this book.")
    for term, meaning in GLOSSARY:
        p.text(M, y, term.upper(), "MontXB", 8.5, DEEP)
        y = p.para(M + 150, y, meaning, "Body", 11, inner - 150, INK, 14)
        y -= 5
    if y < 50:
        raise Overflow("money words page overflow")
    p.footer(n, total)


def notes(p: Pen, title: str, n: int, total: int) -> None:
    W, H = p.W, p.H
    y = p.title(H - M - 24, title)
    _ruled(p, y - 6, 50, 24)
    p.footer(n, total)


def last_back(p: Pen, n: int, total: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * M
    y = p.title(H - M - 24, "About this planner")
    for head, body in (
        ("Education, not advice", "The Quiet Money Daily Planner is an educational tool. It is not financial, tax, legal or investment advice and it never recommends a particular product. Examples use made-up numbers and stated assumptions. Returns are never guaranteed and past results do not predict the future. Talk to a qualified professional about your own situation."),
        ("Made with AI assistance", f"{AI_LINE} The lessons were written and fact-checked with the Quiet Money studio's tools, and every computed figure comes from one shared set of math functions that is tested. The pictures are original artwork drawn in code or made with AI tools."),
        ("Licence", f"{LICENSE} One purchase covers printing as many copies as you need for yourself and your household."),
        ("Questions or mistakes", "If you find an error, reply to the message where you bought this. It gets fixed and you get the update."),
    ):
        p.text(M, y, head.upper(), "MontXB", 9.5, DEEP)
        y -= 16
        y = p.para(M, y, body, "Body", 12, inner, INK, 16.5)
        y -= 14
    p.footer(n, total)


# ---------------------------------------------------------------- art + build

def _art_job(args) -> str:
    day, motif = args
    out = planner_art.GENERATED / f"day-{day:03d}.jpg"
    src = planner_art.owner_image(day)
    if out.exists() and out.stat().st_mtime > max(Path(planner_art.__file__).stat().st_mtime, src.stat().st_mtime if src else 0):
        return str(out)
    return str(planner_art.save_day(day, motif))


def ensure_art(days: list[planner_content.Day], workers: int | None = None) -> dict[int, Path]:
    planner_art.GENERATED.mkdir(parents=True, exist_ok=True)
    jobs = [(d.n, d.motif) for d in days]
    workers = workers or max(1, min(8, (os.cpu_count() or 2)))
    if workers == 1:
        done = [_art_job(j) for j in jobs]
    else:
        with ProcessPoolExecutor(workers) as ex:
            done = list(ex.map(_art_job, jobs, chunksize=8))
    return {d.n: Path(f) for d, f in zip(days, done)}


def build_pdf(size: str, days: list[planner_content.Day], art: dict[int, Path], cover: Image.Image | None, out: Path, weeks: list | None = None) -> Path:
    from reportlab.pdfgen import canvas
    W, H = SIZES[size]
    total = FRONT + len(days) + BACK
    c = canvas.Canvas(str(out), pagesize=(W, H), pageCompression=1)
    c.setTitle(NAME)
    c.setAuthor("Quiet Money")
    c.setSubject("365-day money planner. Educational, not financial advice.")
    c.setCreator("Quiet Money studio")
    p = Pen(c, W, H)
    page = 1

    def done():
        nonlocal page
        c.showPage()
        page += 1

    if cover is not None:                                     # page 1: the cover, full bleed art on the page size
        from reportlab.lib.utils import ImageReader
        buf = io.BytesIO()
        cover.convert("RGB").save(buf, "JPEG", quality=88, optimize=True)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, W, H)
    done()
    welcome(p, page, total); done()
    snapshot(p, page, total); done()
    debt_map(p, page, total); done()
    year_map(p, weeks or planner_content.week_themes(days), page, total); done()
    for d in days:
        im = Image.open(art[d.n])
        PAGERS.get(d.kind, day_page)(p, d, im, page, total)
        done()
    summary(p, page, total); done()
    money_words(p, page, total); done()
    notes(p, "Notes", page, total); done()
    notes(p, "Notes", page, total); done()
    last_back(p, page, total); done()
    c.save()
    return out


def previews(pdf: Path, pages: dict[str, int], dest: Path, dpi: int = 70) -> list[Path]:
    """PNG previews of chosen pages (name -> page number) via pdftoppm. Used for the listing; skipped quietly where pdftoppm is missing."""
    dest.mkdir(parents=True, exist_ok=True)
    made = []
    for name, pg in pages.items():
        stem = dest / f"_{name}"
        try:
            subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(pg), "-l", str(pg), "-png", "-singlefile", str(pdf), str(stem)], check=True, timeout=120, capture_output=True)
        except (FileNotFoundError, subprocess.SubprocessError):
            return made
        final = dest / f"{name}.png"
        stem.with_suffix(".png").replace(final)
        made.append(final)
    return made


def build(sizes: tuple[str, ...] = ("Letter", "A4"), limit: int | None = None, with_cover: bool = True) -> dict:
    t0 = time.time()
    every = planner_content.load()
    weeks = planner_content.week_themes(every)
    days = every[:limit] if limit else every
    art = ensure_art(days)
    from faceless import planner_cover
    out: dict = {"days": len(days), "files": {}}
    for size in sizes:
        cov = planner_cover.cover(*[round(v * 200 / 72) for v in SIZES[size]]) if with_cover else None
        f = OUT / f"Quiet-Money-Daily-Planner-{size}.pdf"
        OUT.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f".{f.name}.tmp")
        build_pdf(size, days, art, cov, tmp, weeks)
        os.replace(tmp, f)
        out["files"][size] = {"path": str(f.relative_to(STUDIO)), "mb": round(f.stat().st_size / 2**20, 1)}
    out["seconds"] = round(time.time() - t0)
    write_atomic(OUT / "build.json", __import__("json").dumps(out, indent=1) + "\n")
    return out


# ---------------------------------------------------------------- the product gauntlet

ADVICE = re.compile(r"\byou should (buy|sell|invest in)\b|\b(buy|sell) (bitcoin|ethereum|crypto|stocks?|shares)\b|guaranteed (return|profit|income)|risk[- ]free|get rich|can'?t lose|double your money|financial freedom in \d", re.I)


def check(build_first: bool = False) -> list[tuple[str, bool, str, bool]]:
    """(gate, ok, detail, hard). Text and layout gates always run; file gates run on whatever PDFs are built."""
    import hashlib
    gates: list[tuple[str, bool, str, bool]] = []
    days = planner_content.load()
    gates.append(("content_complete", len(days) == 365 and [d.n for d in days] == list(range(1, 366)), f"{len(days)} days, numbered 1 to 365", True))
    blob = "\n".join(f"{d.title}\n{d.lesson}\n{d.task}" for d in days)
    left = re.findall(r"[{}]|\bnan\b|\binf\b", blob)
    gates.append(("numbers_all_computed", not left, f"{len(days)} days, no unresolved placeholder or nan" if not left else f"found {left[:5]}", True))
    bad = sorted({m.group(0) for m in ADVICE.finditer(blob)})
    gates.append(("no_advice_or_promises", not bad, "none found" if not bad else f"found: {bad}", True))
    dup = len(days) - len({d.lesson for d in days})
    gates.append(("no_duplicate_lessons", dup == 0, f"{dup} duplicate lesson(s)", True))
    _hex, split = _rl()
    inner = SIZES["A4"][0] - 2 * M
    long = []
    for d in days:
        if len(split(d.title.upper(), "Anton", 27, inner)) > 1:
            long.append(f"day {d.n} title")
        if len(split(d.lesson, "Body", 12.5, inner)) > 9:
            long.append(f"day {d.n} lesson")
        if len(split(d.task, "BodyB", 11.5, inner - 44)) > 4:
            long.append(f"day {d.n} task")
    gates.append(("text_fits_the_page", not long, "every title is one line, lessons 9 lines or fewer, tasks 4 lines or fewer" if not long else f"too long: {long[:5]}", True))
    from faceless import listing
    cat = {p["id"]: p for p in listing.catalog()["products"]}.get(PRODUCT)
    if cat:
        gates += [(g.name, g.ok, g.detail, g.hard) for g in listing.text_gates(cat) + listing.file_gates(cat)]
    from pypdf import PdfReader
    want = FRONT + 365 + BACK
    for size in SIZES:
        f = OUT / f"Quiet-Money-Daily-Planner-{size}.pdf"
        if not f.exists():
            gates.append((f"pdf_{size.lower()}_built", False, "not built yet: run `python -m faceless planner build`", True))
            continue
        r = PdfReader(str(f))
        pw, ph = (float(v) for v in r.pages[0].mediabox[2:])
        ok = len(r.pages) == want and abs(pw - SIZES[size][0]) < 1 and abs(ph - SIZES[size][1]) < 1
        gates.append((f"pdf_{size.lower()}_pages", ok, f"{len(r.pages)} pages (want {want}), {pw:.0f}x{ph:.0f} pt", True))
        text2 = (r.pages[1].extract_text() or "") + (r.pages[-1].extract_text() or "")
        gates.append((f"pdf_{size.lower()}_disclosures", "not financial" in text2.lower() and "AI assistance" in text2, "not-advice and AI lines on the welcome and last pages", True))
        gates.append((f"pdf_{size.lower()}_etsy_size", f.stat().st_size <= MAX_BYTES, f"{f.stat().st_size / 2**20:.1f} MB (Etsy: 20 MB per file)", True))
    gen = sorted(planner_art.GENERATED.glob("day-*.jpg"))
    if gen:
        same = len(gen) - len({hashlib.md5(g.read_bytes()).hexdigest() for g in gen})
        gates.append(("pictures_distinct", same == 0, f"{len(gen)} pictures, {same} identical", False))
    owner = sum(1 for d in days if planner_art.owner_image(d.n))
    gates.append(("owner_pictures_in_use", owner > 0, f"{owner} of 365 days use the owner's pictures; {365 - owner} are drawn", False))
    return gates
