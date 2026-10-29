#!/usr/bin/env python3
"""Snapshot the channel's public numbers from the owner's phone (skill faceless-performance-review).
usage: perf-snapshot.py   -> analytics/snapshots/youtube-<date>.json  (every Short: title, views, in feed order, newest first)
The YouTube app exposes "<title>, <n> views - play Short" for each tile on the channel's Shorts tab. TikTok's grid does not expose its numbers to the UI tree:
read them from a screenshot of the profile and add them to the same file by hand (see the skill)."""
import datetime as dt, html, json, os, re, subprocess, sys, time
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
def adb(c): return subprocess.run(["adb", "shell", c], capture_output=True, text=True).stdout
def dump():
    return subprocess.run("adb exec-out uiautomator dump /dev/tty", shell=True, capture_output=True, text=True).stdout
def parse_views(s):
    s = s.replace(",", "")
    if s.lower().startswith("no"): return 0
    m = re.match(r"([\d.]+)\s*([KkMm]?)", s)
    return int(float(m.group(1)) * {"": 1, "k": 1000, "m": 1000000}[m.group(2).lower()]) if m else None
adb("am force-stop com.google.android.youtube"); adb("am start -a android.intent.action.VIEW -d https://www.youtube.com/@quietmoneyrule/shorts com.google.android.youtube"); time.sleep(8)
seen, rows, idle = set(), [], 0
while idle < 3 and len(rows) < 400:
    new = 0
    for d in re.findall(r'content-desc="([^"]*play Short)"', dump()):
        d = html.unescape(d); m = re.match(r"(.*), ([\d.,KkMm]+|No) views? - play Short$", d)
        if m and m.group(1) not in seen:
            seen.add(m.group(1)); rows.append({"title": m.group(1), "views": parse_views(m.group(2))}); new += 1
    idle = idle + 1 if not new else 0
    adb("input swipe 540 1700 540 800 350"); time.sleep(1.3)
out = os.path.join(REPO, "analytics", "snapshots", f"youtube-{dt.date.today()}.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({"date": str(dt.date.today()), "shorts": rows}, open(out, "w"), indent=1)
print(len(rows), "Shorts ->", out)
