"""The host: lines are checked, the choice is validated, clips are priced before they are paid for and need the reference photo to be generated."""

import json
from datetime import date

import pytest

from faceless import host
from faceless.providers import ProviderError, ProviderUnavailable


def test_candidate_lines_all_fit_ten_seconds_and_pass_the_checks():
    for k, text in host.INTRO_CANDIDATES.items():
        assert host.check_line(text) == [], k
        assert len(text.split()) <= host.MAX_WORDS


def test_lines_that_trail_off_run_long_or_promise_are_refused():
    assert host.check_line("Welcome to the channel where we talk about money...")
    assert host.check_line("word " * 40 + "end.")
    assert host.check_line("You will get rich, guaranteed returns on every dollar.")


def test_choose_line_validates_the_deciders_answer(monkeypatch):
    class D:
        value, backend = "zzz", "jev"
    monkeypatch.setattr(host.decide, "ask", lambda q, s, job=None: {"intro_line": D()})
    key, text, backend = host.choose_line()
    assert key in host.INTRO_CANDIDATES and text == host.INTRO_CANDIDATES[key] and backend == "jev"


def test_clip_is_priced_not_paid_without_apply_and_refuses_a_bad_line(monkeypatch, tmp_path):
    monkeypatch.setattr(host, "ANCHOR", tmp_path / "none.wav")
    monkeypatch.setattr(host.muapi, "estimate", lambda m, p: 1.5)
    out = host.make_clip(host.INTRO_CANDIDATES["b"])
    assert out["applied"] is False and out["price_usd"] == 1.5 and out["model"] == "seedance-2-i2v"
    with pytest.raises(ProviderError):
        host.make_clip("Trailing off...")


def test_generating_needs_the_reference_photo(monkeypatch, tmp_path):
    monkeypatch.setattr(host, "ANCHOR", tmp_path / "none.wav")
    monkeypatch.setattr(host, "REFERENCE", tmp_path / "missing.png")
    monkeypatch.setattr(host.muapi, "estimate", lambda m, p: 1.5)
    with pytest.raises(ProviderUnavailable, match="reference photograph"):
        host.make_clip(host.INTRO_CANDIDATES["b"], apply=True)


def test_later_clips_use_the_reference_audio_model_so_the_voice_carries_over(monkeypatch, tmp_path):
    anchor = tmp_path / "a.wav"
    anchor.write_bytes(b"x")
    monkeypatch.setattr(host, "ANCHOR", anchor)
    monkeypatch.setattr(host.muapi, "estimate", lambda m, p: 1.5)
    out = host.make_clip(host.INTRO_CANDIDATES["b"])
    assert out["model"] == "seedance-2-omni-reference-no-video-fast" and out["voice_anchor"] is True


def test_the_prompt_locks_face_look_pin_voice_and_the_words():
    p = host.shot_prompt(host.INTRO_CANDIDATES["b"])
    assert "@image1" in p and "gold enamel pin" in p and "black letter Q" in p and host.INTRO_CANDIDATES["b"] in p and "no subtitles" in p


def test_due_is_once_a_week_on_the_weekday_and_only_when_enabled(monkeypatch, tmp_path):
    cfg = {"host": {"enabled": True, "weekday": 0}}
    monkeypatch.setattr(host.config, "load", lambda: cfg)
    monkeypatch.setattr(host, "STATE", tmp_path / "host.json")
    monday, tuesday = date(2026, 10, 12), date(2026, 10, 13)
    assert host.due(monday) and not host.due(tuesday)
    (tmp_path / "host.json").write_text(json.dumps({"videos": [{"date": "2026-10-12"}]}))
    assert not host.due(monday)                     # already made this week
    assert host.due(date(2026, 10, 19))             # next Monday
    cfg["host"]["enabled"] = False
    assert not host.due(date(2026, 10, 19))


def test_the_shipped_host_is_off_until_the_owner_approves():
    assert host.config.load()["host"]["enabled"] is False


def test_a_registered_host_clip_cannot_be_posted_until_the_owner_approves(monkeypatch, tmp_path):
    from faceless import state as st
    monkeypatch.setattr(host, "STATE", tmp_path / "host.json")
    monkeypatch.setattr("faceless.config.Paths.jobs", tmp_path / "jobs")
    monkeypatch.setattr("faceless.config.Paths.output", tmp_path / "out", raising=False)
    (tmp_path / "jobs").mkdir()
    r = host.register(tmp_path / "v.mp4", "Welcome to Quiet Money.", "Welcome")
    job = st.load_job(r["job"])
    assert job.scores["passed"] is False and job.status == "packaged"
