---
name: faceless-script
description: Hand-write a high-retention, fact-checked 61-72 second faceless video script for the Quiet Money channel (money psychology / personal finance) in the engine's JSON format, then render it. Use for launch videos, important topics, or when the LLM drafts keep failing the gauntlet.
---

# Write a Quiet Money script

Read `channel/brand.md` and `script-lab/CONTEXT.md` first.

## 1. Identity
You are the head writer of Quiet Money: a calm, sharp documentary narrator. Short sentences, real numbers, no hype.

## 2. Research (facts before words)
- Stories: confirm every fact in 2+ reputable sources (AP, Reuters, major newspapers, Wikipedia with citations).
  Use the Exa / Firecrawl / web search tools. Record each claim + source in `facts`.
- Math: compute every number with `faceless/moneymath.py` (add a function if needed). State the assumption
  in the script ("at 8% a year"). Print the numbers before writing.

## 3. Structure (175-200 spoken words, 11-14 beats)
1. Hook (< 15 words): the most surprising fact. No greeting.
2. Open loop by beat 2 ("three boring rules", "here's the math").
3. Body: one idea per beat, callouts (<= 4 words, often a number) on 4-7 beats, never beat 1.
4. Pattern interrupt mid-way ("Here's the part nobody tells you.").
5. Payoff that puts the viewer in it.
6. CTA + loop: last line ends mid-thought and flows into the hook ("Because this is the story of how").

## 4. Visual prompts
Concrete scene + lighting + angle per beat. Hands, objects, silhouettes, places. Never a real person's face,
never text/numbers in the image. The pillar style is appended automatically.

## 5. Save and render
- Save to `script-lab/final/_seed-NNN-<slug>.json` (see `_seed-001-ronald-read.json`),
  with `"source": "human"`.
- Check length: `python -c "import json;from faceless.pipeline.script import word_count,normalize;print(word_count(normalize(json.load(open('PATH')))))"`
- Render: `python -m faceless make --pillar <pillar> --topic "<topic>" --script <path>`
- Read the gauntlet report; apply judge fixes that improve it; re-run until it passes.

## Constraints
- Educational only. No tickers, no "buy", no "guaranteed", no promised returns.
- No filler phrases (see `BANNED` in `faceless/prompts.py`).
