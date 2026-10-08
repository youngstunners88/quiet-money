"""A second judge for the quality gates: Gemini 3.8 Flash through the Muapi desk (about $0.0002 a call, reads one image).

Cloudflare Clef is the primary decision model (free neurons, calibrated yes-probabilities). It shares one free pool with image
generation, so on a day the pool is spent, or when Cloudflare is down, Clef cannot answer, and the gates that keep text, faces and
logos out of stills and promises and product pushes out of scripts would silently vanish. This judge answers the same typed yes/no
questions in the same shape, so qa.py can fall back to it without changing a threshold. It is less calibrated than Clef (language
models tend to answer near 0 or 1), which is acceptable for a fallback and is why Clef stays first.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

from faceless import config, events, muapi
from faceless.config import Paths
from faceless.providers import ProviderError, ProviderUnavailable

MODEL = "gemini-3-8-flash"
SYSTEM = ("You are a strict quality inspector for short videos about personal finance. For each question, give the probability from 0 to 1 that the answer is YES, "
          "judging only what you can see or read. Be decisive: 0.02 or lower when it is clearly not there, 0.98 or higher when it clearly is, and a value near 0.5 only when you truly cannot tell. "
          "Reply with one JSON object that maps each question name to its probability, and nothing else.")


# Language models hedge: measured live on 2026-10-08, clean stills scored 0.20 to 0.28 and a still with printed words or a face scored 0.72 to 0.75,
# even when told to be decisive. Stretching three times around 0.5 puts clean at 0 and clear at 1, so Clef's thresholds (0.6 to 0.7) keep working
# and an undecided answer (near 0.5) stays under them.
STRETCH = 3.0


def available() -> bool:
    return bool(config.load().get("qa", {}).get("fallback_judge", True)) and muapi.available()


def _one_image(images: list) -> Path:
    """One file for the model: a single image as is, several frames as a 2x2 sheet (the model reads one picture per call)."""
    if len(images) == 1:
        return Path(images[0])
    ims = [Image.open(p).convert("RGB") for p in images[:4]]
    w, h = 540, 960
    sheet = Image.new("RGB", (w * 2, h * 2), "black")
    for i, im in enumerate(ims):
        im.thumbnail((w, h))
        sheet.paste(im, ((i % 2) * w, (i // 2) * h))
    out = Paths.cache / "judge" / "sheet.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, "JPEG", quality=85)
    return out


def _parse(text: str, names: list[str]) -> dict[str, float]:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except ValueError:
        data = {}
    out = {}
    for n in names:
        try:
            out[n] = min(1.0, max(0.0, 0.5 + (float(data[n]) - 0.5) * STRETCH))
        except (KeyError, TypeError, ValueError):
            pass
    missing = [n for n in names if n not in out]
    if missing:
        raise ProviderError(f"judge answered without {missing}")
    return out


def run(state, questions: dict, images: list | None = None, model: str = "clef", job: str | None = None) -> dict:
    """Same call and answer shape as clef.run: {question: {"noul": probability}}. `model` is accepted and ignored."""
    if not muapi.available():
        raise ProviderUnavailable("MUAPI_API_KEY not set")
    if any(q.get("type") != "noul" for q in questions.values()):
        raise ValueError("the fallback judge answers noul (yes/no) questions only")
    names = list(questions)
    lines = "\n".join(f'- "{n}": {q["instructions"]}' for n, q in questions.items())
    payload = {"prompt": f"{SYSTEM}\n\nContext: {str(state)[:1500]}\n\nQuestions:\n{lines}", "system_prompt": SYSTEM}       # the instruction goes in both: some routes ignore the system field
    if images:
        payload["image_url"] = muapi.upload(_one_image(list(images)))
    for attempt in (1, 2):                                   # an upstream 500 ("try again later") happens; a second ask costs $0.0002
        try:
            out = muapi.run(MODEL, payload, Paths.cache / "judge", job=job, max_usd=0.01, label="judge")
            if not out["text"]:
                raise ProviderError("judge returned no text")
            answers = _parse(out["text"][0], names)
            break
        except ProviderError:
            if attempt == 2:
                raise
    events.emit("JUDGE_CALL", job=job, model=MODEL, questions=names, images=len(images or []), usd=out.get("usd"))
    return {n: {"noul": p} for n, p in answers.items()}
