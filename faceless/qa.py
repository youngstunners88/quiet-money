"""Semantic quality and compliance gates, answered by a decision model (Cloudflare Clef) instead of hand-written heuristics.

Images: does the still show readable text or a watermark, a clearly visible human face, or a brand logo? Our prompts forbid all
three, but image models still print calculator keys and faces, and no pixel-statistics gate can see that. A flagged beat becomes a
designed motion card (free, never has text artifacts), except the hook beat, which is regenerated once. Scripts: does the text
promise returns, push a specific product, or read as hype? Every threshold lives in [qa] and is tuned from data (`faceless qa`).
Clef answers first. When it cannot (its free pool is spent, an outage, no key), a second judge (Gemini through the Muapi desk, about
$0.0002 a call) answers the same questions, so the gates do not silently disappear on a bad day. Only when neither can answer is
there "no opinion", which is never a failure and is recorded as QA_UNAVAILABLE so a run of unchecked days is visible.
"""

from __future__ import annotations

from faceless import config, events
from faceless.providers import ProviderError, ProviderUnavailable, clef, judge

IMAGE_Q = {
    "text": {"type": "noul", "instructions": "Does the image contain a sign, caption, label, watermark or any readable words or letters? "
             "Numerals on a clock face, calculator keys or a ruler do not count; only words and letters do."},
    "face": {"type": "noul", "instructions": "Is a real-looking human face clearly visible, with eyes, nose and mouth?"},
    "logo": {"type": "noul", "instructions": "Does the image show a recognizable brand logo or trademarked design?"},
}
SCRIPT_Q = {
    "promises_returns": {"type": "noul", "instructions": "Does the text promise or guarantee investment returns, profits or income?"},
    "specific_advice": {"type": "noul", "instructions": "Does the text tell the reader to buy or sell a specific stock, coin, fund or product?"},
    "hype": {"type": "noul", "instructions": "Does the text use get-rich-quick hype, fear-mongering or exaggerated urgency?"},
}


def cfg() -> dict:
    return {"enabled": True, "text_max": 0.7, "face_max": 0.6, "logo_max": 0.6, "max_swaps": 3, "promises_max": 0.5,
            "advice_max": 0.5, "hype_max": 0.7, "dup_soft": 0.55, "dup_hard": 0.72, "frame_max": 0.6, **config.load().get("qa", {})}


def enabled() -> bool:
    return bool(cfg()["enabled"]) and (clef.available() or judge.available())


_announced: set[tuple[str, str]] = set()


def _once(event: str, job: str | None, **fields) -> None:
    """One journal line per job and reason, not one per still."""
    key = (event, job or "")
    if key not in _announced:
        _announced.add(key)
        events.emit(event, job=job, **fields)


def ask(state, questions: dict, images: list | None = None, model: str = "clef", job: str | None = None) -> dict:
    """Clef first (free and calibrated), the Muapi judge when Clef cannot answer. Raises ProviderUnavailable when neither can."""
    why = None
    if clef.available():
        try:
            return clef.run(state, questions, images=images, model=model, job=job)
        except (ProviderUnavailable, ProviderError) as e:
            why = f"{type(e).__name__}: {str(e)[:80]}"
    if judge.available():
        _once("QA_FALLBACK", job, why=why or "no Cloudflare key")
        return judge.run(state, questions, images=images, job=job)
    _once("QA_UNAVAILABLE", job, why=why or "no Cloudflare key and no Muapi key")
    raise ProviderUnavailable(why or "no decision model available")


def check_image(path: str, narration: str = "", job: str | None = None) -> dict | None:
    """{'text','face','logo': probability, 'flags': [names over threshold]} or None when there is no opinion."""
    if not enabled():
        return None
    try:
        ans = ask(f"A generated still for a personal-finance video. Narration: {narration[:300]}", IMAGE_Q, images=[path], job=job)
    except (ProviderUnavailable, ProviderError):
        return None
    except Exception as e:  # noqa: BLE001 - a broken file or odd response must never cost a video its slot
        events.emit("QA_ERROR", job=job, what="image", error=f"{type(e).__name__}: {str(e)[:120]}")
        return None
    c = cfg()
    p = {k: round(clef.probability(ans.get(k, {})), 3) for k in IMAGE_Q}
    return {**p, "flags": [k for k in IMAGE_Q if p[k] > c[f"{k}_max"]]}


FRAME_Q = {"flag": {"type": "noul", "instructions": "Do any of these frames show legible text, letters or numbers, a recognizable brand logo, or a clearly visible human face? "
                    "Also answer yes if the scene visibly warps, melts or morphs between frames."}}


def check_frames(paths: list[str], job: str | None = None) -> bool | None:
    """True when a generated clip's frames should be rejected, False when they look clean, None when the model has no opinion."""
    if not enabled():
        return None
    try:
        ans = ask("Frames sampled from an AI-generated video clip for a personal-finance video.", FRAME_Q, images=paths[:4], job=job)
    except (ProviderUnavailable, ProviderError):
        return None
    except Exception as e:  # noqa: BLE001
        events.emit("QA_ERROR", job=job, what="frames", error=f"{type(e).__name__}: {str(e)[:120]}")
        return None
    return clef.probability(ans.get("flag", {})) > cfg()["frame_max"]


def check_script(text: str, job: str | None = None) -> dict | None:
    if not enabled():
        return None
    try:
        ans = ask(text[:2000], SCRIPT_Q, model="clef", job=job)
    except (ProviderUnavailable, ProviderError):
        return None
    except Exception as e:  # noqa: BLE001
        events.emit("QA_ERROR", job=job, what="script", error=f"{type(e).__name__}: {str(e)[:120]}")
        return None
    c = cfg()
    p = {k: round(clef.probability(ans.get(k, {})), 3) for k in SCRIPT_Q}
    limits = {"promises_returns": c["promises_max"], "specific_advice": c["advice_max"], "hype": c["hype_max"]}
    return {**p, "flags": [k for k in SCRIPT_Q if p[k] > limits[k]]}


def script_gates(script: dict, job: str | None = None) -> list:
    """Gauntlet gates from the decision model. Promising returns or pushing a product is hard (our own compliance rule)."""
    from faceless.gauntlet import Gate
    text = " ".join(b.get("say", "") for b in script.get("beats", []))
    res = check_script(text, job)
    if res is None:
        return []
    detail = ", ".join(f"{k} {res[k]:.2f}" for k in SCRIPT_Q)
    return [Gate("no_promised_returns", "promises_returns" not in res["flags"], 6, True, detail, "script"),
            Gate("no_specific_advice", "specific_advice" not in res["flags"], 6, True, detail, "script"),
            Gate("no_hype", "hype" not in res["flags"], 3, False, detail, "script")]


def narration(script: dict) -> str:
    return script.get("title", "") + ". " + " ".join(b.get("say", "") for b in script.get("beats", []))


def nearest_in_history(script: dict, job: str | None = None, k: int = 3) -> list[tuple[float, str]] | None:
    """Most similar earlier scripts by centered embedding similarity: [(similarity, job id)]. None when there are too few earlier
    scripts to center on, or no embedding provider can serve."""
    import json

    from faceless import embed
    from faceless.config import Paths
    names, texts = [], []
    for p in sorted(Paths.final.glob("*.json")):
        if p.name.startswith("_") or p.stem == job:
            continue
        try:
            texts.append(narration(json.loads(p.read_text(encoding="utf-8"))))
            names.append(p.stem)
        except (OSError, ValueError):
            continue
    if len(texts) < 12:
        return None
    vecs = embed.embed([narration(script)] + texts)
    if vecs is None:
        return None
    cv = embed.centered(vecs, vecs[1:])
    sims = sorted(((embed.cosine(cv[0], v), n) for v, n in zip(cv[1:], names)), reverse=True)
    return sims[:k]


def duplicate_gates(script: dict, job: str | None = None) -> list:
    """A script about the same thing as an earlier one reads as 'interchangeable' to YouTube's reviewers and to viewers.
    Soft from `dup_soft` (centered similarity), hard from `dup_hard`. No gates when embeddings are unavailable."""
    from faceless.gauntlet import Gate
    c = cfg()
    try:
        near = nearest_in_history(script, job)
    except Exception as e:  # noqa: BLE001 - embeddings are an extra opinion, never a dependency
        events.emit("QA_ERROR", job=job, what="duplicate", error=f"{type(e).__name__}: {str(e)[:120]}")
        return []
    if not near:
        return []
    top, who = near[0]
    detail = f"closest earlier script {who[-48:]} at {top:.2f} (soft {c['dup_soft']}, hard {c['dup_hard']})"
    return [Gate("not_semantic_duplicate", top < c["dup_hard"], 6, True, detail, "script"),
            Gate("distinct_topic", top < c["dup_soft"], 3, False, detail, "script")]


def calibrate(images: int = 40, scripts: int = 30) -> dict:
    """Run the questions over cached stills and finished scripts so thresholds come from data. Spends free neurons: keep n small."""
    import json
    import random

    from faceless.config import Paths
    rnd = random.Random(7)
    pics = sorted((Paths.cache / "images").glob("*.jpg"))
    rnd.shuffle(pics)
    out = {"images": [], "scripts": []}
    for p in pics[:images]:
        r = check_image(str(p))
        if r:
            out["images"].append({"file": p.name, **r})
    finals = sorted(p for p in Paths.final.glob("*.json") if not p.name.startswith("_"))
    rnd.shuffle(finals)
    for p in finals[:scripts]:
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
            r = check_script(" ".join(b.get("say", "") for b in s["beats"]))
        except (OSError, ValueError, KeyError):
            continue
        if r:
            out["scripts"].append({"file": p.stem, **r})
    return out
