#!/bin/bash
# Cloud sessions (Claude Code on the web, scheduled routines) start from a fresh container:
# install the engine's Python dependencies so `python -m faceless daily` and the tests run.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"
# A flaky network at 09:17 must not cost a day: retry each install with a growing pause before giving up.
retry() {
  local n=0
  until "$@"; do
    n=$((n + 1))
    if [ "$n" -ge 4 ]; then echo "error: '$*' failed $n times" >&2; return 1; fi
    echo "retry $n: $*" >&2
    sleep $((n * 8))
  done
}
# composio depends on pysher, whose legacy setup.py breaks on Debian's patched setuptools
retry python -m pip install -q --disable-pip-version-check --use-pep517 pysher
retry python -m pip install -q --disable-pip-version-check -r requirements.txt
command -v ffmpeg >/dev/null || echo "warning: ffmpeg not found; renders will fail" >&2
# HyperFrames (motion cards): free, local, no key. Warm the pinned CLI and turn its anonymous telemetry off.
if command -v npx >/dev/null 2>&1; then
  npx --yes hyperframes@0.8.136 telemetry disable >/dev/null 2>&1 || true
fi
