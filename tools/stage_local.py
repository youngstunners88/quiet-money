#!/usr/bin/env python3
"""Stage locally produced Shorts (production/output/<day>/<job>/final.mp4 + meta.json) as distribution/queue/<day>/q<N>/ for the phone upload scripts.
Rewrites wording that trips ttpolicy (skill faceless-tiktok-policy), lints, and prints loudness. usage: stage_local.py DAY [--into QUEUE_DAY] [--jobs JOB_ID,JOB_ID,...]
(--jobs stages only those jobs, numbered q1.. in the order given; --into names a different queue day than the render day)"""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from faceless import ttpolicy
day = sys.argv[1]; root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SWAP = [(r"\bbleeds?\b", "drains"), (r"\bbleeding\b", "draining"), (r"[Ff]ree money [Rr]eset", "Free reset"), (r"\bpassive income\b", "lasting income"), (r"not free money", "not a free pass")]
ASCII = {"\u2014": ", ", "\u2013": "-", "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " "}
def clean(t):
    for a, b in SWAP: t = re.sub(a, b, t)
    for a, b in ASCII.items(): t = t.replace(a, b)
    return t.encode("ascii", "ignore").decode()
args = sys.argv[2:]
into = args[args.index("--into") + 1] if "--into" in args else day
only = args[args.index("--jobs") + 1].split(",") if "--jobs" in args else None
n = 0
for d in (only if only else sorted(os.listdir(os.path.join(root, "production/output", day)))):
    p = os.path.join(root, "production/output", day, d)
    if not os.path.isfile(p + "/final.mp4") or not os.path.isfile(p + "/meta.json"): continue
    m = json.load(open(p + "/meta.json")); n += 1
    q = os.path.join(root, "distribution/queue", into, f"q{n}"); os.makedirs(q, exist_ok=True)
    shutil.copy(p + "/final.mp4", q + "/video.mp4")
    title, desc, cap = clean(m["title"]), clean(m["description"]), clean(m["caption"])
    open(q + "/POST.md", "w").write(f"# q{n}\n\n## YouTube Shorts\nTitle: {title}\n\n{desc}\n\n## TikTok\n{cap}\n")
    open(q + "/tiktok.txt", "w").write(cap)
    hits = ttpolicy.blockers(title + " " + desc + " " + cap)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", q + "/video.mp4"], capture_output=True, text=True).stdout.strip()
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", q + "/video.mp4", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)[-1]
    print(f"q{n} {d[:45]} | {title} | {float(dur):.1f}s {lufs} LUFS | lint: {'OK' if not hits else [str(h) for h in hits]}")
