# Intake: video-db/videodb-python

- **Source:** https://github.com/video-db/videodb-python
- **Looked at:** 2026-10-11 11:47 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | Apache-2.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `build-time-code`:** installs by running its own script (install.sh / setup.py / source-only release): read it before use
- **MED `hidden-comment`:** a 146-character HTML comment, invisible when rendered: read it
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: VIDEO_DB_API_KEY, YOUR_API_KEY

## Commands its docs tell you to run (read, do not run)

```
pip install videodb
pip install 'videodb[capture]'
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
[![PyPI version][pypi-shield]][pypi-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![Website][website-shield]][website-url]


<br />
<p align="center">
  <a href="https://videodb.io/">
    <img src="https://codaio.imgix.net/docs/_s5lUnUCIU/blobs/bl-RgjcFrrJjj/d3cbc44f8584ecd42f2a97d981a144dce6a66d83ddd5864f723b7808c7d1dfbc25034f2f25e1b2188e78f78f37bcb79d3c34ca937cbb08ca8b3da1526c29da9a897ab38eb39d084fd715028b7cc60eb595c68ecfa6fa0bb125ec2b09da65664a4f172c2f" alt="Logo" width="300" height="">
  </a>

  <h3 align="center">VideoDB Python SDK</h3>

  <p align="center">
    Video Database for your AI Applications
    <br />
    <a href="https://docs.videodb.io"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/video-db/videodb-cookbook">View Demo</a>
    ·
    <a href="https://github.com/video-db/videodb-python/issues">Report Bug</a>
    ·
    <a href="https://github.com/video-db/videodb-python/issues">Request Feature</a>
  </p>
</p>



# VideoDB Python SDK

VideoDB Python SDK provides programmatic access to VideoDB's serverless video infrastructure. Build AI applications that understand and process video as structured data with support for semantic search, scene extraction, transcript generation, and multimodal content generation.

## 📑 Table of Contents

- [Installation](#installation)
- [Quick Start
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**KILL**, pipeline stage: render.

Apache-2.0 SDK for a paid cloud service: it needs an API key and uploads our videos to a third party, to do search, scene extraction and editing that ffmpeg, the existing transcript tools and our own render already cover for free.

**Worth taking:** Nothing.

**Only the owner can:** If competitor-video search is ever needed, TokConnect (connected) already reads public TikTok data; no new vendor.
