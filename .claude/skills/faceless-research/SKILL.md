---
name: faceless-research
description: Deep-dive research on a person, book, or money framework (e.g. Alex Hormozi, Robert Kiyosaki, Dan Peña) and turn it into a verified research brief plus backlog topics that the automated daily batch uses on its own. Use when asked to research someone for videos, add a new figure or framework to a series, fact-check claims about a real person, or when a held video's judge flags unsourced claims about a person.
---

# Research → brief → automated videos

A brief is a short, verified note in `channel/research/<id>.md`. The engine loads it automatically:
backlog topics carry `"brief": "<id>"`, the script writer may state ONLY the brief's facts about that person,
and the fact-check judge scores claims against it. Once a brief and its topics exist, the daily routine makes
those videos with no further human work, so the brief is the quality gate. Get it right.

## 1. Research (verify, don't collect)
Use WebSearch / WebFetch. For every fact you keep:
- Prefer primary or neutral sources: Wikipedia, court records, company filings, the person's own posts and
  books, major outlets. Blog summaries are fine for what a framework says, never for biography numbers.
- Self-reported numbers (net worth, "turned $820 into $450M") go under "His own claims" and are always
  voiced with "he says". Disputed facts: leave out, or state both sides.
- Collect criticism too (lawsuits, bankruptcies, disputed stories, debt). Every video needs an honest catch.
- Keep what supports a 60-second video: dated facts, exact numbers, named frameworks, one or two short quotes
  that are verifiably theirs.

## 2. Write the brief (`channel/research/<id>.md`, id = lowercase surname, ascii)
Sections, in this order (the engine strips everything from `## Sources` down before prompting):
```
# Full Name
Researched YYYY-MM-DD. Use only what is below; anything else needs a new source first.
## Verified facts (attribute them)
## His/Her own claims (only with "he says")      <- if any
## Frameworks (explain in plain words, credit them)
## The honest catch (every video names one)
## Never
## Sources
```
Keep it under ~45 lines: it is injected into every prompt for that person's topics.

## 3. Add topics to the backlog
Append JSON lines to `script-lab/ideas/backlog.jsonl`:
`{"pillar": "escape", "topic": "...", "angle": "...", "hook": "...", "brief": "<id>"}`.
One framework or fact per topic; the hook must be true as written. Interleave people so a batch doesn't
make five videos about the same person. Other pillars can use briefs too (e.g. a `story` about a real person).

## 4. Check before automation picks it up
```bash
python -c "from faceless import research; print(research.brief('<id>'))"   # loads, no Sources section
python -m pytest -q tests
python -m faceless make --pillar escape --topic "<exact topic from the backlog>"   # one test video
```
Read the gauntlet report: `judge_facts` must pass and `suspect_claims` should be empty. If the judge flags a
claim that is true, add its source to the brief instead of weakening the gate.

## Never
- Put a claim in a brief you could not source. Copy long passages from books (short quotes only, attributed).
- Imply the person endorses or knows the channel. Show their face in visuals.
- Write a key or token into a brief (briefs are public in the repo).
