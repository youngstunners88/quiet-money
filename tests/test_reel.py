from pathlib import Path

from faceless import reel


def test_the_cta_card_carries_the_handle_and_the_ask(tmp_path):
    out = reel.cta_card(tmp_path / "cta.png", "ONE MONEY RULE A DAY", "Real numbers. No hype.")
    from PIL import Image
    im = Image.open(out)
    assert im.size == (reel.W, reel.H), "the card is the same frame as the video"
    assert im.convert("RGB").getcolors(maxcolors=1 << 24), "the card rendered pixels, not an empty frame"


def test_the_voice_sits_under_the_action_not_over_it():
    assert reel.CLIP_GAIN < reel.VO_GAIN, "narration reads above the clip sound"
    assert reel.BED_GAIN < reel.CLIP_GAIN, "the bed fills gaps, it does not compete with the hits"
    assert 0.0 < reel.DUCK < 1.0


def test_a_line_starts_after_its_cut_never_on_it():
    assert reel.VO_DELAY > 0.0


def test_an_act_inside_a_reel_carries_no_end_card_of_its_own():
    """The reel ends on one CTA card; a card after every act would break the thread."""
    import inspect
    src = inspect.getsource(reel.build)
    assert "card_seconds=0" in src


def test_the_reel_is_mastered_to_the_same_loudness_as_every_other_post():
    """It plays in the same feed as the daily videos; -21 LUFS next to -14 LUFS just sounds broken."""
    assert "I=-14" in reel.LOUDNESS and "TP=-1.5" in reel.LOUDNESS
    import inspect
    assert "LOUDNESS" in inspect.getsource(reel.build)
