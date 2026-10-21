"""The First Quiet Week: the free lead magnet that is a true sample of the Daily Planner (days 1-7 as printed in the book).

    python -m faceless.lead_magnet_sample        # writes channel/offers/lead-magnets/first-quiet-week/The-First-Quiet-Week.pdf

The day pages are drawn by the planner's own page functions from the planner's own content, so the sample can never drift from
the book. The cover and the last page are new copy from channel/offers/lead-magnets/first-quiet-week/CONTENT.md. No wellness
poster and no Quinton picture: the sample carries no unchecked claim and needs no AI-person mark.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from faceless import offer, planner_content
from faceless import product_planner as pp
from faceless.config import STUDIO

DEST = STUDIO / "channel" / "offers" / "lead-magnets" / "first-quiet-week" / "The-First-Quiet-Week.pdf"
PLANNER_URL = "https://chrisclassroom4.gumroad.com/l/utwsfs"
BLACK = "#0B0B0C"
PAGES = 9


def bridge_url() -> str:
    """The one link in the sample: the live planner listing, tagged so a sale from the sample can be counted."""
    return offer.tracked(PLANNER_URL, "magnet", "pdf", "first_quiet_week")


def _dark(p: pp.Pen) -> None:
    p.c.setFillColor(p.hex(BLACK))
    p.c.rect(0, 0, p.W, p.H, stroke=0, fill=1)


def cover(p: pp.Pen, n: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * pp.M
    _dark(p)
    p.text(W / 2, H - 70, "Q U I E T   M O N E Y", "MontXB", 10, pp.GOLD_BRIGHT, "c")
    p.text(W / 2, H - 150, "THE FIRST", "Anton", 54, "#FFFFFF", "c")
    p.text(W / 2, H - 210, "QUIET WEEK", "Anton", 54, pp.GOLD_BRIGHT, "c")
    y = p.para(pp.M + 20, H - 250, "Seven days. Seven small pages. The first week of the Quiet Money Daily Planner, exactly as it appears in the book.",
               "BodyI", 13, inner - 40, "#E8E8EA", 18)
    y -= 18
    for head, body in (
        ("How to use this", "Print it, or keep it open next to a notebook. Do one page a day. You do not need to start on a Monday: the book is undated, and so is this."),
        ("What you will find", "Day 1 to Day 5 are the five daily pages: Learn, By the numbers, Do it, Mindset, Action. Day 6 is the weekly check-in. Day 7 is the reflect-and-reset page. These are the real pages, not a mock-up."),
        ("One note on Day 1", "Day 1 asks for the Net Worth Snapshot at the front of the book. In this sample, use the notes lines: what you own, what you owe, and the difference."),
        ("A note on the numbers", "Every number in this week is a worked example with its assumptions stated. Rates are hypothetical. None of it is a promise about what money will do, and none of it is advice about your situation."),
    ):
        p.text(pp.M + 20, y, head.upper(), "MontXB", 9.5, pp.GOLD_BRIGHT)
        y -= 16
        y = p.para(pp.M + 20, y, body, "Body", 12, inner - 40, "#FFFFFF", 16.5)
        y -= 12
    p.text(W / 2, 92, "DAY 1 LEARN  |  2 NUMBERS  |  3 DO IT  |  4 MINDSET  |  5 ACTION  |  6 CHECK-IN  |  7 RESET", "MontXB", 7.5, pp.GOLD, "c")
    p.text(W / 2, 40, f"{pp.AI_LINE} Educational content, not financial advice.", "BodyI", 8.5, "#BDBDC2", "c")
    p.text(W - pp.M, 24, f"{n} / {PAGES}", "Body", 7.5, "#8A8A90", "r")


def bridge(p: pp.Pen, n: int) -> None:
    W, H, inner = p.W, p.H, p.W - 2 * pp.M
    _dark(p)
    p.text(W / 2, H - 150, "YOU JUST DID", "Anton", 46, "#FFFFFF", "c")
    p.text(W / 2, H - 205, "WEEK 1 OF 52", "Anton", 46, pp.GOLD_BRIGHT, "c")
    y = p.para(pp.M + 30, H - 260, "That is how the whole book works: one page, one small action, a check-in on Saturday and a reset on Sunday. "
               "If you did even two of the seven days, you know more about your own numbers than you did last week.", "Body", 13, inner - 60, "#FFFFFF", 18)
    y -= 24
    y = p.para(pp.M + 30, y, "If you want the other 51 weeks, the full Quiet Money Daily Planner is 427 printable pages in US Letter and A4, $17, "
               "with a 30-day refund.", "MontXB", 12, inner - 60, pp.GOLD_BRIGHT, 17)
    y -= 26
    bw, bh = 300, 40
    bx = (W - bw) / 2
    p.box(bx, y - bh, bw, bh, pp.GOLD_BRIGHT, 1.2, fill=pp.GOLD_BRIGHT, r=8)
    p.text(W / 2, y - bh + 14, "GET THE FULL PLANNER", "MontXB", 12, BLACK, "c")
    p.c.linkURL(bridge_url(), (bx, y - bh, bx + bw, y), relative=0)
    p.text(W / 2, y - bh - 22, "chrisclassroom4.gumroad.com/l/utwsfs", "Body", 9, "#BDBDC2", "c")
    p.text(W / 2, 40, f"{pp.AI_LINE} Educational content, not financial advice. Every number is a worked example; rates are hypothetical.",
           "BodyI", 8, "#BDBDC2", "c")
    p.text(W - pp.M, 24, f"{n} / {PAGES}", "Body", 7.5, "#8A8A90", "r")


def build(size: str = "Letter", out: Path = DEST) -> Path:
    from reportlab.pdfgen import canvas
    pp._rl()
    days = planner_content.load()[:7]
    art = pp.ensure_art(days)
    W, H = pp.SIZES[size]
    out.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out), pagesize=(W, H), pageCompression=1)
    c.setTitle("The First Quiet Week (free sample of The Quiet Money Daily Planner)")
    c.setAuthor("Quiet Money")
    c.setSubject("Seven free days of money lessons. Educational, not financial advice.")
    p = pp.Pen(c, W, H)
    cover(p, 1)
    c.showPage()
    for i, d in enumerate(days, start=2):
        pp.PAGERS.get(d.kind, pp.day_page)(p, d, Image.open(art[d.n]), i, PAGES)
        c.showPage()
    bridge(p, PAGES)
    c.showPage()
    c.save()
    return out


if __name__ == "__main__":
    print(build())
