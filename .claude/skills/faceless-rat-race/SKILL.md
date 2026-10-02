---
name: faceless-rat-race
description: Run Quiet Money's "Escape the Rat Race" series, income-building frameworks from Alex Hormozi, Robert Kiyosaki, and Dan Peña plus passive-income math, for viewers who want side income and to leave the paycheck-to-paycheck cycle. Make a batch now, add topics, add a new figure, and keep the series bold but honest. Use when asked for passive income, side hustle, "escape the rat race", aggressive income tactics, or videos about Hormozi, Kiyosaki, or Peña.
---

# Escape the Rat Race (pillar `escape`)

The series runs on automation: weight 1.5 in `studio.toml` gives it a slot in every daily batch, topics come
from the backlog (then from LLM ideation limited to people with research briefs), and every script is checked
against its brief by the judge. Humans only add briefs and topics.

## What a video is
1. Hook: one true, specific line ("He says he started an oil company with $820.").
2. Credit the idea to its author by name within the first 3 beats (gate: `pillar_structure`).
3. The framework in plain words (Value Equation, Rule of 100, asset vs liability, OPM...).
4. One real number from the fact sheet (`faceless/moneymath.py`: the 4% rule, years to reach it, Rule of 100 volume).
5. One concrete move the viewer can make this week.
6. The honest catch: effort, risk, debt, or what critics say (also required by the gate).
Tone: aggressive and direct about effort and action; never hype about results. No promised income.

## Make videos now
```bash
python -m faceless daily --extra 5 --pillar escape   # 5 series videos; they bank into the next free slots
python -m faceless make --pillar escape --topic "<exact backlog topic>"   # one specific topic
```
Then follow `faceless-daily` (review report, spot-check frames, commit state, send videos).

## Add topics or a new figure
- Topics for existing people: append backlog lines with `"brief": "hormozi" | "kiyosaki" | "pena"` or `""` for
  pure passive-income math (see `faceless-research` step 3).
- A new person (e.g. another builder or investor): run the `faceless-research` skill first; no brief, no videos.

## Guardrails (the gauntlet enforces most; you enforce the rest)
- Self-reported numbers keep "he says". Kiyosaki's predictions are never stated as facts.
- No "quit your job", "guaranteed", or income promises; business and real-estate tactics always carry their risk
  (most new businesses close within five years; leverage magnifies losses).
- Faces of real people never appear; visuals are hands, offices, skylines, documents at an angle.
- The channel teaches their ideas; it is not affiliated with them. Never imply endorsement.

## Weekly
Compare the series' retention and follows with the other pillars (`faceless-analytics`). If it wins, raise its
weight to 2.0 (max 2 slots a day); if a person's topics underperform, rotate in a new brief.
