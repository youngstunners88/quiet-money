# Intake: souzatharsis/podcastfy

- **Source:** https://github.com/souzatharsis/podcastfy
- **Looked at:** 2026-10-16 05:33 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | Apache-2.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
python -m podcastfy.client --url <url1> --url <url2>
python = "^3.11"
python-dotenv = "^1.0.1"
python-levenshtein = "^0.26.0"
apt-get install -y \
python3-full \
python3-pip \
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">
<a name="readme-top"></a>

Like this project? Consider supporting it by checking out our new O'Reilly book 

[LLMs: The Hard Parts](https://a.co/d/04ZCeM2b).

<a href="https://trendshift.io/repositories/12965" target="_blank"><img src="https://trendshift.io/api/badge/repositories/12965" alt="Podcastfy.ai | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

# Podcastfy.ai 🎙️🤖
An Open Source API alternative to NotebookLM's podcast feature: Transforming Multimodal Content into Captivating Multilingual Audio Conversations with GenAI



https://github.com/user-attachments/assets/5d42c106-aabe-44c1-8498-e9c53545ba40



[Paper](https://github.com/souzatharsis/podcastfy/blob/main/paper/paper.pdf) |
[Python Package](https://github.com/souzatharsis/podcastfy/blob/59563ee105a0d1dbb46744e0ff084471670dd725/podcastfy.ipynb) |
[CLI](https://github.com/souzatharsis/podcastfy/blob/59563ee105a0d1dbb46744e0ff084471670dd725/usage/cli.md) |
[Web App](https://openpod.fly.dev/) |
[Feedback](https://github.com/souzatharsis/podcastfy/issues)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/souzatharsis/podcastfy/blob/main/podcastfy.ipynb)
[![PyPi Status](https://img.shields.io/pypi/v/podcastfy)](https://pypi.org/project/podcastfy/)
![PyPI Downloads](https://static.pepy.tech/badge/podca
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-16)

**PARK**, pipeline stage: script.

Apache-2.0. Turns text, PDFs, websites, YouTube or a topic into a two-voice conversation (short 2-5 minutes or long 30+), with 100+ LLMs for the transcript and OpenAI, Google, ElevenLabs or Microsoft Edge voices. We already hold every part it wraps: Opus 5.5 on OpenRouter writes, Edge and ElevenLabs speak, ffmpeg mixes. The one thing we lack is the conversation format itself. It is a pip package with a pinned-nothing install and a Python 3.11 floor, which is more dependency than the idea needs.

**Worth taking:** The format, rebuilt in our own code: a two-host dialogue script (host and sceptic, one voice each, Edge voices free) written by Opus from a research brief, rendered with the existing captions as a 'Quiet Money Talks' format for long-form and for 60-second Shorts. The README says nothing on the prompt itself; the prompt and conversation_custom.md were not read.

**Only the owner can:** Say yes to a sandbox trial, or to building the two-host format in-house (recommended: no new dependency).
