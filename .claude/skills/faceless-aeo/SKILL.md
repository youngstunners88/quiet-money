---
name: faceless-aeo
description: Measure and improve whether AI assistants (ChatGPT, Claude, Gemini, Perplexity) recommend, mention, and cite Quiet Money. Run quantized visibility probes, mine the cited sources for outreach, reverse pages into target prompts, and run on-page experiments. Use for AI visibility, answer-engine optimization, "are we showing up in ChatGPT", or citation mining.
---

# Answer-engine optimization (AEO)

Method from the Ahrefs × Dan Petrovic research (summarized in `channel/seo-playbook.md`):
assistants search an index (GPT ≈ Bing, Claude ≈ Brave, Gemini ≈ Google), re-rank, and recommend through their
own trained bias. You can't buy prompt volume (it doesn't exist); you measure fixed probes over time.

## Probe (weekly; ~$0.20 via OpenRouter)
```bash

python -m faceless aeo                       # all engines x studio.toml [aeo].entities
python -m faceless aeo --engines perplexity  # one engine
```
Writes one row per engine x entity to `analytics/aeo.jsonl`: recommended names, our position, mentioned,
cited URLs, our citation share. Report: mention rate, mean position when mentioned, citation share, and the
top recommended competitors. Trends need several weeks; never conclude from one run.

## Citation mining (turn probes into actions)
1. Collect the `cited` URLs across rows; group by domain. These pages feed the answers.
2. For listicles ("best personal finance channels"), draft a short inclusion pitch with the best-matching
   library page (`faceless-seo` outreach log).
3. For topics where a weak page is cited, write a better rule page and video on that exact question.

## Page → prompts
```python
from faceless import aeo
aeo.page_to_prompts(open("site/rules/<slug>/index.html").read())
```
Add the best prompts as entities (quantized) or as backlog topics.

## On-page experiments (one variable at a time)
Change one element on a rule page (the "The rule:" sentence, the FAQ, the title), deploy, re-probe the matching
entity for 2+ weeks, keep the variant only if position/mention rate improves. Log experiments in
`analytics/aeo-experiments.md`.

## Never
Spam pages, fake reviews, or prompt-injection text on pages. Quality filters detect them (the same compression
trick our `voice_quality` gate uses) and they damage the brand in model training.
