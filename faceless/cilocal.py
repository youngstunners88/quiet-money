"""CI as GitHub sees it, run here before anything is pushed.

A test that passes on this machine and fails on the runner leans on something a clean checkout does not have: a gitignored build output
(the kit zip, rendered media), a tool the runner lacks (LibreOffice, Node), a key in the environment, the network. `python -m faceless ci`
exports exactly the files a commit would contain (tracked plus new, never ignored) into a temp folder, scrubs the environment down to what
the runner has after its apt-get step (git, ffmpeg, poppler; no keys), and runs the same steps as .github/workflows/ci.yml there.
Run it before every push of code. It writes nothing to the repo.
"""

from __future__ import annotations

import os
import shlex
import shutil
import site
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from faceless.config import STUDIO

# What the runner has after its install step. LibreOffice and Node are deliberately absent: tests that need them must skip, not fail.
TOOLS = ("git", "ffmpeg", "ffprobe", "pdftoppm", "pdftotext")
# The commands of .github/workflows/ci.yml, word for word (tests/test_hygiene.py fails if the two drift apart).
STEPS = [
    ("tests", "python -m pytest -q tests"),
    ("skills", "python -m faceless skills"),
    ("imports", 'python -c "import faceless.cli, faceless.orchestrator, faceless.site, faceless.aeo, faceless.brand, faceless.muapi, faceless.preflight, faceless.watchdog, faceless.shop, faceless.listing"'),
    ("site", "python -m faceless site build"),
]


def files() -> list[str]:
    """What a commit would contain: tracked files plus new ones that are not ignored, minus anything deleted."""
    r = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=STUDIO, capture_output=True, check=True)
    names = [n for n in r.stdout.decode("utf-8", "replace").split("\0") if n]
    return sorted({n for n in names if (STUDIO / n).is_file() or (STUDIO / n).is_symlink()})          # skills are symlinked into .claude/skills; a checkout keeps them


def export(dest: Path) -> int:
    n = 0
    for rel in files():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        if (STUDIO / rel).is_symlink():
            os.symlink(os.readlink(STUDIO / rel), dest / rel)
        else:
            shutil.copy2(STUDIO / rel, dest / rel)
        n += 1
    git = {"GIT_AUTHOR_NAME": "ci", "GIT_AUTHOR_EMAIL": "ci@example.com", "GIT_COMMITTER_NAME": "ci", "GIT_COMMITTER_EMAIL": "ci@example.com"}
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True, env={**os.environ, **git})
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True, env={**os.environ, **git})
    return n


def clean_env(work: Path) -> dict[str, str]:
    """Home in the temp folder, PATH holding only the runner's tools, and no key, token or secret of any kind."""
    bindir = work / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    for tool in TOOLS:
        found = shutil.which(tool)
        if found and not (bindir / tool).exists():
            (bindir / tool).symlink_to(found)
    for name in ("python", "python3"):                         # the runner has both on PATH; a shim keeps this interpreter's own environment intact
        shim = bindir / name
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    (work / "home").mkdir(exist_ok=True)
    # PYTHONUSERBASE keeps this interpreter's own packages visible although HOME moved; it carries no secret
    return {"HOME": str(work / "home"), "PATH": str(bindir), "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "CI": "true", "PYTHONUSERBASE": site.getuserbase()}


def run(only: str | None = None, keep: bool = False) -> int:
    work = Path(tempfile.mkdtemp(prefix="faceless-ci-"))
    repo = work / "repo"
    repo.mkdir()
    started = time.time()
    count = export(repo)
    env = clean_env(work)
    print(f"exported {count} files to {repo}; running as the runner would (no keys; tools: {', '.join(t for t in TOOLS if shutil.which(t))})\n")
    failed = 0
    for name, command in STEPS:
        if only and name != only:
            continue
        argv = shlex.split(command)
        argv[0] = sys.executable
        t0 = time.time()
        r = subprocess.run(argv, cwd=repo, env=env, capture_output=True, text=True, check=False)
        ok = r.returncode == 0
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:8} {time.time() - t0:5.0f} s   {command if len(command) < 70 else command[:67] + '...'}")
        if not ok:
            print("\n".join("      " + line for line in (r.stdout + r.stderr).strip().splitlines()[-30:]))
    print(f"\n{'CI would be GREEN' if not failed else f'CI would be RED ({failed} step(s))'} ({time.time() - started:.0f} s)")
    if keep or failed:
        print(f"kept {repo} for inspection (delete it when done)")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return 1 if failed else 0
