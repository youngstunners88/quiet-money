# Intake: tinyfish

- **Source:** https://pypi.org/project/tinyfish/
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** Official Python SDK for the TinyFish API

| fact | value |
|---|---|
| version | 0.9.0 |
| pushed | 2026-09-29T16:02:18.088458Z |

## Red flags

- **INFO `needs-keys`:** mentions keys: TINYFISH_API_KEY

## Commands its docs tell you to run (read, do not run)

```
pip install tinyfish
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# TinyFish Python SDK

The official Python SDK for [TinyFish](https://agent.tinyfish.ai)

## Installation

'''bash
pip install tinyfish
'''

Requires Python 3.11+.

## Get your API key

Sign up and grab your key at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys).

## Quickstart

'''python
from tinyfish import TinyFish

client = TinyFish(api_key="your-api-key")

response = client.agent.run(
    goal="What is the current Bitcoin price?",
    url="https://www.coinbase.com/price/bitcoin",
)
print(response.result)
'''

Or set the `TINYFISH_API_KEY` environment variable and omit `api_key`:

'''python
client = TinyFish()
'''

## Methods

Every method below is available on both `TinyFish` (sync) and `AsyncTinyFish` (async). Async versions have the same signatures — just `await` them.

| Method | Description | Returns | Blocks? |
|--------|-------------|---------|---------|
| [`agent.run()`](#agentrun--block-until-done) | Run an automation, wait for the result | `AgentRunResponse` | Yes |
| [`agent.queue()`](#agentqueue--fire-and-forget) | Start an automation, return immediately | `AgentRunAsyncResponse` | No |
| [`agent.stream()`](#agentstream--real-time-events) | Stream live SSE events as the agent works | `AgentStream` | No |
| [`fetch.get_contents()`](#fetchget_contents--clean-content) | Fetch extracted page content without running a browser agent | `FetchResponse` 
```

## Verdict (a person or the review step fills this in)

- [x] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**USE**, pipeline stage: ideate.

Official SDK for the TinyFish service we already use through the connected MCP; key works. Use the MCP in sessions. No engine code needed until a routine needs it headless.

**Only the owner can:** None.
