#!/bin/bash
# Cloud sessions (Claude Code on the web, scheduled routines) start from a fresh container:
# install the engine's Python dependencies so `python -m faceless daily` and the tests run.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"
# composio depends on pysher, whose legacy setup.py breaks on Debian's patched setuptools
python -m pip install -q --disable-pip-version-check --use-pep517 pysher
python -m pip install -q --disable-pip-version-check -r requirements.txt
command -v ffmpeg >/dev/null || echo "warning: ffmpeg not found; renders will fail" >&2
# HyperFrames (motion cards): free, local, no key. Warm the pinned CLI and turn its anonymous telemetry off.
if command -v npx >/dev/null 2>&1; then
  npx --yes hyperframes@0.8.136 telemetry disable >/dev/null 2>&1 || true
fi
