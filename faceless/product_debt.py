"""Product: Debt Payoff & Compound Interest Planner (spreadsheet).

Up to eight debts, an avalanche or snowball plan with freed-up minimums rolled forward, the same debts on minimums only for
comparison, a compound-growth table, and a pay-debt-or-invest check. The month-by-month math lives on the visible
"Engine (math)" tab as plain formulas (no macros, no scripts), so a buyer can audit every cell. The build is recalculated
in LibreOffice and compared with an independent Python simulation of the same rules before it is ever listed.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from faceless import config
from faceless.products import (DISCLAIMER, GOLD, GOOD_FILL, INK, MUTED, OUT, _header, _label, _put, _title, _widths, load_workbook,
                               recalc)

SHEETS = ["Start here", "1 Your debts", "2 Payoff plan", "3 Compound growth", "4 Pay debt or invest", "Engine (math)"]
N, MONTHS, FIRST = 8, 240, 9          # debts, months simulated (20 years), first month row on the engine tab
BLOCK = 10                            # engine columns per debt: start, interest, minimum, extra, left, end | min-only: start, interest, paid, end
C0 = 10                               # first debt block starts in column J
SAMPLE = [("Credit card A (example)", 4200, 0.2499, 105), ("Credit card B (example)", 1800, 0.1999, 45),
          ("Car loan (example)", 7500, 0.079, 210), ("Student loan (example)", 12000, 0.055, 130)]
DEFAULTS = {"debts": SAMPLE, "extra": 200, "method": "Avalanche", "start": 5000, "monthly": 300, "ret": 0.07, "years": 30,
            "apr": 0.2499, "x_extra": 200, "x_ret": 0.07, "x_years": 5}


def _col(j: int, off: int) -> str:
    """Engine column letter for debt j (1-based) and offset within its block."""
    return L(C0 + (j - 1) * BLOCK + off)


def build_debt_planner(dest: Path, **over) -> Path:
    d = {**DEFAULTS, **over}
    wb = Workbook()
    ws = wb.active
    ws.title = SHEETS[0]
    _title(ws, "Debt Payoff & Compound Interest Planner", "Find the fastest way out of debt, then let compounding work for you.", 6)
    steps = ["1. Open '1 Your debts' and replace the blue example debts with yours (up to 8). Choose Avalanche or Snowball and type your extra monthly payment.",
             "2. Open '2 Payoff plan': your debt-free month, total interest, and how much interest and time the plan saves against paying only minimums.",
             "3. '3 Compound growth' shows what a lump sum and a monthly amount become once the debt is gone.",
             "4. '4 Pay debt or invest' compares what paying a debt saves (its interest rate) with an assumed investment return.",
             "5. 'Engine (math)' is every month of the calculation in plain formulas, so you can check any number."]
    for i, t in enumerate(steps):
        _label(ws, f"A{4 + i}", t)
        ws.merge_cells(f"A{4 + i}:F{4 + i}")
        ws.row_dimensions[4 + i].height = 34
    _label(ws, "A10", "Colors", True)
    _put(ws, "A11", "Blue = you type here", inp=True)
    _put(ws, "A12", "Gray = formula")
    _label(ws, "A14", "How the plans differ", True)
    for i, t in enumerate(["Avalanche: extra money goes to the highest interest rate first. It costs the least interest.",
                           "Snowball: extra money goes to the smallest balance first. Quick wins keep some people going. It usually costs a little more interest.",
                           "Both plans keep paying the same total each month: when a debt is paid off, its payment rolls onto the next one.",
                           "Minimums only: every debt paid on its own minimum, nothing rolled over. That is the comparison line."]):
        _label(ws, f"A{15 + i}", t)
        ws.merge_cells(f"A{15 + i}:F{15 + i}")
        ws.row_dimensions[15 + i].height = 30
    _label(ws, "A20", DISCLAIMER + " Interest is calculated monthly (rate / 12) with no rounding; your lender's exact figures will differ slightly.")
    ws.merge_cells("A20:F20")
    ws.row_dimensions[20].height = 56
    ws["A20"].font = Font(name="Calibri", size=10, italic=True, color=MUTED)
    _label(ws, "A22", "License: personal use for you and your household. Please do not resell or redistribute the file.")
    ws.merge_cells("A22:F22")
    _widths(ws, [30, 18, 18, 18, 18, 18])

    # ---- 1 Your debts
    y = wb.create_sheet(SHEETS[1])
    _title(y, "1 Your debts", "List up to eight. Leave unused rows blank. Example debts shown.", 7)
    _header(y, 3, ["Debt", "Balance", "Yearly interest rate", "Monthly minimum", "Plan order", "Check", ""])
    for i in range(N):
        r = 4 + i
        row = d["debts"][i] if i < len(d["debts"]) else (None, None, None, None)
        _put(y, f"A{r}", row[0], inp=True)
        y[f"A{r}"].alignment = Alignment(horizontal="left")
        _put(y, f"B{r}", row[1], fmt="$#,##0.00", inp=True)
        _put(y, f"C{r}", row[2], fmt="0.00%", inp=True)
        _put(y, f"D{r}", row[3], fmt="$#,##0.00", inp=True)
        # priority score: bigger = paid first; ties go to the earlier row. Blank / zero-balance rows get "" and drop out.
        y[f"H{r}"] = (f'=IF(N(B{r})>0,IF($B$15="Snowball",-B{r}*1000+(100-ROW())*0.001,N(C{r})*100000000+(100-ROW())),"")')
        _put(y, f"E{r}", f'=IF(H{r}="","",COUNTIF($H$4:$H$11,">"&H{r})+1)', fmt="0")
        _put(y, f"F{r}", f'=IF(AND(N(B{r})>0,N(D{r})<N(B{r})*N(C{r})/12),"Minimum is below the monthly interest",IF(AND(N(B{r})>0,N(D{r})=0),"Enter a minimum",""))')
        y[f"F{r}"].alignment = Alignment(horizontal="left")
        y[f"H{r}"].font = Font(size=8, color="BBBBBB")
    y["H3"] = "priority score (helper)"
    y["H3"].font = Font(size=8, color="BBBBBB")
    dv = DataValidation(type="decimal", operator="between", formula1="0", formula2="1", allow_blank=True, showErrorMessage=True,
                        errorTitle="Enter a percentage", error="Type the yearly rate as a percentage, for example 24.99%.")
    y.add_data_validation(dv)
    dv.add("C4:C11")
    _label(y, "A13", "Plan settings", True)
    _label(y, "A14", "Extra you can pay each month (on top of minimums)")
    _put(y, "B14", d["extra"], fmt="$#,##0", inp=True)
    _label(y, "A15", "Method")
    _put(y, "B15", d["method"], inp=True)
    dv2 = DataValidation(type="list", formula1='"Avalanche,Snowball"', showErrorMessage=True, errorTitle="Pick a method", error="Choose Avalanche or Snowball.")
    y.add_data_validation(dv2)
    dv2.add("B15")
    _label(y, "A16", "Total you pay toward debt each month")
    _put(y, "B16", '=SUMIF(B4:B11,">0",D4:D11)+N(B14)', fmt="$#,##0.00", bold=True)
    _label(y, "A17", "Total debt today")
    _put(y, "B17", "=SUM(B4:B11)", fmt="$#,##0.00", bold=True)
    _widths(y, [46, 16, 18, 16, 12, 36, 4, 14])
    y.column_dimensions["H"].hidden = True
    y.freeze_panes = "A4"

    # ---- Engine (math)
    e = wb.create_sheet(SHEETS[5])
    e.sheet_view.showGridLines = True
    e["A1"] = "Engine (math): every month, every debt, plain formulas. Nothing here needs editing."
    e["A1"].font = Font(bold=True, size=12)
    heads = ["Month", "Left after minimums", "Plan: total owed", "Plan: interest", "", "Min-only: total owed", "Min-only: interest", "", ""]
    for c, h in enumerate(heads, 1):
        e.cell(8, c, h).font = Font(bold=True, size=9)
    sub = ["start", "interest", "minimum", "extra", "left", "end", "min-only start", "min-only interest", "min-only paid", "min-only end"]
    yd = f"'{SHEETS[1]}'!"
    for j in range(1, N + 1):
        c = _col(j, 0)
        idx = f"MATCH({j},{yd}$E$4:$E$11,0)"
        e[f"{c}3"] = f'=IFERROR(INDEX({yd}$A$4:$A$11,{idx}),"")'
        e[f"{c}4"] = f"=IFERROR(INDEX({yd}$B$4:$B$11,{idx}),0)"
        e[f"{c}5"] = f"=IFERROR(INDEX({yd}$C$4:$C$11,{idx}),0)"
        e[f"{c}6"] = f"=IFERROR(INDEX({yd}$D$4:$D$11,{idx}),0)"
        e[f"{c}7"] = f"Debt in plan order {j}: balance, rate, minimum (rows 4-6)"
        e[f"{c}7"].font = Font(size=8, color="999999")
        for k, h in enumerate(sub):
            e.cell(8, C0 + (j - 1) * BLOCK + k, h).font = Font(bold=True, size=9)
    for m in range(1, MONTHS + 1):
        r, p = FIRST + m - 1, FIRST + m - 2
        e[f"A{r}"] = m
        minpays = "+".join(f"{_col(j, 2)}{r}" for j in range(1, N + 1))
        e[f"B{r}"] = f"={yd}$B$16-({minpays})"
        for j in range(1, N + 1):
            s, i_, mn, ex, lf, en, bs, bi, bp, be = (_col(j, k) for k in range(BLOCK))
            prev_left = f"$B{r}" if j == 1 else f"{_col(j - 1, 4)}{r}"
            e[f"{s}{r}"] = f"=${s}$4" if m == 1 else f"={en}{p}"
            e[f"{i_}{r}"] = f"={s}{r}*${s}$5/12"
            e[f"{mn}{r}"] = f"=MIN(${s}$6,{s}{r}+{i_}{r})"
            e[f"{ex}{r}"] = f"=MAX(0,MIN({prev_left},{s}{r}+{i_}{r}-{mn}{r}))"
            e[f"{lf}{r}"] = f"={prev_left}-{ex}{r}"
            e[f"{en}{r}"] = f"={s}{r}+{i_}{r}-{mn}{r}-{ex}{r}"
            e[f"{bs}{r}"] = f"=${s}$4" if m == 1 else f"={be}{p}"
            e[f"{bi}{r}"] = f"={bs}{r}*${s}$5/12"
            e[f"{bp}{r}"] = f"=MIN(${s}$6,{bs}{r}+{bi}{r})"
            e[f"{be}{r}"] = f"={bs}{r}+{bi}{r}-{bp}{r}"
        e[f"C{r}"] = "=" + "+".join(f"{_col(j, 5)}{r}" for j in range(1, N + 1))
        e[f"D{r}"] = "=" + "+".join(f"{_col(j, 1)}{r}" for j in range(1, N + 1))
        e[f"F{r}"] = "=" + "+".join(f"{_col(j, 9)}{r}" for j in range(1, N + 1))
        e[f"G{r}"] = "=" + "+".join(f"{_col(j, 7)}{r}" for j in range(1, N + 1))
    last = FIRST + MONTHS - 1
    for c in range(1, C0 + N * BLOCK):
        e.column_dimensions[L(c)].width = 11
    e.freeze_panes = f"B{FIRST}"

    # ---- 2 Payoff plan
    p2 = wb.create_sheet(SHEETS[2], 2)
    _title(p2, "2 Payoff plan", "What the plan saves against paying only the minimums.", 6)
    rng = lambda col: f"'{SHEETS[5]}'!${col}${FIRST}:${col}${last}"  # noqa: E731
    cap = f'">{MONTHS}"'
    rows = [("Method", f"={yd}B15", "@", False),
            ("Months to debt-free (your plan)", f'=IF({yd}B17<=0,0,IF(COUNTIF({rng("C")},">0.005")>={MONTHS},{cap},COUNTIF({rng("C")},">0.005")+1))', "0", True),
            ("Interest you will pay (your plan)", f"=SUM({rng('D')})", "$#,##0", True),
            ("Months to debt-free (minimums only)", f'=IF({yd}B17<=0,0,IF(COUNTIF({rng("F")},">0.005")>={MONTHS},{cap},COUNTIF({rng("F")},">0.005")+1))', "0", True),
            ("Interest you will pay (minimums only)", f"=SUM({rng('G')})", "$#,##0", True),
            ("Interest saved", "=B8-B6", "$#,##0", True),
            ("Months saved", '=IF(AND(ISNUMBER(B7),ISNUMBER(B5)),B7-B5,"-")', "0", True),
            ("Years to debt-free (your plan)", '=IF(ISNUMBER(B5),B5/12,"-")', "0.0", True)]
    _header(p2, 3, ["Result", "Value", "", "", "", ""])
    for k, (lab, f, fmt, bold) in enumerate(rows):
        r = 4 + k
        _label(p2, f"A{r}", lab, bold=bold)
        _put(p2, f"B{r}", f, fmt=fmt, bold=bold)
    _label(p2, "A13", "Minimums-only figures cover the first 20 years (240 months); a debt that would take longer shows '>240'.")
    p2.merge_cells("A13:F13")
    _header(p2, 15, ["Paid off in this order", "Debt", "Balance", "Rate", "Paid off in month", ""])
    for j in range(1, N + 1):
        r = 15 + j
        en = _col(j, 5)
        c0 = _col(j, 0)
        _put(p2, f"A{r}", j, fmt="0")
        _put(p2, f"B{r}", f"='{SHEETS[5]}'!{c0}3")
        p2[f"B{r}"].alignment = Alignment(horizontal="left")
        _put(p2, f"C{r}", f"='{SHEETS[5]}'!{c0}4", fmt="$#,##0")
        _put(p2, f"D{r}", f"='{SHEETS[5]}'!{c0}5", fmt="0.00%")
        _put(p2, f"E{r}", f'=IF(C{r}>0,IF(COUNTIF({rng(en)},">0.005")>={MONTHS},{cap},COUNTIF({rng(en)},">0.005")+1),"")', fmt="0")
    ch = LineChart()
    ch.title = "Total owed by month: your plan vs minimums only"
    ch.height, ch.width = 9, 22
    ch.add_data(Reference(e, min_col=3, min_row=8, max_row=FIRST + 119), titles_from_data=True)
    ch.add_data(Reference(e, min_col=6, min_row=8, max_row=FIRST + 119), titles_from_data=True)
    ch.set_categories(Reference(e, min_col=1, min_row=FIRST, max_row=FIRST + 119))
    p2.add_chart(ch, "A26")
    p2.conditional_formatting.add("A16:E23", FormulaRule(formula=['$C16>0'], fill=GOOD_FILL))
    _widths(p2, [40, 28, 14, 12, 18, 4])

    # ---- 3 Compound growth
    g = wb.create_sheet(SHEETS[3], 3)
    _title(g, "3 Compound growth", "What a starting amount plus a monthly amount become. Returns are assumptions, never promises.", 5)
    for k, (lab, key, fmt) in enumerate([("Starting amount", "start", "$#,##0"), ("Monthly amount you add", "monthly", "$#,##0"),
                                         ("Expected yearly return (assumption)", "ret", "0.0%"), ("Years", "years", "0")]):
        _label(g, f"A{4 + k}", lab)
        _put(g, f"B{4 + k}", d[key], fmt=fmt, inp=True)
    _label(g, "A9", "Value at the end of your years", True)
    _put(g, "B9", "=FV(B6/12,B7*12,-B5,-B4)", fmt="$#,##0", bold=True)
    _label(g, "A10", "Of which you put in", True)
    _put(g, "B10", "=B4+B5*B7*12", fmt="$#,##0", bold=True)
    _label(g, "A11", "Growth you did not have to earn", True)
    _put(g, "B11", "=B9-B10", fmt="$#,##0", bold=True)
    _label(g, "A12", "Years to double (rule of 72)", True)
    _put(g, "B12", '=IF(B6>0,72/(B6*100),"-")', fmt="0.0", bold=True)
    _header(g, 14, ["Year", "Value", "You put in", "Growth", ""])
    for yr in range(0, 41):
        r = 15 + yr
        _put(g, f"A{r}", yr, fmt="0")
        _put(g, f"B{r}", f"=FV($B$6/12,A{r}*12,-$B$5,-$B$4)", fmt="$#,##0")
        _put(g, f"C{r}", f"=$B$4+$B$5*A{r}*12", fmt="$#,##0")
        _put(g, f"D{r}", f"=B{r}-C{r}", fmt="$#,##0")
    g.conditional_formatting.add("A15:D55", FormulaRule(formula=["$A15=$B$7"], fill=GOOD_FILL))
    ch2 = LineChart()
    ch2.title = "Value vs what you put in"
    ch2.height, ch2.width = 9, 20
    ch2.add_data(Reference(g, min_col=2, min_row=14, max_row=55), titles_from_data=True)
    ch2.add_data(Reference(g, min_col=3, min_row=14, max_row=55), titles_from_data=True)
    ch2.set_categories(Reference(g, min_col=1, min_row=15, max_row=55))
    g.add_chart(ch2, "G3")
    _widths(g, [38, 16, 16, 16, 4])
    g.freeze_panes = "A4"

    # ---- 4 Pay debt or invest
    x = wb.create_sheet(SHEETS[4], 4)
    _title(x, "4 Pay debt or invest?", "Paying a debt saves its interest rate. Investing earns an assumed return, with risk.", 4)
    for k, (lab, key, fmt) in enumerate([("Interest rate of the debt (yearly)", "apr", "0.00%"), ("Extra you could use each month", "x_extra", "$#,##0"),
                                         ("Expected investment return (assumption)", "x_ret", "0.0%"), ("Years", "x_years", "0")]):
        _label(x, f"A{4 + k}", lab)
        _put(x, f"B{4 + k}", d[key], fmt=fmt, inp=True)
    _label(x, "A9", "Value if the extra pays the debt (as long as it exists)", True)
    _put(x, "B9", "=FV(B4/12,B7*12,-B5)", fmt="$#,##0", bold=True)
    _label(x, "A10", "Value if the extra is invested", True)
    _put(x, "B10", "=FV(B6/12,B7*12,-B5)", fmt="$#,##0", bold=True)
    _label(x, "A11", "Verdict", True)
    _put(x, "B11", '=IF(B4>B6,"Pay the debt first: its rate beats your assumed return","Investing may win on paper, but returns are not guaranteed: keep a $1,000 buffer, then compare risk")', bold=True)
    x["B11"].alignment = Alignment(wrap_text=True, vertical="center")
    x.row_dimensions[11].height = 48
    _label(x, "A13", "Rule of thumb: paying off a 24% debt beats almost any assumed return; a 4% loan may not. Paying a debt saves its known rate; investing earns an assumed return, with risk. "
                     "Taxes, employer matches and your own situation change the answer; this is education, not advice.")
    x.merge_cells("A13:D13")
    x.row_dimensions[13].height = 60
    _widths(x, [58, 40, 4, 4])

    for sh in wb.worksheets:
        sh.sheet_properties.tabColor = GOLD if sh.title in (SHEETS[1], SHEETS[2]) else INK
        sh.page_setup.orientation = "landscape"
        sh.page_setup.fitToWidth = 1
        sh.page_setup.fitToHeight = 0 if sh.title == SHEETS[5] else 1     # every tab prints as one page except the 240-row engine
        sh.sheet_properties.pageSetUpPr.fitToPage = True
    wb.properties.title = "Debt Payoff & Compound Interest Planner"
    wb.properties.creator = "Quiet Money"
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "Debt-Payoff-and-Compound-Interest-Planner.xlsx"
    wb.save(out)
    return out


# ---- independent Python simulation of the same rules ------------------------------------------------

def simulate(debts: list[tuple], extra: float, method: str = "Avalanche", months: int = MONTHS) -> dict:
    """Plan (rolled-forward) and minimums-only payoff, month by month, unrounded, exactly as the Engine tab computes."""
    live = [(n, float(b), float(a), float(m)) for n, b, a, m in debts if b and b > 0]
    order = sorted(range(len(live)), key=(lambda i: (live[i][1], i)) if method == "Snowball" else (lambda i: (-live[i][2], i)))
    bal = [live[i][1] for i in order]
    apr = [live[i][2] for i in order]
    mn = [live[i][3] for i in order]
    budget = sum(m for _n, _b, _a, m in live) + extra
    bbal = list(bal)
    plan_months = base_months = None if live else 0
    plan_int = base_int = 0.0
    paid = [None] * len(bal)
    for m in range(1, months + 1):
        ints = [b * a / 12 for b, a in zip(bal, apr)]
        mins = [min(x, b + i) for x, b, i in zip(mn, bal, ints)]
        left = budget - sum(mins)
        for j in range(len(bal)):
            ex = max(0.0, min(left, bal[j] + ints[j] - mins[j]))
            left -= ex
            bal[j] = bal[j] + ints[j] - mins[j] - ex
            if paid[j] is None and bal[j] < 0.005:
                paid[j] = m
        plan_int += sum(ints)
        bints = [b * a / 12 for b, a in zip(bbal, apr)]
        bpay = [min(x, b + i) for x, b, i in zip(mn, bbal, bints)]
        bbal = [b + i - p for b, i, p in zip(bbal, bints, bpay)]
        base_int += sum(bints)
        if plan_months is None and sum(bal) < 0.005:
            plan_months = m
        if base_months is None and sum(bbal) < 0.005:
            base_months = m
    return {"plan_months": plan_months, "plan_interest": plan_int, "base_months": base_months, "base_interest": base_int,
            "order_paid": paid}


def expected_growth(start: float, monthly: float, ret: float, years: int) -> dict:
    r = ret / 12
    n = years * 12
    fv = start * (1 + r) ** n + monthly * ((1 + r) ** n - 1) / r if r else start + monthly * n
    return {"value": fv, "put_in": start + monthly * n, "doubling": 72 / (ret * 100) if ret else None}


def verify_debt(xlsx: Path, **over) -> dict:
    """Recalculate in LibreOffice and compare the headline cells with the Python simulation and moneymath-style growth."""
    d = {**DEFAULTS, **over}
    calc = recalc(xlsx)
    if calc is None:
        return {"ok": None, "rows": [], "errors": ["LibreOffice Calc is not available (install libreoffice-calc): cannot recalculate"]}
    wb = load_workbook(calc, data_only=True)
    p, g, x = wb[SHEETS[2]], wb[SHEETS[3]], wb[SHEETS[4]]
    sim = simulate(d["debts"], d["extra"], d["method"])
    gro = expected_growth(d["start"], d["monthly"], d["ret"], d["years"])
    pay_debt = d["x_extra"] * (((1 + d["apr"] / 12) ** (d["x_years"] * 12) - 1) / (d["apr"] / 12))
    pay_inv = d["x_extra"] * (((1 + d["x_ret"] / 12) ** (d["x_years"] * 12) - 1) / (d["x_ret"] / 12))
    pairs = [("plan months", p["B5"].value, sim["plan_months"]), ("plan interest", p["B6"].value, sim["plan_interest"]),
             ("minimums-only months", p["B7"].value, sim["base_months"]), ("minimums-only interest", p["B8"].value, sim["base_interest"]),
             ("interest saved", p["B9"].value, sim["base_interest"] - sim["plan_interest"]),
             ("growth value", g["B9"].value, gro["value"]), ("growth put in", g["B10"].value, gro["put_in"]),
             ("pay-debt value", x["B9"].value, pay_debt), ("invest value", x["B10"].value, pay_inv)]
    live = [i for i, deb in enumerate(d["debts"]) if deb[1] and deb[1] > 0]
    paid = [p[f"E{16 + j}"].value for j in range(len(live))]
    order = sorted(live, key=(lambda i: (d["debts"][i][1], i)) if d["method"] == "Snowball" else (lambda i: (-d["debts"][i][2], i)))
    for k in range(len(order)):
        pairs.append((f"debt {k + 1} paid off in month", paid[k], sim["order_paid"][k]))
    rows, ok = [], True
    for name, got, want in pairs:
        good = isinstance(got, (int, float)) and abs(got - want) <= max(0.01, abs(want) * 1e-7)
        ok &= good
        rows.append((name, got, round(want, 4), good))
    errors = [f"{ws.title}!{c.coordinate}={c.value}" for ws in wb for row in ws.iter_rows() for c in row
              if isinstance(c.value, str) and c.value.startswith("#")]
    return {"ok": bool(ok and not errors), "rows": rows, "errors": errors, "calc": str(calc)}


def listing(price: float | None = None) -> str:
    price = price if price is not None else config.load().get("forecast", {}).get("product_price", 19.0)
    link = config.load()["channel"].get("link_in_bio", "")
    return f"""# Listing: Debt Payoff & Compound Interest Planner

The owner approves price, copy and the account before anything goes live. Bundle it with the Rat Race Escape Planner later.

## Gumroad
- **Name:** Debt Payoff & Compound Interest Planner (Excel + Google Sheets)
- **Price:** ${price:.0f} (test $12 / $19 / $29 after 20 views)
- **Images:** `preview-1.png` to `preview-5.png` (real screenshots of the file)
- **File:** `Debt-Payoff-and-Compound-Interest-Planner.xlsx`

### Description
See your debt-free date, and how much interest the right plan saves, before you pay another dollar.

**One spreadsheet, five tabs:**
- **Your debts**: up to eight debts with balance, rate and minimum. Choose Avalanche (highest rate first, least interest) or Snowball (smallest balance first, quick wins).
- **Payoff plan**: your debt-free month, total interest, and the interest and months saved against paying only minimums, plus the order each debt disappears.
- **Compound growth**: a starting amount plus a monthly amount, 40 years, with a chart of what you put in vs what compounding added.
- **Pay debt or invest?**: what paying a debt saves (its interest rate) against an assumed investment return, with a plain verdict.
- **Engine (math)**: every month of the calculation in ordinary formulas, so you can check any number. No macros, no scripts, no login.

**Honest notes:** the plan keeps the total monthly payment constant and rolls each paid-off debt's payment onto the next. Interest is calculated monthly with no rounding, so your lender's exact figures will differ slightly. The workbook was recalculated and compared against an independent simulation. It is a planning tool and education, not financial advice.

*Designed by Quiet Money with AI assistance.*

### Tags
debt payoff, debt snowball, debt avalanche, compound interest calculator, budget planner, spreadsheet template, get out of debt, financial freedom

### After-purchase message
Thanks for grabbing the planner. Start on tab 1 and replace the example debts with yours. If a number looks wrong, reply and it gets fixed. More free tools: {link}

## Etsy
Same copy and previews. Use the disclosure line "Designed by Quiet Money with AI assistance" and check Etsy's current Creativity Standards wording before publishing. Digital download, no shipping.

## Rules we keep
No income or savings guarantees, no fake testimonials or scarcity. 30-day refund promise.
"""
