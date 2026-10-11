# Intake: m-bain/whisperX

- **Source:** https://github.com/m-bain/whisperX
- **Looked at:** 2026-10-11 11:47 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | BSD (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `hidden-comment`:** a 194-character HTML comment, invisible when rendered: read it
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: YOUR_HF_TOKEN

## Commands its docs tell you to run (read, do not run)

```
pip install whisperx
uvx whisperx
uvx git+https://github.com/m-bain/whisperX.git
git clone https://github.com/m-bain/whisperX.git
uv sync --all-extras --dev
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<h1 align="center">WhisperX</h1>

## Recall.ai - Meeting Transcription API

If you’re looking for a transcription API for meetings, consider checking out [Recall.ai's Meeting Transcription API](https://www.recall.ai/product/meeting-transcription-api?utm_source=github&utm_medium=sponsorship&utm_campaign=mbain-whisperx), an API that works with Zoom, Google Meet, Microsoft Teams, and more. Recall.ai diarizes by pulling the speaker data and separate audio streams from the meeting platforms, which means 100% accurate speaker diarization with actual speaker names.


<p align="center">
  <a href="https://github.com/m-bain/whisperX/stargazers">
    <img src="https://img.shields.io/github/stars/m-bain/whisperX.svg?colorA=orange&colorB=orange&logo=github"
         alt="GitHub stars">
  </a>
  <a href="https://github.com/m-bain/whisperX/issues">
        <img src="https://img.shields.io/github/issues/m-bain/whisperx.svg"
             alt="GitHub issues">
  </a>
  <a href="https://github.com/m-bain/whisperX/blob/master/LICENSE">
        <img src="https://img.shields.io/github/license/m-bain/whisperX.svg"
             alt="GitHub license">
  </a>
  <a href="https://arxiv.org/abs/2303.00747">
        <img src="http://img.shields.io/badge/Arxiv-2303.00747-B31B1B.svg"
             alt="ArXiv paper">
  </a>
  <a href="https://twitter.com/intent/tweet?text=&url=https%3A%2F%2Fgithub.com%2Fm-bain%2
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**PARK**, pipeline stage: voice.

BSD licence, word-level forced alignment. Our primary voice (Edge) and ElevenLabs return word timings; only the Gemini fallback estimates them. WhisperX needs PyTorch (gigabytes) and is meant for GPU, so it would slow every CI run to fix a fallback. Lighter aligners exist if the fallback ever matters.

**Worth taking:** The idea: align the text to the audio instead of estimating.

**Only the owner can:** Revisit if the Gemini voice becomes the default.
