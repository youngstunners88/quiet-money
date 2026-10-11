import sys, types
from pathlib import Path
from faceless.pipeline import cards
from faceless import config
style = sys.argv[1]
job = types.SimpleNamespace(id="sample-"+style, dir=Path("state/tmp/ledger")/style, artifacts={"style": style}, pillar="escape")
job.dir.mkdir(parents=True, exist_ok=True)
script = {"beats": [
 {"say": "Quit your job forever", "callout": "", "visual": ""},
 {"say": "Three thousand a month needs about nine hundred thousand invested.", "callout": "$900,000"},
 {"say": "That is the four percent rule: twelve times your yearly spend, times twenty-five.", "callout": "4% RULE"},
 {"say": "Save five hundred a month and it takes thirty-four years.", "callout": "34 YEARS"},
 {"say": "Save two thousand a month and it takes eleven.", "callout": "$500 VS $2,000"},
 {"say": "First, count your real monthly spend, not your salary.", "callout": "STEP ONE"},
 {"say": "Second, multiply by three hundred.", "callout": "STEP TWO"},
 {"say": "The number is smaller than you think, and the gap is your savings rate.", "callout": ""},
 {"say": "Raise the rate before you chase the return.", "callout": "SAVINGS RATE"},
]}
picked = cards.pick(script, None, "escape", "ledger" if style == "ledger" else "cinematic")
if style != "ledger":   # the house look for the same beats, for a side by side
    picked = {i: ({"kind": "phrase", "text": cards.key_phrase(b)} if not cards.parse_number(b.get("callout","")) else {"kind":"stat", **cards.parse_number(b["callout"])}) for i, b in enumerate(script["beats"]) if i}
    picked[4] = cards.parse_compare("$500 VS $2,000"); picked[5] = cards.parse_step("STEP ONE", script["beats"][5]["say"]); picked[6] = cards.parse_step("STEP TWO", script["beats"][6]["say"])
spans = {i: (i*5.0, i*5.0+5.0) for i in range(len(script["beats"]))}
print({i: s["kind"] for i, s in picked.items()})
r = cards.render_reel(job, picked, spans, "escape", "#FFD23F", 30)
print(r)
