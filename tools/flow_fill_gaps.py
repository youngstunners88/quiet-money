#!/usr/bin/env python3
"""Fill beats that have no Flow still with a varied crop of the nearest neighbour that has one.
usage: .venv/bin/python tools/flow_fill_gaps.py PLAN_FULL.json
A different crop (1.45x zoom, corner picked by beat number) reads as a new shot once the pipeline's own move is applied.
Only fills beats listed in the plan's full beat set (production/cache/flow/<day>/<job>/beatNN.jpg); never overwrites."""
import json, sys
from pathlib import Path
from PIL import Image
plan = json.load(open(sys.argv[1]))
for v in plan["videos"]:
    for b in v["beats"]:
        out = Path(b["file"])
        if out.exists():
            continue
        folder, n = out.parent, b["beat"]
        have = sorted(folder.glob("beat*.jpg"), key=lambda p: abs(int(p.stem[4:]) - n))
        if not have:
            print("NO SOURCE", out); continue
        im = Image.open(have[0]).convert("RGB")
        w, h = im.size
        z = 1.45
        cw, ch = int(w / z), int(h / z)
        corner = [(0, 0), (w - cw, 0), (0, h - ch), (w - cw, h - ch), ((w - cw) // 2, (h - ch) // 2)][n % 5]
        crop = im.crop((corner[0], corner[1], corner[0] + cw, corner[1] + ch)).resize((1080, 1920), Image.LANCZOS)
        crop.save(out, "JPEG", quality=95)
        print("filled", out.name, "from", have[0].name)
