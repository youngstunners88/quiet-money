"""Motion cards: designed, animated scenes drawn in code with HyperFrames (HTML -> headless Chrome -> MP4).

Free and local: Apache-2.0, no API key, no cloud account, no per-render fee (Node 22 + ffmpeg + Chrome).
A card replaces an AI still for one beat, so it needs no image generation: an animated count-up for a beat
whose callout is a number, or a kinetic phrase card for any other beat. Used when
  - [production.cards].mode = "numbers": numeric-callout beats of the listed pillars become count-up cards, or
  - mode = "auto" (default): a beat whose image fell to procedural placeholder art becomes a card instead.
All cards of a video render in ONE reel (a single Chrome launch); render.py cuts each shot out of the reel.
Any failure returns None and the caller keeps the still image, so cards can never block a video.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from faceless import config, events
from faceless.config import Paths

CLI = "hyperframes@0.8.136"      # pinned: the same input must keep producing the same video
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"

# per-pillar look: (background top, background bottom, glow). The accent comes from [production].accent.
PALETTE = {
    "story": ("#2a1708", "#0d0703", "#ff9a3c"),
    "math": ("#14110a", "#050505", "#ffd23f"),
    "psychology": ("#101a26", "#05080d", "#6fb3ff"),
    "myth": ("#2a0b10", "#0a0305", "#ff4d5e"),
    "playbook": ("#0e2118", "#04100a", "#35e0a1"),
    "escape": ("#0b1630", "#03060f", "#ff7a2f"),
}
NUM = re.compile(r"^\s*([$€£]?)\s*(\d[\d,]*(?:\.\d+)?)\s*([%xX]|[KkMmBb](?![a-z]))?\s*(.*?)\s*$")


def available() -> bool:
    if not shutil.which("npx") or not shutil.which("ffmpeg"):
        return False
    try:
        v = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
        return int(v.lstrip("v").split(".")[0]) >= 22
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def parse_number(callout: str) -> dict | None:
    """'$698,202' -> value 698202; '21 YEARS' -> value 21 + tail 'YEARS'; '8%' -> suffix '%'. None if not numeric."""
    m = NUM.match(callout or "")
    if not m:
        return None
    cur, digits, suf, tail = m.groups()
    dec = len(digits.split(".")[1]) if "." in digits else 0
    value = float(digits.replace(",", ""))
    return {"static": not cur and not suf and dec == 0 and 1900 <= value <= 2100,   # a year: show it, don't count to it
            "value": value, "prefix": cur, "suffix": (suf or "").upper() if suf in ("x", "X") else (suf or ""),
            "decimals": dec, "label": tail[:24].upper()}


WORDS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6}
STEP = re.compile(r"^\s*STEP\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|[1-6])\b", re.I)
VS = re.compile(r"\s+(?:VS\.?|VERSUS)\s+", re.I)


def parse_compare(callout: str) -> dict | None:
    """'$698,202 VS $298,072' -> two bars sized by value; 'ASSET VS LIABILITY' -> a two-word face-off. None otherwise."""
    parts = VS.split((callout or "").strip())
    if len(parts) != 2 or not all(0 < len(x) <= 16 for x in parts):
        return None
    nums = [parse_number(x) for x in parts]
    if all(nums) and all(n["value"] > 0 for n in nums) and not any(n["static"] for n in nums):
        return {"kind": "compare", "numeric": True, "a": parts[0].strip(), "b": parts[1].strip(),
                "va": nums[0]["value"], "vb": nums[1]["value"]}
    if any(nums):      # one side a number, the other a word: not a clean comparison
        return None
    return {"kind": "compare", "numeric": False, "a": parts[0].strip().upper(), "b": parts[1].strip().upper()}


def parse_step(callout: str, say: str = "") -> dict | None:
    """'STEP TWO' -> numeral 2 with the beat's own gist underneath."""
    m = STEP.match(callout or "")
    if not m:
        return None
    tok = m.group(1).upper()
    n = int(tok) if tok.isdigit() else WORDS[tok]
    body = re.sub(r"^\s*(?:first|second|third|next|then|step\s+\w+)\b[,:]?\s*", "", say or "", flags=re.I)
    first = re.split(r"(?<=[.!?])\s", body.strip())[0] if body.strip() else ""
    return {"kind": "steps", "n": n, "word": tok if not tok.isdigit() else list(WORDS)[n - 1], "gist": " ".join(first.split()[:10]).rstrip(".,;:")}


def key_phrase(beat: dict) -> str:
    """Callout if the beat has one, else its first few spoken words: what the card says in big type."""
    c = (beat.get("callout") or "").strip()
    if c:
        return c.upper()
    words = re.findall(r"[A-Za-z0-9$%'.,-]+", beat.get("say", ""))
    return " ".join(words[:5]).upper().rstrip(".,")


def pick(script: dict, imgs: list[dict] | None, pillar_id: str) -> dict[int, dict]:
    """Which beats become cards, with their specs. imgs=None means the decision is made before images exist."""
    cfg = config.load()["production"].get("cards", {})
    mode = cfg.get("mode", "auto")
    if mode == "off" or not available():
        return {}
    out: dict[int, dict] = {}
    for i, beat in enumerate(script["beats"]):
        if i == 0:      # the hook beat keeps its hero still (cover image + hook box sit on it)
            continue
        num = parse_number(beat.get("callout", ""))
        placeholder = imgs is not None and i < len(imgs) and imgs[i]["provider"] == "procedural"
        if mode == "numbers" and cfg.get("variety", True):    # comparisons and numbered steps suit every series
            spec = parse_compare(beat.get("callout", "")) or parse_step(beat.get("callout", ""), beat.get("say", ""))
            if spec:
                out[i] = spec
                continue
        wants = (mode == "numbers" and num and pillar_id in cfg.get("pillars", [])) or placeholder
        if wants:
            out[i] = {"kind": "stat", **num} if num else {"kind": "phrase", "text": key_phrase(beat)}
    return out


def _fmt(v: float, decimals: int) -> str:
    return f"{v:,.{decimals}f}"


def _scene(n: int, t0: float, dur: float, spec: dict, pal: tuple, accent: str, fps: int, kicker: str = "") -> tuple[str, str]:
    """(html, js) for one scene, absolutely timed on the reel's single timeline."""
    bg0, bg1, glow = pal
    sid = f"s{n}"
    pre = f'<div class="scene clip" id="{sid}" data-start="{t0:.3f}" data-duration="{dur:.3f}" data-track-index="0">'
    bg = (f'<div class="bg" style="background:radial-gradient(120% 70% at 50% 28%,{bg0} 0%,{bg1} 70%)"></div>'
          f'<div class="glow" id="{sid}g" style="background:radial-gradient(closest-side,{glow}55,transparent)"></div>')
    grid = "".join(f'<div class="ln" id="{sid}l{k}" style="top:{150 + k * 210}px"></div>' for k in range(8))
    dots = "".join(f'<div class="dot" id="{sid}d{k}" style="left:{(k * 137) % 1000 + 40}px;top:{(k * 241) % 1500 + 120}px;'
                   f'background:{accent}"></div>' for k in range(10))
    js = [f'tl.set("#{sid}",{{opacity:1}},{t0:.3f});',
          f'tl.fromTo("#{sid}g",{{scale:0.6,opacity:0}},{{scale:1.15,opacity:1,duration:{dur:.3f},ease:"sine.out"}},{t0:.3f});']
    for k in range(8):   # grid lines drift upward: constant motion keeps the scene alive
        js.append(f'tl.fromTo("#{sid}l{k}",{{y:0,opacity:0.0}},{{y:-90,opacity:0.16,duration:{dur:.3f},ease:"none"}},{t0:.3f});')
    for k in range(10):
        js.append(f'tl.fromTo("#{sid}d{k}",{{y:0,opacity:0}},{{y:-{160 + k * 25},opacity:0.5,duration:{dur:.3f},ease:"sine.inOut"}},{t0 + (k % 4) * 0.08:.3f});')
    if spec["kind"] == "stat":
        steps = 0 if spec.get("static") else max(8, min(48, round(dur * 14)))
        end = spec["value"]
        spans = []
        for s in range(steps + 1):
            p = s / steps
            val = end * (1 - (1 - p) ** 3)      # ease-out cubic toward the real number
            text = f'{spec["prefix"]}{_fmt(val if s < steps else end, spec["decimals"])}{spec["suffix"]}'
            spans.append(f'<span class="num" id="{sid}n{s}">{html.escape(text)}</span>')
            ts = t0 + 0.12 + (dur * 0.62) * (s / (steps + 1))
            te = t0 + 0.12 + (dur * 0.62) * ((s + 1) / (steps + 1)) if s < steps else t0 + dur
            js.append(f'tl.set("#{sid}n{s}",{{visibility:"hidden"}},{t0:.3f});')
            js.append(f'tl.set("#{sid}n{s}",{{visibility:"visible"}},{ts:.3f});')
            if s < steps:
                js.append(f'tl.set("#{sid}n{s}",{{visibility:"hidden"}},{te:.3f});')
        label = html.escape(spec.get("label", ""))
        end_text = f'{spec["prefix"]}{_fmt(end, spec["decimals"])}{spec["suffix"]}'
        size = min(300, int(940 / (max(3, len(end_text)) * 0.47)))      # the widest value must fit the frame
        spans = [x.replace('class="num"', f'class="num" style="font-size:{size}px"') for x in spans]
        pts = [(round(960 * k / 40), round(500 - 470 * (2.718281828 ** (3 * k / 40) - 1) / (2.718281828 ** 3 - 1))) for k in range(41)]
        line = " ".join(f"{x},{y}" for x, y in pts)
        chart = (f'<div class="chart" id="{sid}c"><svg width="960" height="520" viewBox="0 0 960 520">'
                 f'<defs><linearGradient id="{sid}gr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{accent}" stop-opacity="0.38"/>'
                 f'<stop offset="1" stop-color="{accent}" stop-opacity="0"/></linearGradient></defs>'
                 f'<polygon points="{line} 960,520 0,520" fill="url(#{sid}gr)"/>'
                 f'<polyline points="{line}" fill="none" stroke="{accent}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"/></svg></div>')
        body = (f'<div class="kick">{html.escape(kicker)}</div>'
                f'<div class="stat" id="{sid}b"><div class="numwrap" style="height:{size}px">{"".join(spans)}</div>'
                f'<div class="bar" id="{sid}r" style="background:{accent}"></div>'
                f'<div class="lab" id="{sid}t">{label}</div></div>{chart}')
        js.append(f'tl.fromTo("#{sid}c",{{width:0,opacity:0.9}},{{width:960,opacity:0.9,duration:{dur * 0.85:.3f},ease:"power2.inOut"}},{t0 + 0.1:.3f});')
        js.append(f'tl.fromTo("#{sid}b",{{scale:0.86,opacity:0.35}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(1.6)"}},{t0:.3f});')
        js.append(f'tl.fromTo("#{sid}r",{{scaleX:0}},{{scaleX:1,duration:{dur * 0.6:.3f},ease:"power2.out"}},{t0 + 0.2:.3f});')
        js.append(f'tl.fromTo("#{sid}t",{{opacity:0,y:20}},{{opacity:1,y:0,duration:0.4}},{t0 + 0.5:.3f});')
    elif spec["kind"] == "compare":
        body, extra = _compare(sid, t0, dur, spec, accent, kicker)
        js += extra
    elif spec["kind"] == "steps":
        body, extra = _steps(sid, t0, dur, spec, accent, kicker)
        js += extra
    else:
        words = spec["text"].split()
        spans = "".join(f'<span class="w" id="{sid}w{k}">{html.escape(w)}</span> ' for k, w in enumerate(words))
        fs = 150 if len(words) <= 3 else 128 if len(words) <= 5 else 108
        body = (f'<div class="kick">{html.escape(kicker)}</div><div class="pwrap"><div class="phrase" id="{sid}b" style="font-size:{fs}px">{spans}</div>'
                f'<div class="bar" id="{sid}r" style="background:{accent}"></div></div>')
        for k in range(len(words)):
            js.append(f'tl.fromTo("#{sid}w{k}",{{opacity:0,y:50,scale:0.9}},{{opacity:1,y:0,scale:1,duration:0.35,ease:"power3.out"}},'
                      f'{t0 + 0.1 + k * min(0.22, dur * 0.5 / max(1, len(words))):.3f});')
        js.append(f'tl.fromTo("#{sid}r",{{scaleX:0}},{{scaleX:1,duration:{dur * 0.5:.3f},ease:"power2.out"}},{t0 + 0.3:.3f});')
    js.append(f'tl.to("#{sid}",{{opacity:0,duration:0.001}},{t0 + dur - 0.002:.3f});')
    return pre + bg + grid + dots + body + "</div>", "\n".join(js)


def _compare(sid: str, t0: float, dur: float, spec: dict, accent: str, kicker: str) -> tuple[str, list[str]]:
    """Two amounts as bars grown from one baseline, or two words facing off around a VS. Only fromTo/set tweens (seek-safe)."""
    js: list[str] = []
    if spec["numeric"]:
        hi = max(spec["va"], spec["vb"])
        base, top = 1500, 820
        parts = []
        for k, (label, v, col, cx) in enumerate(((spec["a"], spec["va"], accent, 340), (spec["b"], spec["vb"], "rgba(255,255,255,.38)", 740))):
            h = max(70, round(top * v / hi))
            fs = min(104, int(400 / (max(4, len(label)) * 0.47)))
            parts.append(f'<div class="cb" id="{sid}b{k}" style="left:{cx - 160}px;top:{base - h}px;width:320px;height:{h}px;background:{col}"></div>'
                         f'<div class="cv" id="{sid}v{k}" style="left:{cx - 200}px;top:{base - h - fs - 36}px;width:400px;font-size:{fs}px">{html.escape(label)}</div>')
            js.append(f'tl.fromTo("#{sid}b{k}",{{scaleY:0}},{{scaleY:1,duration:{dur * 0.5:.3f},ease:"power3.out"}},{t0 + 0.25 + 0.15 * k:.3f});')
            js.append(f'tl.fromTo("#{sid}v{k}",{{opacity:0,y:24}},{{opacity:1,y:0,duration:0.4,ease:"power2.out"}},{t0 + 0.25 + dur * 0.4 + 0.15 * k:.3f});')
        parts.append(f'<div class="vs" id="{sid}x" style="left:490px;top:{base + 40}px">VS</div>')
        js.append(f'tl.fromTo("#{sid}x",{{opacity:0,scale:0.5}},{{opacity:1,scale:1,duration:0.4,ease:"back.out(2)"}},{t0 + 0.2:.3f});')
        return f'<div class="kick">{html.escape(kicker)}</div>' + "".join(parts), js
    fs = min(170, int(900 / (max(5, len(spec["a"]), len(spec["b"])) * 0.5)))
    body = (f'<div class="kick">{html.escape(kicker)}</div>'
            f'<div class="fo" style="top:540px;font-size:{fs}px" id="{sid}a">{html.escape(spec["a"])}</div>'
            f'<div class="vs" id="{sid}x" style="left:490px;top:{540 + fs + 50}px">VS</div>'
            f'<div class="fo" style="top:{540 + fs + 190}px;font-size:{fs}px;color:{accent}" id="{sid}c">{html.escape(spec["b"])}</div>')
    js += [f'tl.fromTo("#{sid}a",{{opacity:0,x:-320}},{{opacity:1,x:0,duration:0.5,ease:"power3.out"}},{t0 + 0.15:.3f});',
           f'tl.fromTo("#{sid}x",{{opacity:0,scale:0.4}},{{opacity:1,scale:1,duration:0.4,ease:"back.out(2)"}},{t0 + 0.55:.3f});',
           f'tl.fromTo("#{sid}c",{{opacity:0,x:320}},{{opacity:1,x:0,duration:0.5,ease:"power3.out"}},{t0 + 0.75:.3f});']
    return body, js


def _steps(sid: str, t0: float, dur: float, spec: dict, accent: str, kicker: str) -> tuple[str, list[str]]:
    """A numbered step: a ring that draws itself around the numeral, the step word, and the beat's own gist."""
    circ = round(2 * 3.14159265 * 190)
    gist = html.escape(spec.get("gist", "")).upper()
    body = (f'<div class="kick">{html.escape(kicker)}</div>'
            f'<div class="ring" id="{sid}n"><svg width="440" height="440" viewBox="0 0 440 440"><circle cx="220" cy="220" r="190" fill="none" '
            f'stroke="rgba(255,255,255,.14)" stroke-width="14"/><circle id="{sid}o" cx="220" cy="220" r="190" fill="none" stroke="{accent}" '
            f'stroke-width="14" stroke-linecap="round" stroke-dasharray="{circ}" stroke-dashoffset="{circ}" transform="rotate(-90 220 220)"/></svg>'
            f'<div class="rn">{spec["n"]}</div></div>'
            f'<div class="sw" id="{sid}w">STEP {html.escape(spec["word"])}</div>'
            f'<div class="sg" id="{sid}g">{gist}</div>')
    js = [f'tl.fromTo("#{sid}n",{{scale:0.7,opacity:0}},{{scale:1,opacity:1,duration:0.45,ease:"back.out(1.7)"}},{t0:.3f});',
          f'tl.fromTo("#{sid}o",{{strokeDashoffset:{circ}}},{{strokeDashoffset:0,duration:{dur * 0.55:.3f},ease:"power2.inOut"}},{t0 + 0.15:.3f});',
          f'tl.fromTo("#{sid}w",{{opacity:0,y:24}},{{opacity:1,y:0,duration:0.4}},{t0 + 0.4:.3f});',
          f'tl.fromTo("#{sid}g",{{opacity:0,y:30}},{{opacity:1,y:0,duration:0.5,ease:"power2.out"}},{t0 + 0.65:.3f});']
    return body, js


def build_project(root: Path, specs: list[tuple[int, dict, float]], pillar_id: str, accent: str, fps: int,
                  kicker: str = "") -> float:
    """Write the HyperFrames project for the reel; returns its total duration. specs: (beat, spec, seconds)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    for f in ("Anton-Regular.ttf", "Montserrat-Black.ttf"):
        shutil.copy2(Paths.fonts / f, root / "assets" / f)
    pal = PALETTE.get(pillar_id, PALETTE["math"])
    scenes, js, t = [], [], 0.0
    for n, (_beat, spec, dur) in enumerate(specs):
        h, j = _scene(n, t, dur, spec, pal, accent, fps, kicker)
        scenes.append(h)
        js.append(j)
        t += dur
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080, height=1920">
<script src="{GSAP}"></script>
<style>
@font-face{{font-family:"Anton";src:url("assets/Anton-Regular.ttf")}}
@font-face{{font-family:"MontserratBlack";src:url("assets/Montserrat-Black.ttf")}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#000}}
.scene{{position:absolute;left:0;top:0;width:1080px;height:1920px;overflow:hidden;opacity:0}}
.bg,.glow{{position:absolute}} .bg{{inset:0}}
.glow{{left:90px;top:230px;width:900px;height:900px;border-radius:50%}}
.ln{{position:absolute;left:60px;width:960px;height:2px;background:#fff;opacity:0}}
.dot{{position:absolute;width:10px;height:10px;border-radius:50%;opacity:0}}
.kick{{position:absolute;left:0;top:300px;width:1080px;text-align:center;font:400 40px/1 "Anton";letter-spacing:12px;
  color:#fff;opacity:.55}}
.chart{{position:absolute;left:60px;top:1290px;width:0;height:520px;overflow:hidden;opacity:.9}}
.stat{{position:absolute;left:0;top:430px;width:1080px;text-align:center;opacity:0}}
.numwrap{{position:relative;height:300px}}
.num{{position:absolute;left:0;width:1080px;top:0;font:400 300px/1 "Anton";color:#fff;letter-spacing:-4px;
  text-shadow:0 0 60px rgba(255,255,255,.25);visibility:hidden}}
.bar{{height:12px;width:560px;margin:34px auto 0;transform-origin:left center;border-radius:6px}}
.lab{{margin-top:34px;font:400 74px/1.1 "Anton";letter-spacing:8px;color:#fff;opacity:0}}
.pwrap{{position:absolute;left:70px;top:430px;width:940px}}
.phrase{{width:940px;text-align:center;font:400 128px/1.12 "MontserratBlack";
  color:#fff;text-transform:uppercase;text-shadow:0 6px 40px rgba(0,0,0,.6)}}
.pwrap .bar{{margin-top:44px}}
.w{{display:inline-block;opacity:0}}
.cb{{position:absolute;transform-origin:center bottom;border-radius:14px 14px 0 0;opacity:.95}}
.cv{{position:absolute;text-align:center;font:400 96px/1 "Anton";color:#fff;opacity:0;letter-spacing:-1px}}
.vs{{position:absolute;width:100px;text-align:center;font:400 54px/1 "Anton";color:#fff;opacity:0;letter-spacing:4px}}
.fo{{position:absolute;left:60px;width:960px;text-align:center;font:400 150px/1 "Anton";color:#fff;opacity:0;letter-spacing:2px;
  text-shadow:0 6px 40px rgba(0,0,0,.6)}}
.ring{{position:absolute;left:320px;top:420px;width:440px;height:440px;opacity:0}}
.rn{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font:400 270px/1 "Anton";color:#fff}}
.sw{{position:absolute;left:0;top:930px;width:1080px;text-align:center;font:400 84px/1 "Anton";letter-spacing:12px;color:#fff;opacity:0}}
.sg{{position:absolute;left:100px;top:1270px;width:880px;text-align:center;font:400 60px/1.2 "MontserratBlack";color:#fff;opacity:0;
  text-shadow:0 4px 30px rgba(0,0,0,.6)}}
</style></head>
<body>
<div id="root" data-composition-id="cards" data-start="0" data-duration="{t:.3f}" data-width="1080" data-height="1920" data-fps="{fps}">
{"".join(scenes)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines = window.__timelines || {{}};
window.__timelines["cards"] = tl;
tl.seek(0);
</script></body></html>"""
    (root / "index.html").write_text(page, encoding="utf-8")
    (root / "meta.json").write_text(json.dumps({"id": "cards", "name": "cards"}), encoding="utf-8")
    (root / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components",
                                                                 "assets": "assets"}}), encoding="utf-8")
    return t


def render_reel(job, picked: dict[int, dict], beat_spans: dict[int, tuple[float, float]], pillar_id: str,
                accent: str, fps: int) -> tuple[Path, dict[int, float]] | None:
    """Render every card of the video in one HyperFrames run. Returns (reel.mp4, {beat: offset seconds in reel})."""
    root = job.dir / "cards"
    specs = [(i, spec, max(0.5, beat_spans[i][1] - beat_spans[i][0])) for i, spec in sorted(picked.items())]
    total = build_project(root, specs, pillar_id, accent, fps, kicker=config.pillar(pillar_id).name.upper())
    out = root / "reel.mp4"
    cmd = ["npx", "--yes", CLI, "render", str(root), "-o", str(out), "-f", str(fps), "-q", "looks", "--quiet", "--workers", "2"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=420,
                           env={**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1"})
    except (OSError, subprocess.TimeoutExpired) as e:
        events.emit("CARDS_FAILED", job=job.id, error=type(e).__name__)
        return None
    if p.returncode != 0 or not out.exists():
        events.emit("CARDS_FAILED", job=job.id, error=(p.stderr or p.stdout)[-300:])
        return None
    offsets, t = {}, 0.0
    for i, _spec, dur in specs:
        offsets[i] = t
        t += dur
    events.emit("CARDS_RENDERED", job=job.id, cards=len(specs), seconds=round(total, 1))
    return out, offsets
