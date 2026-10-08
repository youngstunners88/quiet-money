# Intake: microsoft/agent-lightning

- **Source:** https://github.com/microsoft/agent-lightning
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
uv sync
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <img src="docs/images/agl-v1.0.svg" alt="Agent Lightning v1.0" width="500">
</p>

<p align="center"><em>3,500-Line Lightweight Agentic RL Framework for Training Agents with Real Harnesses!</em></p>

<p align="center">
  <a href="https://microsoft.github.io/agent-lightning/stable/">Documentation</a> &nbsp;·&nbsp; <a href="https://arxiv.org/pdf/2608.17528">Technical Report</a> &nbsp;·&nbsp; <a href="https://github.com/microsoft/agent-lightning/issues/236">WeChat Group (微信群)</a> &nbsp;·&nbsp; <a href="LICENSE">MIT License</a>
</p>

> Agent Lightning was completely refactored in v1.0. For legacy releases earlier than v1.0, see [this branch](https://github.com/microsoft/agent-lightning/tree/v0.x).

## ⚡ News

- [2026/09] We release [a new coding agent example based on an MoE model](https://microsoft.github.io/agent-lightning/stable/76-example-coding-agent-moe/). Pure RL improves Qwen3.5-35B-A3B on SWE-bench Verified from 47.8% to 61.6% after training it on only 1.8K training examples!
- [2026/08] [Agent Lightning Skill](https://github.com/microsoft/agent-lightning/tree/main/skills#agent-lightning-skill) is released. It helps a coding agent improve another AI agent against a benchmark.
- [2026/08] [Agent Lightning v1.0 technical report](https://arxiv.org/abs/2608.17528) is released!
- [2026/08] We open source Agent Lightning v1.0!

## ⚡ Key Features

- 🪶 **~3,500
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: measure.

MIT reinforcement-learning framework for training agents. Needs a benchmark and hundreds of scored runs; our metrics file has none yet. Same phase as dspy.

**Worth taking:** Its 'agent improves another agent against a benchmark' skill is a model for tuning the script prompt once real retention data exists.
