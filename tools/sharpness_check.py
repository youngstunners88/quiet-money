#!/usr/bin/env python3
"""Measure whether a video is sharp enough to post. usage: .venv/bin/python tools/sharpness_check.py [--flat] VIDEO.mp4 [...]

Samples 8 frames and reports resolution, fps, bitrate and edge energy (mean of PIL FIND_EDGES on luma). Reference values:
the 2026-10-31 soft Shorts (FLUX 4B stills, crf 21 / 6M cap) scored about 2.5; the Flow-still remakes (crf 16) score 12 to 15.
FAIL when: width < 1080, bitrate < 6 Mbps, or median edge energy < 6. Exit 1 on any FAIL."""
import subprocess, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter


def probe(v):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,bit_rate:format=duration,bit_rate",
                        "-of", "default=nw=1", v], capture_output=True, text=True).stdout
    d = dict(l.split("=", 1) for l in o.split("\n") if "=" in l)
    num, den = d["r_frame_rate"].split("/")
    br = int(d.get("bit_rate") if d.get("bit_rate", "N/A") != "N/A" else 0) or int(float(d.get("bit_rate", 0) or 0))
    return int(d["width"]), int(d["height"]), float(num) / float(den), float(d["duration"]), br


bad = 0
flat = "--flat" in sys.argv   # flat drawn graphics (Showhow, cards) compress small and have little edge texture: only resolution is gated
for v in [a for a in sys.argv[1:] if not a.startswith("--")]:
    w, h, fps, dur, br = probe(v)
    energies = []
    with tempfile.TemporaryDirectory() as t:
        for i in range(8):
            f = Path(t) / f"{i}.png"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{dur * (i + 0.5) / 8:.2f}", "-i", v, "-frames:v", "1", str(f)])
            if f.exists():
                energies.append(float(np.asarray(Image.open(f).convert("L").filter(ImageFilter.FIND_EDGES), dtype=float).mean()))
    med = float(np.median(energies)) if energies else 0.0
    problems = [m for ok, m in ((w >= 1080, f"width {w} < 1080"), (flat or br >= 6_000_000 or br == 0, f"bitrate {br/1e6:.1f} Mbps < 6"), (flat or med >= 6, f"edge energy {med:.1f} < 6 (soft picture)")) if not ok]
    print(f"{'FAIL' if problems else 'PASS'}  {Path(v).parent.name}/{Path(v).name}: {w}x{h} {fps:g}fps {br/1e6:.1f} Mbps, edge energy {med:.1f}" + (f"  <- {'; '.join(problems)}" if problems else ""))
    bad += bool(problems)
sys.exit(1 if bad else 0)
