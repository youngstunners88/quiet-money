"""Sketches: motion scenes that Claude Haiku 5.5 designs and code draws.

A beat that is a diagram rather than a photograph (a staircase of coins, a ring that fills, a ledger with entries struck out) is designed by a
small model as JSON, never as code. The model returns elements (rectangles, circles, lines, paths, text, repeats) and tweens (fade, slide, scale,
rotate, draw); this module validates every field against a whitelist, expands the repeats, and emits the same HTML + GSAP timeline the other motion
cards use, so HyperFrames draws it into the video's one reel. Because the model writes data and not code, the worst a poisoned script can do is
produce an ugly scene, which a frame check then replaces with a kinetic phrase card.

Why this exists: variety (every scene is composed for its own beat), animated graphics instead of a photo slideshow (TikTok's Creator Rewards
excludes videos made of photos or text overlays alone), and fewer generated stills. It does not save much money by itself: a still from the free
Cloudflare pool costs nothing; a scene costs about a tenth of a cent (measured: 1,700 prompt and 1,800 output tokens, 6 to 10 s, at low effort).

    [production.sketch] mode = "on"      # off by default; the owner turns it on after looking at a sample

Nothing here posts anything or touches an account. Spend is metered in the ledger under the provider name `sketch`.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from faceless import config, events, ledger, safety
from faceless.providers import ProviderError, ProviderUnavailable, http

MODEL = "anthropic/claude-haiku-5.5"
PRICE_IN, PRICE_OUT = 0.10e-6, 0.50e-6            # dollars a token, prompts up to 100k (Anthropic and OpenRouter list the same)
CANVAS = (1080, 1920)
BAND = (1085.0, 1275.0)                           # captions are drawn in here (the prompt says 1070-1290): nothing may rest or end in it
AREA = (10.0, 360.0, 1070.0, 1870.0)              # x0, y0, x1, y1 every element must stay inside: the series name is drawn at y 300-345, and the prompt asks for x 70-1010 (text widths are only estimates)
MAX_ELEMENTS, MAX_TWEENS, MAX_REPEAT = 60, 140, 24

ROLES = ("accent", "accent2", "ink", "muted", "dim", "danger", "glow")
EASE_RE = re.compile(r"^(?:(?:power[1-4]|sine|expo|circ)\.(?:in|out|inOut)|back\.(?:in|out|inOut)(?:\(\d(?:\.\d+)?\))?|linear|none)\Z")
ORIGINS = {f"{a}% {b}%" for a in (0, 25, 50, 75, 100) for b in (0, 25, 50, 75, 100)}
TWEEN_PROPS = {"opacity": (0.0, 1.0, 1.0), "x": (-400.0, 400.0, 0.0), "y": (-400.0, 400.0, 0.0), "scale": (0.0, 3.0, 1.0), "scaleX": (0.0, 3.0, 1.0),
               "scaleY": (0.0, 3.0, 1.0), "rotation": (-360.0, 360.0, 0.0), "draw": (0.0, 1.0, 1.0)}      # name -> (min, max, resting value)
ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,15}\Z")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}\Z")
TEXT_RE = re.compile(r"^[A-Za-z0-9 .,:;!?%$€£&'\"()+=/*×→≈·\-–]{1,36}\Z")
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
FONT_EM = {"anton": 0.50, "black": 0.68}          # average advance as a share of the font size: deliberately generous
FONTS = {"anton": "Anton", "black": "MontserratBlack"}


class SpecError(ValueError):
    """The model's scene was refused; the message says why in words the model can act on."""


class SketchError(RuntimeError):
    """No valid scene could be obtained for a beat (the beat keeps a card or a still). `reasons` lists why each attempt was refused."""

    def __init__(self, message: str, reasons: list[str] | None = None):
        super().__init__(message)
        self.reasons = reasons or []


def settings() -> dict:
    cfg = config.load()["production"].get("sketch", {})
    return {"mode": cfg.get("mode", "off"), "model": cfg.get("model", MODEL), "effort": cfg.get("effort", "low"),
            "max_per_video": int(cfg.get("max_per_video", 4)), "pillars": list(cfg.get("pillars", ["math", "playbook", "escape", "myth"])),
            "daily_usd": float(cfg.get("daily_usd", 0.25)), "per_scene_usd": float(cfg.get("per_scene_usd", 0.01)),
            "min_seconds": float(cfg.get("min_seconds", 2.5)), "min_score": int(cfg.get("min_score", 4)), "revise": bool(cfg.get("revise", True))}


def enabled() -> bool:
    from faceless.pipeline import cards
    return settings()["mode"] == "on" and bool(config.env("OPENROUTER_API_KEY")) and cards.available() and not safety.paused()


# ---------------------------------------------------------------- numbers: a scene may only show figures its beat already carries

def figures(text: str) -> set[str]:
    """'$1,800', '8%', '4.5' -> {'1800', '8', '4.5'}: the comparison form of every number in a text."""
    out = set()
    for m in NUM_RE.findall(text or ""):
        n = m.replace(",", "").rstrip(".")
        out.add(n.lstrip("0") or "0" if "." not in n else n)
    return out


FUNCTION_WORDS = {"a", "an", "the", "of", "to", "in", "on", "at", "by", "per", "vs", "and", "or", "for", "with", "is", "are", "it", "you", "your", "no",
                  "total", "year", "years", "month", "months", "day", "days", "week", "weeks", "step", "x"}


def _stem(w: str) -> str:
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z]+", (text or "").lower())}


def allowed_words(beat: dict, script: dict) -> set[str]:
    """The words a scene may show: the beat's narration and callout and the script's checked facts, plus plain function words and units of time.
    A label that the narrator did not say is a claim nobody checked ("LOST" over a gain), so it is refused."""
    text = [beat.get("say", ""), beat.get("callout", "")]
    for f in script.get("facts", []) if isinstance(script.get("facts"), list) else []:
        if isinstance(f, dict):
            text += [str(f.get("claim", ""))]
    return words(" ".join(text)) | {_stem(w) for w in FUNCTION_WORDS}


def allowed_figures(beat: dict, script: dict) -> set[str]:
    """The numbers a scene may show: the beat's own, plus every figure in the script's checked facts (claims and their arithmetic)."""
    text = [beat.get("say", ""), beat.get("callout", "")]
    for f in script.get("facts", []) if isinstance(script.get("facts"), list) else []:
        if isinstance(f, dict):
            text += [str(f.get("claim", "")), str(f.get("basis", ""))]
    return figures(" ".join(text))


# ---------------------------------------------------------------- validation

def _num(v, lo: float, hi: float, what: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise SpecError(f"{what} must be a number, got {v!r}")
    if not lo <= v <= hi:
        raise SpecError(f"{what} = {v} is outside {lo:g}..{hi:g}")
    return float(v)


def _color(v, what: str, allow_none: bool = True) -> str:
    if v in ROLES or (allow_none and v == "none") or (isinstance(v, str) and HEX_RE.match(v)):
        return v
    raise SpecError(f"{what} must be one of {', '.join(ROLES)}, none, or #rrggbb; got {v!r}")


PATH_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4, "Z": 0}


def parse_path(d: str) -> list[tuple[float, float]]:
    """The points of a path using only absolute M L H V C Q Z commands; anything else raises SpecError."""
    if not isinstance(d, str) or len(d) > 600 or not re.fullmatch(r"[MLHVCQZ0-9eE.,\- +]+", d):
        raise SpecError("path d may only use the absolute commands M L H V C Q Z with plain numbers (max 600 characters)")
    toks = re.findall(r"[MLHVCQZ]|-?(?:\d+\.?\d*|\.\d+)(?:[eE]-?\d+)?", d)
    if not toks or toks[0] != "M":
        raise SpecError("a path must start with M (a moveto)")
    pts: list[tuple[float, float]] = []
    cx = cy = 0.0
    i = 0
    cmd = ""
    while i < len(toks):
        if toks[i] in PATH_ARITY:
            cmd = toks[i]
            i += 1
            if cmd == "Z":
                continue
        if not cmd:
            raise SpecError("path d must start with M")
        n = PATH_ARITY[cmd]
        args = toks[i:i + n]
        if len(args) < n or any(a in PATH_ARITY for a in args):
            raise SpecError(f"path command {cmd} needs {n} numbers")
        vals = [float(a) for a in args]
        i += n
        if cmd == "H":
            cx = vals[0]
        elif cmd == "V":
            cy = vals[0]
        else:
            for k in range(0, n, 2):
                cx, cy = vals[k], vals[k + 1]
                pts.append((cx, cy))
            continue
        pts.append((cx, cy))
    if len(pts) < 2:
        raise SpecError("a path needs at least two points")
    return pts


def _bbox(e: dict) -> tuple[float, float, float, float]:
    t = e["type"]
    if t == "rect":
        return e["x"], e["y"], e["x"] + e["w"], e["y"] + e["h"]
    if t == "circle":
        return e["cx"] - e["r"], e["cy"] - e["r"], e["cx"] + e["r"], e["cy"] + e["r"]
    if t in ("line", "path"):
        pts = [(e["x1"], e["y1"]), (e["x2"], e["y2"])] if t == "line" else e["_pts"]
        h = e.get("sw", 0) / 2
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs) - h, min(ys) - h, max(xs) + h, max(ys) + h
    width = len(e["text"]) * e["size"] * FONT_EM[e["font"]] + max(0, len(e["text"]) - 1) * e["spacing"]
    x0 = e["x"] - (width / 2 if e["anchor"] == "middle" else width if e["anchor"] == "end" else 0)
    return x0, e["y"] - 0.85 * e["size"], x0 + width, e["y"] + 0.25 * e["size"]


def _moved(box, origin: str, st: dict) -> tuple[float, float, float, float]:
    """The box after a tween state (offset, scale, rotation about the element's origin)."""
    ox_pct, oy_pct = (float(p.strip("%")) / 100 for p in origin.split())
    ox, oy = box[0] + (box[2] - box[0]) * ox_pct, box[1] + (box[3] - box[1]) * oy_pct
    ang = math.radians(st.get("rotation", 0.0))
    sx, sy = st.get("scale", 1.0) * st.get("scaleX", 1.0), st.get("scale", 1.0) * st.get("scaleY", 1.0)
    pts = []
    for px, py in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])):
        dx, dy = (px - ox) * sx, (py - oy) * sy
        pts.append((ox + dx * math.cos(ang) - dy * math.sin(ang) + st.get("x", 0.0), oy + dx * math.sin(ang) + dy * math.cos(ang) + st.get("y", 0.0)))
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _inside(box, who: str, when: str, band: bool = True) -> None:
    x0, y0, x1, y1 = box
    if x0 < AREA[0] or x1 > AREA[2] or y0 < AREA[1] or y1 > AREA[3]:
        raise SpecError(f"{who} ({when}) reaches x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f}: keep elements inside x {AREA[0]:.0f}-{AREA[2]:.0f}, y {AREA[1]:.0f}-{AREA[3]:.0f}")
    if band and y1 > BAND[0] and y0 < BAND[1]:
        raise SpecError(f"{who} ({when}) covers y {max(y0, BAND[0]):.0f}-{min(y1, BAND[1]):.0f}: y {BAND[0]:.0f}-{BAND[1]:.0f} is reserved for captions and must stay empty")


def _element(raw) -> dict:
    if not isinstance(raw, dict):
        raise SpecError("every element must be an object")
    t = raw.get("type")
    eid = raw.get("id")
    if t not in ("rect", "circle", "line", "path", "text"):
        raise SpecError(f"element type {t!r} is not allowed (rect, circle, line, path, text, repeat)")
    if not isinstance(eid, str) or not ID_RE.match(eid):
        raise SpecError(f"element id {eid!r} must be lowercase letters, digits or _, starting with a letter (max 16)")
    e: dict = {"id": eid, "type": t, "opacity": _num(raw.get("opacity", 1), 0, 1, f"{eid}.opacity"), "origin": raw.get("origin", "50% 50%")}
    if e["origin"] not in ORIGINS:
        raise SpecError(f"{eid}.origin {e['origin']!r} must look like '50% 100%' (multiples of 25%)")
    if t == "rect":
        e |= {"x": _num(raw.get("x"), -50, 1130, f"{eid}.x"), "y": _num(raw.get("y"), 0, 1950, f"{eid}.y"), "w": _num(raw.get("w"), 1, 1100, f"{eid}.w"),
              "h": _num(raw.get("h"), 1, 1500, f"{eid}.h"), "rx": _num(raw.get("rx", 0), 0, 300, f"{eid}.rx"),
              "fill": _color(raw.get("fill", "accent"), f"{eid}.fill"), "stroke": _color(raw.get("stroke", "none"), f"{eid}.stroke"),
              "sw": _num(raw.get("sw", 0), 0, 60, f"{eid}.sw")}
    elif t == "circle":
        e |= {"cx": _num(raw.get("cx"), -50, 1130, f"{eid}.cx"), "cy": _num(raw.get("cy"), 0, 1950, f"{eid}.cy"), "r": _num(raw.get("r"), 1, 700, f"{eid}.r"),
              "fill": _color(raw.get("fill", "accent"), f"{eid}.fill"), "stroke": _color(raw.get("stroke", "none"), f"{eid}.stroke"),
              "sw": _num(raw.get("sw", 0), 0, 60, f"{eid}.sw")}
    elif t == "line":
        e |= {"x1": _num(raw.get("x1"), -50, 1130, f"{eid}.x1"), "y1": _num(raw.get("y1"), 0, 1950, f"{eid}.y1"), "x2": _num(raw.get("x2"), -50, 1130, f"{eid}.x2"),
              "y2": _num(raw.get("y2"), 0, 1950, f"{eid}.y2"), "stroke": _color(raw.get("stroke", "ink"), f"{eid}.stroke", allow_none=False),
              "sw": _num(raw.get("sw", 6), 1, 60, f"{eid}.sw")}
    elif t == "path":
        pts = parse_path(raw.get("d"))
        e |= {"d": raw["d"].strip(), "_pts": pts, "fill": _color(raw.get("fill", "none"), f"{eid}.fill"),
              "stroke": _color(raw.get("stroke", "ink"), f"{eid}.stroke"), "sw": _num(raw.get("sw", 8), 0, 60, f"{eid}.sw")}
        if e["fill"] == "none" and (e["stroke"] == "none" or e["sw"] == 0):
            raise SpecError(f"path {eid} draws nothing: give it a stroke and a stroke width, or a fill")
    else:
        text = raw.get("text")
        if not isinstance(text, str) or not TEXT_RE.match(text):
            raise SpecError(f"text of {eid} must be 1-36 plain characters (letters, digits and . , : ; ! ? % $ & ' \" ( ) + = / - only); got {text!r}")
        font = raw.get("font", "anton")
        if font not in FONTS:
            raise SpecError(f"{eid}.font must be anton or black")
        anchor = raw.get("anchor", "middle")
        if anchor not in ("start", "middle", "end"):
            raise SpecError(f"{eid}.anchor must be start, middle or end")
        e |= {"x": _num(raw.get("x"), 0, 1080, f"{eid}.x"), "y": _num(raw.get("y"), 0, 1950, f"{eid}.y"), "text": text, "size": _num(raw.get("size"), 48, 320, f"{eid}.size"),
              "font": font, "anchor": anchor, "spacing": _num(raw.get("spacing", 0), 0, 24, f"{eid}.spacing"),
              "fill": _color(raw.get("fill", "ink"), f"{eid}.fill", allow_none=False)}
    return e


def _shift(e: dict, dx: float, dy: float, new_id: str) -> dict:
    c = dict(e)
    c["id"] = new_id
    for kx, ky in (("x", "y"), ("cx", "cy"), ("x1", "y1"), ("x2", "y2")):
        if kx in c and ky in c:
            c[kx] += dx
            c[ky] += dy
    if c["type"] == "path":
        c["_pts"] = [(px + dx, py + dy) for px, py in e["_pts"]]
        c["d"] = _shift_path(e["d"], dx, dy)
    return c


def _shift_path(d: str, dx: float, dy: float) -> str:
    toks = re.findall(r"[MLHVCQZ]|-?(?:\d+\.?\d*|\.\d+)(?:[eE]-?\d+)?", d)
    out, cmd, k = [], "", 0
    for tk in toks:
        if tk in PATH_ARITY:
            cmd, k = tk, 0
            out.append(tk)
            continue
        v = float(tk)
        axis = "x" if cmd == "H" else "y" if cmd == "V" else ("x" if k % 2 == 0 else "y")
        out.append(f"{v + (dx if axis == 'x' else dy):g}")
        k += 1
    return " ".join(out)


def _final_box(e: dict, tweens: list[dict]):
    """An element's box where it ends up: its resting box moved by the last tween that sets x or y."""
    box = _bbox(e)
    st = {}
    for tw in sorted((t for t in tweens if t["target"] == e["id"]), key=lambda t: t["at"] + t["dur"]):
        st.update({k: v for k, v in tw["to"].items() if k in ("x", "y", "scale", "scaleX", "scaleY", "rotation")})
    return _moved(box, e["origin"], st) if st else box


def _no_overlap(flat: list[dict], tweens: list[dict]) -> None:
    """Two pieces of text may not sit on each other in the finished frame."""
    texts = [(e["id"], _final_box(e, tweens)) for e in flat if e["type"] == "text"]
    for i, (a, ba) in enumerate(texts):
        for b, bb in texts[i + 1:]:
            ix, iy = min(ba[2], bb[2]) - max(ba[0], bb[0]), min(ba[3], bb[3]) - max(ba[1], bb[1])
            if ix > 8 and iy > 8:
                small = min((ba[2] - ba[0]) * (ba[3] - ba[1]), (bb[2] - bb[0]) * (bb[3] - bb[1])) or 1
                if ix * iy / small > 0.12:
                    raise SpecError(f"the text '{a}' and the text '{b}' overlap in the finished frame (about {ix:.0f} x {iy:.0f} px): move one so they are 40 px or more apart")


def _fills_the_frame(shown: list[dict]) -> None:
    """A scene needs presence: its elements together must spread over a real part of the main area, not sit in a corner."""
    boxes = [_bbox(e) for e in shown]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    if (x1 - x0) < 440 or (y1 - y0) < 360:
        raise SpecError(f"the finished picture is only {x1 - x0:.0f} x {y1 - y0:.0f} px: make the main graphic bigger so it spans at least 500 px across and 360 px down the main area")


def validate(raw, *, dur: float, allowed: set[str] | None = None, vocab: set[str] | None = None) -> dict:
    """The model's scene as a clean, flat, bounded spec. Raises SpecError with a reason the model can fix.
    `allowed` is the set of figures the scene may show and `vocab` the set of words (both from the beat); None skips that check."""
    if not isinstance(raw, dict) or not isinstance(raw.get("elements"), list) or not isinstance(raw.get("tweens"), list):
        raise SpecError("the reply must be one JSON object with an 'elements' list and a 'tweens' list")
    motif = str(raw.get("motif", ""))[:60]
    flat: list[dict] = []
    groups: dict[str, list[str]] = {}
    aliases: dict[str, list[str]] = {}            # the item's own id, when a repeat declares one: the copies answer to it too
    seen: set[str] = set()

    def add(e: dict) -> None:
        if e["id"] in seen:
            raise SpecError(f"element id {e['id']!r} is used twice")
        seen.add(e["id"])
        flat.append(e)

    for r in raw["elements"]:
        if isinstance(r, dict) and r.get("type") == "repeat":
            n = int(_num(r.get("count"), 2, MAX_REPEAT, "repeat.count"))
            base = _element({**r["item"], "id": r.get("id")}) if isinstance(r.get("item"), dict) else None
            if base is None:
                raise SpecError("a repeat needs an 'item' object (any element except repeat)")
            dx, dy = _num(r.get("dx", 0), -1100, 1100, "repeat.dx"), _num(r.get("dy", 0), -1900, 1900, "repeat.dy")
            ids = [f"{base['id']}_{k}" for k in range(n)]
            groups[base["id"]] = ids
            if isinstance(r["item"].get("id"), str) and r["item"]["id"] != base["id"] and ID_RE.match(r["item"]["id"]):
                aliases[r["item"]["id"]] = ids
            for k, i in enumerate(ids):
                add(_shift(base, dx * k, dy * k, i))
        else:
            add(_element(r))
        if len(flat) > MAX_ELEMENTS:
            raise SpecError(f"too many elements (max {MAX_ELEMENTS} counting repeats)")
    if not flat:
        raise SpecError("no elements")
    by_id = {e["id"]: e for e in flat}

    limit = max(0.5, dur - 0.2)
    tweens: list[dict] = []
    for r in raw["tweens"]:
        if not isinstance(r, dict):
            raise SpecError("every tween must be an object")
        tgt = str(r.get("target", ""))
        if tgt in by_id:
            targets = [tgt]
        elif tgt in groups:                                       # the bare id of a repeat means all its copies
            targets = groups[tgt]
        elif tgt in aliases:
            targets = aliases[tgt]
        elif tgt.endswith("*") and (hits := [i for i in by_id if i.startswith(tgt[:-1])] or [i for a, ids in aliases.items() if (a + "_").startswith(tgt[:-1]) for i in ids]):
            targets = hits
        elif tgt.endswith("_*") and tgt[:-2] in by_id:
            targets = [tgt[:-2]]
        else:
            raise SpecError(f"tween target {tgt!r} matches no element. Declared ids: {', '.join(list(by_id)[:14])}{'...' if len(by_id) > 14 else ''}. "
                            f"Use an exact id, or 'prefix_*' where the prefix is exactly how those ids begin (the copies of a repeat 'coins' are coins_0, coins_1, ...)")
        at = _num(r.get("at", 0), 0, 20, "tween.at")
        d = _num(r.get("dur", 0.5), 0.05, 3.0, "tween.dur")
        stag = _num(r.get("stagger", 0), 0, 0.5, "tween.stagger") if len(targets) > 1 else 0.0
        ease = r.get("ease", "power2.out")
        if not isinstance(ease, str) or not EASE_RE.match(ease):
            raise SpecError(f"ease {ease!r} must look like power2.out, power3.inOut, sine.inOut, expo.out, back.out(1.7) or linear")
        frm, to = r.get("from"), r.get("to")
        if not isinstance(frm, dict) or not isinstance(to, dict) or not (frm or to):
            raise SpecError("every tween needs 'from' and 'to' objects")
        props = set(frm) | set(to)
        for p in props:
            if p not in TWEEN_PROPS:
                raise SpecError(f"tween property {p!r} is not allowed ({', '.join(TWEEN_PROPS)})")
        f2 = {p: _num(frm.get(p, TWEEN_PROPS[p][2]), TWEEN_PROPS[p][0], TWEEN_PROPS[p][1], f"tween.from.{p}") for p in props}
        t2 = {p: _num(to.get(p, TWEEN_PROPS[p][2]), TWEEN_PROPS[p][0], TWEEN_PROPS[p][1], f"tween.to.{p}") for p in props}
        for k, tid in enumerate(targets):
            if "draw" in props and by_id[tid]["type"] not in ("line", "path"):
                raise SpecError(f"'draw' only works on a line or a path, not on {tid} ({by_id[tid]['type']})")
            start = at + k * stag
            if limit - start < 0.1:
                raise SpecError(f"tween on {tid} starts at {start:.2f}s but the scene is {dur:.1f}s long and every tween must finish 0.2s before the end")
            tweens.append({"target": tid, "at": round(start, 3), "dur": round(min(d, limit - start), 3), "from": f2, "to": t2, "ease": ease})
        if len(tweens) > MAX_TWEENS:
            raise SpecError(f"too many tweens (max {MAX_TWEENS} counting repeats)")

    # geometry: every element, at rest and at both ends of each of its tweens, stays in the frame and out of the caption band
    for e in flat:
        box = _bbox(e)
        _inside(box, e["id"], "at rest")
        for tw in (t for t in tweens if t["target"] == e["id"]):
            for label, st in (("start of a tween", tw["from"]), ("end of a tween", tw["to"])):
                if set(st) & {"x", "y", "scale", "scaleX", "scaleY", "rotation"}:
                    _inside(_moved(box, e["origin"], st), e["id"], label, band=label.startswith("end"))
    # what the last frame shows
    final = {e["id"]: e["opacity"] for e in flat}
    for tw in sorted(tweens, key=lambda t: t["at"] + t["dur"]):
        if "opacity" in tw["to"]:
            final[tw["target"]] = tw["to"]["opacity"]
    shown = [e for e in flat if final[e["id"]] > 0.05]
    if len(shown) < 3 or not any(e["type"] == "text" for e in shown):
        raise SpecError("the last frame must show at least three elements including some text: every element that starts hidden needs a tween that shows it")
    _no_overlap(flat, tweens)
    _fills_the_frame(shown)
    # words: a scene says only what its beat already says
    if vocab is not None:
        odd = sorted({w for e in flat if e["type"] == "text" for w in re.findall(r"[a-z]+", e["text"].lower()) if _stem(w) not in vocab and len(w) > 1})
        if odd:
            raise SpecError(f"the scene uses words the narrator never said: {', '.join(odd)}. Label things only with words from the narration or the callout (plain words like 'a', 'of', 'per', 'total', 'years' are fine)")
    # numbers: a scene shows only figures its beat already carries
    if allowed is not None:
        extra = sorted({n for e in flat if e["type"] == "text" for n in figures(e["text"])} - allowed - {"0"})
        if extra:
            raise SpecError(f"the scene shows numbers that are not in the narration, the callout or the checked facts: {', '.join(extra)}. Remove them or use words")
    return {"motif": motif, "elements": [{k: v for k, v in e.items() if k != "_pts"} for e in flat], "tweens": tweens}


# ---------------------------------------------------------------- drawing (HTML + GSAP calls for the shared reel)

def palette(accent: str, accent2: str, glow: str) -> dict[str, str]:
    return {"accent": accent, "accent2": accent2, "ink": "#ffffff", "muted": "rgba(255,255,255,0.62)", "dim": "rgba(255,255,255,0.20)",
            "danger": "#ff4d5e", "glow": glow, "none": "none"}


def _c(v: str, pal: dict) -> str:
    return pal.get(v, v)


def emit(sid: str, t0: float, spec: dict, pal: dict) -> tuple[str, list[str]]:
    """(svg markup, timeline calls) for one validated scene. Only fromTo tweens, so any frame can be redrawn on its own."""
    parts, js = [], []
    draws = {t["target"] for t in spec["tweens"] if "draw" in t["from"] or "draw" in t["to"]}
    for e in spec["elements"]:
        eid = f"{sid}_{e['id']}"
        op = f' opacity="{e["opacity"]:g}"' if e["opacity"] != 1 else ""
        dash = ' pathLength="1" stroke-dasharray="1 1" stroke-dashoffset="0"' if e["id"] in draws else ""
        t = e["type"]
        if t == "rect":
            stroke = f' stroke="{_c(e["stroke"], pal)}" stroke-width="{e["sw"]:g}"' if e["stroke"] != "none" and e["sw"] else ""
            parts.append(f'<rect id="{eid}" x="{e["x"]:g}" y="{e["y"]:g}" width="{e["w"]:g}" height="{e["h"]:g}" rx="{e["rx"]:g}" fill="{_c(e["fill"], pal)}"{stroke}{op}/>')
        elif t == "circle":
            stroke = f' stroke="{_c(e["stroke"], pal)}" stroke-width="{e["sw"]:g}"' if e["stroke"] != "none" and e["sw"] else ""
            parts.append(f'<circle id="{eid}" cx="{e["cx"]:g}" cy="{e["cy"]:g}" r="{e["r"]:g}" fill="{_c(e["fill"], pal)}"{stroke}{op}/>')
        elif t == "line":
            parts.append(f'<path id="{eid}" d="M {e["x1"]:g} {e["y1"]:g} L {e["x2"]:g} {e["y2"]:g}" fill="none" stroke="{_c(e["stroke"], pal)}" stroke-width="{e["sw"]:g}" '
                         f'stroke-linecap="round"{dash}{op}/>')
        elif t == "path":
            stroke = f' stroke="{_c(e["stroke"], pal)}" stroke-width="{e["sw"]:g}" stroke-linecap="round" stroke-linejoin="round"' if e["stroke"] != "none" and e["sw"] else ""
            parts.append(f'<path id="{eid}" d="{html.escape(e["d"], quote=True)}" fill="{_c(e["fill"], pal)}"{stroke}{dash}{op}/>')
        else:
            sp = f' letter-spacing="{e["spacing"]:g}"' if e["spacing"] else ""
            parts.append(f'<text id="{eid}" x="{e["x"]:g}" y="{e["y"]:g}" font-family="{FONTS[e["font"]]}, sans-serif" font-size="{e["size"]:g}" fill="{_c(e["fill"], pal)}" '
                         f'text-anchor="{e["anchor"]}"{sp}{op}>{html.escape(e["text"])}</text>')
        js.append(f'gsap.set("#{eid}",{{transformOrigin:"{e["origin"]}"}});')
    first: set[tuple[str, str]] = set()
    for tw in spec["tweens"]:
        frm, to = {}, {}
        for p in set(tw["from"]) | set(tw["to"]):
            if p == "draw":
                frm["strokeDashoffset"], to["strokeDashoffset"] = round(1 - tw["from"][p], 4), round(1 - tw["to"][p], 4)
            else:
                frm[p], to[p] = tw["from"][p], tw["to"][p]
        fresh = any((tw["target"], p) not in first for p in frm)
        first |= {(tw["target"], p) for p in frm}
        opts = {**to, "duration": tw["dur"], "ease": tw["ease"]}
        if not fresh:          # a second tween on a property must not repaint its start before the first one has run
            opts["immediateRender"] = False
        js.append(f'tl.fromTo("#{sid}_{tw["target"]}",{json.dumps(frm)},{json.dumps(opts)},{t0 + tw["at"]:.3f});')
    return f'<svg class="sk" width="{CANVAS[0]}" height="{CANVAS[1]}" viewBox="0 0 {CANVAS[0]} {CANVAS[1]}">{"".join(parts)}</svg>', js


# ---------------------------------------------------------------- asking the model

MOTIFS = ["a staircase of coins", "a ring that fills", "a row of dominoes tipping", "a ledger with entries struck out", "a funnel that narrows",
          "a thermometer rising", "a timeline of dots", "a pair of balance scales", "a stack of bills that grows", "a battery draining",
          "a bridge being built plank by plank", "a snowball rolling and growing", "a calendar grid filling in", "a receipt that gets longer",
          "a dial turning to a number", "a ladder with a marker climbing", "a bucket with a slow leak", "two paths that split apart",
          "a pie cut into three slices", "a row of switches turning off", "a chain of linked rings", "a tree adding branches",
          "a scoreboard", "a gauge needle sweeping"]

HEAD = """You are a motion-graphics designer for a vertical educational finance video (1080 wide x 1920 tall, origin top-left, y grows downward).
You design ONE scene as JSON. A renderer draws and animates it. You never write code.

LAYOUT
- A dark gradient background and the series name at y=300 are drawn for you. Draw only the scene.
- Main area y 380-1040. Lower area y 1300-1800. Keep y 1070-1290 completely EMPTY: captions are drawn there.
- Keep everything inside x 70-1010. Line things up on a grid, centre the focal element on x=540, leave 24 px or more between a label and a shape.
- Text is about 0.5 x size wide per character in anton and 0.68 x size in black: make sure it fits inside x 70-1010. Nothing may rest or end inside y 1070-1290, including after a slide or a scale.

DESIGN
- The scene illustrates what the narrator says and adds no claim. Label things only with the narrator's own words (and plain words like a, of, per, total, years).
- One big idea: a key figure or phrase at size 120-300 and one supporting graphic that spans at least 520 px across and 360 px down the main area.
- At most three text elements besides the key figure. Keep 40 px or more between any two texts and never put one text over another.
- Bold flat shapes, strokes 8-28 px, rounded corners (rx 12-24). Motion should be simple and in order: draw, grow, then the figure lands.

ELEMENTS (numbers are canvas pixels; ids are lowercase letters, digits or _, starting with a letter, unique)
{"id","type":"rect","x","y","w","h","rx":0-60,"fill","stroke","sw","opacity","origin"}
{"id","type":"circle","cx","cy","r",...}
{"id","type":"line","x1","y1","x2","y2","stroke","sw"}
{"id","type":"path","d","fill":"none","stroke","sw"}   d uses ONLY absolute commands M L H V C Q Z
{"id","type":"text","x","y","text","size":48-320,"font":"anton"|"black","fill","anchor":"start"|"middle"|"end","spacing"}   y is the baseline; anton is tall and condensed, black is wide; text is at most 36 plain characters
{"id","type":"repeat","count":2-24,"dx","dy","item":{any element above except repeat}}   the copies are id_0, id_1, ... and copy k is shifted by k*dx, k*dy. Use repeat for rows of identical things instead of writing each one.
Optional on any element: "opacity" 0-1 (default 1), "origin" for scale and rotation, one of "50% 50%" (default), "50% 100%", "50% 0%", "0% 50%", "100% 50%" (or any 0/25/50/75/100 pair).
Colors: "accent" (gold), "accent2" (green), "ink" (white), "muted" (soft white), "dim" (faint white), "danger" (red), "glow", or "#rrggbb", or "none".
Elements are drawn in array order (later on top).

TWEENS (every tween has BOTH from and to; the target must be a declared id, or 'prefix_*')
{"target":"id" or "prefix_*","at":seconds,"dur":0.1-2.5,"from":{...},"to":{...},"ease":"power2.out","stagger":0-0.4}
Properties: opacity 0-1, x and y (pixel offset, -400..400), scale 0-3, scaleX, scaleY, rotation (degrees), draw 0-1 (draws a line or path from nothing to that fraction; only on line or path).
Eases: power1.out power2.out power3.out power2.inOut power3.inOut back.out(1.7) sine.inOut expo.out linear.
A target is an exact id, or 'prefix_*' where the prefix is exactly how those ids begin (a repeat 'coins' makes coins_0, coins_1, ... so target 'coins_*'). Never target an id you did not declare.
Stagger delays each matched element by that many seconds.
All tweens must finish at least 0.2 s before the scene ends, and the last frame must show the finished picture with nothing hidden.
An element that starts hidden (opacity 0) needs a tween that shows it. Do not add empty or invisible elements.

RULES
- Show ONLY the numbers listed under "Numbers you may show". Never invent a figure, a percentage, a year, or an axis label with a number.
- No promises about returns or income, no advice words. No logos, faces or people.
- Take the motif you are given as the visual idea and make it your own. 10 to 45 elements, 8 to 40 tweens.

"""

EXAMPLES = [
    {"motif": "bar race", "elements": [
        {"id": "b1", "type": "rect", "x": 200, "y": 760, "w": 260, "h": 280, "rx": 14, "fill": "muted", "origin": "50% 100%"},
        {"id": "b2", "type": "rect", "x": 620, "y": 520, "w": 260, "h": 520, "rx": 14, "fill": "accent", "origin": "50% 100%"},
        {"id": "base", "type": "line", "x1": 120, "y1": 1050, "x2": 960, "y2": 1050, "stroke": "dim", "sw": 6},
        {"id": "n2", "type": "text", "x": 750, "y": 480, "text": "$226,659", "size": 120, "font": "anton", "fill": "ink", "anchor": "middle"}],
     "tweens": [
        {"target": "base", "at": 0.1, "dur": 0.5, "from": {"draw": 0}, "to": {"draw": 1}, "ease": "power2.out"},
        {"target": "b1", "at": 0.3, "dur": 0.8, "from": {"scaleY": 0}, "to": {"scaleY": 1}, "ease": "power3.out"},
        {"target": "b2", "at": 0.5, "dur": 1.0, "from": {"scaleY": 0}, "to": {"scaleY": 1}, "ease": "power3.out"},
        {"target": "n2", "at": 1.3, "dur": 0.5, "from": {"opacity": 0, "y": 30}, "to": {"opacity": 1, "y": 0}, "ease": "back.out(1.7)"}]},
    {"motif": "ring that fills", "elements": [
        {"id": "track", "type": "path", "d": "M 540 440 C 678 440 790 552 790 690 C 790 828 678 940 540 940 C 402 940 290 828 290 690 C 290 552 402 440 540 440", "fill": "none", "stroke": "dim", "sw": 28},
        {"id": "arc", "type": "path", "d": "M 540 440 C 678 440 790 552 790 690 C 790 828 678 940 540 940 C 402 940 290 828 290 690 C 290 552 402 440 540 440", "fill": "none", "stroke": "accent2", "sw": 28},
        {"id": "num", "type": "text", "x": 540, "y": 770, "text": "8%", "size": 220, "font": "anton", "fill": "ink", "anchor": "middle"},
        {"id": "lbl", "type": "text", "x": 540, "y": 1020, "text": "a year", "size": 64, "font": "black", "fill": "muted", "anchor": "middle"}],
     "tweens": [
        {"target": "track", "at": 0.1, "dur": 0.4, "from": {"opacity": 0}, "to": {"opacity": 1}, "ease": "power2.out"},
        {"target": "arc", "at": 0.3, "dur": 1.6, "from": {"draw": 0}, "to": {"draw": 0.8}, "ease": "power2.inOut"},
        {"target": "num", "at": 0.5, "dur": 0.6, "from": {"opacity": 0, "scale": 0.6}, "to": {"opacity": 1, "scale": 1}, "ease": "back.out(1.7)"},
        {"target": "lbl", "at": 1.2, "dur": 0.5, "from": {"opacity": 0, "y": 24}, "to": {"opacity": 1, "y": 0}, "ease": "power2.out"}]},
]
SYSTEM = (HEAD + "EXAMPLE 1 (two bars grow and a figure lands; everything sits above y 1060)\n" + json.dumps(EXAMPLES[0], separators=(",", ":"))
          + "\n\nEXAMPLE 2 (a ring draws itself and a figure lands in it)\n" + json.dumps(EXAMPLES[1], separators=(",", ":")) + "\n\nReply with the JSON object only.")


def motif_for(job_id: str, beat: int, used: list[str] | None = None) -> str:
    """A visual idea chosen from the job and the beat, so the same video always asks for the same scenes and different videos ask for different ones."""
    h = int(hashlib.sha1(f"{job_id}:{beat}".encode(), usedforsecurity=False).hexdigest()[:8], 16)
    pool = [m for m in MOTIFS if m not in (used or [])] or MOTIFS
    return pool[h % len(pool)]


def user_message(beat: dict, ctx: dict) -> str:
    nums = ", ".join(sorted(ctx["allowed"], key=lambda s: (len(s), s))) or "none (use words only)"
    return (f"Series: {ctx['series']}\nNarration: {beat['say']}\nOn-screen callout: {beat.get('callout') or '(none)'}\nScene length: {ctx['seconds']:.1f} seconds\n"
            f"Motif: {ctx['motif']}\nNumbers you may show: {nums}\nColors: gold and green on a dark background.")


def _cost(usage: dict) -> float:
    if isinstance(usage.get("cost"), (int, float)):
        return float(usage["cost"])
    return usage.get("prompt_tokens", 0) * PRICE_IN + usage.get("completion_tokens", 0) * PRICE_OUT


def _post(body: dict) -> dict:
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=120, headers={"Authorization": f"Bearer {key}"})
    if r.status_code == 429:
        raise ProviderUnavailable("openrouter rate limit")
    if r.status_code != 200:
        raise ProviderError(f"openrouter {r.status_code}")
    return r.json()


def author(beat: dict, ctx: dict, *, job: str | None = None, prior: str = "", feedback: list[str] | None = None) -> dict:
    """One validated scene for one beat. Asks once, and once more with the refusal reason. Returns {spec, raw, usd, tokens, seconds, attempts, reasons};
    raises SketchError if neither answer is valid and ProviderUnavailable if a spend limit or the pause stops it.
    `prior` and `feedback` redo a scene a reviewer looked at: the model sees its own JSON and what was wrong with the frames."""
    from faceless.providers.llm import _extract_json
    s = settings()
    safety.guard("sketch scene", s["per_scene_usd"])
    if not ledger.allow("sketch", "usd", s["per_scene_usd"], s["daily_usd"]):
        raise ProviderUnavailable(f"sketch daily cap ${s['daily_usd']:.2f} reached")
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_message(beat, ctx)}]
    if prior and feedback:
        msgs += [{"role": "assistant", "content": prior[:6000]},
                 {"role": "user", "content": "A reviewer watched the rendered frames of that scene and said:\n- " + "\n- ".join(feedback[:5])
                  + "\nDesign it again so those problems are gone (a different layout is fine). Return the complete JSON object."}]
    usd = tokens = 0.0
    text = ""
    started = time.time()
    why = ""
    reasons: list[str] = []
    for attempt in (1, 2):
        body = {"model": s["model"], "messages": msgs, "response_format": {"type": "json_object"}, "max_tokens": 6000, "usage": {"include": True},
                "reasoning": {"effort": s["effort"]}}
        try:
            data = _post(body)
        except ProviderUnavailable:
            raise
        except (ProviderError, OSError) as e:
            why = f"request failed: {type(e).__name__}"
            time.sleep(2)
            continue
        u = data.get("usage", {})
        spent = _cost(u)
        usd += spent
        tokens += u.get("total_tokens", 0)
        ledger.spend("sketch", "usd", spent, usd=spent, job=job)
        try:
            text = data["choices"][0]["message"]["content"] or ""
            spec = validate(_extract_json(text), dur=ctx["seconds"], allowed=ctx["allowed"], vocab=ctx.get("vocab"))
        except (KeyError, IndexError, ProviderError, SpecError) as e:
            why = str(e)[:400]
            reasons.append(why)
            msgs = msgs + [{"role": "assistant", "content": text[:6000]},
                           {"role": "user", "content": f"That scene was refused: {why}\nFix it and return the complete JSON object again."}]
            continue
        return {"spec": spec, "raw": text, "usd": round(usd, 6), "tokens": int(tokens), "seconds": round(time.time() - started, 1), "attempts": attempt,
                "reasons": reasons}
    raise SketchError(why or "no valid scene", reasons)


# ---------------------------------------------------------------- choosing beats and planning a video

def choose_beats(script: dict, spans: list[tuple[float, float]], planned: dict, cfg: dict) -> list[int]:
    """Which beats become sketch candidates: never the hook or the closing line, never one already a card, long enough to read, not next to another
    sketch or card; beats that carry a callout or a figure first. Deterministic."""
    n = len(script["beats"])
    scored = []
    for i, b in enumerate(script["beats"]):
        if i == 0 or i >= n - 1 or i in planned or i >= len(spans) or spans[i][1] - spans[i][0] < cfg["min_seconds"]:
            continue
        score = 3 * bool((b.get("callout") or "").strip()) + 2 * bool(re.search(r"\d", b.get("say", "")))
        scored.append((-score, i))
    chosen: list[int] = []
    for _, i in sorted(scored):
        if len(chosen) >= cfg["max_per_video"]:
            break
        if all(abs(i - j) > 1 for j in chosen) and all(abs(i - j) > 1 for j in planned):
            chosen.append(i)
    return sorted(chosen)


def context(job, script: dict, i: int, spans: list, motif: str) -> dict:
    beat = script["beats"][i]
    return {"series": config.pillar(job.pillar).name, "seconds": spans[i][1] - spans[i][0], "motif": motif, "allowed": allowed_figures(beat, script),
            "vocab": allowed_words(beat, script)}


def plan(job, script: dict, planned: dict[int, dict]) -> dict[int, dict]:
    """Sketch candidates for a video, as card specs {beat: {"kind": "sketch", "spec", "raw", "motif", "usd"}}. A candidate keeps its still: it replaces the
    still only if the rendered frames pass a review. Never raises: a beat whose scene cannot be made simply has none."""
    cfg = settings()
    if job.pillar not in cfg["pillars"] or not enabled():
        return {}
    try:
        spans = [tuple(b) for b in json.loads((job.dir / "voice.json").read_text(encoding="utf-8"))["beats"]]
    except (OSError, ValueError, KeyError):
        return {}
    pick = choose_beats(script, spans, planned, cfg)
    used: list[str] = []
    motifs = {}
    for i in pick:
        motifs[i] = motif_for(job.id, i, used)
        used.append(motifs[i])

    def one(i: int):
        try:
            got = author(script["beats"][i], context(job, script, i, spans, motifs[i]), job=job.id)
        except (SketchError, ProviderError, ProviderUnavailable) as e:
            events.emit("SKETCH_FAILED", job=job.id, beat=i, error=str(e)[:200], reasons=getattr(e, "reasons", [])[:2])
            return i, None
        job.add_cost("sketch", got["usd"])
        events.emit("SKETCH_AUTHORED", job=job.id, beat=i, motif=got["spec"]["motif"], usd=got["usd"], tokens=got["tokens"], seconds=got["seconds"], attempts=got["attempts"],
                    elements=len(got["spec"]["elements"]), tweens=len(got["spec"]["tweens"]))
        return i, {"kind": "sketch", "spec": got["spec"], "raw": got["raw"], "motif": motifs[i], "usd": got["usd"]}

    with ThreadPoolExecutor(max_workers=2) as ex:
        return {i: card for i, card in ex.map(one, pick) if card}


def candidates(imgs: list[dict]) -> dict[int, dict]:
    """The sketch card specs of the rows that carry one, are not already a card, and still have their still to fall back on. Nothing when the lane is off."""
    if settings()["mode"] != "on":
        return {}
    return {r["beat"]: r["sketch"] for r in imgs if r.get("sketch") and r.get("path") and not r.get("card")}


def apply_to_rows(imgs: list[dict], kept: dict[int, dict], report: dict[int, dict]) -> None:
    """Record what the review decided on the image rows: a scene that stands becomes the beat's card (its still stays on the row as the fallback), and
    every reviewed scene keeps its verdict for the audit trail."""
    for r in imgs:
        b = r["beat"]
        if b in report:
            r["sketch_review"] = report[b]
        if b in kept:
            r["card"] = kept[b]


# ---------------------------------------------------------------- looking at the rendered frames

CRITIC = """You review one animated scene from a short educational finance video. You see three frames of the scene (early, middle, final) side by side, and the narration it illustrates.
Each frame is a tall phone video. The series name at the top is part of the template. Captions are drawn later over the middle of the frame (about 55-70% of the way down), so the area there and the empty space below it are intended: never count them as a problem.
Judge the FINAL frame mainly. Score 1-5:
5 = clear, balanced, professional: one obvious focal idea, readable text, nothing overlapping, the picture explains the narration
4 = good with a small flaw
3 = acceptable filler: readable but plain, loosely related, or slightly cramped
2 = poor: text overlapping other text or shapes, shapes that do not form a coherent picture, almost nothing happening, or a picture unrelated to the narration
1 = broken: empty, cut off, or unreadable
Reply with JSON only: {"score": n, "problems": ["short phrase", ...]}"""


def _ffmpeg_frame(reel: Path, t: float, size: tuple[int, int]):
    """A frame of the reel at t seconds as a PIL image of `size`, or None when ffmpeg cannot read it."""
    import io
    import subprocess

    from PIL import Image
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(reel), "-frames:v", "1", "-vf", f"scale={size[0]}:{size[1]}", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True, timeout=60, check=False)
    return Image.open(io.BytesIO(p.stdout)).convert("RGB") if p.returncode == 0 and p.stdout else None


def _gray(reel: Path, t: float):
    """A quarter-size grayscale frame of the reel at t seconds as a numpy array, or None."""
    import numpy as np
    im = _ffmpeg_frame(reel, t, (270, 480))
    return np.asarray(im.convert("L")) if im is not None else None


def judge_frame(img) -> str:
    """'' when a frame looks like a finished scene; otherwise the reason it does not (empty, washed out, or something in the caption band)."""
    bright = img > 110
    if float(bright.mean()) < 0.004:
        return "the last frame is empty"
    if float(bright.mean()) > 0.6:
        return "the last frame is washed out"
    if float(bright[int(BAND[0] / 4):int(BAND[1] / 4)].mean()) > 0.03:
        return "something sits in the caption band"
    return ""


def strip(reel: Path, offset: float, seconds: float) -> bytes | None:
    """Three frames of one scene (early, middle, final) side by side as a small PNG for the reviewer."""
    import io

    from PIL import Image
    frames = [_ffmpeg_frame(reel, offset + seconds * f, (270, 480)) for f in (0.15, 0.5, 0.92)]
    if any(f is None for f in frames):
        return None
    out = Image.new("RGB", (270 * 3, 480))
    for k, f in enumerate(frames):
        out.paste(f, (270 * k, 0))
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


def critique(png: bytes, beat: dict, *, job: str | None = None) -> dict:
    """The reviewer's {score 1-5, problems[], usd} for one scene's frames. Raises ProviderError or ProviderUnavailable when it cannot answer."""
    import base64

    from faceless.providers.llm import _extract_json
    s = settings()
    safety.guard("sketch review", 0.002)
    content = [{"type": "text", "text": f"Narration: {beat.get('say', '')}\nCallout: {beat.get('callout', '')}"},
               {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}}]
    data = _post({"model": s["model"], "messages": [{"role": "system", "content": CRITIC}, {"role": "user", "content": content}],
                  "response_format": {"type": "json_object"}, "max_tokens": 1500, "usage": {"include": True}, "reasoning": {"effort": "low"}})
    spent = _cost(data.get("usage", {}))
    ledger.spend("sketch", "usd", spent, usd=spent, job=job)
    try:
        res = _extract_json(data["choices"][0]["message"]["content"] or "")
        score = int(res["score"])
    except (KeyError, IndexError, TypeError, ValueError, ProviderError) as e:
        raise ProviderError(f"reviewer gave no score: {type(e).__name__}") from e
    problems = [str(p)[:160] for p in (res.get("problems") or [])[:5]] if isinstance(res.get("problems"), list) else []
    return {"score": max(1, min(5, score)), "problems": problems, "usd": spent}


def review(job, reel: tuple[Path, dict], cand: dict[int, dict], spans: list, script: dict) -> dict[int, dict]:
    """For every candidate in the rendered reel: {ok, score, problems, reason}. Two cheap frame checks first, then the reviewer's score.
    A scene passes only with both; when the reviewer cannot answer the scene does not pass (nothing generated ships unreviewed)."""
    path, offsets = reel
    cfg = settings()

    def one(item):
        i, _spec = item
        sec = max(0.5, spans[i][1] - spans[i][0])
        off = offsets.get(i)
        if off is None:
            return i, {"ok": False, "score": None, "problems": [], "reason": "not in the reel"}
        for t in (off + sec * 0.6, off + sec - 0.4):
            img = _gray(path, t)
            if img is not None and (why := judge_frame(img)):
                return i, {"ok": False, "score": None, "problems": [why], "reason": why}
        png = strip(path, off, sec)
        if png is None:
            return i, {"ok": False, "score": None, "problems": [], "reason": "frames could not be read"}
        try:
            got = critique(png, script["beats"][i], job=job.id)
        except (ProviderError, ProviderUnavailable, OSError) as e:
            return i, {"ok": False, "score": None, "problems": [], "reason": f"reviewer unavailable ({type(e).__name__})"}
        job.add_cost("sketch", got["usd"])
        ok = got["score"] >= cfg["min_score"]
        return i, {"ok": ok, "score": got["score"], "problems": got["problems"], "reason": "" if ok else f"reviewer score {got['score']}"}

    with ThreadPoolExecutor(max_workers=3) as ex:
        out = dict(ex.map(one, cand.items()))
    for i, v in sorted(out.items()):
        events.emit("SKETCH_REVIEWED", job=job.id, beat=i, ok=v["ok"], score=v["score"], reason=v["reason"], problems=v["problems"][:3])
    return out


def revise(job, failed: dict[int, dict], cand: dict[int, dict], spans: list, script: dict) -> dict[int, dict]:
    """One more try for each scene the reviewer turned down: the model sees its own JSON and the reviewer's words. Returns the new card specs."""
    def one(i: int):
        old = cand[i]
        try:
            got = author(script["beats"][i], context(job, script, i, spans, old.get("motif", "")), job=job.id, prior=old.get("raw", ""), feedback=failed[i]["problems"])
        except (SketchError, ProviderError, ProviderUnavailable) as e:
            events.emit("SKETCH_FAILED", job=job.id, beat=i, error=str(e)[:200], reasons=getattr(e, "reasons", [])[:2], revision=True)
            return i, None
        job.add_cost("sketch", got["usd"])
        events.emit("SKETCH_REVISED", job=job.id, beat=i, usd=got["usd"], attempts=got["attempts"], elements=len(got["spec"]["elements"]))
        return i, {"kind": "sketch", "spec": got["spec"], "raw": got["raw"], "motif": old.get("motif", ""), "usd": got["usd"], "revised": True}

    with ThreadPoolExecutor(max_workers=2) as ex:
        return {i: card for i, card in ex.map(one, sorted(failed)) if card}


def settle(job, reel: tuple[Path, dict], picked: dict[int, dict], cand: dict[int, dict], spans: list, script: dict, rerender):
    """Look at the candidates in the rendered reel, keep the ones that pass, give the rest one revision, and return (reel to use, {beat: card spec that
    stands}, {beat: review}). `rerender(picked)` draws a new reel (or returns None); every offset the caller uses must come from the reel returned here."""
    report = review(job, reel, cand, spans, script)
    kept = {i: cand[i] for i, v in report.items() if v["ok"]}
    redo = {i: v for i, v in report.items() if not v["ok"] and v["problems"]}        # a reviewer's words, or what the frame check saw; "reviewer unavailable" has none
    if redo and settings()["revise"]:
        fresh = revise(job, redo, cand, spans, script)
        if fresh:
            picked2 = {b: spec for b, spec in picked.items() if b not in cand or b in kept}
            picked2.update(fresh)
            reel2 = rerender(picked2)
            if reel2:
                again = review(job, reel2, fresh, spans, script)
                for i, v in again.items():
                    report[i] = {**v, "revised": True}
                    if v["ok"]:
                        kept[i] = fresh[i]
                reel = reel2
                events.emit("SKETCH_SETTLED", job=job.id, kept=sorted(kept), asked=sorted(cand), revised=sorted(fresh))
                return reel, kept, report
    events.emit("SKETCH_SETTLED", job=job.id, kept=sorted(kept), asked=sorted(cand), revised=[])
    return reel, kept, report
