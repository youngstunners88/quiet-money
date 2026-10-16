# Quiet Money YouTube Posts MCP

YouTube's API has no call that creates a Community (Posts tab) post. This MCP server fills the gap by driving **your own signed-in browser profile on your own machine**, the way you would by hand: open the Posts tab, add the picture, paste the caption, press Post.

## What it is and is not
- It never sees a password, cookie or token. You sign in once in a real browser window (`community_login`); the sign-in stays in a folder on your machine (`~/.quiet-money/yt-profile`, outside this repository).
- It is browser automation, which YouTube's terms do not permit. Your account, your call. It posts five pictures a day at human pace (45-120 s apart) and never more than `QM_COMMUNITY_MAX_PER_DAY` (5).
- **Untested against the live YouTube page.** It is tested against a stand-in composer (`tests/test_community_mcp.py`). YouTube's page can differ, so the first run is a dry run. If a step fails it saves a screenshot and an accessibility dump in `~/.quiet-money/yt-shots/`; send those and the selector is a one-line fix.

## Set up on your computer (once)
```bash
git clone <this repo> && cd quiet-money/mcp-servers/yt-community
pip install -r requirements.txt && playwright install chromium
```
Add to Claude Desktop / Claude Code (`claude mcp add` or `.mcp.json`):
```json
{"mcpServers": {"quiet-money-youtube-posts": {"command": "python", "args": ["/full/path/to/quiet-money/mcp-servers/yt-community/server.py"]}}}
```
Then ask Claude: "community_login" (sign in as the channel owner in the window that opens), then "community_post day=<date> index=1" (a dry run: it fills the composer and shows a screenshot, it does not press Post).

## Switching publishing on
Publishing is off until you set `QM_COMMUNITY_APPROVED=1` in the MCP server's environment on your machine. Then `community_post(..., publish=true)` or `community_post_day(publish=true)` presses Post. `state/PAUSE` (the kill switch) stops it.

## Tools
`community_status`, `community_login`, `community_post(day, index, publish)`, `community_post_day(day, publish)`.
Pictures and captions come from `distribution/comics/<day>/` (`python -m faceless comics`); every post is logged in `state/community_posts.jsonl` so nothing posts twice.
