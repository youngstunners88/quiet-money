"""Edge TTS is retried on the same voice before the voice chain moves on. Offline: edge_tts is replaced."""

import sys
import types

import pytest

from faceless.providers import ProviderError, tts


def _fake_edge(monkeypatch, plan):
    """plan: one entry per attempt, 'fail' or 'ok'. Returns the attempt counter."""
    calls = {"n": 0}

    class Communicate:
        def __init__(self, *a, **k):
            pass

        async def stream(self):
            calls["n"] += 1
            if plan[calls["n"] - 1] == "fail":
                raise RuntimeError("NoAudioReceived")
            yield {"type": "audio", "data": b"x" * 5000}
            yield {"type": "WordBoundary", "offset": 0, "duration": 5_000_000, "text": "hello"}
    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=Communicate))
    monkeypatch.setattr(tts, "_edge_ssl_patch", lambda: None)
    monkeypatch.setattr(tts, "_to_wav", lambda mp3, out: out.write_bytes(b"wav"))
    monkeypatch.setattr(tts.time, "sleep", lambda s: None)
    return calls


def test_a_transient_no_audio_is_retried_on_the_same_voice(tmp_path, monkeypatch):
    calls = _fake_edge(monkeypatch, ["fail", "fail", "ok"])
    words = tts.edge("hello", tmp_path / "v.wav")
    assert calls["n"] == 3 and words[0]["w"] == "hello"                  # the third try worked, no voice change


def test_three_failures_still_raise_so_the_chain_can_move_on(tmp_path, monkeypatch):
    calls = _fake_edge(monkeypatch, ["fail", "fail", "fail"])
    with pytest.raises(ProviderError):
        tts.edge("hello", tmp_path / "v.wav")
    assert calls["n"] == 3
