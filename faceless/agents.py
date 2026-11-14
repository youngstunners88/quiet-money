"""Every AI agent on this machine in one place: installed CLI agents, their default model, and the live herdr workspaces/panes.

Reads only. Version commands are cached for 30 s because the page is rebuilt on every request. Nothing here starts, stops, prompts or
installs an agent; the page only shows what exists and the command that opens it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

SOURCE = "claude/codex/opencode/hermes/gemini/ollama --version, ~/.claude/settings.json, ~/.codex/config.toml, ~/.hermes/config.yaml, herdr api snapshot"
_CACHE: dict[str, tuple[float, dict]] = {}
_TTL = 30.0

CLIS = (
    {"id": "claude", "name": "Claude Code", "bin": "claude", "version": ["--version"], "launch": "claude"},
    {"id": "codex", "name": "Codex", "bin": "codex", "version": ["--version"], "launch": "codex"},
    {"id": "opencode", "name": "OpenCode", "bin": "opencode", "version": ["--version"], "launch": "opencode"},
    {"id": "hermes", "name": "Hermes", "bin": "hermes", "version": ["--version"], "launch": "hermes chat"},
    {"id": "gemini", "name": "Gemini CLI", "bin": "gemini", "version": ["--version"], "launch": "gemini"},
    {"id": "ollama", "name": "Ollama", "bin": "ollama", "version": ["--version"], "launch": "ollama ps"},
)


def _run(args: list[str], timeout: float = 8.0) -> str | None:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    text = ((r.stdout or "") + (r.stderr or "")).strip()
    return text or None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _first_line(text: str | None) -> str | None:
    return text.splitlines()[0].strip() if text else None


def default_models() -> dict[str, dict]:
    """The model each agent is configured to use, from that agent's own config file. Never guessed."""
    out: dict[str, dict] = {}

    claude = {}
    try:
        cfg = json.loads(_read(Path.home() / ".claude" / "settings.json") or "{}")
        if cfg.get("model"):
            claude = {"model": str(cfg["model"]), "source": "~/.claude/settings.json"}
    except ValueError:
        pass
    out["claude"] = claude

    codex = {}
    m = re.search(r'(?m)^model\s*=\s*"([^"]+)"', _read(Path.home() / ".codex" / "config.toml"))
    if m:
        codex = {"model": m.group(1), "source": "~/.codex/config.toml"}
    out["codex"] = codex

    hermes = {}
    lines = _read(Path.home() / ".hermes" / "config.yaml").splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "model:":
            block = lines[i + 1:i + 14]
            dm = next((re.match(r"\s+default:\s*(\S+)", b) for b in block if re.match(r"\s+default:\s*(\S+)", b)), None)
            pm = next((re.match(r"\s+provider:\s*(\S+)", b) for b in block if re.match(r"\s+provider:\s*(\S+)", b)), None)
            if dm:
                hermes = {"model": dm.group(1).strip("\"'"), "provider": pm.group(1).strip("\"'") if pm else None,
                          "source": "~/.hermes/config.yaml"}
            break
    out["hermes"] = hermes
    return out


def _herdr() -> dict:
    text = _run(["herdr", "api", "snapshot"])
    if not text:
        return {"running": False, "error": "herdr is not installed", "workspaces": [], "agents": []}
    try:
        doc = json.loads(text)
    except ValueError:
        return {"running": True, "error": "herdr answered with something that is not JSON", "workspaces": [], "agents": []}
    if "error" in doc:
        return {"running": False, "error": (doc.get("error") or {}).get("message") or "herdr server is not running", "workspaces": [], "agents": []}
    snap = (doc.get("result") or {}).get("snapshot") or {}
    agents = [{"id": a.get("pane_id"), "agent": a.get("agent"), "status": a.get("agent_status"), "workspace": a.get("workspace_id"),
               "cwd": a.get("cwd")} for a in snap.get("agents") or []]
    return {"running": True, "error": None, "version": snap.get("version"),
            "workspaces": [{"id": w.get("workspace_id"), "label": w.get("label"), "panes": w.get("pane_count"),
                            "status": w.get("agent_status"), "focused": bool(w.get("focused"))} for w in snap.get("workspaces") or []],
            "agents": agents}


def build() -> dict:
    hit = _CACHE.get("agents")
    if hit and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    defaults = default_models()
    clis = []
    for spec in CLIS:
        path = None
        for d in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(d) / spec["bin"]
            if candidate.is_file() and os.access(candidate, os.X_OK):
                path = str(candidate)
                break
        clis.append({"id": spec["id"], "name": spec["name"], "installed": bool(path), "path": path,
                     "version": _first_line(_run([spec["bin"], *spec["version"]])) if path else None,
                     "launch": spec["launch"], "default": defaults.get(spec["id"]) or {}})
    doc = {"clis": clis, "herdr": _herdr(), "source": SOURCE}
    _CACHE["agents"] = (time.monotonic(), doc)
    return doc


def summary(doc: dict | None) -> str:
    if not doc:
        return "Agents: source missing"
    installed = [c["id"] for c in doc.get("clis") or [] if c.get("installed")]
    herdr = doc.get("herdr") or {}
    return f"Agents: {len(installed)} installed ({', '.join(installed) or 'none'}); herdr {'running' if herdr.get('running') else 'not running'}"
