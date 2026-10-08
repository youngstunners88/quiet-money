# Intake: calesthio/Crucix

- **Source:** https://github.com/calesthio/Crucix
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | AGPL-3.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **MED `binary-download`:** ships or downloads prebuilt binaries: unreviewed code
- **MED `brand-risk`:** promotes get-rich-quick, trading-bot or crypto-promotion content: wrong for a money-education brand
- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: ADSB_API_KEY, AISSTREAM_API_KEY, DISCORD_BOT_TOKEN, EIA_API_KEY, FIRMS_MAP_KEY, FRED_API_KEY, LLM_API_KEY, TELEGRAM_BOT_TOKEN

## Commands its docs tell you to run (read, do not run)

```
git clone https://github.com/calesthio/Crucix.git
npm install
npm run dev
docker compose up -d
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">

# Crucix

**Your own intelligence terminal. 27 sources. One command. Zero cloud.**

## [Visit The Live Site: crucix.live](https://www.crucix.live/)

[![Live Website](https://img.shields.io/badge/live-crucix.live-00d4ff?style=for-the-badge)](https://www.crucix.live/)
[![Open Demo](https://img.shields.io/badge/open-live%20dashboard-0b1220?style=for-the-badge&logo=googlechrome&logoColor=white)](https://www.crucix.live/)

[![Node.js 22+](https://img.shields.io/badge/node-22%2B-brightgreen)](#quick-start)
[![License: AGPL v3](https://img.shields.io/badge/license-AGPLv3-blue.svg)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-1%20(express)-orange)](#architecture)
[![Sources](https://img.shields.io/badge/OSINT%20sources-27-cyan)](#data-sources-27)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)](#docker)

**Enter The Signal Network**

[![Signal Wire](https://img.shields.io/badge/Signal%20Wire-%40crucixmonitor-111111?style=for-the-badge&logo=x&logoColor=white)](https://x.com/crucixmonitor)
[![Ops Room](https://img.shields.io/badge/Ops%20Room-Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ChVy7SF4)

![Crucix Dashboard](docs/dashboard.png)

<details>
<summary>More screenshots</summary>

| Boot Sequence | World Map |
|:---:|:---:|
| ![Boot](docs/boot.png) | ![Map](docs/map.png) |

| 3D
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: ideate.

AGPL-3.0 intelligence terminal over 27 sources, mostly geopolitics and trading: off-brand for a money-education channel. One thing is worth taking.

**Worth taking:** Its list of keyless economic APIs. Checked from our network today: US Treasury FiscalData works and needs no key (total public debt outstanding $40.27 trillion on 2026-10-06; average T-bill rate 3.87% on 2026-09-30). FRED timed out and the BLS public API reported its shared daily quota used, so live inflation and mortgage-rate facts need an owner-provided free FRED key or a different egress.

**Only the owner can:** Optional: a free FRED API key if timely macro numbers are wanted.
