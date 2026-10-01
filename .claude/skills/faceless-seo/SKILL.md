---
name: faceless-seo
description: Build, deploy, and grow the Quiet Money website (Money Rules Library) for search and AI-answer visibility. Regenerate pages with schema.org markup, sitemap, robots, llms.txt, and RSS; ping IndexNow; verify Search Console/Bing; and run backlink and citation outreach. Use for anything about the website, SEO, indexing, structured data, or backlinks.
---

# Website SEO

The playbook and its sources: `channel/seo-playbook.md`. Code: `faceless/site.py`.

## Build and check locally
```bash

python -m faceless site build          # -> site/ (every published video becomes /rules/<slug>/)
cd site && python -m http.server 8765  # open http://localhost:8765
```
Verify before shipping:
- Every page fits a 360 px viewport (no horizontal scroll); the hook, rule, and key numbers are above the fold.
- JSON-LD parses (`python -c "import json,re,sys; [json.loads(m) for m in re.findall(r'ld\+json\">(.+?)</script>', open('site/index.html').read())]"`).
- `sitemap.xml` lists every page; `robots.txt` allows the AI crawlers; `llms.txt` lists every rule.

## Deploy
Push to the default branch: `.github/workflows/site.yml` builds and deploys to GitHub Pages, then
runs `python -m faceless site indexnow` so Bing (ChatGPT's main index) hears about new pages the same day.
First deploy only: repo Settings → Pages → Source: **GitHub Actions**.

## One-time owner steps
- Google Search Console → add URL-prefix property for `[site].base_url` → HTML tag method → paste the token in
  `studio.toml [site].google_verification` → push → Verify → submit `sitemap.xml`.
- Bing Webmaster Tools → import from Search Console (or paste `bing_verification`).

## Page rules (what makes a page citable)
- One rule per page; the H1 is the question it answers; the "The rule:" sentence states the answer plainly
  (answer engines extract verbatim snippets).
- Numbers come from `moneymath.py`; stories list sources. FAQ answers are direct, 1-2 sentences.
- Stay on topic: money rules only (topical centrality).

## Growth loop
1. Weekly: `python -m faceless aeo` (see `faceless-aeo`): which URLs do engines cite for our entities?
2. Those listicles and pages are the outreach list: ask to be included, link the best-matching rule page.
3. Log every backlink and submission in `analytics/backlinks.md` (date, URL, status).
