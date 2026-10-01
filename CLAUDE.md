# Quiet Money Studio

I run **Quiet Money**, a faceless short-form channel (TikTok, YouTube Shorts, Instagram Reels)
about money psychology and personal finance for 18-40 year olds who feel behind with money.
Tagline: *The money rules nobody taught you.* Output: **5 videos a day**, 61-72 seconds,
cinematic AI stills + neural voiceover + word-by-word captions. The engine runs without a human;
humans set strategy, connect accounts, and review held videos.

## Workspaces

- `/channel`: brand, audience, pillars, monetization, compliance (the "why" and the rules)
- `/script-lab`: ideas backlog, drafts, final scripts (the writing room)
- `/production`: rendering pipeline, visual style, output (the edit bay)
- `/distribution`: posting packs, platforms, schedule (the shipping dock)
- `/analytics`: metrics in, pillar weights out (the scoreboard)
- `/gauntlet`: quality gates and reports (the QA desk)
- `/repo-farm`: which external repos/tools we use, park, or reject
- `/faceless`: the engine (Python). `/state`: journal, jobs, ledger, decisions

## Routing

| Task | Go to | Read | Skill |
|---|---|---|---|
| Produce today's batch | `/` | this file | `faceless-daily` |
| Write or fix a script | `/script-lab` | `script-lab/CONTEXT.md`, `channel/brand.md` | `faceless-script` |
| Find new topics / trends | `/script-lab/ideas` | `script-lab/CONTEXT.md` | `faceless-trends` |
| Change look, voice, music, captions | `/production` | `production/CONTEXT.md` | n/a |
| Post, schedule, platform settings | `/distribution` | `distribution/CONTEXT.md` | `faceless-publish` |
| Review performance, re-weight pillars | `/analytics` | `analytics/CONTEXT.md` | `faceless-analytics` |
| Quality problems, failed gates | `/gauntlet` | `gauntlet/CONTEXT.md` | `faceless-gauntlet` |
| Money: affiliates, products, rewards | `/channel` | `channel/monetization.md` | n/a |
| Engine code: providers, routing, state | `/faceless` | `faceless/CONTEXT.md` | n/a |
| Add / evaluate a repo or tool | `/repo-farm` | `repo-farm/registry.md` | n/a |
| Create/rebrand channels, brand kit, profiles | `/channel` | `channel/profiles.md` | `faceless-channel-setup` |
| Website, SEO, indexing, backlinks | `/faceless/site.py` | `channel/seo-playbook.md` | `faceless-seo` |
| AI-assistant visibility (ChatGPT/Claude/Gemini) | `/analytics` | `channel/seo-playbook.md` | `faceless-aeo` |
| Grow reach, "go viral", weekly growth review | `/analytics` | `analytics/CONTEXT.md` | `faceless-growth` |
| Connect an app (YouTube, TikTok, Drive...), pull channel stats | `/faceless/providers` | `composio_tools.py` | `faceless-composio` (+ `composio`) |

## Commands (run from this folder)

```bash
python -m faceless doctor                      # tools, fonts, keys
python -m faceless daily                       # the day's 5 videos, gated + packaged
python -m faceless make --pillar story         # one video, topic from the backlog
python -m faceless make --pillar math --script path.json   # one video from a hand-written script
python -m faceless gauntlet <job_id>           # re-run every gate on a finished job
python -m faceless status                      # today's jobs + spend
python -m faceless composio status             # connected apps (Composio)
python -m faceless site build                  # Money Rules Library website -> site/
python -m faceless aeo                         # AI answer-engine visibility probe
python -m faceless brand                       # regenerate the brand kit
python -m pytest -q tests                      # engine tests
```

## Naming conventions

- Job id: `YYYY-MM-DD-s<slot>-<pillar>-<topic-slug>`
- Final scripts: `script-lab/final/<job_id>.json`; hand-written seeds: `script-lab/final/_seed-NNN-<slug>.json`
- Drafts: `script-lab/drafts/<job_id>.r<round>.json`
- Renders: `production/output/<day>/<job_id>/final.mp4` (+ voice.json, images.json, captions.ass, meta.json)
- Posting packs: `distribution/queue/<day>/slot<N>-<pillar>/` (video.mp4, cover.jpg, POST.md, meta.json)
- Gauntlet reports: `gauntlet/reports/<job_id>.md|json`, daily: `gauntlet/reports/daily-<day>.md`

## Rules

1. Every number is true. Calculations come from `faceless/moneymath.py`; stories come from documented facts.
2. Education, never advice: no "buy this stock/coin", no promised returns. Disclaimers go in every description.
3. Real people are never shown by face: hands, silhouettes, objects, places.
4. AI disclosure label ON for every post (TikTok AI-generated toggle, YouTube "altered or synthetic").
5. Five pillars rotate daily with different looks, keys, and formats. Never ship near-duplicates.
6. Nothing ships below gauntlet score 80 or with a hard-gate failure; those are held for review.
7. Free providers first; paid fallbacks are capped in the ledger.
