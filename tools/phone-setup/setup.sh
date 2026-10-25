#!/usr/bin/env bash
# Quiet Money phone lane: set this Mac or Linux computer up to drive the phone (skill faceless-phone). Run from anywhere:
#   bash tools/phone-setup/setup.sh
# It checks the tools, builds the phone server, adds it to Claude Code, and runs the doctor. Safe to run again.
set -euo pipefail
cd "$(dirname "$0")/../.."
missing=0
need() { if command -v "$1" >/dev/null 2>&1; then echo "ok      $1"; else echo "MISSING $1  ->  $2"; missing=1; fi; }
need git     "install git"
need node    "install Node.js 20 or newer (nodejs.org, or: brew install node / sudo apt install nodejs npm)"
need python3 "install Python 3.11 or newer (brew install python / sudo apt install python3 python3-pip)"
need adb     "install Android Platform Tools (brew install android-platform-tools / sudo apt install adb)"
[ "$missing" = 0 ] || { echo; echo "Install what is missing, then run this again."; exit 1; }

command -v claude >/dev/null 2>&1 || npm install -g @anthropic-ai/claude-code
python3 -m pip install --quiet requests pillow

( cd tools/open-device-mcp && npm ci && npm run build && npm link )

claude mcp add open-device -- open-device-mcp serve 2>/dev/null || true
echo; echo "--- open-device-mcp doctor ---"
open-device-mcp doctor
echo; echo "Next: plug the phone in with USB debugging on, tap Allow, and follow tools/phone-setup/TEST.md"
