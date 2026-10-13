# Intake: browser-use/sdk

- **Source:** https://github.com/browser-use/sdk
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `license-unknown`:** no LICENSE file at the top level and the API was not reachable: check by hand
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <img src="static/sdks-banner.png" alt="Browser Use SDKs" />
</p>

# Browser Use SDKs

Official SDKs for [Browser Use Cloud](https://browser-use.com).

- **Browser Use Agents:** use the explicit V4 interface to give an agent a task
  and receive its completed result.
- **Browser Infrastructure:** use the explicit V4 SDK browser resource, or the
  V4 REST API, to create and control a managed browser.

| Package | Language | Registry |
|---------|----------|----------|
| [browser-use-sdk](browser-use-python/) | Python | PyPI |
| [browser-use-sdk](browser-use-node/) | TypeScript | npm |

Start with the [Cloud quickstart](https://docs.browser-use.com/cloud/quickstart).

## Docs

[docs.browser-use.com](https://docs.browser-use.com)
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**PARK**, pipeline stage: post.

MIT, cloud browser agent. Key `BROWSER_USE_API_KEY` works but holds $0.0 credit, and the studio already has TinyFish (works) and Photopea headless for browser jobs. Revisit if a task needs a logged-in browser nothing else can drive.

**Worth taking:** Task-as-prompt API shape.

**Only the owner can:** Top up credit only if a job needs it.
