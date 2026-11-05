#!/usr/bin/env python3
"""Type a realm prompt into the open Flow project's prompt box and verify it. usage: flow-video-type.py SLUG
The Flow prompt box is not labelled in the UI tree; it sits above the mode pill. Typing uses adb input text in short chunks (no ( ) ' " & ;)."""
import html, json, os, re, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slug = sys.argv[1]
item = next(x for x in json.load(open(f"{REPO}/channel/flow/realms/"+os.environ.get("REALMS","2026-11-05")+".json")) if x["slug"] == slug)
want = item["prompt"]
def adb(c): return subprocess.run(["adb", "shell", c], capture_output=True, text=True).stdout
def dump(): return subprocess.run("adb exec-out uiautomator dump /dev/tty", shell=True, capture_output=True, text=True).stdout
def texts():
    return [html.unescape(m.group(1) or m.group(2) or "") for m in re.finditer(r'text="([^"]*)"|content-desc="([^"]*)"', dump())]
for i in range(0, len(want), 24):
    adb("input text '" + want[i:i + 24].replace(" ", "%s") + "'"); time.sleep(0.2)
time.sleep(2)
norm = lambda s: re.sub(r"\s+", " ", s).strip()
got = max((t for t in texts() if t.startswith(want[:40])), key=len, default="")
print("typed", len(got), "of", len(want), "chars; exact match:", norm(got) == norm(want))
if norm(got) != norm(want):
    a = norm(want).split(" "); b = norm(got).split(" ")
    import difflib
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal": print(tag, a[i1:i2][:8], "->", b[j1:j2][:8])
