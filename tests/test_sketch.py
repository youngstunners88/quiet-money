"""Sketches: motion scenes a small model designs as data. Everything here is offline: the model, the renderer and the reviewer are replaced by fakes.
What is pinned: the validator refuses what would look wrong or say something unchecked, the drawing is data-only, the model call is metered and bounded,
and a scene replaces a still only when a review of its rendered frames passes (nothing generated ships unreviewed)."""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from faceless import config, ledger, safety
from faceless.pipeline import render, sketch, visuals
from faceless.providers import ProviderError, ProviderUnavailable, images
from faceless.state import Job

ALLOWED = {"226659", "8", "30"}
VOCAB = sketch.words("invest that same amount monthly at 8% for 30 years it turns into $226,659 bar race ring that fills") | {sketch._stem(w) for w in sketch.FUNCTION_WORDS}


def base_scene():
    """A small valid scene: three bars growing, a base line, a figure."""
    return {"motif": "bars", "elements": [
        {"id": "bar_1", "type": "rect", "x": 140, "y": 760, "w": 200, "h": 280, "fill": "muted", "origin": "50% 100%"},
        {"id": "bar_2", "type": "rect", "x": 440, "y": 600, "w": 200, "h": 440, "fill": "accent", "origin": "50% 100%"},
        {"id": "bar_3", "type": "rect", "x": 740, "y": 440, "w": 200, "h": 600, "fill": "accent2", "origin": "50% 100%"},
        {"id": "base", "type": "line", "x1": 100, "y1": 1050, "x2": 980, "y2": 1050, "stroke": "dim", "sw": 6},
        {"id": "fig", "type": "text", "x": 540, "y": 1460, "text": "$226,659", "size": 150, "font": "anton", "fill": "ink", "anchor": "middle"}],
        "tweens": [
        {"target": "base", "at": 0.1, "dur": 0.4, "from": {"draw": 0}, "to": {"draw": 1}},
        {"target": "bar_*", "at": 0.3, "dur": 0.7, "from": {"scaleY": 0}, "to": {"scaleY": 1}, "ease": "power3.out", "stagger": 0.2},
        {"target": "fig", "at": 1.6, "dur": 0.5, "from": {"opacity": 0, "y": 30}, "to": {"opacity": 1, "y": 0}, "ease": "back.out(1.7)"}]}


def check(scene, dur=5.0, allowed=ALLOWED, vocab=VOCAB):
    return sketch.validate(scene, dur=dur, allowed=allowed, vocab=vocab)


def refused(scene, match, **kw):
    with pytest.raises(sketch.SpecError, match=match):
        check(scene, **kw)


# ---------------------------------------------------------------- figures and words

def test_figures_are_compared_without_signs_or_commas():
    assert sketch.figures("$1,800 a year, 8% for 30 years, 4.5x and 007") == {"1800", "8", "30", "4.5", "7"}
    assert sketch.figures("no numbers here") == set()


def test_allowed_figures_and_words_come_from_the_beat_and_the_checked_facts():
    beat = {"say": "Invest $15 a month for 10 years.", "callout": "$1,800 total"}
    script = {"facts": [{"claim": "A $15/month plan for 10 years is $1,800", "basis": "15 * 12 * 10 = 1,800"}, "junk", {"claim": 5}]}
    assert sketch.allowed_figures(beat, script) == {"15", "10", "1800", "12", "5"}
    vocab = sketch.allowed_words(beat, script)
    assert {"invest", "month", "year", "total", "plan", "a", "per"} <= vocab and "lost" not in vocab
    assert sketch.allowed_words(beat, {}) >= {"invest", "the"}                     # a script without facts is fine


# ---------------------------------------------------------------- paths

def test_parse_path_reads_absolute_commands_and_refuses_the_rest():
    assert sketch.parse_path("M 10 20 L 30 40 H 90 V 100 Z")[-2:] == [(90.0, 40.0), (90.0, 100.0)]
    assert len(sketch.parse_path("M 0 0 C 10 0 20 10 20 20 Q 30 30 40 40")) == 6      # the curves contribute their control points too
    for bad in ("m 1 2 l 3 4", "M 1 2 A 3 4 5 6 7", "M 1 2 L", "L 1 2 3 4", "M 1 2", "M 1 2 L 3 4 " + "L 5 6 " * 200, "M 1 2 L <3> 4", ""):
        with pytest.raises(sketch.SpecError):
            sketch.parse_path(bad)


# ---------------------------------------------------------------- validation

def test_both_examples_in_the_prompt_are_valid_scenes():
    for ex in sketch.EXAMPLES:
        assert sketch.validate(ex, dur=5.0, allowed={"226659", "8"}, vocab=sketch.words("a year")) ["tweens"]
    assert "EXAMPLE 1" in sketch.SYSTEM and "EXAMPLE 2" in sketch.SYSTEM and sketch.SYSTEM.endswith("Reply with the JSON object only.")


def test_a_good_scene_is_normalised_flat_and_bounded():
    spec = check(base_scene())
    assert [e["id"] for e in spec["elements"]][:3] == ["bar_1", "bar_2", "bar_3"] and spec["motif"] == "bars"
    glob = [t for t in spec["tweens"] if t["target"].startswith("bar_")]
    assert [t["target"] for t in glob] == ["bar_1", "bar_2", "bar_3"] and [t["at"] for t in glob] == [0.3, 0.5, 0.7]       # the prefix matched three elements, staggered
    assert all(t["at"] + t["dur"] <= 4.8 + 1e-6 for t in spec["tweens"])
    assert all(set(t["from"]) == set(t["to"]) for t in spec["tweens"])


def test_a_missing_side_of_a_tween_is_filled_with_the_resting_value_and_a_late_tween_is_clamped():
    sc = base_scene()
    sc["tweens"] = [{"target": "fig", "at": 4.0, "dur": 2.0, "from": {"opacity": 0}, "to": {"y": 0}}] + sc["tweens"][:2]
    spec = check(sc)
    t = spec["tweens"][0]
    assert t["from"] == {"opacity": 0.0, "y": 0.0} and t["to"] == {"opacity": 1.0, "y": 0.0} and t["at"] + t["dur"] <= 4.8 + 1e-6


def test_repeats_expand_with_shifted_copies_and_answer_to_the_bare_id_a_glob_and_the_items_own_id():
    sc = base_scene()
    sc["elements"][:3] = [{"id": "rows", "type": "repeat", "count": 3, "dx": 300, "dy": 0,
                           "item": {"id": "bar", "type": "rect", "x": 140, "y": 600, "w": 200, "h": 440, "fill": "accent", "origin": "50% 100%"}}]
    for target in ("rows", "rows_*", "bar", "bar_*"):
        sc["tweens"][1] = {"target": target, "at": 0.3, "dur": 0.7, "from": {"scaleY": 0}, "to": {"scaleY": 1}, "stagger": 0.1}
        spec = check(sc)
        copies = [e for e in spec["elements"] if e["id"].startswith("rows_")]
        assert [e["x"] for e in copies] == [140, 440, 740], target
        assert [t["target"] for t in spec["tweens"] if t["target"].startswith("rows_")] == ["rows_0", "rows_1", "rows_2"], target


@pytest.mark.parametrize("mutate, match", [
    (lambda s: s["elements"].append({"id": "q", "type": "star"}), "not allowed"),
    (lambda s: s["elements"].append({"id": "Bad Id", "type": "rect", "x": 1, "y": 400, "w": 5, "h": 5}), "element id"),
    (lambda s: s["elements"].append(dict(s["elements"][0])), "used twice"),
    (lambda s: s["elements"][0].update(x=5000), "outside"),
    (lambda s: s["elements"][0].update(fill="blue"), "must be one of"),
    (lambda s: s["elements"][0].update(origin="10% 10%"), "origin"),
    (lambda s: s["elements"][0].update(w=0), "outside"),
    (lambda s: s["elements"][4].update(text="<b>hi</b> $226,659"), "plain characters"),
    (lambda s: s["elements"][4].update(text="x" * 37), "plain characters"),
    (lambda s: s["elements"][4].update(size=20), "outside"),
    (lambda s: s["elements"][4].update(font="comic"), "font"),
    (lambda s: s["tweens"][2].update(ease="wiggle"), "ease"),
    (lambda s: s["tweens"][2].update(**{"from": {"blur": 1}, "to": {"blur": 2}}), "not allowed"),
    (lambda s: s["tweens"][2].update(**{"from": {}, "to": {}}), "from' and 'to"),
    (lambda s: s["tweens"][2].update(target="ghost"), "matches no element"),
    (lambda s: s["tweens"][2].update(at=4.95), "finish 0.2s before"),
    (lambda s: s["tweens"][0].update(target="b1"), "only works on a line or a path"),
    (lambda s: s["tweens"][2].update(**{"to": {"opacity": 0}}), "last frame must show"),
])
def test_the_validator_refuses_each_kind_of_bad_scene_with_a_reason_the_model_can_act_on(mutate, match):
    sc = copy.deepcopy(base_scene())
    if match == "only works on a line or a path":
        sc["tweens"][0] = {"target": "bar_1", "at": 0.1, "dur": 0.4, "from": {"draw": 0}, "to": {"draw": 1}}
    else:
        mutate(sc)
    refused(sc, match)


def test_nothing_may_rest_or_end_in_the_caption_band_but_a_slide_may_start_near_it():
    sc = base_scene()
    sc["elements"][4]["y"] = 1200
    refused(sc, "reserved for captions")
    sc = base_scene()
    sc["tweens"][2] = {"target": "fig", "at": 1.0, "dur": 0.5, "from": {"opacity": 0, "y": -300}, "to": {"opacity": 1, "y": 0}}      # starts high, ends at rest below the band
    check(sc)
    sc["tweens"][2] = {"target": "fig", "at": 1.0, "dur": 0.5, "from": {"opacity": 0, "y": 0}, "to": {"opacity": 1, "y": -250}}      # ends inside the band
    refused(sc, "reserved for captions")
    sc["tweens"][2] = {"target": "fig", "at": 1.0, "dur": 0.5, "from": {"opacity": 0, "scale": 0.2}, "to": {"opacity": 1, "scale": 3}}
    refused(sc, "reaches|reserved")


def test_two_texts_may_not_sit_on_each_other_in_the_finished_frame():
    sc = base_scene()
    sc["elements"].append({"id": "lbl", "type": "text", "x": 540, "y": 1470, "text": "total", "size": 90, "font": "anton", "fill": "ink", "anchor": "middle"})
    sc["tweens"].append({"target": "lbl", "at": 1.8, "dur": 0.4, "from": {"opacity": 0}, "to": {"opacity": 1}})
    refused(sc, "overlap")
    sc["elements"][-1]["y"] = 1660
    check(sc)


def test_a_scene_squeezed_into_a_corner_is_refused():
    sc = base_scene()
    for k, e in enumerate(sc["elements"][:3]):
        e.update(w=40, h=40, y=800, x=300 + 60 * k)
    sc["elements"][3].update(x1=280, x2=480)
    sc["elements"][4].update(text="8", size=60, x=380, y=900)
    refused(sc, "bigger")


def test_the_scene_may_only_use_the_numbers_and_words_its_beat_already_carries():
    sc = base_scene()
    sc["elements"][4]["text"] = "$294,510"
    refused(sc, "numbers that are not")
    sc["elements"][4]["text"] = "0"                                                        # zero is not a claim
    check(sc)
    sc["elements"][4]["text"] = "LOST OVER TIME"
    refused(sc, "words the narrator never said: lost")
    sc["elements"][4].update(text="8% for 30 years", size=80)
    check(sc)
    check(sc, allowed=None, vocab=None)                                                   # the checks can be skipped by a caller that has no beat


def test_size_limits_hold():
    sc = base_scene()
    sc["elements"] = [{"id": "r", "type": "repeat", "count": 25, "dx": 10, "dy": 0, "item": {"id": "d", "type": "circle", "cx": 100, "cy": 500, "r": 5}}] + sc["elements"]
    refused(sc, "outside 2..24")
    sc = base_scene()
    sc["elements"] = [{"id": f"e{i}", "type": "circle", "cx": 100 + i * 5, "cy": 500, "r": 4} for i in range(61)] + sc["elements"]
    refused(sc, "too many elements")
    for bad in ({}, [], {"elements": "x", "tweens": []}, {"elements": [], "tweens": []}, {"elements": [1], "tweens": []}):
        with pytest.raises(sketch.SpecError):
            sketch.validate(bad, dur=5.0)


# ---------------------------------------------------------------- drawing

def test_the_emitted_scene_is_data_only_and_each_property_is_tweened_from_a_known_start():
    spec = check(base_scene())
    svg, js = sketch.emit("s3", 12.0, spec, sketch.palette("#FFD23F", "#2EE59D", "#ff9a3c"))
    assert svg.startswith('<svg class="sk" width="1080" height="1920" viewBox="0 0 1080 1920">') and 'fill="#FFD23F"' in svg and 'fill="#2EE59D"' in svg
    assert 'id="s3_bar_1"' in svg and 'font-family="Anton, sans-serif"' in svg and "&" not in svg.replace("&amp;", "")
    assert 'pathLength="1"' in svg and 'stroke-dasharray="1 1"' in svg                                  # the base line is drawn with a dash trick
    assert not any(bad in (svg + "".join(js)).lower() for bad in ("<script", "http", "onload", "onclick", "javascript", "eval(", "function"))
    assert all(line.startswith(("gsap.set(", "tl.fromTo(")) for line in js)
    assert any('"strokeDashoffset": 1' in line and '"strokeDashoffset": 0' in line for line in js)      # draw 0 -> 1 is a dash offset 1 -> 0
    import re as _re
    assert any(line.endswith(",12.300);") for line in js) and all(_re.search(r",1[23]\.\d{3}\);$", line) for line in js if line.startswith("tl.fromTo"))


def test_a_second_tween_on_the_same_property_does_not_repaint_its_start():
    sc = base_scene()
    sc["tweens"].append({"target": "fig", "at": 3.0, "dur": 0.5, "from": {"opacity": 1, "y": 0}, "to": {"opacity": 1, "y": -20}})
    _, js = sketch.emit("s0", 0.0, check(sc), sketch.palette("#fff", "#0f0", "#f90"))
    later = [line for line in js if "s0_fig" in line and "tl.fromTo" in line]
    assert '"immediateRender": false' in later[-1] and '"immediateRender"' not in later[0]


def test_text_is_escaped_even_if_a_spec_skipped_validation():
    spec = {"motif": "x", "elements": [{"id": "t", "type": "text", "x": 1, "y": 500, "text": "<b>&</b>", "size": 60, "font": "anton", "anchor": "middle", "spacing": 0,
                                        "fill": "ink", "opacity": 1, "origin": "50% 50%"}], "tweens": []}
    svg, _ = sketch.emit("s", 0.0, spec, sketch.palette("#fff", "#0f0", "#f90"))
    assert "&lt;b&gt;&amp;&lt;/b&gt;" in svg and "<b>" not in svg


# ---------------------------------------------------------------- choosing beats

def _script(n=12, callouts=(2, 5, 9)):
    return {"beats": [{"say": f"beat {i} has 10 dollars" if i % 2 else f"beat {i}", "callout": "$5" if i in callouts else ""} for i in range(n)]}


CFG = {"min_seconds": 2.5, "max_per_video": 4}


def test_choose_beats_skips_the_ends_cards_and_neighbours_and_prefers_callouts():
    spans = [(i * 5.0, i * 5.0 + 5.0) for i in range(12)]
    pick = sketch.choose_beats(_script(), spans, {}, CFG)
    assert pick == sorted(pick) and 0 not in pick and 11 not in pick and {2, 5, 9} <= set(pick) and len(pick) <= 4
    assert all(b - a > 1 for a, b in zip(pick, pick[1:]))
    assert sketch.choose_beats(_script(), spans, {5: {}}, CFG) and not {4, 5, 6} & set(sketch.choose_beats(_script(), spans, {5: {}}, CFG))
    short = [(i * 5.0, i * 5.0 + (1.0 if i == 2 else 5.0)) for i in range(12)]
    assert 2 not in sketch.choose_beats(_script(), short, {}, CFG)
    assert sketch.choose_beats(_script(), spans, {}, CFG) == sketch.choose_beats(_script(), spans, {}, CFG)
    assert len(sketch.choose_beats(_script(), spans, {}, {**CFG, "max_per_video": 2})) == 2
    assert sketch.choose_beats({"beats": [{"say": "a"}, {"say": "b"}]}, [(0, 5), (5, 10)], {}, CFG) == []


def test_motifs_are_stable_per_beat_and_do_not_repeat_within_a_video():
    assert sketch.motif_for("job-a", 3) == sketch.motif_for("job-a", 3)
    assert len({sketch.motif_for("job-a", i) for i in range(1, 10)}) > 3
    used = []
    for i in (2, 5, 9, 11):
        used.append(sketch.motif_for("job-a", i, used))
    assert len(set(used)) == 4


# ---------------------------------------------------------------- asking the model

def reply(obj, cost=0.0012, tokens=3000):
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return {"choices": [{"message": {"content": text}}], "usage": {"cost": cost, "total_tokens": tokens, "prompt_tokens": 1800, "completion_tokens": 1200}}


class FakePost:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, body):
        self.calls.append(body)
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


BEAT = {"say": "Invest that same amount monthly at 8% for 30 years and it turns into $226,659.", "callout": "$226,659 total"}
CTX = {"series": "The Math They Hide", "seconds": 5.0, "motif": "a ring that fills", "allowed": ALLOWED, "vocab": VOCAB}


@pytest.fixture
def no_wait(monkeypatch):
    monkeypatch.setattr(sketch.time, "sleep", lambda s: None)


def test_author_returns_a_validated_scene_and_meters_the_spend(monkeypatch, no_wait):
    post = FakePost(reply(base_scene(), cost=0.0013))
    monkeypatch.setattr(sketch, "_post", post)
    got = sketch.author(BEAT, CTX, job="j1")
    assert got["attempts"] == 1 and got["usd"] == 0.0013 and got["spec"]["elements"] and json.loads(got["raw"])["motif"] == "bars"
    body = post.calls[0]
    assert body["model"] == "anthropic/claude-haiku-5.5" and body["reasoning"] == {"effort": "low"} and body["response_format"] == {"type": "json_object"}
    assert body["messages"][0]["role"] == "system" and "EXAMPLE 2" in body["messages"][0]["content"]
    user = body["messages"][1]["content"]
    assert "226659" in user and "Motif: a ring that fills" in user and "The Math They Hide" in user
    assert ledger.used("sketch", "usd") == pytest.approx(0.0013) and ledger.usd_total() == pytest.approx(0.0013)


def test_a_refused_scene_is_sent_back_once_with_the_reason(monkeypatch, no_wait):
    bad = base_scene()
    bad["elements"][4]["text"] = "$999,999"
    post = FakePost(reply(bad), reply(base_scene()))
    monkeypatch.setattr(sketch, "_post", post)
    got = sketch.author(BEAT, CTX)
    assert got["attempts"] == 2 and got["usd"] == pytest.approx(0.0024) and len(got["reasons"]) == 1 and "999999" in got["reasons"][0]
    again = post.calls[1]["messages"]
    assert again[-2]["role"] == "assistant" and "$999,999" in again[-2]["content"] and "refused" in again[-1]["content"] and "999999" in again[-1]["content"]


def test_two_refusals_in_a_row_raise_with_every_reason(monkeypatch, no_wait):
    bad = base_scene()
    bad["elements"][4]["text"] = "$999,999"
    monkeypatch.setattr(sketch, "_post", FakePost(reply(bad), reply("not json at all")))
    with pytest.raises(sketch.SketchError) as e:
        sketch.author(BEAT, CTX)
    assert len(e.value.reasons) == 2 and ledger.used("sketch", "usd") == pytest.approx(0.0024)       # both calls were paid for and both are in the ledger


def test_a_failing_request_is_retried_once_and_then_given_up(monkeypatch, no_wait):
    monkeypatch.setattr(sketch, "_post", FakePost(ProviderError("openrouter 502"), reply(base_scene())))
    assert sketch.author(BEAT, CTX)["attempts"] == 2
    monkeypatch.setattr(sketch, "_post", FakePost(ProviderError("openrouter 502"), ProviderError("openrouter 502")))
    with pytest.raises(sketch.SketchError):
        sketch.author(BEAT, CTX)
    monkeypatch.setattr(sketch, "_post", FakePost(ProviderUnavailable("openrouter rate limit")))
    with pytest.raises(ProviderUnavailable):
        sketch.author(BEAT, CTX)


def test_the_daily_cap_the_pause_and_the_studio_ceiling_stop_a_scene_before_any_request(monkeypatch):
    post = FakePost(reply(base_scene()))
    monkeypatch.setattr(sketch, "_post", post)
    monkeypatch.setitem(config.load()["production"]["sketch"], "daily_usd", 0.005)
    ledger.spend("sketch", "usd", 0.0045, usd=0.0045)
    with pytest.raises(ProviderUnavailable, match="cap"):
        sketch.author(BEAT, CTX)
    monkeypatch.setitem(config.load()["production"]["sketch"], "daily_usd", 5.0)
    ledger.spend("gemini", "usd", 2.995, usd=2.995)                                                   # the studio ceiling is the second wall
    with pytest.raises(ProviderUnavailable, match="ceiling"):
        sketch.author(BEAT, CTX)
    assert not post.calls
    monkeypatch.setattr(safety, "paused", lambda: "owner asked for a break")
    with pytest.raises(ProviderUnavailable, match="paused"):
        sketch.author(BEAT, CTX)


def test_a_redo_shows_the_model_its_own_json_and_the_reviewers_words(monkeypatch, no_wait):
    post = FakePost(reply(base_scene()))
    monkeypatch.setattr(sketch, "_post", post)
    sketch.author(BEAT, CTX, prior='{"motif": "old"}', feedback=["8% overlaps the card", "lower half is empty"])
    msgs = post.calls[0]["messages"]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"] and msgs[2]["content"] == '{"motif": "old"}'
    assert "8% overlaps the card" in msgs[3]["content"] and "lower half is empty" in msgs[3]["content"]


# ---------------------------------------------------------------- planning a video

def _job(tmp_path, monkeypatch, pillar="math", beats=12):
    monkeypatch.setattr(Job, "dir", property(lambda self: tmp_path / "job"))
    job = Job(id="2026-10-08-s1-math-x", pillar=pillar, topic="t", day="2026-10-08")
    job.dir.mkdir(parents=True, exist_ok=True)
    (job.dir / "voice.json").write_text(json.dumps({"beats": [[i * 5.0, i * 5.0 + 5.0] for i in range(beats)]}), encoding="utf-8")
    return job


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setitem(config.load()["production"]["sketch"], "mode", "on")
    monkeypatch.setattr(sketch, "enabled", lambda: sketch.settings()["mode"] == "on")


def test_plan_authors_the_chosen_beats_and_a_failed_beat_just_has_no_scene(tmp_path, monkeypatch, on):
    job = _job(tmp_path, monkeypatch)
    seen = []

    def fake_author(beat, ctx, **kw):
        seen.append(ctx["motif"])
        if "beat 5" in beat["say"]:
            raise sketch.SketchError("refused twice", ["a", "b"])
        return {"spec": check(base_scene()), "raw": "{}", "usd": 0.0015, "tokens": 3000, "seconds": 9.0, "attempts": 1}
    monkeypatch.setattr(sketch, "author", fake_author)
    got = sketch.plan(job, _script(), {})
    assert set(got) == {2, 9} | ({x for x in got if x not in (2, 5, 9)}) and 5 not in got and all(c["kind"] == "sketch" and c["spec"]["elements"] for c in got.values())
    assert len(set(seen)) == len(seen) and job.cost["sketch"] == pytest.approx(0.0015 * len(got))


def test_plan_does_nothing_when_off_unavailable_or_for_other_series(tmp_path, monkeypatch):
    job = _job(tmp_path, monkeypatch)
    monkeypatch.setattr(sketch, "author", lambda *a, **k: pytest.fail("the model must not be asked"))
    assert sketch.plan(job, _script(), {}) == {}                                                   # mode off (the default)
    monkeypatch.setitem(config.load()["production"]["sketch"], "mode", "on")
    monkeypatch.setattr(sketch, "enabled", lambda: False)
    assert sketch.plan(job, _script(), {}) == {}
    monkeypatch.setattr(sketch, "enabled", lambda: True)
    story = _job(tmp_path, monkeypatch, pillar="story")
    assert sketch.plan(story, _script(), {}) == {}
    (story.dir / "voice.json").unlink()
    math = _job(tmp_path, monkeypatch)
    (math.dir / "voice.json").unlink()
    assert sketch.plan(math, _script(), {}) == {}                                                  # no voice yet: nothing to time against


def test_enabled_needs_the_mode_a_key_node_and_no_pause(monkeypatch):
    from faceless.pipeline import cards
    monkeypatch.setattr(cards, "available", lambda: True)
    assert not sketch.enabled()
    monkeypatch.setitem(config.load()["production"]["sketch"], "mode", "on")
    assert not sketch.enabled()                                                                    # no OPENROUTER_API_KEY
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    assert sketch.enabled()
    monkeypatch.setattr(cards, "available", lambda: False)
    assert not sketch.enabled()
    monkeypatch.setattr(cards, "available", lambda: True)
    monkeypatch.setattr(safety, "paused", lambda: "stop")
    assert not sketch.enabled()


def test_candidates_are_only_rows_with_a_still_that_are_not_cards_and_only_when_on(monkeypatch):
    rows = [{"beat": 1, "path": "a.jpg", "sketch": {"kind": "sketch"}}, {"beat": 2, "path": "b.jpg", "card": {"kind": "stat"}, "sketch": {"kind": "sketch"}},
            {"beat": 3, "path": None, "sketch": {"kind": "sketch"}}, {"beat": 4, "path": "d.jpg"}]
    assert sketch.candidates(rows) == {}
    monkeypatch.setitem(config.load()["production"]["sketch"], "mode", "on")
    assert sketch.candidates(rows) == {1: {"kind": "sketch"}}


# ---------------------------------------------------------------- the reviewer

def test_critique_returns_a_clamped_score_and_short_problems(monkeypatch):
    post = FakePost(reply({"score": 9, "problems": ["x" * 400, "second"]}, cost=0.0002))
    monkeypatch.setattr(sketch, "_post", post)
    got = sketch.critique(b"\x89PNG", BEAT, job="j1")
    assert got["score"] == 5 and len(got["problems"][0]) == 160 and got["problems"][1] == "second"
    content = post.calls[0]["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,") and "Narration:" in content[0]["text"]
    assert ledger.used("sketch", "usd") == pytest.approx(0.0002)
    for junk in ("no json", {"problems": []}, {"score": "high"}):
        monkeypatch.setattr(sketch, "_post", FakePost(reply(junk)))
        with pytest.raises(ProviderError):
            sketch.critique(b"x", BEAT)


def test_judge_frame_flags_empty_washed_out_and_caption_band_frames():
    quiet = np.zeros((480, 270), dtype=np.uint8)
    assert sketch.judge_frame(quiet) == "the last frame is empty"
    full = np.full((480, 270), 200, dtype=np.uint8)
    assert sketch.judge_frame(full) == "the last frame is washed out"
    ok = quiet.copy()
    ok[100:140, 40:230] = 255
    assert sketch.judge_frame(ok) == ""
    ok[290:310, 20:250] = 255                                                                       # y ~1200: inside the band
    assert sketch.judge_frame(ok) == "something sits in the caption band"


# ---------------------------------------------------------------- settling a reel

SPANS = [(i * 5.0, i * 5.0 + 5.0) for i in range(12)]
REEL = (Path("reel.mp4"), {2: 0.0, 5: 5.0, 9: 10.0})


@pytest.fixture
def frames(monkeypatch):
    ok = np.zeros((480, 270), dtype=np.uint8)
    ok[100:140, 40:230] = 255
    monkeypatch.setattr(sketch, "_gray", lambda reel, t: ok)
    monkeypatch.setattr(sketch, "strip", lambda reel, off, sec: b"png")


def cards_for(*beats):
    return {b: {"kind": "sketch", "spec": check(base_scene()), "raw": '{"motif": "old"}', "motif": f"m{b}", "usd": 0.0015} for b in beats}


def scores(monkeypatch, table, calls=None):
    def fake(png, beat, job=None):
        n = int(beat["say"].split()[1])
        if calls is not None:
            calls.append(n)
        v = table[n]
        if isinstance(v, Exception):
            raise v
        return {"score": v[0], "problems": v[1], "usd": 0.0002}
    monkeypatch.setattr(sketch, "critique", fake)


def test_scenes_the_reviewer_passes_are_kept_and_nothing_is_redrawn(tmp_path, monkeypatch, frames):
    job = _job(tmp_path, monkeypatch)
    scores(monkeypatch, {2: (5, []), 5: (4, ["small"]), 9: (4, [])})
    monkeypatch.setattr(sketch, "revise", lambda *a, **k: pytest.fail("nothing failed"))
    cand = cards_for(2, 5, 9)
    reel, kept, report = sketch.settle(job, REEL, {**cand, 3: {"kind": "stat"}}, cand, SPANS, _script(), lambda picked: pytest.fail("no redraw needed"))
    assert reel is REEL and set(kept) == {2, 5, 9} and all(v["ok"] for v in report.values()) and job.cost["sketch"] == pytest.approx(0.0006)


def test_a_turned_down_scene_gets_one_revision_and_a_second_look_in_a_new_reel(tmp_path, monkeypatch, frames):
    job = _job(tmp_path, monkeypatch)
    scores(monkeypatch, {2: (5, []), 5: (2, ["8% overlaps the card"]), 9: (2, ["almost empty"])})
    fresh = cards_for(5)
    fresh[5]["revised"] = True
    monkeypatch.setattr(sketch, "revise", lambda job_, failed, cand_, spans, script: {i: fresh[i] for i in failed if i in fresh})
    new_reel = (Path("reel2.mp4"), {2: 0.0, 5: 5.0})
    seen = []

    def rerender(picked):
        seen.append(sorted(picked))
        return new_reel
    cand = cards_for(2, 5, 9)
    other = {3: {"kind": "stat"}}
    # beat 5's second look passes, beat 9 had no revision (the model could not redo it), so it stays a still
    calls = []
    scores(monkeypatch, {2: (5, []), 5: (2, ["8% overlaps the card"]), 9: (2, ["almost empty"])}, calls)
    first = sketch.critique
    state = {"n": 0}

    def second_look(png, beat, job=None):
        n = int(beat["say"].split()[1])
        state["n"] += 1
        return {"score": 4, "problems": [], "usd": 0.0002} if (n == 5 and state["n"] > 3) else first(png, beat, job)
    monkeypatch.setattr(sketch, "critique", second_look)
    reel, kept, report = sketch.settle(job, REEL, {**cand, **other}, cand, SPANS, _script(), rerender)
    assert reel is new_reel and seen == [[2, 3, 5]]                                                  # kept scene, other card and the revision; the failed original of 9 is gone
    assert set(kept) == {2, 5} and kept[5]["revised"] and report[5]["revised"] and report[5]["ok"] and not report[9]["ok"]


def test_a_reviewer_that_cannot_answer_keeps_every_still(tmp_path, monkeypatch, frames):
    job = _job(tmp_path, monkeypatch)
    scores(monkeypatch, {2: ProviderUnavailable("no key"), 5: ProviderError("502"), 9: OSError("down")})
    monkeypatch.setattr(sketch, "revise", lambda *a, **k: pytest.fail("there is nothing to revise without a reviewer"))
    cand = cards_for(2, 5, 9)
    reel, kept, report = sketch.settle(job, REEL, cand, cand, SPANS, _script(), lambda p: pytest.fail("no redraw"))
    assert kept == {} and all("reviewer unavailable" in v["reason"] for v in report.values())


def test_a_failed_frame_check_is_a_reason_to_revise_and_unreadable_frames_are_a_reason_to_drop(tmp_path, monkeypatch, frames):
    job = _job(tmp_path, monkeypatch)
    monkeypatch.setattr(sketch, "_gray", lambda reel, t: np.zeros((480, 270), dtype=np.uint8))
    scores(monkeypatch, {2: (5, []), 5: (5, []), 9: (5, [])})
    revised = []
    monkeypatch.setattr(sketch, "revise", lambda job_, failed, *a: revised.append(sorted(failed)) or {})
    cand = cards_for(2, 5, 9)
    _, kept, report = sketch.settle(job, REEL, cand, cand, SPANS, _script(), lambda p: None)
    assert kept == {} and revised == [[2, 5, 9]] and report[2]["problems"] == ["the last frame is empty"]
    monkeypatch.setattr(sketch, "strip", lambda *a: None)
    monkeypatch.setattr(sketch, "_gray", lambda reel, t: None)
    report = sketch.review(job, REEL, cand, SPANS, _script())
    assert all(v["reason"] == "frames could not be read" and not v["ok"] for v in report.values())
    assert sketch.review(job, (REEL[0], {}), cand, SPANS, _script())[2]["reason"] == "not in the reel"


def test_no_revision_when_it_is_switched_off_or_the_redraw_fails(tmp_path, monkeypatch, frames):
    job = _job(tmp_path, monkeypatch)
    scores(monkeypatch, {2: (5, []), 5: (2, ["messy"]), 9: (4, [])})
    monkeypatch.setattr(sketch, "revise", lambda *a, **k: cards_for(5))
    cand = cards_for(2, 5, 9)
    monkeypatch.setitem(config.load()["production"]["sketch"], "revise", False)
    reel, kept, _ = sketch.settle(job, REEL, cand, cand, SPANS, _script(), lambda p: pytest.fail("revision is off"))
    assert reel is REEL and set(kept) == {2, 9}
    monkeypatch.setitem(config.load()["production"]["sketch"], "revise", True)
    reel, kept, _ = sketch.settle(job, REEL, cand, cand, SPANS, _script(), lambda p: None)         # the second render failed: the first review stands
    assert reel is REEL and set(kept) == {2, 9}


def test_revise_asks_with_the_old_json_and_the_reviewers_words_and_survives_a_refusal(tmp_path, monkeypatch):
    job = _job(tmp_path, monkeypatch)
    asked = []

    def fake_author(beat, ctx, **kw):
        asked.append((ctx["motif"], kw["prior"], kw["feedback"]))
        if "beat 9" in beat["say"]:
            raise sketch.SketchError("no", ["x"])
        return {"spec": check(base_scene()), "raw": "{}", "usd": 0.0015, "tokens": 1, "seconds": 1.0, "attempts": 1}
    monkeypatch.setattr(sketch, "author", fake_author)
    cand = cards_for(5, 9)
    got = sketch.revise(job, {5: {"problems": ["overlap"]}, 9: {"problems": ["empty"]}}, cand, SPANS, _script())
    assert set(got) == {5} and got[5]["revised"] and sorted(asked) == [("m5", '{"motif": "old"}', ["overlap"]), ("m9", '{"motif": "old"}', ["empty"])]


def test_the_review_is_written_on_the_rows_and_a_kept_scene_becomes_the_beats_card():
    rows = [{"beat": 1, "path": "a.jpg"}, {"beat": 2, "path": "b.jpg"}, {"beat": 3, "path": "c.jpg"}]
    kept = {2: {"kind": "sketch", "spec": {}}}
    sketch.apply_to_rows(rows, kept, {2: {"ok": True, "score": 5}, 3: {"ok": False, "score": 2}})
    assert rows[1]["card"] == kept[2] and rows[1]["sketch_review"]["ok"] and "card" not in rows[2] and rows[2]["sketch_review"]["score"] == 2 and "sketch_review" not in rows[0]


# ---------------------------------------------------------------- the renderer takes a kept scene from the reel, and a lost reel changes nothing

pytestmark_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg is not installed")


@pytestmark_ffmpeg
def test_render_cuts_a_kept_scene_from_the_reel_and_writes_the_review_back(tmp_path, monkeypatch):
    from faceless.pipeline import cards
    monkeypatch.setattr(Job, "dir", property(lambda self: tmp_path / "job"))
    monkeypatch.setitem(config.load()["production"]["sketch"], "mode", "on")
    job = Job(id="sk-1", pillar="math", topic="t", day="2026-10-08")
    job.dir.mkdir(parents=True)
    total = 7.0
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=180:duration={total}", "-af", "volume=0.5", "-ar", "44100", "-ac", "1",
                    str(job.dir / "voice.wav")], check=True)
    reel_path = tmp_path / "reel.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=0x224466:s=1080x1920:r=30:d=4", "-pix_fmt", "yuv420p", str(reel_path)], check=True)
    voice = {"duration": total, "beats": [[0.0, 2.4], [2.4, 4.8], [4.8, total]],
             "words": [{"w": w, "start": 0.2 + i * 0.55, "end": 0.6 + i * 0.55, "display": w} for i, w in enumerate("keep your money simple and calm and clear".split())]}
    script = {"title": "t", "hook_text": "KEEP IT SIMPLE", "beats": [{"say": "beat 0", "callout": ""}, {"say": "beat 1 and 200", "callout": "$200"}, {"say": "beat 2", "callout": ""}]}
    for i in range(3):
        images.procedural("abstract", 864, 1536, i, tmp_path / f"img{i}.jpg")

    def fresh_rows():
        rows = [{"path": str(tmp_path / f"img{i}.jpg"), "beat": i, "provider": "cloudflare"} for i in range(3)]
        rows[1]["sketch"] = cards_for(1)[1]
        return rows
    pics = fresh_rows()
    asked = {}

    def fake_reel(job_, picked, spans, pillar, accent, fps):
        asked["picked"] = sorted(picked)
        return reel_path, {1: 1.0}
    monkeypatch.setattr(cards, "render_reel", fake_reel)
    monkeypatch.setattr(sketch, "settle", lambda job_, reel, picked, cand, spans, script_, rerender: (reel, cand, {1: {"ok": True, "score": 5, "problems": [], "reason": ""}}))
    info = render.run(job, script, voice, pics)
    assert asked["picked"] == [1] and info["shots"] >= 3
    rows = json.loads((job.dir / "images.json").read_text(encoding="utf-8"))
    assert rows[1]["card"]["kind"] == "sketch" and rows[1]["sketch_review"]["score"] == 5 and "card" not in rows[0]
    final = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(job.dir / "final.mp4")], capture_output=True, text=True, check=True)
    assert abs(float(json.loads(final.stdout)["format"]["duration"]) - total) < 0.25
    # the reel is lost: the still is used and nothing breaks
    monkeypatch.setattr(cards, "render_reel", lambda *a, **k: None)
    pics2 = fresh_rows()
    info = render.run(job, script, voice, pics2)
    assert info["shots"] >= 3 and "card" not in pics2[1]


# ---------------------------------------------------------------- the visuals stage writes candidates next to the stills

def test_visuals_attaches_a_drafted_scene_to_the_beats_still_and_survives_a_crashing_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(Job, "dir", property(lambda self: tmp_path / "job"))
    job = Job(id="vis-1", pillar="math", topic="t", day="2026-10-08")
    job.dir.mkdir(parents=True)
    still = tmp_path / "s.jpg"
    images.procedural("abstract", 64, 64, 1, still)
    monkeypatch.setattr(images, "generate", lambda prompt, **kw: ("cloudflare", str(still)))
    script = {"beats": [{"say": f"beat {i}", "visual": "a desk", "callout": ""} for i in range(4)]}
    monkeypatch.setattr(sketch, "plan", lambda job_, script_, planned: {2: {"kind": "sketch", "spec": {}}, 9: {"kind": "sketch", "spec": {}}})
    rows = visuals.run(job, script)
    assert rows[2]["sketch"]["kind"] == "sketch" and "sketch" not in rows[1] and len(rows) == 4          # beat 9 does not exist: ignored
    assert json.loads((job.dir / "images.json").read_text(encoding="utf-8"))[2]["sketch"]["kind"] == "sketch"

    def crash(*a, **k):
        raise RuntimeError("model client exploded")
    monkeypatch.setattr(sketch, "plan", crash)
    rows = visuals.run(job, script)
    assert len(rows) == 4 and not any("sketch" in r for r in rows)


@pytestmark_ffmpeg
def test_an_error_in_the_review_leaves_the_stills_and_the_first_reel_alone(tmp_path, monkeypatch):
    from faceless.pipeline import cards
    monkeypatch.setattr(Job, "dir", property(lambda self: tmp_path / "job"))
    monkeypatch.setitem(config.load()["production"]["sketch"], "mode", "on")
    job = Job(id="sk-2", pillar="math", topic="t", day="2026-10-08")
    job.dir.mkdir(parents=True)
    total = 7.0
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=180:duration={total}", "-af", "volume=0.5", "-ar", "44100", "-ac", "1",
                    str(job.dir / "voice.wav")], check=True)
    reel_path = tmp_path / "reel.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=0x224466:s=1080x1920:r=30:d=4", "-pix_fmt", "yuv420p", str(reel_path)], check=True)
    voice = {"duration": total, "beats": [[0.0, 2.4], [2.4, 4.8], [4.8, total]],
             "words": [{"w": w, "start": 0.2 + i * 0.55, "end": 0.6 + i * 0.55, "display": w} for i, w in enumerate("keep your money simple and calm and clear".split())]}
    script = {"title": "t", "hook_text": "KEEP IT SIMPLE", "beats": [{"say": "beat 0", "callout": ""}, {"say": "beat 1", "callout": "$200"}, {"say": "beat 2", "callout": ""}]}
    for i in range(3):
        images.procedural("abstract", 864, 1536, i, tmp_path / f"img{i}.jpg")
    rows = [{"path": str(tmp_path / f"img{i}.jpg"), "beat": i, "provider": "cloudflare"} for i in range(3)]
    rows[1]["sketch"] = cards_for(1)[1]
    names = []

    def fake_reel(job_, picked, spans, pillar, accent, fps, name="reel"):
        names.append(name)
        return reel_path, {1: 1.0}

    def boom(*a, **k):
        raise RuntimeError("the reviewer's client exploded")
    monkeypatch.setattr(cards, "render_reel", fake_reel)
    monkeypatch.setattr(sketch, "settle", boom)
    info = render.run(job, script, voice, rows)
    assert info["shots"] >= 3 and "card" not in rows[1] and names == ["reel"]                    # the still stands; only the first reel was drawn
    from faceless import events
    assert any(e["type"] == "SKETCH_FAILED" and e.get("stage") == "review" for e in events.read())
    # and a second pass, when settle asks for one, is drawn to another file so the first reel's offsets stay true
    def asks_for_a_second_pass(job_, reel, picked, cand, spans, script_, rerender):
        rerender({1: {}})
        return reel, {}, {}
    monkeypatch.setattr(sketch, "settle", asks_for_a_second_pass)
    rows2 = [{"path": str(tmp_path / f"img{i}.jpg"), "beat": i, "provider": "cloudflare"} for i in range(3)]
    rows2[1]["sketch"] = cards_for(1)[1]
    names.clear()
    render.run(job, script, voice, rows2)
    assert names == ["reel", "reel2"]
