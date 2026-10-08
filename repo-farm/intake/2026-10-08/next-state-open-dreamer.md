# Intake: next-state/open-dreamer

- **Source:** https://github.com/next-state/open-dreamer
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | unrecognised text in LICENSE |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
pip install uv
uv sync
uv run scripts/train_tokenizer.py
uv run scripts/tokenize_minecraft_dataset.py
python - <<'PY'
uv run scripts/train_dynamics.py
uv run scripts/eval_fvd.py
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">

<img src="assets/banner.png" alt="Open Dreamer" width="100%" />

**An open, real-time implementation of the Dreamer 4 world-model pipeline in JAX/Flax.**

[🌐 Website & Blog Post](https://next-state.github.io/open-dreamer/) &nbsp;·&nbsp;
[🎮 Live Demo](https://next-state.github.io/open-dreamer/) &nbsp;·&nbsp;
[⚡ Inference Code](https://github.com/reactor-team/open-dreamer)

<br />
<br />

<strong>Authors</strong>
<br />
<a href="https://www.diego-marti.com/">Diego Marti Monso</a><sup>\*</sup> &nbsp;·&nbsp;
<a href="https://francesco215.github.io/">Francesco Sacco</a><sup>\*</sup> &nbsp;·&nbsp;
<a href="https://edwardshu.com/">Edward Hu</a>
<br />
<sub><sup>*</sup> Equal contribution</sub>

<br />
<br />

<sub>REAL-TIME DEMO POWERED BY</sub>

<a href="https://reactor.inc">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/reactor-logo-light.svg" />
    <img alt="Reactor" src="assets/reactor-logo-dark.svg" height="24" />
  </picture>
</a>

</div>

---

Open Dreamer is a simple, performant, and easy-to-use JAX/Flax NNX
implementation of the Dreamer 4 world model — trained on Minecraft/VPT-style
gameplay and playable in real time. This repository holds the **training
pipeline**: a causal video tokenizer, an action-conditioned latent dynamics
model, and the tools to generate rollouts and measure quality.

This repo currently supports:

-
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: none.

Research code and blog post on training a world model (Dreamer 4 reproduction, CoinRun, JAX). Interesting science, no role in a faceless finance channel.

**Only the owner can:** The team@orbismedia.ca line in the document is a contact address; nothing is sent on the owner's behalf.
