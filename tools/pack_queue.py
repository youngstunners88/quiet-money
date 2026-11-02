#!/usr/bin/env python3
"""Copy a finished render into a posting pack. usage: .venv/bin/python tools/pack_queue.py DAY SLOT PACKNAME"""
import glob, json, os, shutil, sys
day, slot, name = sys.argv[1:4]
out = glob.glob(f"production/output/{day}/{day}-s{slot}-*/final.mp4")[0]
m = json.load(open(os.path.dirname(out) + "/meta.json"))
q = f"distribution/queue/{day}/{name}"
os.makedirs(q, exist_ok=True); shutil.copy(out, q + "/video.mp4")
open(q + "/POST.md", "w").write(f"# {name}\n\n## YouTube Shorts\nTitle: {m['title']}\n\n{m['description']}\n\n## TikTok\n{m['caption']}\n")
open(q + "/tiktok.txt", "w").write(m["caption"])
print(name, m["title"])
