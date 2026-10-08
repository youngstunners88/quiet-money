# Intake: gooseworks

- **Source:** https://www.npmjs.com/package/gooseworks
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** GooseWorks CLI — give your coding agent real data tools

| fact | value |
|---|---|
| version | 0.4.5 |
| license | MIT |
| created | 2026-04-05T10:22:53.209Z |
| pushed | 2026-10-08T06:47:44.655Z |
| weekly_downloads | 154 |
| versions | 52 |
| maintainers | ['akhil_bisht', 'shivsak'] |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `tiny`:** 154 downloads last week
- **INFO `needs-keys`:** mentions keys: GOOSEWORKS_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npx gooseworks@latest install --claude --mcp
npx gooseworks@latest install --claude --mcp --with goose-graphics
npx gooseworks@latest install --cursor --mcp
npx gooseworks@latest install --codex --mcp
npx gooseworks@latest install --all
npx skills add gooseworks-ai/gooseworks
npx gooseworks install --claude    # Configure for Claude Code
npx gooseworks install --cursor    # Configure for Cursor
npx gooseworks install --codex     # Configure for Codex
npx gooseworks install --all       # Configure all detected agents
npx gooseworks install --claude --with goose-graphics
npx gooseworks install --claude --with goose-graphics --with aeo
npx gooseworks install --all --ref <campaign-or-referral-code>
npx gooseworks login
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# GooseWorks

Put your AI agent on the growth team. GooseWorks gives Claude Code, Cursor, and Codex specialist skills for research, lead generation, social data, ads, product photography, graphics, and growth work—with one install.

## Install

**Paste this into your agent** (Claude Code, Cursor, Codex, or a chat app like Claude or ChatGPT):

'''text
Install gooseworks: https://gooseworks.ai/install.md
'''

Your agent reads that page and follows it. The page is short and you can read it too. It makes the agent:

1. **Ask you first.** It says exactly what it will install and waits for your OK. The install touches your agent's skills folder, its MCP config and `~/.gooseworks/credentials.json`, nothing else, and only ever runs `npx gooseworks@latest …`.
2. **Install** the GooseWorks skills and register the `gooseworks` MCP server with the right flag for your agent (`--claude`, `--cursor`, `--codex`), always with `--mcp`.
3. **Sign you in** with Google in your browser (the URL is always printed too).
4. **Check the install** with `npx gooseworks@latest doctor` and tell you to restart the agent so the MCP tools load.
5. **Set up your company** after the restart: it asks for your website and saves what it learns as a reusable **Company Brain** that improves every later research, creative, and growth task.

Want a specific skill too? Say so: `Install gooseworks: https://gooseworks.ai/
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: sell.

MIT package from a SaaS: skills for ads and growth that run through its own MCP server, Google sign-in, a credentials file and a cloud 'Company Brain'. Its install flow tells the agent to read a web page and follow it, which is the pattern we refuse (web pages are data). Our business runs no paid ads.

**Worth taking:** Ideas only: ad-angle-miner (mine reviews and forum threads for the angles that convert) maps to product-listing research; brand-research context pack is what CLAUDE.md and channel/brand.md already are.
