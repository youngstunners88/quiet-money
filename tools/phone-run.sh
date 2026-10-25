#!/usr/bin/env bash
# Run every due phone job on the owner's computer (skill faceless-phone). Needs: the repo, adb with the phone connected,
# and the open-device MCP server added to Claude Code (`claude mcp add open-device -- open-device-mcp serve`).
# Opus 5.5 drives the phone (owner, 2026-10-25: autonomy first); PHONE_MODEL overrides it.
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --rebase --quiet origin main
adb get-state >/dev/null || { echo "no phone: plug it in and allow USB debugging"; exit 1; }
claude -p --model "${PHONE_MODEL:-claude-opus-5-5}" "Use the faceless-phone skill. Run every job that 'python -m faceless phone next --push' hands out, one at a time, following references/recipes.md, and record each with 'phone done'. Stop at the first thing that needs the owner. Then commit state/phone and push to main." \
  --allowedTools "mcp__open-device__*" "Bash(python -m faceless phone:*)" "Bash(python -m faceless client reply:*)" "Bash(git add:*)" "Bash(git commit:*)" "Bash(git push:*)" "Bash(git pull:*)" "Read" "Write"
