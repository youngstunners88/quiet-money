"""`python -m faceless ci` must see what the runner sees: the files a commit would hold, no keys, only the runner's tools,
and the same steps as .github/workflows/ci.yml."""

import os
import subprocess

from faceless import cilocal
from faceless.config import STUDIO


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args], cwd=repo, capture_output=True, check=True)


def test_every_step_is_a_command_of_the_real_workflow():
    workflow = (STUDIO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    missing = [name for name, command in cilocal.STEPS if command not in workflow]
    assert not missing, f"cilocal.STEPS drifted from ci.yml: {missing}"


def test_the_export_holds_what_a_commit_would_and_never_an_ignored_file(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text("*.zip\nsecret.env\n", encoding="utf-8")
    (repo / "kept.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "gone.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    (repo / "gone.py").unlink()                                  # tracked, deleted in the working tree: a commit would delete it
    (repo / "new.py").write_text("z = 3\n", encoding="utf-8")    # untracked and not ignored: a commit would add it
    (repo / "build.zip").write_bytes(b"zip")                     # ignored build output: absent from a clean checkout
    (repo / "secret.env").write_text("KEY=1\n", encoding="utf-8")
    (repo / "shared").mkdir()
    (repo / "shared" / "skill.md").write_text("s\n", encoding="utf-8")
    (repo / "linked").symlink_to("shared")                          # a directory symlink, like .claude/skills/composio
    _git(repo, "add", "linked", "shared")
    monkeypatch.setattr(cilocal, "STUDIO", repo)
    assert cilocal.files() == [".gitignore", "kept.py", "linked", "new.py", "shared/skill.md"]
    dest = tmp_path / "out"
    dest.mkdir()
    assert cilocal.export(dest) == 5 and not (dest / "build.zip").exists() and (dest / ".git").exists()
    assert (dest / "linked").is_symlink() and (dest / "linked" / "skill.md").read_text(encoding="utf-8") == "s\n"


def test_the_runner_environment_has_no_keys_and_only_the_runner_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("MUAPI_API_KEY", "k-should-not-leak")
    monkeypatch.setenv("GITHUB_TOKEN", "t-should-not-leak")
    env = cilocal.clean_env(tmp_path)
    assert set(env) == {"HOME", "PATH", "LANG", "PYTHONDONTWRITEBYTECODE", "CI", "PYTHONUSERBASE"}
    assert not any("should-not-leak" in v for v in env.values())
    tools = set(os.listdir(env["PATH"]))
    assert tools <= {*cilocal.TOOLS, "python", "python3"}
    assert "soffice" not in tools and "libreoffice" not in tools and "npx" not in tools
