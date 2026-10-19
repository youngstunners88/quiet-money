from pathlib import Path

from faceless import contextlint


def _studio(tmp_path: Path, claude: str, ctx_lines: int = 5) -> Path:
    (tmp_path / "faceless").mkdir()
    (tmp_path / "faceless" / "cli.py").write_text('sub.add_parser("daily")\n', encoding="utf-8")
    (tmp_path / ".claude" / "skills" / "faceless-daily").mkdir(parents=True)
    (tmp_path / "script-lab").mkdir()
    (tmp_path / "script-lab" / "CONTEXT.md").write_text("x\n" * ctx_lines, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(claude, encoding="utf-8")
    return tmp_path


GOOD = "- `/script-lab`: writing\n\n| Task | Go to | Read | Skill |\n|---|---|---|---|\n| Write | `/script-lab` | `script-lab/CONTEXT.md` | `faceless-daily` |\n\n`python -m faceless daily`\n"


def test_a_true_map_passes(tmp_path):
    assert contextlint.check(_studio(tmp_path, GOOD)) == []


def test_drift_is_reported(tmp_path):
    bad = GOOD.replace("faceless-daily`", "faceless-ghost`").replace("script-lab/CONTEXT.md", "script-lab/GONE.md") + "`python -m faceless nope`\n"
    msgs = " ".join(m for _, m in contextlint.check(_studio(tmp_path, bad)))
    assert "faceless-ghost" in msgs and "GONE.md" in msgs and "nope" in msgs


def test_long_context_and_unrouted_skill_warn(tmp_path):
    root = _studio(tmp_path, GOOD.replace("`faceless-daily`", "`n/a`"), ctx_lines=90)
    levels = dict((m.split()[0], l) for l, m in contextlint.check(root))
    assert levels.get("script-lab/CONTEXT.md") == "warn" and levels.get("skill") == "warn"
