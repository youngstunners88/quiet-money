#!/usr/bin/env python3
"""Contact sheet of a job's Flow stills. usage: .venv/bin/python tools/stills_sheet.py SLOT OUT.jpg"""
import glob, sys
from PIL import Image, ImageDraw
fs = sorted(glob.glob(f"production/cache/flow/*/*-s{sys.argv[1]}-*/beat*.jpg"))
sh = Image.new("RGB", (150 * 7, 290 * ((len(fs) + 6) // 7)))
d = ImageDraw.Draw(sh)
for i, f in enumerate(fs):
    x, y = 150 * (i % 7), 290 * (i // 7)
    sh.paste(Image.open(f).resize((150, 267)), (x, y)); d.text((x + 4, y + 270), f[-6:-4], fill="white")
sh.save(sys.argv[2]); print(len(fs))
