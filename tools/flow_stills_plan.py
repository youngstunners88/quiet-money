#!/usr/bin/env python3
"""Plan the Flow stills for a set of scripts: the exact job id, beat folder and prompt for every beat that needs a picture.

usage: PYTHONPATH=. python tools/flow_stills_plan.py OUT.json SCRIPT.json:PILLAR:SLOT [...]
The pipeline uses production/cache/flow/<day>/<job id>/beatNN.jpg before any image generator (faceless/pipeline/visuals.py),
so a beat with a saved Flow picture costs nothing. Job ids carry the UTC day: run `faceless make` with the same slot on the same UTC day.
"""
import json, sys
from datetime import datetime, timezone

from faceless import config
from faceless.config import Paths
from faceless.pipeline import cards
from faceless.pipeline.visuals import build_prompt
from faceless.state import slugify

day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
plan = {"day": day, "videos": []}
for arg in sys.argv[2:]:
    path, pillar, slot = arg.rsplit(":", 2)
    script = json.load(open(path, encoding="utf-8"))
    jid = f"{day}-s{slot}-{pillar}-{slugify(script.get('title', 'untitled'), 32)}"
    style = cards.style_for(jid, pillar)
    planned = cards.pick(script, None, pillar, style)
    folder = Paths.cache / "flow" / jid[:10] / jid
    beats = []
    for i, b in enumerate(script["beats"]):
        if i in planned:
            continue
        prompt = build_prompt(b["visual"] or b["say"], config.pillar(pillar).style, script.get("look", ""))
        beats.append({"beat": i + 1, "file": str(folder / f"beat{i + 1:02d}.jpg"), "prompt": prompt})
    plan["videos"].append({"script": path, "pillar": pillar, "slot": int(slot), "job": jid, "title": script.get("title"), "beats": beats})
json.dump(plan, open(sys.argv[1], "w"), indent=1)
print(day, sum(len(v["beats"]) for v in plan["videos"]), "stills over", len(plan["videos"]), "videos")
for v in plan["videos"]:
    print(f"  {v['job']}: {len(v['beats'])}")
