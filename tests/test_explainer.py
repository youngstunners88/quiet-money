"""The explainer look: scenes are drawn from a script's `scene` objects, timed to the spoken words, with no image generator."""

import json

from faceless.pipeline import explainer, script as script_mod, visuals


def beats():
    return [
        {"say": "In 2015 he walked away from fifteen million.", "callout": "", "scene": {"type": "fork", "left": {"label": "A", "value": "$15M"}, "right": {"label": "B", "value": "STAKE"}}},
        {"say": "It was four million a year.", "callout": "$4M", "scene": {"type": "stat", "value": "$4M", "label": "A YEAR", "word": "four"}},
        {"say": "Check or stake?", "callout": "", "scene": {"type": "end", "text": "CHECK OR STAKE?"}},
    ]


def test_a_beat_keeps_its_scene_through_normalize():
    s = script_mod.normalize({"title": "t", "hook_text": "h", "beats": beats()})
    assert [b.get("scene", {}).get("type") for b in s["beats"]] == ["fork", "stat", "end"]


def test_a_beat_without_a_scene_gets_a_number_or_phrase_card():
    plan = explainer.choose({"beats": [{"say": "It cost $4M a year.", "callout": "$4M"}, {"say": "Then it changed everything.", "callout": ""}]})
    assert plan[0]["type"] == "stat" and plan[1]["type"] == "phrase" and plan[0]["kind"] == "explainer"


def test_scene_times_are_video_time_and_follow_the_spoken_word():
    spec = {"type": "stat", "value": "$4M", "label": "A YEAR", "word": "four", "words": [(0.2, 0.5, "It"), (0.3, 0.6, "four")]}
    _html, js = explainer._scene(3, 20.0, 5.0, spec, False)
    first = next(ln for ln in js.splitlines() if ln.startswith('E("#s3_v"'))
    assert ",20.300," in first                               # 20.0 (scene start) + 0.3 (the word "four", earlier than the cap)
    assert explainer._OFFSET == 0.0                           # the shift never leaks into the next scene


def test_only_the_first_scene_is_lit_at_frame_zero_and_the_last_never_leaves():
    h0, js0 = explainer._scene(0, 0.0, 4.0, {"type": "end", "text": "X", "words": []}, False)
    h1, js1 = explainer._scene(1, 4.0, 4.0, {"type": "end", "text": "X", "words": []}, True)
    assert 'tl.set("#sc0",{opacity:1,x:0},0.000)' in js0 and 'tl.to("#sc1"' not in js1


def test_every_scene_type_builds(tmp_path):
    for typ in explainer.BUILDERS:
        spec = {"type": typ, "words": [], "left": {"label": "A"}, "right": {"label": "B"}, "items": [{"label": "x", "value": 1, "text": "$1"}, {"label": "y", "value": 3, "text": "$3"}],
                "events": [{"year": "2008", "label": "X"}], "lines": ["A B"], "value": "$5", "text": "T", "percent": 20}
        html_, js = explainer._scene(1, 2.0, 4.0, spec, False)
        assert html_.startswith('<div id="sc1"') and js
    _html, js = explainer._scene(1, 2.0, 4.0, {"type": "catch", "lines": ["ONE"], "words": []}, False)
    assert "s1_tag" in js


def test_the_project_has_every_scene_and_the_total_length(tmp_path, monkeypatch):
    monkeypatch.setattr(explainer.Paths, "fonts", explainer.Paths.fonts)
    specs = [(i, {"kind": "explainer", **b["scene"], "words": []}, 4.0) for i, b in enumerate(beats())]
    total = explainer.build_project(tmp_path, specs, 24)
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert total == 12.0 and all(f'id="sc{i}"' in page for i in range(3)) and 'data-duration="12.000"' in page
    assert json.loads((tmp_path / "meta.json").read_text())["id"] == "cards"


def test_visuals_uses_the_explainer_without_any_image_provider(tmp_path, monkeypatch):
    from faceless.pipeline import cards

    class Job:
        id, pillar, artifacts, dir = "j1", "story", {}, tmp_path

    monkeypatch.setattr(cards, "available", lambda: True)
    rows = visuals.run(Job, {"look": "explainer", "beats": beats()})
    assert Job.artifacts["style"] == "explainer" and all(r["provider"] == "card" and r["path"] is None for r in rows)


def test_no_element_waits_for_a_late_word_longer_than_the_cap():
    late = {"type": "stat", "value": "$4M", "label": "A YEAR", "word": "four", "words": [(4.0, 4.4, "four")]}
    _html, js = explainer._scene(0, 0.0, 6.0, late, False)
    assert f",{explainer.WAIT:.3f}," in next(ln for ln in js.splitlines() if ln.startswith('E("#s0_v"'))
