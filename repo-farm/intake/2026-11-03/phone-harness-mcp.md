# Intake: phone-harness/mcp

- **Source:** https://github.com/phone-harness/mcp
- **Looked at:** 2026-11-03 11:53 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: PHONE_HARNESS_API_KEY

## Commands its docs tell you to run (read, do not run)

```
claude mcp add --transport http phone-harness https://mcp.phone-harness.com/mcp
uv sync
uv run pytest
uv run phone-harness-mcp --help
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Phone Harness MCP 🔌

**Give any MCP agent a real iPhone or an Android emulator in the cloud.**

Add Phone Harness as a custom connector in Claude, Cursor, ChatGPT, Codex, or any MCP client, and your agent can see the screen, tap, type, swipe, and open apps on a real iPhone or an Android emulator.

## Setup

### General

Streamable HTTP. Sign-in is OAuth and asks for the `phone:drive` scope. An API key can be sent as a bearer token instead; see the FAQ.

    https://mcp.phone-harness.com/mcp

[<img src="https://img.shields.io/badge/Add_to-Claude-000000?style=flat-square&logo=claude&logoColor=white" alt="Add to Claude">](https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=Phone%20Harness&connectorUrl=https%3A%2F%2Fmcp.phone-harness.com%2Fmcp)
[<img src="https://img.shields.io/badge/Add_to-Cursor-000000?style=flat-square&logo=cursor" alt="Add to Cursor">](cursor://anysphere.cursor-deeplink/mcp/install?name=phone-harness&config=eyJ1cmwiOiJodHRwczovL21jcC5waG9uZS1oYXJuZXNzLmNvbS9tY3AifQ==)
[<img src="https://img.shields.io/badge/Add_to-VS_Code-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white" alt="Add to VS Code">](https://vscode.dev/redirect/mcp/install?name=phone-harness&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fmcp.phone-harness.com%2Fmcp%22%7D)

- **Works in any MCP client.** Claude, Cursor, ChatGPT, Codex, VS Co
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Deep dive: phone-harness/mcp against our phone lane

Read from the public README, `docs/self-hosting.md`, the source tree and `server.py`, `cloud.py`, `auth.py` (raw files only; no clone, install or run). `phone.py`, the screenshot code, the tests and `server.json` were not read in full, so claims about their internals are limited to what the files above state.

### What it is
- A hosted MCP server at `https://mcp.phone-harness.com/mcp` that gives an agent a cloud Android emulator (or a cloud iPhone). Tools mirror the mobile-mcp naming: screen, tap, type, swipe, open app.
- Auth: OAuth with `phone:drive` scope, or a `pck_…` API key as bearer. The server checks the bearer against the vendor's `/me` endpoint and caches the answer for 60 s.
- Also runnable locally over stdio (`uvx phone-harness-mcp`), but the local mode still calls the vendor's HTTPS API for devices.
- Pricing (from the README): cloud Android at about 5 cents a minute for a temporary device; a saved phone is an option; cloud iPhone about $80–100 a month flat.
- Start-device waits up to a fixed ready timeout and asks the service to end the device if it never becomes ready. Good cost protection.

### What it does not do (from its own docs)
- No file push onto the device, no URL open, no app install. Our lane needs all three: the rendered Short must reach the YouTube or TikTok gallery picker.
- No safety modes, allowlist, dry run or audit trail of hashes. Ours has all four (OpenDeviceMCP).
- The device is a vendor emulator or cloud iPhone, not the owner's phone. Logins to YouTube, TikTok and Fiverr would sit on the vendor's machine. The community and Posts-tab accounts would be inside a third party's environment.

### Cost, per month (assumptions labelled)
Assumption: 15 phone jobs a day (5 comics, 5 Shorts, 5 TikToks), about 3 minutes of device time each.
- Cloud Android at 5 cents a minute: 15 × 3 × $0.05 = $2.25 a day, about $67 a month, before any retries. Retries and Flow pictures would add more.
- Cloud iPhone: $80–100 a month flat, plus the same no-file-push problem.
- Ours: $0 marginal. The owner's phone, the owner's accounts, USB or Wi-Fi adb. The cost is the host (a PC that is on) and the owner's time to plug in.

### Where ours is weaker (stated plainly)
- The home host has never checked in (`state/phone/host.json` has seen: false, stale: true). The phone lane is not proven end to end on the owner's device from the cloud side.
- The receipts show 10 Shorts and 10 TikToks done, 5 Shorts held, and 24 TikToks queued. Some receipts have no URL, so they cannot be audited against the channel yet.
- It depends on a machine that is awake. The vendor's cloud has no such dependency.

### Where theirs is weaker
- Cannot move our media. That alone blocks the Shorts and TikTok jobs.
- Vendor-hosted accounts and emulators are a platform-ToS and account-safety risk for the channel.
- Recurring cost with no benefit we cannot already get from OpenDeviceMCP.
- Partial: the GitHub API was rate-limited, so stars, last commit and maintainer count are unknown.

### Steals worth taking (copy the idea, not the code)
1. A bounded device session: a start that ends itself on timeout. Our `phone next` could adopt the same rule for the host: if no device answers within N minutes, record a stale receipt and stop, rather than retrying.
2. The mirrored tool names (screen, tap, type, swipe, open app). Useful if the recipes ever need to be readable by other MCP clients. Low priority.

### Verdict
**PARK**, with a named condition: revisit only if the owner's phone host is unreachable for more than a week *and* the owner approves a paid cloud trial. Until then, keep OpenDeviceMCP as the phone lane. The steal in item 1 goes into the faceless-phone-host skill as a follow-up, not as a code change in this intake.

## Decision (2026-11-03)

**PARK**, pipeline stage: post.

Hosted cloud emulator or cloud iPhone (MIT code, paid service). It cannot push our rendered videos onto a device, which the Short and TikTok jobs need. About $67 a month at our volume on cloud Android, or $80-100 flat on iPhone, against $0 for the owner's own phone through OpenDeviceMCP. Runs the owner's logins on a vendor's machine. Revisit only if the owner's home host stays unreachable for a week and the owner approves a paid trial.

**Worth taking:** A bounded device session: a device start that ends itself on timeout, so a missing phone stops the job instead of retrying. Candidate for the faceless-phone-host skill.

**Only the owner can:** Any trial needs the owner's yes: money (cloud device minutes or a flat plan) and a third-party account.
