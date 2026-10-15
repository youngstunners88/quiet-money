---
name: faceless-paper-collage
description: Make a Vox-style torn-paper collage explainer for Quiet Money at low cost, with Claude Opus 5.5 on OpenRouter writing the whole video (script, one-keyword callouts, paper-collage scene directions) and the free pipeline rendering it. Method taken from holy-templar/vox-animated-ad-mcp without its paid MaxFusion service. Use when asked for a Vox-style, paper-collage, editorial explainer, a creative motion-graphics experiment, or to save cost and rate limit on a special video.
---

# Faceless paper collage

## Why this and not the repo's tool
The study repo (`holy-templar/vox-animated-ad-mcp`, AGPL-3.0) drives a paid generation service (MaxFusion, Google Omni, 10-second clips, "per-clip costs apply, no upfront quote"). We take its method and leave the service: no key, no per-clip bill, no code or text copied (AGPL).

## The method we keep
1. One idea per line; cold-open on the strangest true detail; a curiosity gap that escalates; end on one insight to use today.
2. One keyword or 1-3 words on screen per beat. Never subtitles or full sentences.
3. One locked look in every shot: torn paper, hand-cut cutouts, drop shadows, warm off-white ground, black ink, one burnt-orange and one teal accent (`collage.LOOK`, repeated in every scene because each image is made alone).
4. Motion explains, never decorates: each scene is a visual metaphor for the beat (stacked coins, a torn calendar, a splitting clock).
5. Gates before spend: script and scene list are read by the owner first. Numbers come only from `faceless/moneymath.py` (rule 1).
6. Faceless: no people, no faces (rule 3).

## Steps (cheap on rate limit)
1. `python3 -c "from faceless import collage; s = collage.write('TOPIC', 'ANGLE'); print(s['_path'], s['_check'])"` runs Opus 5.5 once (about $0.09, cap `collage.CAP_USD`) and writes `script-lab/final/_collage-<topic>.json`. Check `_check`: word count 175-200 and `numbers_not_in_fact_sheet` empty or only results of the Rule of 72 (72 divided by a rate).
2. Render free: `python -m faceless make --pillar math --script script-lab/final/_collage-<topic>.json --no-publish` (images from the free providers first; HyperFrames cards for numbers). `--no-publish` is for owner review of a new style only; once the owner says go, drop it and the video joins the normal flow.
3. Frame-check the output, send it to the owner, and ask for go before any posting or series use.
4. To change the topic, only the `collage.write` arguments change. Real people need a research brief first (rule 8).

## Hard rules
- Education only; no returns, no income claims; AI label on. The paid MaxFusion MCP is not connected and is not to be.
- Spend: `[collage]` usage shows in the ledger as `collage:usd`; the studio ceiling and `state/PAUSE` apply.
