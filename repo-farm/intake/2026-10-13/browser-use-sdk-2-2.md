# Intake: browser-use-sdk

- **Source:** https://www.npmjs.com/package/browser-use-sdk
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** Official TypeScript SDK for the Browser Use API

| fact | value |
|---|---|
| version | 3.11.3 |
| license | MIT |
| created | 2025-08-09T19:09:34.396Z |
| pushed | 2026-09-04T04:29:01.865Z |
| weekly_downloads | 114459 |
| versions | 57 |
| maintainers | ['sauravpanda', 'gregpr07'] |

## Red flags

- **INFO `needs-keys`:** mentions keys: BROWSER_USE_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npm install browser-use-sdk
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# browser-use-sdk

Official TypeScript SDK for [Browser Use Cloud](https://browser-use.com).

## Install

'''bash
npm install browser-use-sdk
'''

## Quick Start

Get your API key at [cloud.browser-use.com/settings](https://cloud.browser-use.com/settings?tab=api-keys&new=1).

'''bash
export BROWSER_USE_API_KEY=your_key
'''

'''typescript
import { BrowserUse } from "browser-use-sdk/v4";

const client = new BrowserUse();
const run = await client.runs.create({
  task: "Find the top 3 trending repos on GitHub today",
});
const result = await client.runs.waitForCompletion(run.id);
console.log(result.result);
'''

This is the current **Browser Use Agents** interface. Browser Infrastructure's
browser-management resource currently lives in the explicit `browser-use-sdk/v3`
entry point; see the [browser quickstart](https://docs.browser-use.com/cloud/browser/quickstart).

## v3 Bring Your Own LLM Key

Add your provider API key in Browser Use project settings, then enable BYOK for v3 agent runs:

'''typescript
import { BrowserUse } from "browser-use-sdk/v3";

const client = new BrowserUse({ useOwnKey: true });
const result = await client.run("Find the top 3 trending repos on GitHub today");
console.log(result.output);
'''

## Docs

[docs.browser-use.com](https://docs.browser-use.com)

## License

MIT
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?
