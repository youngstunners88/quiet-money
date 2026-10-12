import json, shutil, sys, types
from pathlib import Path
from faceless.pipeline import cards
J = "2026-10-11-s0-ledger-the-1-management-fee-trap"
src = Path("production/output/2026-10-11") / J
script = json.load(open(f"script-lab/final/{J}.json"))
voice = json.load(open(src / "voice.json"))
job = types.SimpleNamespace(id="cast-sample", dir=Path("state/tmp/castjob"), artifacts={"style": "ledger"}, pillar="ledger")
job.dir.mkdir(parents=True, exist_ok=True)
shutil.copy(src / "voice.json", job.dir / "voice.json")
picked = cards.pick(script, None, "ledger", "ledger")
print({i: (s["tpl"] if "tpl" in s else s["kind"], s.get("pal")) for i, s in picked.items()})
spans = {i: tuple(b) for i, b in enumerate(voice["beats"])}
r = cards.render_reel(job, picked, spans, "ledger", "#D9A400", 30)
print(r and r[0])
