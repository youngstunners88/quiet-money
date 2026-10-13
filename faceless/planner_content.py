"""Quiet Money Daily Planner: the 365 lessons as data.

Source files: channel/products/daily-quiet-money-planner/content/q1.txt .. q4.txt (52 weeks, 7 days each, plus the bonus Day 365).
Rule 1 of the studio: every number is true. A lesson never types a computed number by hand; it writes a placeholder like `{fv:200,8,30}` and this module fills
it in from faceless/moneymath.py, so the planner cannot drift from the math the videos quote. `check()` fails on any placeholder it cannot resolve.

Line format (see the header of q1.txt):  L|N|D|M|A  kind | title | lesson | task      S  Saturday check-in prompt      R  Sunday reflect prompt      X  the bonus day.
"""

from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from pathlib import Path

from faceless import moneymath as mm
from faceless.config import STUDIO

CONTENT = STUDIO / "channel" / "products" / "daily-quiet-money-planner" / "content"
FILES = ("q1.txt", "q2.txt", "q3.txt", "q4.txt")
KINDS = {"L": "Learn", "N": "By the numbers", "D": "Do it", "M": "Mindset", "A": "Action", "S": "Weekly check-in", "R": "Reflect and reset", "X": "The last page"}
ORDER = "LNDMASR"
PLACEHOLDER = re.compile(r"\{([a-z0-9_]+):([^{}]*)\}")


# ---------------------------------------------------------------- placeholders

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _num(node: ast.AST) -> float:
    """Evaluate a number expression made only of numbers, + - * / and parentheses. Anything else is refused (no names, no calls)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_num(node.left), _num(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _num(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    raise ValueError("only numbers and + - * / ( ) are allowed in a placeholder")


def _args(raw: str) -> list[float]:
    return [_num(ast.parse(a.strip(), mode="eval").body) for a in raw.split(",") if a.strip()]


def _years(months: float) -> str:
    return f"{months / 12:.0f}"


def _trim(x: float, places: int = 1) -> str:
    s = f"{x:,.{places}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def pmt(principal: float, apr_pct: float, months: int) -> float:
    r = apr_pct / 100 / 12
    return principal / months if r == 0 else principal * r / (1 - (1 + r) ** -months)


FUNCS = {
    "usd": lambda a: mm.money(a),
    "num": lambda a: _trim(a, 2),
    "x": lambda a, b: mm.money(a * b),
    "div": lambda a, b: mm.money(a / b),
    "pct": lambda a, b: f"{_trim(a / b * 100)}%",
    "fv": lambda m, r, y: mm.money(mm.future_value_monthly(m, r / 100, int(y))),
    "put": lambda m, y: mm.money(m * 12 * y),
    "lump": lambda p, r, y: mm.money(mm.lump_sum_growth(p, r / 100, int(y))),
    "gap": lambda p, r1, r2, y: mm.money(mm.lump_sum_growth(p, r1 / 100, int(y)) - mm.lump_sum_growth(p, r2 / 100, int(y))),
    "fvgap": lambda m, r, y1, y2: mm.money(mm.future_value_monthly(m, r / 100, int(y1)) - mm.future_value_monthly(m, r / 100, int(y2))),
    "r72": lambda r: _trim(mm.rule_of_72(r)),
    "infl": lambda a, r, y: mm.money(mm.inflation_value(a, r / 100, int(y))),
    "cmin_y": lambda bal, apr: _years(mm.card_minimum_payoff(bal, apr / 100)[0]),
    "cmin_i": lambda bal, apr: mm.money(mm.card_minimum_payoff(bal, apr / 100)[1]),
    "cpay_m": lambda bal, apr, p: str(mm.card_payoff(bal, apr / 100, p)[0]),
    "cpay_i": lambda bal, apr, p: mm.money(mm.card_payoff(bal, apr / 100, p)[1]),
    "pmt": lambda p, apr, n: mm.money(pmt(p, apr, int(n))),
    "pmti": lambda p, apr, n: mm.money(pmt(p, apr, int(n)) * n - p),
    "cap": lambda m: mm.money(mm.capital_for_income(m)),
    "mtt": lambda m, r, t: _trim(mm.months_to_target(m, r / 100, t) / 12),
}


def fill(text: str) -> str:
    def one(m: re.Match) -> str:
        name, raw = m.group(1), m.group(2)
        if name not in FUNCS:
            raise ValueError(f"unknown placeholder function {name!r} in: {m.group(0)}")
        return FUNCS[name](*_args(raw))
    return PLACEHOLDER.sub(one, text)


# ---------------------------------------------------------------- the days

@dataclass
class Day:
    n: int                     # 1..365
    week: int                  # 1..53 (Day 365 is week 53)
    theme: str
    kind: str                  # L N D M A S R X
    title: str
    lesson: str                # S and R: the prompt
    task: str
    motif: str

    @property
    def label(self) -> str:
        return KINDS[self.kind]


def _motif_for(kind: str, motifs: list[str]) -> str:
    return {"S": "grid", "R": "road", "N": motifs[1], "M": motifs[2], "X": "coin"}.get(kind, motifs[0])


def parse(text: str, weeks: dict[int, dict]) -> None:
    cur = None
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^#\s*WEEK\s+(\d+)\s*\|\s*([^|]+)\|\s*(.+)$", line)
        if m:
            cur = int(m.group(1))
            motifs = [x.strip() for x in m.group(3).split(",")]
            if len(motifs) != 3:
                raise ValueError(f"line {ln}: week {cur} needs exactly three motifs")
            weeks[cur] = {"theme": m.group(2).strip(), "motifs": motifs, "rows": {}}
            continue
        if line.startswith("#"):
            continue
        if cur is None:
            raise ValueError(f"line {ln}: entry before any WEEK header")
        parts = [p.strip() for p in line.split("|")]
        kind = parts[0]
        if kind in "SR" and len(parts) == 2:
            prompt = re.sub(r"^Weekly check-in:\s*", "", parts[1])          # the page title already says it
            weeks[cur]["rows"][kind] = (KINDS[kind], prompt[:1].upper() + prompt[1:], "")
        elif kind in "LNDMAX" and len(parts) == 4:
            weeks[cur]["rows"][kind] = (parts[1], parts[2], parts[3])
        else:
            raise ValueError(f"line {ln}: cannot read {line[:60]!r} (kind {kind!r}, {len(parts)} fields)")


def load(directory: Path = CONTENT) -> list[Day]:
    weeks: dict[int, dict] = {}
    for f in FILES:
        parse((directory / f).read_text(encoding="utf-8"), weeks)
    days: list[Day] = []
    for w in range(1, 53):
        if w not in weeks:
            raise ValueError(f"week {w} is missing")
        rows = weeks[w]["rows"]
        for i, k in enumerate(ORDER):
            if k not in rows:
                raise ValueError(f"week {w} is missing its {KINDS[k]} day ({k})")
            title, lesson, task = rows[k]
            days.append(Day((w - 1) * 7 + i + 1, w, weeks[w]["theme"], k, fill(title), fill(lesson), fill(task), _motif_for(k, weeks[w]["motifs"])))
    x = weeks[52]["rows"].get("X")
    if not x:
        raise ValueError("week 52 needs an X line for the bonus Day 365")
    days.append(Day(365, 52, weeks[52]["theme"], "X", fill(x[0]), fill(x[1]), fill(x[2]), "coin"))
    return days


def week_themes(days: list[Day]) -> list[tuple[int, str, int]]:
    """(week, theme, first day) for the year map."""
    out = {}
    for d in days:
        out.setdefault(d.week, (d.week, d.theme, d.n))
    return [out[w] for w in sorted(out)]
