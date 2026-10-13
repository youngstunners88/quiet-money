"""Keep the Markdown map true: CLAUDE.md routes, each workspace CONTEXT.md describes, skills plug in.

The coach's structure (identity file, one short CONTEXT.md per workspace, skills wired in through a routing table) only works while the files
match the repo. This reads them as data and reports drift; it never edits. `python -m faceless context`.
"""
from __future__ import annotations

import re
from pathlib import Path

from faceless import config

MAX_CONTEXT_LINES = 70  # "keep it under a page"; longer detail goes in referenced files


def _commands(root: Path) -> set[str]:
    src = (root / "faceless" / "cli.py").read_text(encoding="utf-8")
    m = re.search(r'choices=\[([^\]]*)\]', src)
    return set(re.findall(r'add_parser\("([\w-]+)"', src)) | (set(re.findall(r'"([\w-]+)"', m.group(1))) if m else set())


def _exists(root: Path, rel: str) -> bool:
    """A routing cell names `faceless/a.py, b.py`: a bare name counts when a file of that name (or a name starting with it) lives anywhere in the repo."""
    if (root / rel).exists():
        return True
    name = rel.split("/")[-1]
    skip = {".git", "node_modules", "state", "production", "site"}
    return any(p for p in root.rglob(name + "*") if not skip & set(p.relative_to(root).parts[:1]))


def check(root: Path | None = None) -> list[tuple[str, str]]:
    """[(level, message)] with level 'fail' or 'warn'."""
    root = root or Path(config.STUDIO)
    out: list[tuple[str, str]] = []
    text = (root / "CLAUDE.md").read_text(encoding="utf-8")
    skills_dir = root / ".claude" / "skills"
    skills = {p.name for p in skills_dir.iterdir() if p.is_dir()} if skills_dir.exists() else set()

    for ws in re.findall(r"^- `/([\w-]+)`", text, re.M):
        ctx = root / ws / "CONTEXT.md"
        if not ctx.exists():
            out.append(("warn", f"workspace /{ws} has no CONTEXT.md"))
        elif len(ctx.read_text(encoding="utf-8").splitlines()) > MAX_CONTEXT_LINES:
            out.append(("warn", f"{ws}/CONTEXT.md is over {MAX_CONTEXT_LINES} lines: move detail into a referenced file"))

    routed: set[str] = set()
    for row in (l for l in text.splitlines() if l.startswith("| ") and not l.startswith("| Task") and not l.startswith("|---")):
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        for tok in re.findall(r"`([^`]+)`", " ".join(cells[1:3])):
            if tok.startswith("python ") or "*" in tok or " " in tok.strip() or tok == "/":
                continue
            for part in tok.split(","):
                part = part.strip().lstrip("/")
                if part and "." in part.split("/")[-1] or (part and "/" in part):
                    if not _exists(root, part.split("(")[0].strip()):
                        out.append(("fail", f"routing row '{cells[0][:40]}' names {part}, which does not exist"))
        for s in re.findall(r"`([\w-]+)`", cells[3]):
            routed.add(s)
            if s not in skills and s not in {"n/a", "composio"}:
                out.append(("fail", f"routing row '{cells[0][:40]}' names skill {s}, which does not exist"))

    have = _commands(root)
    for c in sorted(set(re.findall(r"python -m faceless (\w[\w-]*)", text))):
        if c not in have:
            out.append(("fail", f"CLAUDE.md shows `python -m faceless {c}`, which is not a command"))
    for s in sorted(x for x in skills - routed if x.startswith("faceless-")):
        out.append(("warn", f"skill {s} is not in the CLAUDE.md routing table"))
    return out


def report(res: list[tuple[str, str]]) -> str:
    return "\n".join(f"{lvl.upper():5} {msg}" for lvl, msg in res) or "PASS  CLAUDE.md, the CONTEXT.md files and the skills agree"
