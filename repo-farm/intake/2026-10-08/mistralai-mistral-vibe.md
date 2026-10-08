# Intake: mistralai/mistral-vibe

- **Source:** https://github.com/mistralai/mistral-vibe
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | Apache-2.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **HIGH `asks-for-secrets`:** asks you to paste a key, password or seed phrase
- **MED `binary-download`:** ships or downloads prebuilt binaries: unreviewed code
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: MISTRAL_API_KEY

## Commands its docs tell you to run (read, do not run)

```
curl -LsSf https://mistral.ai/vibe/install.sh | bash
uv tool install mistral-vibe
pip install mistral-vibe
python-source = "."
python-packages = ["vibe", "mistralai_vibe_local_harness"]
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Mistral Vibe

[![PyPI Version](https://img.shields.io/pypi/v/mistral-vibe)](https://pypi.org/project/mistral-vibe)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/release/python-3120/)
[![CI Status](https://github.com/mistralai/mistral-vibe/actions/workflows/ci.yml/badge.svg)](https://github.com/mistralai/mistral-vibe/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/mistralai/mistral-vibe)](https://github.com/mistralai/mistral-vibe/blob/main/LICENSE)

'''
██████████████████░░
██████████████████░░
████  ██████  ████░░
████    ██    ████░░
████          ████░░
████  ██  ██  ████░░
██      ██      ██░░
██████████████████░░
██████████████████░░
'''

**Mistral's open-source CLI coding assistant.**

Mistral Vibe is a command-line coding assistant powered by Mistral's models. It provides a conversational interface to your codebase, allowing you to use natural language to explore, modify, and interact with your projects through a powerful set of tools.

> [!WARNING]
> Mistral Vibe works on Windows, but we officially support and target UNIX environments.

### One-line install (recommended)

**Linux and macOS**

'''bash
curl -LsSf https://mistral.ai/vibe/install.sh | bash
'''

**Windows**

First, install uv

'''bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
'''

Th
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: none.

Apache-2.0 coding-agent CLI from Mistral, installed by a script, asking for a key. We are on Claude Code. The Mistral API itself could be one more script-writing provider in the chain (resilience); that needs the owner to authorize the MINSTRAL_API_KEY already in the environment.

**Only the owner can:** Authorize or decline Mistral as a fallback LLM provider.
