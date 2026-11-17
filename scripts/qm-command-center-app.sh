#!/usr/bin/env bash
# Open the command center as a desktop app: start the server if needed, then open the signed-in page in the browser.
#
#   scripts/qm-command-center-app.sh
#
# This is what the .desktop entry calls. The token stays on stdout only; it is never written to a log or echoed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/state/tmp/qm-cc-app.log"
mkdir -p "$ROOT/state/tmp"

if ! "$ROOT/scripts/qm-command-center.sh" status >/dev/null 2>&1; then
  "$ROOT/scripts/qm-command-center.sh" start >>"$OUT" 2>&1 || {
    echo "The command center did not start. See $OUT" >&2
    exit 1
  }
fi

URL="$("$ROOT/scripts/qm-command-center.sh" url)"
if [ -z "$URL" ]; then
  echo "Could not build the address; is QM_DASH_TOKEN set? Run: python -m faceless serve --init-token" >&2
  exit 1
fi

# A dedicated app window, not a browser tab: its own profile and window class, no address bar. Falls back to the default browser.
for chrome in chromium chromium-browser google-chrome google-chrome-stable; do
  if command -v "$chrome" >/dev/null 2>&1; then
    mkdir -p "$HOME/.config/qm-command-center"
    exec "$chrome" --app="$URL" --class=qm-cc --name="Quiet Money Command Center" \
      --user-data-dir="$HOME/.config/qm-command-center/chromium" --window-size=1280,900 \
      --no-first-run --no-default-browser-check --password-store=basic
  fi
done
exec xdg-open "$URL"
