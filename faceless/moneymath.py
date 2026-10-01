"""Exact money math. LLMs are bad at arithmetic; the script writer only quotes numbers from here."""

from __future__ import annotations


def future_value_monthly(monthly: float, annual_rate: float, years: int) -> float:
    r, n = annual_rate / 12, years * 12
    return monthly * n if r == 0 else monthly * ((1 + r) ** n - 1) / r


def lump_sum_growth(principal: float, annual_rate: float, years: int) -> float:
    return principal * (1 + annual_rate) ** years


def card_payoff(balance: float, apr: float, payment: float, max_months: int = 1200) -> tuple[int, float]:
    """Months to pay off and total interest paid with a fixed monthly payment."""
    months, interest = 0, 0.0
    while balance > 0.005 and months < max_months:
        i = balance * apr / 12
        if payment <= i:
            return max_months, float("inf")
        interest += i
        balance = balance + i - payment
        months += 1
    return months, interest


def card_minimum_payoff(balance: float, apr: float, pct: float = 0.01, floor: float = 25.0) -> tuple[int, float]:
    """Typical US minimum: 1% of balance + that month's interest, at least $25."""
    months, interest = 0, 0.0
    while balance > 0.005 and months < 1200:
        i = balance * apr / 12
        pay = min(balance + i, max(floor, balance * pct + i))
        interest += i
        balance = balance + i - pay
        months += 1
    return months, interest


def inflation_value(amount: float, rate: float, years: int) -> float:
    return amount / (1 + rate) ** years


def rule_of_72(rate_pct: float) -> float:
    return 72 / rate_pct


def money(x: float) -> str:
    return f"${x:,.0f}"


def fact_sheet() -> str:
    """Pre-computed, verifiable numbers the writer may quote (assumptions stated in each line)."""
    lines = ["MONEY FACT SHEET (computed by code; quote exactly, keep the stated assumption):"]
    for m in (100, 200, 500):
        for y in (20, 30, 40):
            lines.append(f"- {money(m)}/month invested for {y} years at 8%/yr (monthly compounding) "
                         f"= {money(future_value_monthly(m, 0.08, y))} (you put in {money(m * 12 * y)})")
    a = future_value_monthly(200, 0.08, 40)
    b = future_value_monthly(200, 0.08, 30)
    lines.append(f"- Starting at 25 vs 35 with $200/month at 8% until 65: {money(a)} vs {money(b)} "
                 f"(10 years late costs {money(a - b)})")
    for bal in (3000, 6000):
        mo, it = card_minimum_payoff(bal, 0.24)
        lines.append(f"- {money(bal)} credit card at 24% APR paying only the minimum (1% + interest, min $25): "
                     f"{mo} months (~{mo / 12:.0f} years), {money(it)} interest")
        mo2, it2 = card_payoff(bal, 0.24, 300)
        lines.append(f"- Same {money(bal)} at 24% paying $300/month: {mo2} months, {money(it2)} interest")
    for fee in (0.01, 0.0005):
        bal = lump_sum_growth(100000, 0.07 - fee, 30)
        lines.append(f"- $100,000 for 30 years at 7% minus a {fee * 100:.2f}% annual fee = {money(bal)}")
    lines.append(f"- $100 today is worth {money(inflation_value(100, 0.03, 20))} in buying power after 20 years of 3% inflation")
    lines.append(f"- Rule of 72: at 8% money doubles every {rule_of_72(8):.0f} years; at 24% debt doubles every {rule_of_72(24):.0f} years")
    lines.append(f"- $5/day habit = {money(5 * 365)}/year; invested monthly at 8% for 30 years = "
                 f"{money(future_value_monthly(5 * 365 / 12, 0.08, 30))}")
    lines.append(f"- A $15/month subscription for 10 years = {money(15 * 120)}")
    return "\n".join(lines)
