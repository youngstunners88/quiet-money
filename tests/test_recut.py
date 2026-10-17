"""The recut desk: the timeline maths, the range parser, and the two detectors against a built video."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from faceless import recut


def test_ranges_parses_and_sorts():
    assert recut._ranges(["12.4-15.2", "3-4"]) == [(3.0, 4.0), (12.4, 15.2)]


@pytest.mark.parametrize("bad", ["12.4", "5-5", "9-2", "a-b"])
def test_ranges_rejects_nonsense(bad):
    with pytest.raises(ValueError):
        recut._ranges([bad])


def test_plan_drops_remove_time_and_covers_keep_it():
    segs = recut.plan(20.0, drops=[(5.0, 7.0)], covers=[(12.0, 14.0)])
    assert sum(s["seconds"] for s in segs) == pytest.approx(18.0)       # only the dropped 2 s leave the timeline
    assert [s["mode"] for s in segs] == ["play", "play", "cover", "play"]
    covered = next(s for s in segs if s["mode"] == "cover")
    assert (covered["start"], covered["end"]) == (12.0, 14.0)


def test_plan_refuses_an_empty_timeline():
    with pytest.raises(ValueError):
        recut.plan(10.0, drops=[(0.0, 10.0)], covers=[])


def test_pick_music_by_series_and_rejects_unknown():
    assert recut.pick_music("escape").exists()
    assert recut.pick_music(None) is None
    assert recut.pick_music("none") is None
    with pytest.raises(ValueError):
        recut.pick_music("no-such-series")


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    """A short video with hard cuts and a burnt-in mark bottom-right: what a generator hands back.

    Built at a real short's proportions, not a thumbnail: the detectors work on how much of the frame a mark covers, so
    a tiny frame tests behaviour no posted video has."""
    import shutil

    import numpy as np
    from PIL import Image, ImageDraw

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    d = tmp_path_factory.mktemp("recut")
    w, h, fps, secs = 360, 640, 12, 6
    mw, mh = 96, 34
    frames = d / "f"
    frames.mkdir()
    mark = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    ImageDraw.Draw(mark).rectangle([2, 2, mw - 3, mh - 3], outline=(255, 255, 255, 230), width=4)
    rng = np.random.default_rng(3)
    for i in range(fps * secs):
        t = i / fps
        base = np.zeros((h, w, 3), np.uint8)
        base[:, :] = [(30, 60, 90), (120, 40, 40), (40, 110, 70)][int(t // 2) % 3]
        cx = int(w * (0.2 + 0.6 * ((t * 0.9) % 1)))
        yy, xx = np.mgrid[0:h, 0:w]
        base[((xx - cx) ** 2 + (yy - int(h * 0.5)) ** 2) < int(w / 6) ** 2] = (240, 230, 210)
        base = (base + rng.integers(0, 10, (h, w, 3))).clip(0, 255).astype(np.uint8)
        im = Image.fromarray(base)
        im.paste(mark, (w - mw - 10, h - mh - 10), mark)
        im.save(frames / f"f{i:04d}.png")
    out = d / "marked.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(frames / "f%04d.png"),
                    "-f", "lavfi", "-i", f"sine=frequency=200:duration={secs}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-shortest", str(out)],
                   check=True, timeout=600)
    return out


def test_probe_reads_the_file(built):
    info = recut.probe(built)
    assert info["seconds"] == pytest.approx(6.0, abs=0.3)
    assert (info["width"], info["height"]) == (360, 640)
    assert info["has_audio"]


def test_shots_finds_the_hard_cuts(built):
    """The scores are printed to ffmpeg's log, not stdout: a reader on stdout finds nothing and calls it one shot."""
    found = recut.shots(built, recut.probe(built)["seconds"], threshold=0.05)
    assert len(found) > 1
    assert found[0]["start"] == 0.0
    assert all(b["start"] == pytest.approx(a["end"]) for a, b in zip(found, found[1:]))


def test_watermark_is_found_bottom_right(built):
    m = recut.find_watermark(built, recut.probe(built)["seconds"])
    assert m["found"], m.get("reason")
    assert m["corner"] == "bottom-right"
    box = m["box"]                                   # the mark sits at (254, 596) and is 96x34
    assert 254 - 20 < box["x"] + box["w"] / 2 < 254 + 96 + 20
    assert 596 - 20 < box["y"] + box["h"] / 2 < 596 + 34 + 20


def test_apply_cuts_covers_brands_and_scores(built, tmp_path):
    out = tmp_path / "recut.mp4"
    r = recut.apply(built, out, drops=["1.0-2.0"], covers=["3.0-4.0"], music="escape", logo="auto")
    assert out.exists()
    after = recut.probe(out)
    assert after["seconds"] == pytest.approx(5.0, abs=0.4)       # one second dropped, the covered second kept
    assert after["has_audio"]
    assert r["watermark"] and r["music"]
    assert [s["mode"] for s in r["segments"]].count("cover") == 1
