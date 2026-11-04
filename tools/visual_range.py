#!/usr/bin/env python3
"""Keep Quiet Money stills diverse. usage:
  visual_range.py looks                  list look packs and when each was last used
  visual_range.py pick [N]               the N least recently used look packs (default 5)
  visual_range.py lint SCRIPT.json [...] fail stock visuals, repeats inside the script, repeats of recent scripts, a missing or recent look
Skill: .claude/skills/faceless-visual-range"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOKS = json.load(open(f"{ROOT}/.claude/skills/faceless-visual-range/looks.json", encoding="utf-8"))
LOOKS = {k: v for k, v in LOOKS.items() if not k.startswith("_")}
# stock frames that were overused: a beat may use one only with a new subject twist, so they fail the lint
BANNED = ["stormy sea", "lighthouse", "empty highway", "highway stretching", "kitchen table", "coffee cup", "notepad",
          "magnifying glass", "old paper map", "paper map being unfolded", "brass calculator", "stack of ledgers", "banker lamp",
          "steel safe", "open wallet", "stack of gold coins", "tall stack of gold", "glass jar of coins", "glowing sunrise horizon",
          "three identical white coffee cups", "closed brown folder", "dark wooden table", "wooden table"]
STOP = set("a an the of on in at to and with no people faces face soft light close up macro wide shot under over beside by for from into".split())

def words(s): return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2}
def scripts():
    return sorted(glob.glob(f"{ROOT}/script-lab/final/20*.json"))
def pack_of(d):
    if d.get("look_pack") in LOOKS: return d["look_pack"]
    for k, v in LOOKS.items():
        if d.get("look") == v: return k
    return None
def history():
    last = {}
    for i, p in enumerate(scripts()):
        try: d = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        k = pack_of(d)
        if k: last[k] = i
    return last, len(scripts())

def cmd_looks():
    last, n = history()
    for k in LOOKS: print(f"{k:24} {'never used' if k not in last else f'{n - last[k]} scripts ago'}")
def cmd_pick(n=5):
    last, total = history()
    for k in sorted(LOOKS, key=lambda k: last.get(k, -1))[:n]: print(k)
def cmd_lint(paths):
    bad = 0
    recent = []
    for p in scripts()[-40:]:
        try: recent.append((os.path.basename(p), json.load(open(p, encoding="utf-8"))))
        except Exception: pass
    last, total = history()
    for path in paths:
        d = json.load(open(path, encoding="utf-8")); me = os.path.abspath(path); errs = []
        vis = [b.get("visual", "") for b in d["beats"]]
        if not d.get("look"): errs.append("no `look`: every video needs its own look pack (visual_range.py pick)")
        for i, v in enumerate(vis, 1):
            for b in BANNED:
                if b in v.lower(): errs.append(f"beat {i}: stock visual '{b}'")
            if len(v.split()) < 8: errs.append(f"beat {i}: visual too thin to steer the image")
        for i in range(len(vis)):
            for j in range(i + 1, len(vis)):
                a, b = words(vis[i]), words(vis[j])
                if a and b and len(a & b) / len(a | b) > 0.5: errs.append(f"beats {i + 1} and {j + 1} look the same")
        for name, o in recent:
            if os.path.abspath(f"{ROOT}/script-lab/final/{name}") == me: continue
            ov = [words(b.get("visual", "")) for b in o["beats"]]
            hit = sum(1 for v in vis if any(words(v) and x and len(words(v) & x) / len(words(v) | x) > 0.6 for x in ov))
            if hit >= 3: errs.append(f"{hit} visuals repeat {name}")
        print(("FAIL " if errs else "PASS ") + os.path.basename(path))
        for e in errs: print("   ", e)
        bad += bool(errs)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "looks": cmd_looks()
    elif a[0] == "pick": cmd_pick(int(a[1]) if len(a) > 1 else 5)
    elif a[0] == "lint" and len(a) > 1: cmd_lint(a[1:])
    else: print(__doc__)
