"""A video renders end to end with no key, no network and no AI: the regression test for the renderer, the captions and the audio mix.

It builds a seven-second voice (a tone), three procedural pictures and a three-beat script, runs the real renderer, and measures the
file with ffprobe and ffmpeg: 1080x1920, the right length, one audio stream, the delivery loudness, burned-in captions, a cover. It needs
ffmpeg (CI installs it); without ffmpeg it is skipped, never faked."""

import json
import re
import shutil
import subprocess

import pytest

from faceless import config
from faceless.pipeline import render
from faceless.providers import images
from faceless.state import Job

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg is not installed")


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def test_a_video_renders_end_to_end_without_any_key(tmp_path, monkeypatch):
    monkeypatch.setattr(Job, "dir", property(lambda self: tmp_path / "job"))
    monkeypatch.setitem(config.load()["production"]["cards"], "mode", "off")        # HyperFrames is a network install: not part of this smoke test
    job = Job(id="smoke-1", pillar="story", topic="smoke", day="2026-10-08")
    job.dir.mkdir(parents=True)
    total = 7.0
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=180:duration={total}", "-af", "volume=0.5",
                    "-ar", "44100", "-ac", "1", str(job.dir / "voice.wav")], check=True)
    voice = {"duration": total, "beats": [[0.0, 2.4], [2.4, 4.8], [4.8, total]],
             "words": [{"w": w, "start": 0.2 + i * 0.55, "end": 0.6 + i * 0.55, "display": w} for i, w in enumerate("keep your money simple and calm and clear".split())]}
    script = {"title": "Smoke test", "hook_text": "KEEP IT SIMPLE", "beats": [{"say": "keep your money simple", "callout": ""}, {"say": "and calm", "callout": "$200"}, {"say": "and clear", "callout": ""}]}
    pics = []
    for i in range(3):
        p = tmp_path / f"img{i}.jpg"
        images.procedural("abstract", 864, 1536, i, p)
        pics.append({"path": str(p), "beat": i, "provider": "procedural"})
    info = render.run(job, script, voice, pics)

    final = job.dir / "final.mp4"
    meta = probe(final)
    video = next(s for s in meta["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1080, 1920) and video["r_frame_rate"] == "30/1"
    assert abs(float(meta["format"]["duration"]) - total) < 0.25
    assert sum(s["codec_type"] == "audio" for s in meta["streams"]) == 1
    assert -16.5 <= loudness(final) <= -12.0                                         # delivered at about -14 LUFS
    assert info["captioned_words"] > 0 and (job.dir / "cover.jpg").stat().st_size > 5000 and info["shots"] >= 3
    assert (job.dir / "captions.ass").read_text().count("Dialogue:") >= 3            # captions were really written
