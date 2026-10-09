"""Visual stage: one cinematic still per beat, styled per pillar, generated in parallel."""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

from faceless import config, events, flow, hookclip, qa
from faceless.pipeline import cards, sketch
from faceless.providers import images

SUFFIX = ("vertical 9:16 composition, subject in the center third, cinematic, highly detailed, "
          "no text, no letters, no numbers, no watermark, no logo, any printed surface out of focus")


def build_prompt(visual: str, style: str) -> str:
    return f"{visual.rstrip('. ')}. {style}, {SUFFIX}"


def _hook_need(job) -> float | None:
    """The hook beat's length in seconds (voice runs first), or None when it is not known yet."""
    try:
        beats = json.loads((job.dir / "voice.json").read_text(encoding="utf-8"))["beats"]
        return beats[0][1] - beats[0][0]
    except (OSError, ValueError, KeyError, IndexError):
        return None


def _claim_hook_clip(job) -> dict | None:
    """A Flow clip must cover the hook beat. None leaves the still pipeline unchanged."""
    need = _hook_need(job)
    if need is None:
        return None
    got = flow.claim(job, need + 0.2)
    if got:
        events.emit("FLOW_CLIP_USED", job=job.id, source=got["source"], seconds=round(got["duration"], 1))
    return got


def run(job, script: dict) -> list[dict]:
    pillar = config.pillar(job.pillar)
    cfg = config.load()["images"]

    planned = cards.pick(script, None, job.pillar)     # numeric beats of card pillars: no image needed at all
    hook_clip = _claim_hook_clip(job)                   # an owner-made Flow clip replaces the hook still

    def one(i_beat):
        i, beat = i_beat
        if i in planned:
            return {"beat": i, "provider": "card", "path": None, "prompt": "", "card": planned[i]}
        if i == 0 and hook_clip:
            return {"beat": 0, "provider": "clip", "path": hook_clip["frame"], "prompt": "", "clip": hook_clip["clip"]}
        seed = int(hashlib.sha1(f"{job.id}:{i}".encode()).hexdigest()[:8], 16) % 2_000_000_000
        prompt = build_prompt(beat["visual"] or beat["say"], pillar.style)
        provider, path = images.generate(prompt, seed=seed, hero=(i == 0), job=job.id)
        row = {"beat": i, "provider": provider, "path": path, "prompt": prompt}
        if provider != "procedural" and (res := qa.check_image(path, beat["say"], job=job.id)):
            row["qa"] = res
            if res["flags"] and i == 0:        # the hook keeps a still: one cleaner retry, keep whichever looks better
                clean = build_prompt((beat["visual"] or beat["say"]) + ", only objects and places, no people, no faces, no text, no numbers", pillar.style)
                provider2, path2 = images.generate(clean, seed=seed + 101, hero=True, job=job.id)
                res2 = qa.check_image(path2, beat["say"], job=job.id) if provider2 != "procedural" else None
                if res2 is not None and len(res2["flags"]) < len(res["flags"]):
                    row = {"beat": i, "provider": provider2, "path": path2, "prompt": clean, "qa": res2, "retried": True}
        if i == 0 and provider != "procedural" and not row.get("qa", {}).get("flags") and hookclip.enabled():
            need = _hook_need(job)     # no owner-made Flow clip waiting: animate the hook still (off unless [production.hookclip] enabled)
            got = hookclip.make(job, row["path"], need + 0.2, beat["say"]) if need else None
            if got:
                row["clip"] = got["clip"]
                events.emit("HOOK_CLIP_MADE", job=job.id, source=got["source"], usd=got["usd"], seconds=round(got["duration"], 1))
        return row

    with ThreadPoolExecutor(max_workers=1) as sx:           # motion scenes are written while the stills are drawn; they only ever replace a still after a review
        pending = sx.submit(sketch.plan, job, script, planned)
        with ThreadPoolExecutor(max_workers=cfg.get("concurrency", 4)) as ex:
            results = list(ex.map(one, enumerate(script["beats"])))
        try:
            drafts = pending.result()
        except Exception as e:   # noqa: BLE001 - an optional lane must never cost a video its stills
            events.emit("SKETCH_FAILED", job=job.id, error=f"{type(e).__name__}: {e}"[:200])
            drafts = {}
    for i, draft in drafts.items():
        if i < len(results) and results[i].get("path") and not results[i].get("card"):
            results[i]["sketch"] = draft
    # a beat whose image fell all the way to procedural placeholder art becomes a designed motion card instead
    for i, spec in cards.pick(script, results, job.pillar).items():
        if results[i]["provider"] == "procedural":
            results[i] = {**results[i], "provider": "card", "card": spec}
    swaps = int(qa.cfg()["max_swaps"])       # a flagged still becomes a designed card: free, and never has text artifacts
    for i, r in enumerate(results):
        if i == 0 or r.get("card") or not r.get("qa", {}).get("flags") or swaps <= 0 or not cards.available():
            continue
        results[i] = {**r, "card": {"kind": "phrase", "text": cards.key_phrase(script["beats"][i])}, "qa_swapped": r["qa"]["flags"]}
        swaps -= 1
    (job.dir / "images.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    by_provider: dict = {}
    for r in results:
        by_provider[r["provider"]] = by_provider.get(r["provider"], 0) + 1
    events.emit("VISUALS_DONE", job=job.id, providers=by_provider, qa_flagged=sum(1 for r in results if r.get("qa", {}).get("flags")),
                qa_swapped=sum(1 for r in results if r.get("qa_swapped")))
    return results
