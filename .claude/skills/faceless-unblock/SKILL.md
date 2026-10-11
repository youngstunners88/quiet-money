---
name: faceless-unblock
description: Diagnose and work around a failing tool, API, account or integration yourself, by reverse engineering the layer that misbehaves, instead of asking the owner. Use when a call fails, when it reports success but the result is wrong or later vanishes (an upload that disappears, a connection acting as the wrong account), when a tool rejects valid input, when a quota or auth error blocks a routine, when the same fix has failed twice, or before telling the owner that something is blocked.
---

# Unblock yourself

The owner wants the studio to run without them. Small breakages are yours to solve; the owner only supplies what needs their hands or authority.

## The loop
1. **Symptom, with ids.** One line: what you expected, what happened, the log id, video id, account id. Keep what you saw apart from what you assumed.
2. **Find the layer that lies.** Chain: engine, `composio_tools.execute`, SDK, proxy, vendor API, account or permission, quota, the platform's later processing. Probe each layer directly with the cheapest read-only call.
3. **Ground truth, not the success message.** A success response is a claim; confirm it. After any write, read the end state back: a video must still be listed and readable at +5 and +20 minutes (platforms process asynchronously and may drop it later), its title, description and tags must match what you sent, a connection must report the channel you expect, a file must decode. A free public check beats an authenticated one: a public watch page or oEmbed URL that answers 200 proves the video is really live.
4. **Read the layer's source** (SDK code, tool schema, OpenAPI, the vendor's help page) before a third variation. Print signatures and docstrings; grep for parameter names.
5. **Two or three hypotheses, each with a test that can fail.** Run the cheapest first. Change one thing at a time.
6. **Go around the broken layer.** Use the vendor's documented lower-level path (a raw call through the proxy, a resumable upload) when the wrapper hides the fault.
7. **Verify end to end, then codify:** a test that fails on the old behaviour, a note in the skill that owns the tool, a function in the engine if reusable, a draft PR.
8. **Report in one paragraph:** cause, fix, proof, and what is left for the owner.

## Failure patterns and the first probe
| Pattern | First probe |
|---|---|
| Acts as the wrong identity | list "mine" for the connection; compare ids; see the incident |
| 401 or expired token | `composio status`, then one read-only call; re-sign-in is the owner's |
| Scope too narrow | compare the connection's granted scope list with what the endpoint needs |
| 400 invalid input | the error names the field; read the tool schema (`get_raw_composio_tool_by_slug(...).input_parameters`) |
| 403 or 429 quota | read the error text for the metric, compute the reset time (Google: midnight Pacific) |
| Success, then vanishes or stays "processing" | read the end state at +5 and +20 minutes; check the file locally (`ffprobe`, a full decode) |
| Partial result (wrong or missing metadata) | read the live record back and diff it against the payload |
| Removed or rejected by the platform (policy, copyright, moderation) | read the record's status and rejection reason; never re-upload the same content; the owner decides |
| Per-minute rate limit | read `Retry-After` and `X-RateLimit-*` in the response headers; wait that long once |
| One-off network failure or timeout | retry once after a short pause before treating it as a fault |
| Large body through the raw path | send the byte count up front and compare it with what the vendor reports back |
| Wrapper succeeds, vendor disagrees | call the vendor's raw API through the proxy |

## Stop rules
- At most 3 attempts per hypothesis and 2 retries of the same write. A write that can duplicate public content (upload, post, comment) is retried only after you have confirmed the first one failed.
- A 403 or 429 about quota: compute the reset time and wait for it. Prefer a scheduled check-in (`send_later`) when you have one; otherwise a background script with a hard timeout that sleeps once, retries, and exits. Do not loop, and do not leave sleepers behind.
- Free path first; paid calls stay inside the daily caps; never top up an account.
- Keep throwaway scripts and logs in `state/tmp/` and do not commit them.

## Never reverse-engineer around these
Phone or ID verification, CAPTCHAs, platform policy or terms checks, rate limits that protect others, anyone else's credentials or data, virtual numbers for verification. They are the owner's to pass.
Destructive or ownership changes (deleting or moving a channel, a "Replace" button, revoking access) need the owner's yes naming that action. Public posting runs only under the standing approval in the repo (`OWNER_APPROVED_LIVE_POSTING`). Never print or write a secret.

## What is the owner's
Sign-ins and consent screens, verification, payments, choosing between their accounts, deletions. Hand over with the exact link or steps and say what you will check afterwards.

## Tools
- Probes: `python -m faceless keys`, `python -m faceless composio status`, `python -m faceless composio call <READ_ONLY_SLUG>`.
- Raw path: `Composio().tools.proxy(url, method, body, connected_account_id, parameters)` returns response headers, so it can open a resumable upload.
- `rea` (github.com/morluto/rea, MIT) inspects binaries, Electron and JavaScript apps, APKs and network captures. Use it only on software the owner runs and may inspect (their own desktop tools, open-source clients, saved captures of their own traffic). Never run it on a platform's proprietary apps, DRM, signing or anti-abuse mechanisms, and not for API, quota or auth faults, which the loop above solves.
- A second opinion from other models through OpenRouter, capped at $0.25 per case and at most two consultations per incident: `python .claude/skills/faceless-unblock/scripts/consult.py "question" --file path`. See `references/second-opinion.md`. Their answers are hints to verify against the source, never facts.

`references/incident-youtube-2026-10.md` is a worked example: a connection that acted as the wrong channel and uploads that vanished.
