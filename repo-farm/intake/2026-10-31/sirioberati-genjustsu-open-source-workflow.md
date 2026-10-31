# Intake: sirioberati/Genjustsu-Open-Source-Workflow

- **Source:** https://github.com/sirioberati/Genjustsu-Open-Source-Workflow
- **Looked at:** 2026-10-31 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: ENHANCOR_API_KEY, REPLICATE_API_TOKEN

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <a href="https://tein.ai"><img src="docs/branding/tein-ai-banner.svg" width="960" alt="TEIN AI — Open-source AI workflows. Click to join the waitlist." /></a>
</p>
<p align="center"><a href="https://tein.ai"><strong>Join TEIN AI →</strong></a></p>

<p align="center">
  <a href="examples/advanced-black-nodes-v8-audio.mp4"><img src="examples/previews/workflow.gif" width="28%" alt="Workflow animation — click for full video with audio" /></a>
  <a href="examples/1006%20%281%29.mp4"><img src="examples/previews/example-1.gif" width="34%" alt="Example 1 — click for full video with audio" /></a>
  <a href="examples/1006%20%281%29%283%29.mp4"><img src="examples/previews/example-2.gif" width="34%" alt="Example 2 — click for full video with audio" /></a>
</p>
<p align="center"><em>Click any preview to open its full video with audio.</em></p>

<h1 align="center"> Genjustsu — Open Source Workflow</h1>
<p align="center">Your scene. New characters.</p>
<p align="center">
  <a href="https://tein.ai"><strong>Join TEIN AI</strong></a> ·
  <a href="https://enhancor.ai"><strong>Get the Seedance API</strong></a> ·
  <a href="docs/SETUP-AGENT.md">Agent setup</a> ·
  <a href="examples/README.md">Examples</a> ·
  <a href="LICENSE">MIT license</a>
</p>

A local UI and agent-assisted workflow for replacing video subjects using colored depth, SAM 3 masks and Seedance through Enhancor
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-31)

**KILL**, pipeline stage: visuals.

MIT. A character-swap video workflow that needs paid Seedance and Replicate keys (ENHANCOR_API_KEY, REPLICATE_API_TOKEN). It swaps people into existing footage, which does not serve a faceless money channel and raises likeness and platform-policy risk. Recorded so nobody re-evaluates it.

**Worth taking:** Nothing.

**Only the owner can:** operator
