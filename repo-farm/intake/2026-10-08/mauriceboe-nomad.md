# Intake: mauriceboe/NOMAD

- **Source:** https://github.com/mauriceboe/NOMAD
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | AGPL-3.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `binary-download`:** ships or downloads prebuilt binaries: unreviewed code
- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: ENCRYPTION_KEY

## Commands its docs tell you to run (read, do not run)

```
docker compose up -d
apt-get install -y --no-install-recommends tzdata dumb-init wget ca-certificates \
npm ci --workspace=server --omit=dev --ignore-scripts && \
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/logo-trek-light.svg" />
  <source media="(prefers-color-scheme: light)" srcset="docs/logo-trek-dark.svg" />
  <img src="docs/logo-trek-dark.svg" alt="TREK" height="96" />
</picture>

<br />
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/subtitle-light.png" />
  <source media="(prefers-color-scheme: light)" srcset="docs/subtitle-dark.png" />
  <img src="docs/subtitle-dark.png" alt="your trip. your plan." height="28" />
</picture>

A self-hosted, real-time collaborative travel planner — with maps, budgets, packing lists, a journal, and AI built in.

<br />

<a href="https://demo.liketrek.com"><img alt="Demo" src="https://img.shields.io/badge/Demo-try-111827?style=for-the-badge" /></a>
&nbsp;
<a href="https://hub.docker.com/r/mauriceboe/trek"><img alt="Docker" src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge" /></a>
&nbsp;
<a href="https://sonarcloud.io/project/overview?id=liketrek_TREK"><img alt="Sonar Quality Gate" src="https://img.shields.io/sonar/quality_gate/liketrek_TREK?server=https%3A%2F%2Fsonarcloud.io&style=for-the-badge" /></a>
&nbsp;
<img alt="GitHub Actions Workflow Status" src="https://img.shields.io/github/actions/workflow/status/liketrek/TREK/test.yml?branch=main&style=for-the-badge">
&nbsp;
<a href="https://discord.gg/NhZBDSd4
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: none.

AGPL-3.0 self-hosted collaborative travel planner. Unrelated.
