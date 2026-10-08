# Intake: @elevenlabs/cli

- **Source:** https://www.npmjs.com/package/@elevenlabs/cli
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** CLI for elevenlabs

| fact | value |
|---|---|
| version | 1.4.0 |
| created | 2025-10-22T13:27:12.993Z |
| pushed | 2026-09-25T10:55:38.185Z |
| weekly_downloads | 19957 |
| versions | 28 |
| maintainers | ['gmrchk', 'lacop11', 'elevenlabs-paulasjes', 'angelogiacco11labs', 'boris-elevenlabs'] |

## Red flags

- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **INFO `needs-keys`:** mentions keys: ELEVENLABS_API_KEY, ELEVENLABS_E2E_API_KEY

## Commands its docs tell you to run (read, do not run)

```
brew install elevenlabs/tap/elevenlabs
npm install -g @elevenlabs/cli
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/elevenlabs/cli/releases/latest/download/elevenlabs-cli-installer.sh | sh
git clone https://github.com/elevenlabs/cli.git
cargo build --release
cargo install --path .
cargo test                                              # framework + workflow + wire tests
cargo test --manifest-path elevenlabs-sdk/Cargo.toml    # generated SDK crate
cargo test --manifest-path elevenlabs-types/Cargo.toml  # generated types crate
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# ElevenLabs CLI — Agents as Code

![hero](./assets/Cover.png)

Command-line interface for the [ElevenLabs platform](https://elevenlabs.io/docs/agents-platform/overview).

The CLI does two things:

- **Full API access** — every ElevenLabs API endpoint is available as a subcommand (`elevenlabs <resource> <method>`).
- **Agents as Code** — manage Conversational AI agents from local configuration files, with templates, branches, and push/pull sync.

## Table of contents

- [Installation](#installation)
- [Authentication](#authentication)
- [Quick start](#quick-start)
- [Speaking text](#speaking-text)
- [Agents as Code](#agents-as-code)
- [Data residency](#data-residency)
- [UI components](#ui-components)
- [Usage](#usage)
- [Documentation](#documentation)
- [Advanced](#advanced)
  - [Common flags](#common-flags)
  - [Environment variables](#environment-variables)
  - [Telling us what you are doing](#telling-us-what-you-are-doing)
  - [Output formats](#output-formats)
  - [Shell completion](#shell-completion)
- [Development](#development)

## Installation

### Homebrew (macOS / Linux)

'''bash
brew install elevenlabs/tap/elevenlabs
'''

### Scoop (Windows)

'''powershell
scoop bucket add elevenlabs https://github.com/elevenlabs/scoop-bucket
scoop install elevenlabs
'''

### npm (macOS / Linux / Windows)

'''bash
npm install -g @elevenlabs/cli
'''

Installs the same binary through a
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: voice.

MIT. 'Agents as code' for ElevenLabs conversational agents plus every API endpoint as a subcommand; the installer pipes a script into a shell. We do not build voice agents, and ElevenLabs is already an opt-in voice in the chain (and reachable through Muapi at $0.05 per 1,000 characters).
