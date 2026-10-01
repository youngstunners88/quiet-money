# Script lab: the writing room

Ideas go in, gated scripts come out. Read `../channel/brand.md` first; it is the voice.

## Folders
- `ideas/backlog.jsonl`: one topic per line `{pillar, topic, angle, hook}`. The engine takes the first unused,
  non-duplicate topic for a pillar; when a pillar runs dry it asks the LLM for 8 more and appends the fresh ones.
- `drafts/`: every LLM draft, per rewrite round (`<job_id>.r0.json`, `.r1.json`...). Useful to see what the gauntlet fixed.
- `final/`: the script each video was rendered from. Hand-written seeds start with `_seed-`.

## Script anatomy (JSON)
```json
{
  "title": "<= 60 chars, curiosity + specificity",
  "hook_text": "ON-SCREEN HOOK, 2-7 WORDS",
  "beats": [{"say": "1-2 spoken sentences", "callout": "optional big text, <= 4 words", "visual": "image prompt"}],
  "caption": "TikTok/IG caption + 4-5 hashtags",
  "description": "2-3 sentence summary",
  "hashtags": ["#money", "..."],
  "first_comment": "a question that invites replies",
  "facts": [{"claim": "...", "basis": "source or moneymath function"}]
}
```

## The 60-second structure
| Seconds | Beat | Job |
|---|---|---|
| 0-3 | Hook | The single most surprising fact. No greeting. On-screen hook box repeats it. |
| 3-8 | Open loop | Promise the payoff ("three boring rules", "here's the math") |
| 8-50 | Body | 6-9 beats, one idea each, a callout number every 2-3 beats, a pattern interrupt mid-way |
| 50-62 | Payoff | The lesson, stated plainly, with the viewer in it ("you don't need his 50 years...") |
| 62-68 | CTA + loop | Follow CTA, last line ends mid-thought and flows into the hook on replay |

## Process
1. **Pick** a topic: `python -m faceless ideas --pillar math --n 3` (or add your own lines to the backlog).
2. **Write** (automatic): the five-part prompt in `faceless/prompts.py` (identity, task, context with a
   computed money fact sheet, constraints, output format).
3. **Gate**: code checks (length, hook, compliance words, originality) + an LLM judge (hook, retention,
   value, factual risk, compliance risk). Failures go back as rewrite instructions, max 2 rounds.
4. **Hand-write** when it matters (launch videos, sponsored topics): save JSON in `final/` and run
   `python -m faceless make --pillar story --script final/_seed-002-....json`. Human scripts are never rewritten by the LLM.

## Rules
- Spoken length 175-200 words (61-72 s at the house voice pace).
- Numbers: only from the fact sheet (`faceless/moneymath.py`) or a documented source in `facts`.
- Visual prompts: concrete scene + lighting + angle; no faces of real people, no text in images.
