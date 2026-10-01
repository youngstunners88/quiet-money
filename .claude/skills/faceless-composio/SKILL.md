---
name: faceless-composio
description: Connect and use the Quiet Money studio's apps through Composio (YouTube, TikTok, Instagram, Google Drive, Gmail and 1,500 more) from the engine. Check connections, generate Connect Links, run tool calls with log IDs, pull channel metrics, and debug failures. Use when the studio needs an external app, when asked to connect an account, or when a Composio call fails. Load the general `composio` skill for product questions.
---

# Composio in the studio

The studio uses **Composio Platform** (an `ak_` project key) through the engine's provider layer:
`faceless/providers/composio_tools.py`. One stable identity owns every connection:
`studio.toml [composio].user_id` (default `quiet-money-studio`). Never change it casually: connections belong to it.

## Rules (from the official `composio` skill, applied here)
- The key comes from `COMPOSIO_API_KEY` (or the `COMPOSIO_API` alias). Never print, log, rotate, or request it in chat. Never run `composio dev init`.
- Never guess tool slugs. Discover them (step 3) before calling.
- Tools always run through the session (`ct.execute` → `session.execute`), never `composio.tools.execute`.
- Composio handles OAuth: use the Connect Link it returns; do not build an OAuth flow.
- Read-only calls can run freely. **Write actions (upload, post, comment, delete, update) need the owner's
  explicit approval** for that action, unless an approved workflow such as daily publishing already covers it.
- A failed call: get the `log_id` first (it's in the error and in `state/journal.jsonl` → `COMPOSIO_EXECUTE`).

## 1. Check what's connected
```bash
python -m faceless composio status
```

## 2. Connect an app (owner must click the link)
```bash
python -m faceless composio connect youtube          # prints a Connect Link
python -m faceless composio connect youtube --wait   # ...and blocks until authorized
```
Give the link to the owner. Links expire: generate a fresh one rather than reusing an old link.
After connecting, add the slug to `[composio].toolkits` in `studio.toml`.

## 3. Discover tools (never guess)
```bash
python - <<'EOF'
import os; os.environ.setdefault("COMPOSIO_API_KEY", os.environ.get("COMPOSIO_API", ""))
from composio import Composio
for t in Composio().tools.get_raw_composio_tools(toolkits=["youtube"], limit=100):
    print(t.slug, t.tags[:2], t.description[:80])
EOF
```
Prefer tools tagged `readOnlyHint` for checks. Inspect a schema with
`Composio().tools.get_raw_composio_tool_by_slug("SLUG").input_parameters`.

## 4. Call a tool
```bash
python -m faceless composio call YOUTUBE_LIST_CHANNELS --args '{"mine": true, "part": "snippet,statistics"}'
```
In code: `from faceless.providers import composio_tools as ct; ct.execute("SLUG", {...}, job=job.id)`.
Every call is journaled (`COMPOSIO_EXECUTE` with `log_id`) and counted in the ledger.

## Studio uses (by priority)
| Toolkit | Use | Tools (discovered) |
|---|---|---|
| youtube | Pull Shorts stats into `analytics/metrics.jsonl` (closes the feedback loop) | `YOUTUBE_LIST_CHANNEL_VIDEOS`, `YOUTUBE_GET_VIDEO_DETAILS_BATCH`, `YOUTUBE_GET_CHANNEL_STATISTICS` |
| youtube | Publish (owner-approved) | `YOUTUBE_UPLOAD_VIDEO`, `YOUTUBE_UPDATE_THUMBNAIL`, `YOUTUBE_POST_COMMENT` (pinned first comment) |
| tiktok, instagram | Cross-post + metrics | discover with step 3 |
| googledrive | Deliver daily posting packs to the owner's phone | discover with step 3 |
| gmail | Daily run report to the owner | discover with step 3 |

## Debugging
| Symptom | Boundary | Fix |
|---|---|---|
| 401 before any provider call | Composio project key | check the env var exists (don't print it); ask the owner to re-copy from Dashboard → Platform → project → Getting Started |
| 401/403 on a real tool call | the provider account | `composio connect <toolkit>` again for the same user_id, then retry |
| Google "App is blocked" | managed OAuth scopes | connect with an account that owns the channel; for production use a custom OAuth app |
| Tool not found | slug | rediscover (step 3); never invent |
Dashboard: dashboard.composio.dev → Platform → your project → Logs (search the `log_id`) and Connected Accounts.

## CI
The daily workflow reads `COMPOSIO_API_KEY` from repository secrets. Connections made here persist for CI
because they belong to the same project + `user_id`.
