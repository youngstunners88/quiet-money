"""The fallback judge keeps the quality gates alive when Cloudflare Clef cannot answer: same questions, same answer shape, same thresholds.
Live calibration (2026-10-08): clean stills scored 0.20 to 0.28, a still with printed words 0.72, a generated face 0.72 to 0.75."""


import pytest
from PIL import Image

from faceless import config, events, muapi, qa
from faceless.config import Paths
from faceless.providers import ProviderError, ProviderUnavailable, clef, judge


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setattr(Paths, "cache", tmp_path / "cache")
    monkeypatch.setattr(muapi, "available", lambda: True)
    calls = {"upload": [], "run": []}
    monkeypatch.setattr(muapi, "upload", lambda p: calls["upload"].append(str(p)) or "https://hosted/x.jpg")
    reply = {"text": '```json\n{"text": 0.25, "face": 0.72, "logo": 0.5}\n```', "fail_first": False}

    def run(model, payload, out_dir=None, **kw):
        calls["run"].append((model, payload, kw))
        if reply["fail_first"] and len(calls["run"]) == 1:
            raise ProviderError("muapi job failed: Server exception, please try again later")
        return {"text": [reply["text"]] if reply["text"] is not None else [], "usd": 0.0002}
    monkeypatch.setattr(muapi, "run", run)
    calls["reply"] = reply
    return calls


def still(tmp_path, name="a.jpg"):
    p = tmp_path / name
    Image.new("RGB", (864, 1536), "gray").save(p)
    return str(p)


def test_answers_come_back_in_clefs_shape_with_hedged_scores_stretched(desk, tmp_path):
    ans = judge.run("A still.", qa.IMAGE_Q, images=[still(tmp_path)], job="j1")
    assert ans == {"text": {"noul": 0.0}, "face": {"noul": 1.0}, "logo": {"noul": 0.5}}
    model, payload, kw = desk["run"][0]
    assert model == "gemini-3-8-flash" and payload["image_url"] == "https://hosted/x.jpg" and kw["max_usd"] == 0.01
    assert "sign, caption, label" in payload["prompt"] and "JSON" in payload["system_prompt"]
    assert any(e["type"] == "JUDGE_CALL" and e["job"] == "j1" for e in events.read())


def test_several_frames_become_one_sheet_and_one_upload(desk, tmp_path):
    desk["reply"]["text"] = '{"flag": 0.25}'
    judge.run("Frames.", {"flag": qa.FRAME_Q["flag"]}, images=[still(tmp_path, f"{i}.jpg") for i in range(4)])
    assert len(desk["upload"]) == 1 and desk["upload"][0].endswith("sheet.jpg")
    assert Image.open(desk["upload"][0]).size == (1080, 1920)


def test_a_text_only_question_sends_no_image(desk):
    desk["reply"]["text"] = '{"promises_returns": 0.25, "specific_advice": 0.25, "hype": 0.25}'
    judge.run("Some script.", qa.SCRIPT_Q)
    assert "image_url" not in desk["run"][0][1] and desk["upload"] == []


def test_an_upstream_500_is_asked_again_once_then_given_up_on(desk, tmp_path):
    desk["reply"]["fail_first"] = True
    assert judge.run("A still.", qa.IMAGE_Q, images=[still(tmp_path)])["face"]["noul"] == 1.0
    assert len(desk["run"]) == 2
    desk["run"].clear()
    desk["reply"]["text"] = "I cannot answer that"
    with pytest.raises(ProviderError, match="without"):
        judge.run("A still.", qa.IMAGE_Q, images=[still(tmp_path)])
    assert len(desk["run"]) == 2                                      # two asks, then the error surfaces
    desk["reply"]["text"] = None
    with pytest.raises(ProviderError, match="no text"):
        judge.run("A still.", qa.IMAGE_Q, images=[still(tmp_path)])


def test_only_yes_no_questions_and_only_with_a_key(desk, monkeypatch):
    with pytest.raises(ValueError, match="noul"):
        judge.run("x", {"q": {"type": "choice", "instructions": "?"}})
    monkeypatch.setattr(muapi, "available", lambda: False)
    assert not judge.available()
    with pytest.raises(ProviderUnavailable):
        judge.run("x", qa.SCRIPT_Q)
    monkeypatch.setattr(muapi, "available", lambda: True)
    assert judge.available()
    monkeypatch.setitem(config.load().setdefault("qa", {}), "fallback_judge", False)
    assert not judge.available()


# ---------------------------------------------------------------- the QA module uses it when Clef cannot answer

@pytest.fixture
def qa_on(monkeypatch):
    monkeypatch.setitem(config.load().setdefault("qa", {}), "enabled", True)
    monkeypatch.setattr(qa, "_announced", set())


def test_clef_answers_first_and_the_judge_is_not_called(desk, qa_on, monkeypatch, tmp_path):
    monkeypatch.setattr(clef, "available", lambda: True)
    monkeypatch.setattr(clef, "run", lambda *a, **k: {"text": {"noul": 0.9}, "face": {"noul": 0.0}, "logo": {"noul": 0.0}})
    res = qa.check_image(still(tmp_path), "narration", job="j")
    assert res["flags"] == ["text"] and desk["run"] == []


def test_when_clef_is_out_of_free_budget_the_judge_takes_over_and_the_flag_still_works(desk, qa_on, monkeypatch, tmp_path):
    def spent(*a, **k):
        raise ProviderUnavailable("Cloudflare free neuron budget used for today")
    monkeypatch.setattr(clef, "available", lambda: True)
    monkeypatch.setattr(clef, "run", spent)
    desk["reply"]["text"] = '{"text": 0.72, "face": 0.25, "logo": 0.25}'                # the live reading for a still with printed words
    res = qa.check_image(still(tmp_path), "narration", job="j")
    assert res["flags"] == ["text"] and res["face"] == 0.0
    qa.check_image(still(tmp_path), "narration", job="j")
    falls = [e for e in events.read() if e["type"] == "QA_FALLBACK"]
    assert len(falls) == 1 and "neuron budget" in falls[0]["why"]                         # announced once per job, not once per still


def test_with_only_a_muapi_key_qa_still_runs(desk, qa_on, monkeypatch, tmp_path):
    monkeypatch.setattr(clef, "available", lambda: False)
    assert qa.enabled()
    desk["reply"]["text"] = '{"promises_returns": 0.25, "specific_advice": 0.72, "hype": 0.25}'
    res = qa.check_script("Buy this stock now.", job="j")
    assert res["flags"] == ["specific_advice"]


def test_when_nothing_can_answer_it_is_no_opinion_and_it_is_written_down(desk, qa_on, monkeypatch, tmp_path):
    monkeypatch.setattr(clef, "available", lambda: False)
    monkeypatch.setattr(muapi, "available", lambda: False)
    assert not qa.enabled()
    with pytest.raises(ProviderUnavailable):
        qa.ask("x", qa.SCRIPT_Q, job="j9")
    assert any(e["type"] == "QA_UNAVAILABLE" and e["job"] == "j9" for e in events.read())
    assert qa.check_image(still(tmp_path)) is None
