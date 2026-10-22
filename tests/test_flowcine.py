from datetime import date, timedelta

from faceless import flowcine


def test_three_prompts_a_day_and_ten_seconds():
    ps = flowcine.pick(date(2026, 10, 22))
    assert len(ps) == 3
    assert all("10 seconds" in p for p in ps)


def test_no_scene_repeats_within_four_days():
    seen = []
    d = date(2026, 10, 1)
    for i in range(4):
        for p in flowcine.pick(d + timedelta(days=i)):
            assert p not in seen
            seen.append(p)


def test_prompts_forbid_text_faces_and_logos():
    for p in flowcine.pick(date(2026, 10, 22)):
        for word in ("no text", "no logos", "no human faces"):
            assert word in p


def test_shotlist_writes_three_numbered_prompts(tmp_path, monkeypatch):
    monkeypatch.setattr(flowcine, "SHOTLISTS", tmp_path)
    path = flowcine.shotlist(date(2026, 10, 22))
    text = path.read_text(encoding="utf-8")
    assert "## 01" in text and "## 02" in text and "## 03" in text
    assert "## 04" not in text
