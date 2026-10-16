---
name: faceless-comics
description: Quiet Money's second series, funny hand-drawn stick-figure comics posted as picture posts (the channel's Posts tab, not video), five a day. Use when asked for the comics series, picture posts, funny illustrations, daily comic batch, or to change their style, captions or theme.
---

# Faceless comics

## What it is
One picture, one gag about money psychology, then a caption people read after the picture. Black line art on white, gold highlight on the punchline, QUIET MONEY wordmark on top, @QUIETMONEYRULE footer. Size 1080x1350.

## Run it
`python -m faceless comics` makes five (`--n`, `--theme "rent"`, `--day`, `--reference IMG` to recreate a picture the owner supplies). Cost is about $0.21 a batch (Opus 5.5 on OpenRouter), capped at $1 a day in the ledger.
Output: `distribution/comics/<day>/NN-slug/picture.png`, `POST.md` (caption, hashtags, alt text, the joke), `comic.json`.

## Rules
- Text is drawn by the engine from fonts, so spelling is exact; the model only supplies line art and words. SVG is whitelisted (no script, links, images).
- Caption: 40-300 characters, no link, no money promise, passes the offer claim check. It must not repeat the picture's words.
- Never repeat a joke (the engine passes earlier ones to the model). Quotes are shown as "attributed to", never stated as fact (rule 8).
- Real people never drawn by face. Post text ends "Illustrated with AI. Education and humour, not financial advice."
- Look at the pictures before sending: text inside the frame, punchline readable, gag lands.

## Delivery
YouTube's API cannot publish Community posts. Two ways to get them out:
1. **The YouTube Posts MCP** (`mcp-servers/yt-community`, README inside): runs on the owner's own computer, drives their signed-in browser, dry run first, publishing only with `QM_COMMUNITY_APPROVED=1`. Untested against the live page until the owner's first dry run.
2. By hand: Studio, Create, Create post, Image, with the caption from POST.md.
Other platforms (Instagram, Facebook, Pinterest) go through a Composio connect link the owner approves, and only with the owner's yes (rule 9).
