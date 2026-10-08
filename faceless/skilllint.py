"""Skill linter: the skills ARE the scheduled routines' instructions, so a stale or malformed skill is a production bug.

Rules come from Anthropic's "Complete Guide to Building Skills" (folder is kebab-case with exactly SKILL.md; frontmatter has `name` equal
to the folder and a `description` that says what it does and when to use it, under 1024 characters, without angle brackets; no README.md
inside the folder; detail goes in references/ so SKILL.md stays short) plus one rule of ours: every `python -m faceless <command>` a
skill tells the agent to run must be a command that exists, and every `references/` or `scripts/` file it points at must exist.
Skills installed from outside (listed in skills-lock.json) are checked but only ever warn: we do not edit upstream files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from faceless.config import STUDIO

SKILLS = STUDIO / ".claude" / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CMD_RE = re.compile(r"python3? -m faceless\s+([a-z][a-z0-9-]*)")
LINK_RE = re.compile(r"`((?:references|scripts|assets)/[A-Za-z0-9_./-]+)`")
WARN_LINES, FAIL_LINES = 400, 700


def commands() -> set[str]:
    """Every command the CLI defines, read from its source so the check never imports the engine."""
    src = (STUDIO / "faceless" / "cli.py").read_text(encoding="utf-8")
    return set(re.findall(r'sub\.add_parser\(\s*"([a-z][a-z0-9-]*)"', src))


def external() -> set[str]:
    try:
        return set(json.loads((STUDIO / "skills-lock.json").read_text(encoding="utf-8")).get("skills", {}))
    except (OSError, ValueError):
        return set()


def frontmatter(text: str) -> tuple[dict, str] | None:
    """({key: value}, body) for a file that starts with a --- block; one-line values, quotes and '>' folded blocks are understood."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        return None
    fm, key = {}, None
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if kv and not line.startswith(" "):
            key, val = kv.group(1), kv.group(2).strip()
            fm[key] = "" if val in (">", ">-", "|", "|-") else val.strip("\"'")
        elif key and line.strip():
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm, m.group(2)


def lint_one(folder: Path, known: set[str]) -> list[tuple[str, str]]:
    """[(level, message)] with level 'fail' or 'warn'."""
    out: list[tuple[str, str]] = []
    skill = folder / "SKILL.md"
    if not skill.exists():
        names = [p.name for p in folder.iterdir() if p.name.lower() == "skill.md"]
        return [("fail", f"no SKILL.md (found {names[0]!r}: the name is case-sensitive)" if names else "no SKILL.md")]
    parsed = frontmatter(skill.read_text(encoding="utf-8"))
    if not parsed:
        return [("fail", "SKILL.md does not start with a --- frontmatter block")]
    fm, body = parsed
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not NAME_RE.match(name):
        out.append(("fail", f"name {name!r} must be kebab-case"))
    if name != folder.name:
        out.append(("fail", f"name {name!r} must equal the folder name {folder.name!r}"))
    if re.search(r"claude|anthropic", name):
        out.append(("fail", "names with 'claude' or 'anthropic' are reserved"))
    if not desc:
        out.append(("fail", "description is empty"))
    if len(desc) > 1024:
        out.append(("fail", f"description is {len(desc)} characters (limit 1024)"))
    if "<" in desc or ">" in desc:
        out.append(("fail", "description contains < or > (frontmatter is loaded into the system prompt)"))
    if desc and not re.search(r"\b(use when|use for|use to|use it|trigger|when asked|when the user|whenever)\b", desc, re.I):
        out.append(("warn", "description never says when to use the skill (add trigger phrases)"))
    if (folder / "README.md").exists():
        out.append(("fail", "README.md inside a skill folder (put the content in SKILL.md or references/)"))
    lines = len(body.splitlines())
    if lines > FAIL_LINES:
        out.append(("fail", f"SKILL.md body is {lines} lines (limit {FAIL_LINES}; move detail to references/)"))
    elif lines > WARN_LINES:
        out.append(("warn", f"SKILL.md body is {lines} lines (aim under {WARN_LINES}; move detail to references/)"))
    for cmd in sorted(set(CMD_RE.findall(body))):
        if cmd not in known:
            out.append(("fail", f"tells the agent to run `python -m faceless {cmd}`, which is not a command"))
    for ref in sorted(set(LINK_RE.findall(body))):
        if not (folder / ref).exists():
            out.append(("fail", f"points at `{ref}`, which does not exist"))
    return out


def lint_all() -> dict[str, list[tuple[str, str]]]:
    known, ext = commands(), external()
    result = {}
    for folder in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        issues = lint_one(folder, known)
        if folder.name in ext:
            issues = [("warn", m) for _, m in issues]                  # upstream skills never fail the build
        result[folder.name] = issues
    return result


def report(result: dict[str, list[tuple[str, str]]]) -> str:
    lines = []
    for name, issues in result.items():
        status = "FAIL" if any(lv == "fail" for lv, _ in issues) else "warn" if issues else "ok"
        lines.append(f"{status:4}  {name}")
        lines += [f"        {lv}: {msg}" for lv, msg in issues]
    return "\n".join(lines)


def failures(result: dict[str, list[tuple[str, str]]]) -> int:
    return sum(1 for issues in result.values() for lv, _ in issues if lv == "fail")
