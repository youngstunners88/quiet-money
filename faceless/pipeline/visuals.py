"""Visual stage: one cinematic still per beat, styled per pillar, generated in parallel."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

from faceless import config, events
from faceless.pipeline import cards
from faceless.providers import images

SUFFIX = ("vertical 9:16 composition, subject in the center third, cinematic, highly detailed, "
          "no text, no letters, no numbers, no watermark, no logo, any printed surface out of focus")


def build_prompt(visual: str, style: str) -> str:
    return f"{visual.rstrip('. ')}. {style}, {SUFFIX}"


def run(job, script: dict) -> list[dict]:
    pillar = config.pillar(job.pillar)
    cfg = config.load()["images"]

    planned = cards.pick(script, None, job.pillar)     # numeric beats of card pillars: no image needed at all

    def one(i_beat):
        i, beat = i_beat
        if i in planned:
            return {"beat": i, "provider": "card", "path": None, "prompt": "", "card": planned[i]}
        seed = int(hashlib.sha1(f"{job.id}:{i}".encode()).hexdigest()[:8], 16) % 2_000_000_000
        prompt = build_prompt(beat["visual"] or beat["say"], pillar.style)
        provider, path = images.generate(prompt, seed=seed, hero=(i == 0), job=job.id)
        return {"beat": i, "provider": provider, "path": path, "prompt": prompt}

    with ThreadPoolExecutor(max_workers=cfg.get("concurrency", 4)) as ex:
        results = list(ex.map(one, enumerate(script["beats"])))
    # a beat whose image fell all the way to procedural placeholder art becomes a designed motion card instead
    for i, spec in cards.pick(script, results, job.pillar).items():
        if results[i]["provider"] == "procedural":
            results[i] = {**results[i], "provider": "card", "card": spec}
    (job.dir / "images.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    by_provider: dict = {}
    for r in results:
        by_provider[r["provider"]] = by_provider.get(r["provider"], 0) + 1
    events.emit("VISUALS_DONE", job=job.id, providers=by_provider)
    return results
