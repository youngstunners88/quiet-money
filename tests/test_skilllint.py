"""The skill linter: the skills are the routines' instructions, so a malformed or stale skill fails the build."""

from faceless import skilllint

GOOD = "---\nname: demo-skill\ndescription: Does a thing for the studio. Use when asked to do the thing.\n---\n\n# Demo\nRun `python -m faceless doctor`.\n"


def make(tmp_path, name="demo-skill", text=GOOD, extra=None):
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    for rel, body in (extra or {}).items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(body, encoding="utf-8")
    return d


def fails(folder):
    return [m for lv, m in skilllint.lint_one(folder, skilllint.commands()) if lv == "fail"]


def test_every_skill_in_the_repo_passes():
    res = skilllint.lint_all()
    assert skilllint.failures(res) == 0, skilllint.report(res)
    assert "muapi" in res and "faceless-daily" in res


def test_a_good_skill_passes(tmp_path):
    assert fails(make(tmp_path)) == []


def test_name_rules(tmp_path):
    assert any("kebab" in m for m in fails(make(tmp_path, "Demo_Skill", GOOD.replace("demo-skill", "Demo_Skill"))))
    assert any("equal the folder" in m for m in fails(make(tmp_path, "other-name")))
    assert any("reserved" in m for m in fails(make(tmp_path, "claude-helper", GOOD.replace("demo-skill", "claude-helper"))))


def test_description_rules(tmp_path):
    assert any("empty" in m for m in fails(make(tmp_path, "a-skill", "---\nname: a-skill\ndescription:\n---\nbody")))
    assert any("1024" in m for m in fails(make(tmp_path, "b-skill", f"---\nname: b-skill\ndescription: {'x' * 1030}\n---\nbody")))
    assert any("< or >" in m for m in fails(make(tmp_path, "c-skill", "---\nname: c-skill\ndescription: Use when asked to open <file>.\n---\nbody")))
    soft = skilllint.lint_one(make(tmp_path, "d-skill", "---\nname: d-skill\ndescription: A thing.\n---\nbody"), skilllint.commands())
    assert ("warn", "description never says when to use the skill (add trigger phrases)") in soft


def test_structure_rules(tmp_path):
    assert any("frontmatter" in m for m in fails(make(tmp_path, "e-skill", "# no frontmatter")))
    assert any("README.md" in m for m in fails(make(tmp_path, "f-skill", GOOD.replace("demo-skill", "f-skill"), {"README.md": "x"})))
    d = tmp_path / "g-skill"
    d.mkdir()
    (d / "skill.md").write_text(GOOD, encoding="utf-8")
    assert any("case-sensitive" in m for m in fails(d))
    long = GOOD.replace("demo-skill", "h-skill") + "line\n" * 720
    assert any("lines" in m for m in fails(make(tmp_path, "h-skill", long)))


def test_stale_commands_and_files_are_caught(tmp_path):
    text = GOOD.replace("demo-skill", "i-skill") + "Then run `python -m faceless nonexistent-command` and read `references/missing.md`.\n"
    msgs = fails(make(tmp_path, "i-skill", text))
    assert any("nonexistent-command" in m for m in msgs) and any("missing.md" in m for m in msgs)
    ok = GOOD.replace("demo-skill", "j-skill") + "See `references/there.md`.\n"
    assert fails(make(tmp_path, "j-skill", ok, {"references/there.md": "x"})) == []


def test_upstream_skills_only_warn(tmp_path, monkeypatch):
    monkeypatch.setattr(skilllint, "SKILLS", tmp_path)
    monkeypatch.setattr(skilllint, "external", lambda: {"vendor-skill"})
    make(tmp_path, "vendor-skill", "---\nname: vendor-skill\ndescription: <bad>\n---\nbody")
    res = skilllint.lint_all()
    assert skilllint.failures(res) == 0 and res["vendor-skill"]


def test_frontmatter_parser_handles_quotes_and_folded_blocks():
    fm, body = skilllint.frontmatter("---\nname: x\ndescription: >\n  first line\n  second line\nlicense: \"MIT\"\n---\nbody\n")
    assert fm["description"] == "first line second line" and fm["license"] == "MIT" and body == "body\n"
