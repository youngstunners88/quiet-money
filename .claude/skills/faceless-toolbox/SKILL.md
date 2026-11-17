---
name: faceless-toolbox
description: Find a reviewed tool for understanding how a website, app, file format, binary or protocol works, from the local copy of the Awesome REA catalog, before spending tokens on a web search or writing one from scratch. Use when a task needs to read an undocumented API, inspect app traffic, automate an Android screen, decompile something, or when asked what tool exists for a reverse-engineering job. Covers the search command, how to vet a find, and what this studio never does with such tools.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/toolbox.py
---

# The toolbox

About 1,100 tools, agent integrations and guides from [Awesome REA](https://github.com/reacher-z/Awesome-REA) (MIT), searchable
offline. Search is word overlap: no model, no network.

```bash
python -m faceless toolbox find "capture app traffic and write an OpenAPI spec"
python -m faceless toolbox find "inspect android ui hierarchy" --target app -n 5
python -m faceless toolbox show <id>          # requirements and the reviewed link
python -m faceless toolbox find "tiktok" --cases   # how others took something similar apart
python -m faceless toolbox sync               # refresh the copy (two public files; nothing is sent)
```

`--target` is one of `website`, `app`, `binary`, `firmware`, `protocol`, `game`.

## Use it in this order

1. **Say the need in plain words** and search. Try two phrasings before deciding nothing fits.
2. **Read `show <id>`**: requirements first. A tool that needs a paid licence or a rooted phone is not a fit here.
3. **Vet before installing**: `python -m faceless intake <url>`. It reads metadata and red flags and installs nothing. The catalog's
   "source-reviewed" means its documentation was read, not that the tool was run or is safe.
4. **Prefer the smallest thing**: an official API or export beats a captured private one; a documented endpoint beats a UI script.
5. **Nothing fits**: `python -m faceless crew ask research "what you need" --agent <your-id>` opens a card for a better-suited agent (`faceless-crew`).

## What we use these for

- Our own accounts, files and devices: our phone, our exports, our pages, our analytics.
- Reading public pages and documented or openly served data.
- Learning how a format or a flow works so the engine can do its own job with fewer steps and fewer tokens.

## What we never do

- Get past a login, a block, a rate limit, a paywall or a bot check. A 403 is an answer: report it and stop (CLAUDE.md rule 10).
- Read anyone's private data, or automate sending, following or messaging on a platform (rule 9: the owner sends).
- Install or run a find without the intake step, or put a key in a tool's config file (rule 1).
