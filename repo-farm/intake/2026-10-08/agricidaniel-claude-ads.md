# Intake: AgriciDaniel/claude-ads

- **Source:** https://github.com/AgriciDaniel/claude-ads
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `build-time-code`:** installs by running its own script (install.sh / setup.py / source-only release): read it before use
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
git clone https://github.com/AgriciDaniel/claude-ads.git
python3.12 -m venv .venv
python -m claude_ads_core --version
python -m claude_ads_core validate finding path/to/finding.json
claude-ads-core = "claude_ads_core.cli:main"
claude)
claude     Claude Code (verified)
git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/claude-ads"
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <img src="assets/banner.svg" alt="Claude Ads, Claude-first paid-media operations across twelve advertising platforms" width="100%">
</p>

# Claude Ads

Claude-first, portable paid-media operations for agencies, consultants, and
in-house performance teams.

Claude Ads turns authorized exports or account reads into source-grounded
audits, plans, creative workflows, experiments, monitoring, and reports. It is
read-only by default. Live changes stay disabled until the exact platform and
operation pass approval, idempotency, verification, audit, and rollback gates.

> [!NOTE]
> Claude Ads ships from two homes: the **public release** at
> [`AgriciDaniel/claude-ads`](https://github.com/AgriciDaniel/claude-ads)
> (MIT, no membership required) and the **community mirror** at
> `AI-Marketing-Hub/claude-ads`, where
> [AI Marketing Hub Pro](https://www.skool.com/ai-marketing-hub-pro) members
> get early access and direct collaboration.

<p align="center">
  <img src="assets/diagrams/how-it-works.svg" alt="Validated inputs flow through bounded workers into schema-valid findings and deterministic reports" width="100%">
</p>

## What it does

- Audits paid-media accounts with dated evidence and explicit confidence.
- Plans campaigns, channels, budgets, measurement, and experiments.
- Creates copy, image, video, and product-photo briefs and assets.
- Monitors pacing, deliv
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: sell.

MIT paid-media operations kit (audits, plans, creative briefs across twelve ad platforms), read-only by default with approval gates before any live change. We run no paid ads: the business is organic video plus digital products, and ads need conversion data first.

**Worth taking:** Its audit checklists and benchmark tables are the starting point if the owner ever runs Etsy Ads or Meta ads for a product that already converts.
