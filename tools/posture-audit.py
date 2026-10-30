"""Posture audit: does a video put the viewer on offense (a move that creates upside) or on defense (avoid, cancel,
protect, escape a trap)? Labels are hand-assigned from the title and script, so they are a judgment, not a measurement.
Run: python tools/posture-audit.py [snapshot.json]  -> prints medians by posture and writes nothing.
"""
import json, statistics as st, sys
from pathlib import Path

O, D, N = "offense", "defense", "neutral"
LABELS = {
    "How George Foreman Turned a Kitchen Appliance Into $138M": O,
    "The Billionaire Who Drove a 1993 Volvo": N,
    "The Mortgage Payoff Trap": D,
    "How to Kill Hidden PayPal Billing Authorizations": D,
    "Why Dollar-Cost Averaging Costs You Money": O,
    "The 1932 Envelope Trick That Beats Budgeting Apps": N,
    "The $18 Million Lottery Winner Who Gave It All Away": D,
    "Why Your Paycheck Carries the Highest Tax": D,
    "The Brutal Math of Starting at 20 vs 30": O,
    "The College Degree ROI Trap": D,
    "The Real HYSA Yield After Taxes and Inflation": N,
    "The Diversification Lie Draining Your Money": O,
    "The 4 Paths to Wealth (And Why Only 2 Set You Free)": O,
    "Cancel Kindle and Audible in 3 Steps": D,
    "The Brutal Cost of Impressing Strangers": D,
    "Why Optimism Bias Destroys Your Savingst": D,
    "Why You Keep Paying for Things You Don't Use": D,
    "The Value Equation Math for Income Growth": O,
    "The Asset vs Liability Cash Flow Trap": N,
    "The exact number that buys your freedom": O,
    "Why Wealth Isn't an Income Problem": N,
    "The 10-Year Delay That Costs $400,130": D,
    "A small leak will sink a great ship.": D,
    "The House Myth That Costs You Fortunes": D,
    "The Math to Replace Your Paycheck Forever": O,
    "The $16 Million Lottery Trap That Ruined William Post": D,
    "Why Earning $100k Still Feels Like Poverty": D,
    "The 0% Interest Trap That Back-Charges Your Purchase": D,
    "Why Skipping Your Daily Coffee Won't Make You Rich": N,
    "The Janitor Who Secretly Died With $8 Million": N,
    "Drop Your Grocery Bill by 20% Today": D,
    "Why Avoiding Credit Cards Costs You More": N,
    "The Front-Loaded Mortgage Shock": D,
    "The $180 Move That Crushed Wall Street": O,
    "Lower Your Cell Phone Bill in 15 Minutes": D,
    "Why Staying at One Company Costs You 50% in Income": O,
    "Why Your Brain Hates Your Future Self": D,
    "The $6,000 Credit Card Trap": D,
    "The $10,000 Offer Shift": O,
    "Wipe Out Hidden App Store Charges Right Now": D,
    "The Subscription Creep Costing You Thousands": D,
    "The Circle That Controls Your Net Worth": N,
    "How to Cancel Credit Card Protection Fees in 15 Minutes": D,
    "The Quiet Leak Draining Your Money": D,
    "The Net Cash Flow Test for Early Freedom": N,
    "Why Your Student Loan Balance Keeps Growing": D,
    "The Math of Leverage: How Debt Wipes People Out": D,
    "The Brand-New Trap Nobody Realizes": D,
    "Why Being the Smartest Person in the Room Keeps You Broke": N,
    "Why You Research Expensive Things Before Buying Them": N,
    "How Nicolas Cage Blew $150 Million": D,
    "The $6,000 credit card mistake that takes 21 years": D,
    "Why Your Cards Keep You Broke": D,
    "The $100M Fortune That Froze Its Owner": D,
    "The Quiet Money Daily Planner: what's inside": N,
    "The Raise Math Nobody Teaches You": O,
    "Kill This Hidden Bank Fee Today": D,
    "Why Paid Ads Bankrupt New Businesses": D,
    "How to Build a Personal Monopoly": O,
    "Why You Irrationally Overvalue Things You Own": D,
    "Why your brain treats tax refunds like free money": D,
    "The Price Tag Hidden Behind Your Monthly Life": D,
    "When Paper Money Broke a Country": D,
    "Why Tired Brains Buy Stuff at Night": D,
    "The Hidden Direction of Your Cash Flow": N,
    "Why Your Budget Fails (And How to Fix It)": D,
    "The Silent Checking Account Trap": D,
    "The mountain doesn't care how long you trained": N,
}


def main(path):
    rows = json.load(open(path))["shorts"]
    by = {O: [], D: [], N: []}
    missing = [r["title"] for r in rows if r["title"] not in LABELS]
    for r in rows:
        if r["title"] in LABELS:
            by[LABELS[r["title"]]].append(r["views"])
    for k, v in by.items():
        if v:
            print(f"{k:8s} n={len(v):2d} median={st.median(v):5.1f} mean={st.mean(v):5.1f} best={max(v)} zero-or-near={sum(x<=5 for x in v)}")
    if missing:
        print("unlabelled:", missing)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent.parent / "analytics/snapshots/youtube-2026-10-29.json"))
