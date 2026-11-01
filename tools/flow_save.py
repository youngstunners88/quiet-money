#!/usr/bin/env python3
"""Save Flow stills collected in the browser into the beat files the pipeline reads.

usage: .venv/bin/python tools/flow_save.py PLAN.json MAP.json [SHEET.jpg]
MAP.json is {"s<slot>b<NN>": "<signed flow-content.google URL>"} (window.__map in a Flow tab). The CDN URL needs no
login. Each image is resized to 1080x1920 (Lanczos from Flow's 768x1376 original, light unsharp) and written to
production/cache/flow/<day>/<job>/beatNN.jpg, where faceless/pipeline/visuals.py uses it before any generator.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

plan, urls = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
files = {f"s{v['slot']}b{b['beat']:02d}": b["file"] for v in plan["videos"] for b in v["beats"]}
done = []
for key, url in sorted(urls.items()):
    out = Path(files[key])
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".img") as tmp:
        if subprocess.run(["curl", "-sf", "-o", tmp.name, url]).returncode:
            print("FAIL", key); continue
        im = Image.open(tmp.name).convert("RGB")
    if im.size != (1080, 1920):
        im = im.resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    im.save(out, "JPEG", quality=95)
    done.append((key, out))
print(f"saved {len(done)}/{len(urls)}")
if len(sys.argv) > 3 and done:
    th = [Image.open(p).resize((180, 320)) for _, p in done]
    sheet = Image.new("RGB", (180 * min(8, len(th)), 340 * ((len(th) + 7) // 8)), "black")
    d = ImageDraw.Draw(sheet)
    for i, ((k, _), t) in enumerate(zip(done, th)):
        x, y = 180 * (i % 8), 340 * (i // 8)
        sheet.paste(t, (x, y)); d.text((x + 4, y + 322), k, fill="white")
    sheet.save(sys.argv[3])
