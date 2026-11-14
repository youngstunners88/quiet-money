#!/usr/bin/env bash
# Put Hermes in herdr as its own workspace next to the command center (qm-cc).
#
#   scripts/qm-hermes-workspace.sh start    # start herdr if needed, open the qm-hermes workspace, run `hermes chat` in its pane
#   scripts/qm-hermes-workspace.sh open     # focus the qm-hermes workspace
#   scripts/qm-hermes-workspace.sh status   # is herdr running, does the workspace exist, which Hermes version
#   scripts/qm-hermes-workspace.sh stop     # close the qm-hermes workspace (does not stop the shared herdr server)
#
# When herdr is not available it falls back to the Hermes desktop app, so the same key still gets you an agent. Nothing here reads or
# sends a message; it only opens a terminal for the owner.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="qm-hermes"
RUN="$ROOT/state/tmp"
LOG="$RUN/qm-hermes.log"
HERMES="${HERMES_BIN:-$HOME/.local/bin/hermes}"
DESKTOP="${HERMES_DESKTOP_BIN:-$HOME/.local/bin/hermes-desktop}"
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; else PY=python3; fi
mkdir -p "$RUN"

has() { herdr "$1" --help 2>/dev/null | grep -qw "$2"; }
herdr_ok() { command -v herdr >/dev/null 2>&1 && herdr api snapshot >/dev/null 2>&1; }

ensure_herdr() {
  herdr_ok && return 0
  command -v herdr >/dev/null 2>&1 || return 1
  nohup herdr server >"$RUN/herdr-server.log" 2>&1 &
  for _ in $(seq 1 20); do herdr_ok && return 0; sleep 0.25; done
  return 1
}

# Prints "<workspace id> <first pane id>" for the workspace labelled qm-hermes, or nothing.
find_ws() {
  herdr api snapshot 2>/dev/null | "$PY" -c '
import json, re, sys
label = sys.argv[1]
try:
    doc = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
found = {"ws": None, "pane": None}
def walk(node):
    if isinstance(node, dict):
        if node.get("label") == label and not found["ws"]:
            found["ws"] = node.get("workspace_id") or node.get("id")
        for v in node.values():
            walk(v)
    elif isinstance(node, list):
        for v in node:
            walk(v)
walk(doc)
def panes(node):
    if isinstance(node, dict):
        pid = node.get("pane_id") or node.get("id")
        if isinstance(pid, str) and re.fullmatch(r"[\w-]+:p\w+", pid) and not found["pane"]:
            if node.get("workspace_id") == found["ws"] or pid.split(":")[0] == found["ws"]:
                found["pane"] = pid
        for v in node.values():
            panes(v)
    elif isinstance(node, list):
        for v in node:
            panes(v)
if found["ws"]:
    panes(doc)
    print(found["ws"], found["pane"] or "")
' "$LABEL"
}

start() {
  if ! command -v herdr >/dev/null 2>&1; then
    echo "herdr is not installed; opening the Hermes desktop app instead."
    nohup "$DESKTOP" >"$LOG" 2>&1 &
    echo "Started Hermes desktop (log: $LOG)."
    return 0
  fi
  if ! ensure_herdr; then
    echo "herdr did not start; opening the Hermes desktop app instead."
    nohup "$DESKTOP" >"$LOG" 2>&1 &
    echo "Started Hermes desktop (log: $LOG)."
    return 0
  fi
  if ! has workspace create; then
    echo "This herdr does not expose 'workspace create'; open herdr and make the workspace by hand."
    return 1
  fi
  local ws="" pane=""
  read -r ws pane <<<"$(find_ws) "
  if [ -z "$ws" ]; then
    herdr workspace create --cwd "$ROOT" --label "$LABEL" >/dev/null
    read -r ws pane <<<"$(find_ws) "
  fi
  if [ -z "$ws" ]; then
    echo "The $LABEL workspace was not created; run 'herdr' and check 'herdr api snapshot'."
    return 1
  fi
  if [ -n "$pane" ] && has pane run; then
    herdr pane run "$pane" "cd '$ROOT' && '$HERMES' chat" >/dev/null
    echo "Hermes is in the $LABEL workspace ($pane)."
  else
    echo "Workspace $LABEL exists but its pane id was not found; focus it with: $0 open"
  fi
  has workspace focus && herdr workspace focus "$ws" >/dev/null 2>&1 || true
}

stop() {
  if ! herdr_ok; then echo "herdr is not running."; return 0; fi
  local ws="" _pane=""
  read -r ws _pane <<<"$(find_ws) "
  if [ -n "$ws" ] && has workspace close; then
    herdr workspace close "$ws" >/dev/null 2>&1 && echo "Closed workspace $LABEL." || echo "Could not close $LABEL."
  else
    echo "No $LABEL workspace."
  fi
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  open) if herdr_ok && has workspace focus; then read -r ws _p <<<"$(find_ws) "; [ -n "$ws" ] && herdr workspace focus "$ws" || echo "No $LABEL workspace; run: $0 start"; else echo "herdr is not running here."; fi ;;
  status)
    herdr_ok && echo "herdr: running" || echo "herdr: not running"
    read -r ws pane <<<"$(find_ws 2>/dev/null || true) "
    [ -n "$ws" ] && echo "workspace $LABEL: $ws ${pane:-(no pane id)}" || echo "workspace $LABEL: absent"
    if [ -x "$HERMES" ]; then "$HERMES" --version 2>/dev/null | head -1 || true; else echo "hermes: not installed"; fi
    ;;
  *) echo "usage: $0 start|stop|status|open"; exit 2 ;;
esac
