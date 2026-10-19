# Intake: browser-use-sdk

- **Source:** https://pypi.org/project/browser-use-sdk/
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** Python SDK for the Browser Use cloud API

| fact | value |
|---|---|
| version | 3.11.3 |
| pushed | 2026-09-04T04:21:34.155837Z |

## Red flags

- **INFO `needs-keys`:** mentions keys: BROWSER_USE_API_KEY

## Commands its docs tell you to run (read, do not run)

```
uv add browser-use-sdk
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# browser-use-sdk

Official Python SDK for [Browser Use Cloud](https://browser-use.com).

## Install

'''bash
uv add browser-use-sdk
'''

## Quick Start

Get your API key at [cloud.browser-use.com/settings](https://cloud.browser-use.com/settings?tab=api-keys&new=1).

'''bash
export BROWSER_USE_API_KEY=your_key
'''

'''python
from browser_use_sdk.v4 import BrowserUse

with BrowserUse() as client:
    run = client.runs.create("Find the top 3 trending repos on GitHub today")
    result = client.runs.wait_for_completion(run.id)
    print(result.result)
'''

This is the current **Browser Use Agents** interface. Browser Infrastructure's
browser-management resource currently lives in the explicit `browser_use_sdk.v3`
namespace; see the [browser quickstart](https://docs.browser-use.com/cloud/browser/quickstart).

## v3 Bring Your Own LLM Key

Add your provider API key in Browser Use project settings, then enable BYOK for v3 agent runs:

'''python
from browser_use_sdk.v3 import BrowserUse

client = BrowserUse(use_own_key=True)
result = client.run("Find the top 3 trending repos on GitHub today")
print(result.output)
'''

## Docs

[docs.browser-use.com](https://docs.browser-use.com)

## License

MIT
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
