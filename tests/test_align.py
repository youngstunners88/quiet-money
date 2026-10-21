"""Caption timing: alignment of the script to what the voice actually said, and the gate that refuses estimated timings."""

from faceless import align, gauntlet
from faceless.pipeline import voice


def heard(*pairs):
    return [{"w": w, "start": s, "end": s + 0.3} for w, s in pairs]


def test_matched_words_take_the_heard_timing_and_keep_the_script_spelling():
    words, cov = align.match(["Save", "$5", "a", "day."], heard(("save", 0.5), ("$5", 1.0), ("a", 1.4), ("day", 1.6)), 2.0)
    assert [w["w"] for w in words] == ["Save", "$5", "a", "day."] and words[0]["start"] == 0.5 and words[3]["start"] == 1.6 and cov == 1.0


def test_words_the_transcriber_heard_differently_are_spread_inside_the_gap():
    words, cov = align.match(["It", "is", "427", "pages."], heard(("it", 0.0), ("is", 0.4), ("four", 0.8), ("hundred", 1.1), ("twenty-seven", 1.4), ("pages", 2.0)), 2.4)
    assert cov == 0.75 and 0.7 <= words[2]["start"] < words[3]["start"] == 2.0
    assert all(a["start"] <= b["start"] for a, b in zip(words, words[1:]))


def test_gemini_audio_is_aligned_and_a_failed_alignment_is_labelled_estimated(monkeypatch):
    est = [{"w": "Hi.", "start": 0.0, "end": 0.2}]
    monkeypatch.setattr(align, "align", lambda text, wav, total=None: ([{"w": "Hi.", "start": 0.31, "end": 0.6}], 1.0))
    words, timing, cov = voice.timed_words("gemini", "Hi.", "x.wav", 1.0, est)
    assert timing == "aligned" and words[0]["start"] == 0.31
    monkeypatch.setattr(align, "align", lambda text, wav, total=None: None)
    assert voice.timed_words("gemini", "Hi.", "x.wav", 1.0, est)[1] == "estimated"
    assert voice.timed_words("edge", "Hi.", "x.wav", 1.0, est)[1] == "native"


def test_the_caption_sync_gate_fails_only_estimated_timings():
    base = {"duration": 65, "words": [{"w": "x", "start": 0, "end": 1}] * 60}
    gate = lambda v: next(g for g in gauntlet.check_voice({**base, **v}) if g.name == "caption_sync")
    assert gate({"provider": "edge"}).passed and gate({"provider": "gemini", "timing": "aligned"}).passed
    assert not gate({"provider": "gemini", "timing": "estimated"}).passed and not gate({"provider": "gemini"}).passed


def test_a_topic_that_means_the_same_as_a_recent_video_is_skipped(monkeypatch):
    from faceless import embed
    from faceless.pipeline import ideate
    vec = {"same": [1.0, 0.0, 0.0], "other": [0.0, 1.0, 0.0], "past": [1.0, 0.0, 0.0], "x": [0.0, 0.0, 1.0], "y": [0.0, 0.3, 0.95]}
    monkeypatch.setattr(ideate, "recent_scripts", lambda n=120: ["past", "x", "y"])
    monkeypatch.setattr(embed, "embed", lambda texts: [vec[t] for t in texts])
    monkeypatch.setattr(embed, "centered", lambda v, r=None: v)
    items = [{"topic": "same"}, {"topic": "other"}]
    assert ideate.first_distinct(items, [], 0.5)["topic"] == "other"
    assert ideate.first_distinct([{"topic": "same"}], [], 0.5) is None
    monkeypatch.setattr(embed, "embed", lambda texts: None)
    assert ideate.first_distinct(items, [], 0.5)["topic"] == "same"      # no embeddings: the old behaviour


def test_embeddings_never_mix_two_models_in_one_answer(monkeypatch, tmp_path):
    from faceless import embed
    monkeypatch.setattr(embed, "DB", tmp_path / "e.db")
    calls = []
    def gem(texts, model):
        calls.append("gemini")
        if len(calls) > 1:
            raise RuntimeError("429")
        return [[1.0] + [0.0] * 255 for _ in texts]
    def cf(texts, model):
        calls.append("cloudflare")
        return [[0.0, 1.0] + [0.0] * 254 for _ in texts]
    monkeypatch.setattr(embed, "_gemini", gem)
    monkeypatch.setattr(embed, "_cloudflare", cf)
    monkeypatch.setattr(embed, "cfg", lambda: {"chain": ["gemini", "cloudflare"], "gemini_model": "g", "cloudflare_model": "c"})
    out = embed.embed([f"t{i}" for i in range(60)])          # two batches: gemini answers the first, fails the second
    assert all(v[1] == 1.0 for v in out) and embed.LAST_MODEL == "c"


def test_the_backlog_hook_travels_to_the_writer():
    from faceless.pipeline import script
    assert "Suggested opening line" in script.with_hook("an angle", "A janitor died with $8 million.")
    assert script.with_hook("an angle", "") == "an angle"
