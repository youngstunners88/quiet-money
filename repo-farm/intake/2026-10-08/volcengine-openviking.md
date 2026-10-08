# Intake: volcengine/OpenViking

- **Source:** https://github.com/volcengine/OpenViking
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | AGPL-3.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **MED `build-time-code`:** installs by running its own script (install.sh / setup.py / source-only release): read it before use
- **MED `binary-download`:** ships or downloads prebuilt binaries: unreviewed code
- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
uv tool install openviking --upgrade && openviking-server init
curl -fsSL https://openviking.ai/install | bash -s -- --yes --url <SERVER_URL>
curl -fsSL https://openviking.ai/install | bash
pip install "openviking[bot]"
npm = shutil.which("npm")
uv sync --locked --no-editable --reinstall-package openviking --extra bot --extra gemini --extra opengauss --extra context-gateway \
uv lock; \
curl \
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">

<a href="https://openviking.ai/" target="_blank">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/volcengine/OpenViking/main/docs/images/readme-logo-dark.png">
    <img alt="OpenViking" src="https://raw.githubusercontent.com/volcengine/OpenViking/main/docs/images/readme-logo-light.png" width="300" height="56">
  </picture>
</a>

### The Context Database for AI Agents

English / [中文](docs/repository/README_CN.md) / [日本語](docs/repository/README_JA.md)

<a href="https://www.openviking.ai">Website</a> · <a href="https://openviking.ai/studio">Live Demo</a> · <a href="https://github.com/volcengine/OpenViking">GitHub</a> · <a href="https://github.com/volcengine/OpenViking/issues">Issues</a> · <a href="https://docs.openviking.ai/">Docs</a> · <a href="https://blog.openviking.ai/">Blog</a>

<p>
  <a href="https://github.com/volcengine/OpenViking/releases"><img src="https://img.shields.io/github/v/release/volcengine/OpenViking?color=369eff&labelColor=black&logo=github&style=flat-square" alt="release"></a>
  <a href="https://github.com/volcengine/OpenViking"><img src="https://img.shields.io/github/stars/volcengine/OpenViking?labelColor&style=flat-square&color=ffcb47" alt="stars"></a>
  <a href="https://github.com/volcengine/OpenViking/issues"><img src="https://img.shields.io/github/issues/volcengine/OpenViking?lab
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: ideate.

AGPL-3.0 context database for agents (a filesystem-style memory). faceless/memory.py already gives full-text search over every script and outcome; revisit past about 100,000 records.

**Worth taking:** The idea of memory, resources and skills under one path scheme.
