# Intake: muapi-cli

- **Source:** https://pypi.org/project/muapi-cli/
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** Official CLI for muapi.ai — generative media at your fingertips

| fact | value |
|---|---|
| version | 0.2.7 |
| license | MIT |
| pushed | 2026-06-15T05:32:17.749731Z |

## Red flags

- **HIGH `asks-for-secrets`:** asks you to paste a key, password or seed phrase
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **INFO `needs-keys`:** mentions keys: MUAPI_API_KEY, NEW_KEY, YOUR_KEY, YOUR_MUAPI_KEY

## Commands its docs tell you to run (read, do not run)

```
npm install -g muapi-cli
pip install muapi-cli
npx muapi-cli --help
claude mcp add --transport http muapi \
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# muapi CLI

Official command-line interface for [muapi.ai](https://muapi.ai) — generate images, videos, and audio directly from your terminal.

**Agent-first design** — every command works for both humans (colored output, tables) and AI agents (`--output-json`, `--jq` filtering, semantic exit codes, MCP server mode).

## Related Projects

- [Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) — Browser-based GUI for the same models — no CLI required
- [Awesome-GPT-Image-2-API-Prompts](https://github.com/Anil-matcha/Awesome-GPT-Image-2-API-Prompts) — Curated prompt library to run via this CLI

## Install

'''bash
# npm (recommended — no Python required)
npm install -g muapi-cli

# pip
pip install muapi-cli

# or run without installing
npx muapi-cli --help
'''

## Quick Start

'''bash
# New user? Create an account
muapi auth register --email you@example.com --password "..."
muapi auth verify --email you@example.com --otp 123456
muapi auth login --email you@example.com --password "..."

# Or paste an existing API key
muapi auth configure --api-key "YOUR_KEY"

# Generate — pick a curated verb…
muapi image generate "a cyberpunk city at night" --model flux-dev
muapi video generate "a dog running on a beach" --model kling-master
muapi audio create "upbeat lo-fi hip hop for studying"

# …or run any model by endpoint name (schema-driven, covers the whole catalog)
mua
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: visuals.

MIT, 386 downloads a week. The npm package runs a postinstall script that downloads a binary: unreviewed code at install time. The Muapi desk (faceless/muapi.py) calls the API directly with price-first limits, so nothing is lost.

**Worth taking:** Done: the Muapi skill and desk.
