#!/usr/bin/env bash
# Start, stop or check the Quiet Money command center (python -m faceless serve) in a herdr workspace named qm-cc.
#
#   scripts/qm-command-center.sh start    # start it (in herdr when herdr is running, else in the background), wait for health, show the URL + QR
#   scripts/qm-command-center.sh stop     # stop the server and close the qm-cc workspace
#   scripts/qm-command-center.sh status   # is it answering?
#   scripts/qm-command-center.sh open     # focus the qm-cc workspace in herdr
#
# One key each: add to your shell profile
#   alias qmcc='~/quiet-money/scripts/qm-command-center.sh start'
#   alias qmcc-stop='~/quiet-money/scripts/qm-command-center.sh stop'
#
# herdr commands used here are the ones on herdr.dev/docs/socket-api (read 2026-11-11): `herdr workspace create --cwd --label`,
# `herdr pane run <pane> "<command>"`, `herdr pane read <pane> --source recent --lines N`, `herdr api snapshot`.
# NOT VERIFIED ON A REAL HERDR: this script was written in a cloud session with no herdr binary. Before trusting the herdr path it
# checks `herdr <group> --help` for each verb it is about to use; anything it cannot confirm falls back to a plain background
# process, which needs no herdr at all. The id fields read from `herdr api snapshot` are matched loosely for the same reason.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${QM_CC_PORT:-8787}"
LABEL="qm-cc"
RUN="$ROOT/state/tmp"                      # gitignored
LOG="$RUN/qm-cc.log"
PY="${PYTHON:-python3}"
cd "$ROOT"

host() { "$PY" -c "from faceless import serve; print(serve.lan_ip() or '127.0.0.1')"; }
healthy() { curl -fsS -m 2 "http://$(host):$PORT/healthz" >/dev/null 2>&1; }
has() { herdr "$1" --help 2>/dev/null | grep -qw "$2"; }
herdr_ok() { command -v herdr >/dev/null 2>&1 && herdr api snapshot >/dev/null 2>&1; }

# Prints "<workspace id> <first pane id>" for the workspace labelled qm-cc, or nothing.
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
        if isinstance(pid, str) and re.fullmatch(r"[\w-]+:p\w+", pid) and (node.get("workspace_id") == found["ws"] or pid.split(":")[0] == found["ws"]) and not found["pane"]:
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
  if healthy; then echo "Already running: http://$(host):$PORT/ (workspace $LABEL). To see the QR again: stop, then start."; return 0; fi
  if ! "$PY" -c "from faceless import serve; import sys; sys.exit(0 if serve.token() else 1)"; then
    echo "No QM_DASH_TOKEN yet. Run once: $PY -m faceless serve --init-token"; return 2
  fi
  mkdir -p "$RUN"
  local pane=""
  if herdr_ok && has workspace create && has pane run; then
    [ -n "$(find_ws)" ] || herdr workspace create --cwd "$ROOT" --label "$LABEL" >/dev/null
    read -r _ws pane <<<"$(find_ws) "
    if [ -n "$pane" ]; then
      herdr pane run "$pane" "cd '$ROOT' && $PY -m faceless serve --port $PORT"
    else
      echo "herdr is running but the $LABEL pane id could not be read from 'herdr api snapshot'; starting in the background instead."
    fi
  fi
  if [ -z "$pane" ]; then
    nohup "$PY" -m faceless serve --port "$PORT" >"$LOG" 2>&1 &
    echo "Started in the background (no herdr pane). Log and QR: $LOG"
  fi
  for _ in $(seq 1 40); do healthy && break; sleep 0.5; done
  if ! healthy; then echo "The server did not answer on http://$(host):$PORT/healthz within 20 s."; [ -f "$LOG" ] && tail -5 "$LOG"; return 1; fi
  echo "Healthy: http://$(host):$PORT/  (token required; the QR below carries it)"
  if [ -n "$pane" ] && has pane read; then herdr pane read "$pane" --source recent --lines 40; else cat "$LOG"; fi
}

stop() {
  pkill -f "faceless serve --port $PORT" 2>/dev/null && echo "Server stopped." || echo "No server was running on port $PORT."
  if herdr_ok && has workspace close; then
    read -r ws _pane <<<"$(find_ws) "
    [ -n "$ws" ] && herdr workspace close "$ws" >/dev/null 2>&1 && echo "Closed herdr workspace $LABEL."
  fi
  return 0
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  status) if healthy; then echo "up: http://$(host):$PORT/"; else echo "down"; exit 1; fi ;;
  open) if herdr_ok && has workspace focus; then read -r ws _p <<<"$(find_ws) "; [ -n "$ws" ] && herdr workspace focus "$ws" || echo "No $LABEL workspace; run: $0 start"; else echo "herdr is not running here."; fi ;;
  *) echo "usage: $0 start|stop|status|open"; exit 2 ;;
esac
