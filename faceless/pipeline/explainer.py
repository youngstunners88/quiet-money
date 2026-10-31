"""The explainer look: one drawn world, word-timed, no characters (owner's Showhow doc, 2026-10-31; ideas only, no code taken).

A story is told with diagrams drawn in code: a fork in the road, bars that grow, a ring that fills, a timeline, a big number. Every element appears
on the word that names it; one grid drifts under all the scenes so the video reads as one continuous camera move. Brand: night navy, gold, Anton
and Montserrat Black. It reuses the HyperFrames render of the motion cards, so it is free, local and needs no image generator; a failure returns None
and the caller keeps whatever the pipeline did before.

A beat chooses its diagram with a `scene` object in the script (hand-written scripts only; a beat without one gets a number or a phrase card):
  {"type": "fork",   "left": {"label": "...", "value": "...", "sub": "...", "word": "..."}, "right": {...}, "pick": "right"}
  {"type": "stat",   "value": "$4M", "label": "A YEAR", "word": "four", "value2": "~$30M", "label2": "HIS CUT"}
  {"type": "bars",   "items": [{"label": "...", "value": 1, "text": "~$1M", "word": "..."}, ...]}
  {"type": "ring",   "percent": 10, "text": ">10%", "label": "OF BLAZE", "word": "percent"}
  {"type": "timeline", "events": [{"year": "2008", "label": "BEATS", "word": "..."}], "active": 0}
  {"type": "versus", "left": {"label": "FLAT FEE", "sub": "..."}, "right": {"label": "A STAKE", "sub": "..."}}
  {"type": "phrase", "lines": ["A CHECK PAYS ONCE.", "OWNERSHIP KEEPS PAYING."], "hl": ["ONCE", "KEEPS"]}
  {"type": "catch",  "lines": ["..."]}
  {"type": "end",    "text": "CHECK OR STAKE?"}
`word` is a spoken word the element waits for; without it the elements spread evenly across the beat.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from faceless.config import Paths

GOLD = "#FFD23F"
DIM = "#6f7a99"
NAVY, NAVY_D = "#0b1630", "#03060f"

CSS = """
:root{--gold:#FFD23F;--dim:#6f7a99;--ink:#ffffff}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
#bg{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 38%,#12254d 0%,#0b1630 42%,#03060f 100%)}
#grid{position:absolute;left:-400px;top:0;width:1900px;height:1920px;opacity:.55}
#glow{position:absolute;left:140px;top:300px;width:800px;height:800px;border-radius:50%;background:radial-gradient(circle,rgba(255,210,63,.20),rgba(255,210,63,0) 68%)}
#prog{position:absolute;left:0;top:0;width:1080px;height:8px;background:var(--gold);transform-origin:left center;transform:scaleX(0)}
.sc{position:absolute;left:0;top:0;width:1080px;height:1920px;opacity:0}
.ab{position:absolute}
.cap{font:400 58px/1.05 "MontserratBlack";color:var(--ink);text-align:center;text-transform:uppercase}
.big{font:400 210px/1 "Anton";color:var(--ink);text-align:center;letter-spacing:-2px}
.mid{font:400 120px/1 "Anton";color:var(--ink);text-align:center}
.lab{font:400 50px/1.12 "Anton";letter-spacing:6px;color:var(--ink);text-align:center;text-transform:uppercase}
.sub{font:400 34px/1.2 "MontserratBlack";color:#b9c3e0;text-align:center;text-transform:uppercase}
.g{color:var(--gold)}
.w{display:inline-block}
.tag{display:inline-block;padding:14px 34px;background:var(--gold);color:#14110a;font:400 56px/1 "Anton";letter-spacing:8px;border-radius:10px}
.pill{display:inline-block;padding:22px 54px;background:var(--gold);color:#14110a;font:400 62px/1 "Anton";letter-spacing:6px;border-radius:60px}
"""


_OFFSET = 0.0          # start of the scene being written, so every tween carries video time


def _esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def _wat(spec: dict, hint, frac: float, dur: float) -> float:
    """Seconds into the beat when the element should appear: the start of the first spoken word that contains `hint`, else `frac` of the beat."""
    if hint:
        h = str(hint).lower()
        for w in spec.get("words", []):
            if len(w) > 2 and h in str(w[2]).lower():
                return max(0.05, float(w[0]))
    return max(0.05, min(dur - 0.4, dur * frac))


WAIT = 0.5            # the first element of a scene never waits longer than this for its word (the cut has a picture at once); each later one gets 1 s more


def _spread(spec: dict, hints: list, dur: float, first: float = 0.12, last: float = 0.78) -> list[float]:
    """One reveal time per element: its hint word when it has one, otherwise an even slot (the later elements never come before the earlier)."""
    n = max(1, len(hints))
    times, prev = [], 0.0
    for k, h in enumerate(hints):
        t = _wat(spec, h, first + (last - first) * (k / max(1, n - 1)) if n > 1 else first, dur)
        t = max(min(t, WAIT + k), prev + 0.25) if k else min(t, WAIT)
        times.append(min(t, max(0.1, dur - 0.5)))
        prev = times[-1]
    return times


def _fromto(sel: str, frm: str, to: str, at: float, d: float = 0.5, ease: str = "power3.out") -> str:
    return f'E("{sel}",{{{frm}}},{{{to}}},{at + _OFFSET:.3f},{d},"{ease}");'


def _num_parts(text: str) -> tuple[str, float | None, str]:
    """('$', 15.0, 'M') from '$15M'; value None when the text has no plain number (it then appears without counting)."""
    m = re.fullmatch(r"([~<>≈]?\$?)(\d[\d,]*\.?\d*)([KMB%]?)", text.strip())
    if not m:
        return "", None, text
    return m.group(1), float(m.group(2).replace(",", "")), m.group(3)


def _count(eid: str, text: str, at: float, d: float) -> str:
    """A number that counts up to its final text (the last frame always shows the exact text)."""
    pre, val, suf = _num_parts(text)
    if val is None or val < 10:         # a count from zero to a small number only flickers
        return ""
    dec = len(str(val).split(".")[1].rstrip("0")) if "." in str(val) and str(val).split(".")[1].strip("0") else 0
    return (f'(function(){{const o={{v:0}};tl.to(o,{{v:{val},duration:{d},ease:"power2.out",onUpdate:function(){{'
            f'document.getElementById("{eid}").textContent="{pre}"+o.v.toFixed({dec}).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g,",")+"{suf}";}}}},{at + _OFFSET:.3f});}})();'
            f'tl.set("#{eid}",{{textContent:{json.dumps(text)}}},{at + d + 0.02 + _OFFSET:.3f});')


def _scene_fork(n: int, spec: dict, dur: float) -> tuple[str, list[str]]:
    L, R = spec.get("left", {}), spec.get("right", {})
    pick = spec.get("pick", "right")
    tl_, tr_ = _spread(spec, [L.get("word"), R.get("word")], dur, 0.18, 0.5)[:2]
    ids = {k: f"s{n}_{k}" for k in ("trunk", "lp", "rp", "ll", "lv", "ls", "rl", "rv", "rs")}
    lc, rc = (GOLD, DIM) if pick == "left" else (DIM, GOLD)
    htm = f"""
<svg class="ab" style="left:0;top:250px" width="1080" height="900" viewBox="0 0 1080 900">
 <path id="{ids['trunk']}" d="M540,880 L540,600" pathLength="1" stroke="{GOLD}" stroke-width="22" stroke-linecap="round" fill="none" stroke-dasharray="1" stroke-dashoffset="1"/>
 <path id="{ids['lp']}" d="M540,600 C540,480 290,520 290,330" pathLength="1" stroke="{lc}" stroke-width="{26 if pick == 'left' else 14}" stroke-linecap="round" fill="none" stroke-dasharray="1" stroke-dashoffset="1"/>
 <path id="{ids['rp']}" d="M540,600 C540,480 790,520 790,330" pathLength="1" stroke="{rc}" stroke-width="{26 if pick == 'right' else 14}" stroke-linecap="round" fill="none" stroke-dasharray="1" stroke-dashoffset="1"/>
</svg>
<div id="{ids['ll']}" class="ab lab" style="left:40px;top:250px;width:500px;opacity:0;color:{lc if pick != 'left' else GOLD}">{_esc(L.get('label'))}</div>
<div id="{ids['lv']}" class="ab mid" style="left:40px;top:310px;width:500px;opacity:0;color:{lc if pick != 'left' else GOLD}">{_esc(L.get('value'))}</div>
<div id="{ids['ls']}" class="ab sub" style="left:60px;top:450px;width:460px;opacity:0">{_esc(L.get('sub'))}</div>
<div id="{ids['rl']}" class="ab lab" style="left:540px;top:250px;width:500px;opacity:0;color:{rc if pick != 'right' else GOLD}">{_esc(R.get('label'))}</div>
<div id="{ids['rv']}" class="ab mid" style="left:540px;top:310px;width:500px;opacity:0;color:{rc if pick != 'right' else GOLD}">{_esc(R.get('value'))}</div>
<div id="{ids['rs']}" class="ab sub" style="left:560px;top:450px;width:460px;opacity:0">{_esc(R.get('sub'))}</div>"""
    js = [
        _fromto(f"#{ids['trunk']}", "strokeDashoffset:1", "strokeDashoffset:0", 0.05, 0.5, "power2.out"),
        _fromto(f"#{ids['lp']}", "strokeDashoffset:1", "strokeDashoffset:0", tl_, 0.6, "power2.out"),
        _fromto(f"#{ids['rp']}", "strokeDashoffset:1", "strokeDashoffset:0", tr_, 0.6, "power2.out"),
    ]
    for side, t in (("l", tl_), ("r", tr_)):
        for part in ("l", "v", "s"):
            js.append(_fromto(f"#{ids[side + part]}", "opacity:0,y:30", "opacity:1,y:0", t + 0.25 + 0.08 * "lvs".index(part), 0.45))
    return htm, js


def _scene_stat(n: int, spec: dict, dur: float) -> tuple[str, list[str]]:
    v, lab = str(spec.get("value", "")), spec.get("label", "")
    v2, lab2 = spec.get("value2"), spec.get("label2", "")
    t1 = min(_wat(spec, spec.get("word"), 0.1, dur), WAIT)
    t2 = min(_wat(spec, spec.get("word2"), 0.55, dur), WAIT + 1.6)
    two = bool(v2)
    top = 330 if two else 400
    htm = f"""
<div id="s{n}_v" class="ab big" style="left:40px;top:{top}px;width:1000px;opacity:0;{'font-size:190px' if two else ''}">{_esc(v)}</div>
<div id="s{n}_u" class="ab" style="left:200px;top:{top + (210 if two else 250)}px;width:680px;height:12px;background:{GOLD};border-radius:6px;transform-origin:left center;transform:scaleX(0)"></div>
<div id="s{n}_l" class="ab lab" style="left:60px;top:{top + (250 if two else 300)}px;width:960px;opacity:0">{_esc(lab)}</div>
<div id="s{n}_v2" class="ab big g" style="left:40px;top:{top + 400}px;width:1000px;opacity:0;font-size:170px">{_esc(v2 or '')}</div>
<div id="s{n}_l2" class="ab lab" style="left:60px;top:{top + 600}px;width:960px;opacity:0">{_esc(lab2)}</div>"""
    js = [_fromto(f"#s{n}_v", "opacity:0,scale:.82", "opacity:1,scale:1", t1, 0.5, "back.out(1.5)"),
          _fromto(f"#s{n}_u", "scaleX:0", "scaleX:1", t1 + 0.25, 0.5),
          _fromto(f"#s{n}_l", "opacity:0,y:24", "opacity:1,y:0", t1 + 0.35, 0.45), _count(f"s{n}_v", v, t1, min(1.0, dur * 0.4))]
    if two:
        js += [_fromto(f"#s{n}_v2", "opacity:0,scale:.82", "opacity:1,scale:1", t2, 0.5, "back.out(1.5)"),
               _fromto(f"#s{n}_l2", "opacity:0,y:24", "opacity:1,y:0", t2 + 0.3, 0.45), _count(f"s{n}_v2", str(v2), t2, min(1.0, dur * 0.3))]
    return htm, js


def _scene_bars(n: int, spec: dict, dur: float) -> tuple[str, list[str]]:
    items = (spec.get("items") or [])[:3]
    k = max(1, len(items))
    top = max(float(i.get("value", 1)) for i in items) if items else 1.0
    base, maxh, bw = 1000, 560, 250 if k == 2 else 200
    gap = (1080 - k * bw) / (k + 1)
    times = _spread(spec, [i.get("word") for i in items], dur, 0.12, 0.62)
    htm, js = "", []
    for j, it in enumerate(items):
        h = max(24.0, maxh * float(it.get("value", 1)) / top)
        x = gap + j * (bw + gap)
        col = it.get("color") or (GOLD if j == k - 1 else DIM)
        htm += f"""
<div id="s{n}_b{j}" class="ab" style="left:{x:.0f}px;top:{base - h:.0f}px;width:{bw}px;height:{h:.0f}px;background:linear-gradient(180deg,{col},{col}cc);border-radius:14px 14px 0 0;transform-origin:50% 100%;transform:scaleY(0)"></div>
<div id="s{n}_t{j}" class="ab mid" style="left:{x - 60:.0f}px;top:{base - h - 140:.0f}px;width:{bw + 120}px;opacity:0;font-size:96px;color:{col if col != DIM else '#ffffff'}">{_esc(it.get('text', ''))}</div>
<div id="s{n}_n{j}" class="ab sub" style="left:{x - 50:.0f}px;top:{base + 24}px;width:{bw + 100}px;opacity:0">{_esc(it.get('label', ''))}</div>"""
        js += [_fromto(f"#s{n}_b{j}", "scaleY:0", "scaleY:1", times[j], 0.7, "power3.out"),
               _fromto(f"#s{n}_t{j}", "opacity:0,y:20", "opacity:1,y:0", times[j] + 0.45, 0.4),
               _fromto(f"#s{n}_n{j}", "opacity:0", "opacity:1", times[j] + 0.3, 0.4)]
    htm += f'<div class="ab" style="left:80px;top:{base}px;width:920px;height:4px;background:{DIM}"></div>'
    return htm, js


def _scene_ring(n: int, spec: dict, dur: float) -> tuple[str, list[str]]:
    pct = max(1.0, min(99.0, float(spec.get("percent", 10))))
    t = min(_wat(spec, spec.get("word"), 0.2, dur), WAIT)
    htm = f"""
<svg class="ab" style="left:190px;top:330px" width="700" height="700" viewBox="0 0 700 700">
 <circle cx="350" cy="350" r="290" fill="none" stroke="#1d2b55" stroke-width="64"/>
 <circle id="s{n}_arc" cx="350" cy="350" r="290" fill="none" stroke="{GOLD}" stroke-width="64" stroke-linecap="butt" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100" transform="rotate(-90 350 350)"/>
</svg>
<div id="s{n}_v" class="ab big" style="left:190px;top:555px;width:700px;font-size:170px;opacity:0">{_esc(spec.get('text', f'{pct:.0f}%'))}</div>
<div id="s{n}_l" class="ab lab" style="left:60px;top:1060px;width:960px;opacity:0">{_esc(spec.get('label', ''))}</div>"""
    js = [_fromto(f"#s{n}_arc", "strokeDashoffset:100", f"strokeDashoffset:{100 - pct:.1f}", t, 1.0, "power2.out"),
          _fromto(f"#s{n}_v", "opacity:0,scale:.8", "opacity:1,scale:1", t + 0.3, 0.5, "back.out(1.4)"),
          _fromto(f"#s{n}_l", "opacity:0,y:24", "opacity:1,y:0", t + 0.6, 0.45)]
    return htm, js


def _scene_timeline(n: int, spec: dict, dur: float) -> tuple[str, list[str]]:
    ev = (spec.get("events") or [])[:4]
    k = max(1, len(ev))
    active = int(spec.get("active", k - 1))
    times = _spread(spec, [e.get("word") for e in ev], dur, 0.12, 0.62)
    y = 650
    xs = [140 + (800 * j / max(1, k - 1)) if k > 1 else 540 for j in range(k)]
    htm = f'<div id="s{n}_ax" class="ab" style="left:100px;top:{y}px;width:880px;height:8px;background:{DIM};border-radius:4px;transform-origin:left center;transform:scaleX(0)"></div>'
    js = [_fromto(f"#s{n}_ax", "scaleX:0", "scaleX:1", 0.05, 0.7, "power2.out")]
    for j, e in enumerate(ev):
        col = GOLD if j == active else "#ffffff"
        up = j % 2 == 0
        htm += f"""
<div id="s{n}_d{j}" class="ab" style="left:{xs[j] - 22:.0f}px;top:{y - 18}px;width:44px;height:44px;border-radius:50%;background:{col};opacity:0"></div>
<div id="s{n}_y{j}" class="ab mid" style="left:{xs[j] - 200:.0f}px;top:{y - (250 if up else -90)}px;width:400px;opacity:0;font-size:112px;color:{col}">{_esc(e.get('year', ''))}</div>
<div id="s{n}_e{j}" class="ab lab" style="left:{xs[j] - 200:.0f}px;top:{y - (120 if up else -230)}px;width:400px;opacity:0;font-size:42px">{_esc(e.get('label', ''))}</div>"""
        js += [_fromto(f"#s{n}_d{j}", "opacity:0,scale:0", "opacity:1,scale:1", times[j], 0.4, "back.out(2)"),
               _fromto(f"#s{n}_y{j}", "opacity:0,y:30", "opacity:1,y:0", times[j] + 0.1, 0.45),
               _fromto(f"#s{n}_e{j}", "opacity:0", "opacity:1", times[j] + 0.25, 0.4)]
    return htm, js


def _scene_versus(n: int, spec: dict, dur: float) -> tuple[str, list[str]]:
    L, R = spec.get("left", {}), spec.get("right", {})
    t1, t2 = _spread(spec, [L.get("word"), R.get("word")], dur, 0.1, 0.5)[:2]
    htm = f"""
<svg class="ab" style="left:60px;top:300px" width="960" height="560" viewBox="0 0 960 560">
 <path id="s{n}_f" d="M40,380 L440,380" pathLength="1" stroke="{DIM}" stroke-width="18" stroke-linecap="round" fill="none" stroke-dasharray="1" stroke-dashoffset="1"/>
 <path id="s{n}_r" d="M520,420 C640,420 700,380 760,260 C810,160 860,100 920,40" pathLength="1" stroke="{GOLD}" stroke-width="22" stroke-linecap="round" fill="none" stroke-dasharray="1" stroke-dashoffset="1"/>
</svg>
<div id="s{n}_ll" class="ab lab" style="left:40px;top:900px;width:480px;opacity:0;color:{DIM}">{_esc(L.get('label'))}</div>
<div id="s{n}_ls" class="ab sub" style="left:50px;top:970px;width:460px;opacity:0">{_esc(L.get('sub'))}</div>
<div id="s{n}_rl" class="ab lab g" style="left:560px;top:900px;width:480px;opacity:0">{_esc(R.get('label'))}</div>
<div id="s{n}_rs" class="ab sub" style="left:570px;top:970px;width:460px;opacity:0">{_esc(R.get('sub'))}</div>"""
    js = [_fromto(f"#s{n}_f", "strokeDashoffset:1", "strokeDashoffset:0", t1, 0.6, "power2.out"),
          _fromto(f"#s{n}_r", "strokeDashoffset:1", "strokeDashoffset:0", t2, 0.9, "power2.out")]
    for sid, t in (("l", t1), ("r", t2)):
        js += [_fromto(f"#s{n}_{sid}l", "opacity:0,y:24", "opacity:1,y:0", t + 0.2, 0.45), _fromto(f"#s{n}_{sid}s", "opacity:0,y:24", "opacity:1,y:0", t + 0.4, 0.45)]
    return htm, js


def _scene_phrase(n: int, spec: dict, dur: float, tag: str = "") -> tuple[str, list[str]]:
    lines = spec.get("lines") or [spec.get("text", "")]
    hl = {h.upper() for h in spec.get("hl", [])}
    times = _spread(spec, [None] * len(lines), dur, 0.08, 0.6)
    size = 104 if len(lines) < 2 and len(str(lines[0])) < 26 else 88 if len(lines) < 3 else 72
    tagh = f'<div id="s{n}_tag" style="text-align:center;opacity:0;margin-bottom:34px"><span class="tag">{_esc(tag)}</span></div>' if tag else ""
    js = [_fromto(f"#s{n}_tag", "opacity:0,scale:.7", "opacity:1,scale:1", 0.1, 0.4, "back.out(2)")] if tag else []
    body = ""
    for j, line in enumerate(lines):
        words = "".join(f'<span class="w{" g" if re.sub(r"[^A-Z0-9$%]", "", w.upper()) in hl else ""}" style="margin:0 .16em">{_esc(w)}</span>' for w in str(line).split())
        body += f'<div id="s{n}_p{j}" class="cap" style="width:940px;font-size:{size}px;opacity:0">{words}</div>'
        js.append(_fromto(f"#s{n}_p{j}", "opacity:0,y:40", "opacity:1,y:0", times[j], 0.5))
    htm = f'<div class="ab" style="left:70px;top:{300 if tag else 380}px;width:940px;display:flex;flex-direction:column;align-items:center;gap:40px">{tagh}{body}</div>'
    return htm, js


def _scene_end(n: int, spec: dict, dur: float) -> tuple[str, list[str]]:
    t = min(_wat(spec, spec.get("word"), 0.05, dur), 0.8)
    htm = f"""
<div id="s{n}_q" class="ab cap g" style="left:60px;top:400px;width:960px;font-size:140px;line-height:1.05;opacity:0">{_esc(spec.get('text', ''))}</div>
<div id="s{n}_f" class="ab" style="left:0;top:880px;width:1080px;text-align:center;opacity:0"><span class="pill">FOLLOW</span></div>"""
    js = [_fromto(f"#s{n}_q", "opacity:0,scale:.85", "opacity:1,scale:1", t, 0.55, "back.out(1.5)"),
          _fromto(f"#s{n}_f", "opacity:0,y:40", "opacity:1,y:0", t + 0.9, 0.5, "back.out(1.6)"),
          f'tl.to("#s{n}_f",{{scale:1.06,duration:0.6,yoyo:true,repeat:3,ease:"sine.inOut"}},{t + 1.5 + _OFFSET:.3f});']
    return htm, js


BUILDERS = {"fork": _scene_fork, "stat": _scene_stat, "bars": _scene_bars, "ring": _scene_ring, "timeline": _scene_timeline,
            "versus": _scene_versus, "phrase": _scene_phrase, "end": _scene_end}


def choose(script: dict) -> dict[int, dict]:
    """A spec for every beat: its own `scene` when it has one, else a number card or a phrase card made from its callout."""
    from faceless.pipeline import cards
    out: dict[int, dict] = {}
    for i, b in enumerate(script["beats"]):
        sc = b.get("scene")
        if isinstance(sc, dict) and sc.get("type") in BUILDERS | {"catch": 0}:
            out[i] = {"kind": "explainer", **sc}
            continue
        num = cards.parse_number(b.get("callout", ""))
        call = (b.get("callout") or "").strip()
        out[i] = {"kind": "explainer", "type": "stat", "value": call.upper(), "label": ""} if num else {"kind": "explainer", "type": "phrase", "lines": [cards.key_phrase(b)]}
    return out


def _scene(n: int, t0: float, dur: float, spec: dict, last: bool) -> tuple[str, str]:
    global _OFFSET
    typ = spec.get("type", "phrase")
    _OFFSET = t0
    try:
        if typ == "catch":
            body, js = _scene_phrase(n, spec, dur, tag="THE CATCH")
        else:
            body, js = BUILDERS.get(typ, _scene_phrase)(n, spec, dur)
    finally:
        _OFFSET = 0.0
    first = n == 0
    show = f'tl.set("#sc{n}",{{opacity:1,x:0}},{t0:.3f});' if first else ""
    enter = "" if first else f'E("#sc{n}",{{opacity:0,x:140}},{{opacity:1,x:0}},{t0:.3f},0.4,"power3.out");'
    leave = "" if last else f'tl.to("#sc{n}",{{opacity:0,x:-140,duration:0.25,ease:"power2.in"}},{t0 + dur - 0.25:.3f});'
    return f'<div id="sc{n}" class="sc">{body}</div>', "\n".join([show, enter, *js, leave])


def build_project(root: Path, specs: list[tuple[int, dict, float]], fps: int, kicker: str = "QUIET MONEY") -> float:
    """Write the HyperFrames project; returns its duration. specs: (beat, spec, seconds). Scenes are placed one after another on the same drifting world."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    for f in ("Anton-Regular.ttf", "Montserrat-Black.ttf"):
        shutil.copy2(Paths.fonts / f, root / "assets" / f)
    scenes, js, t = [], [], 0.0
    for n, (_b, spec, dur) in enumerate(specs):
        h, j = _scene(n, t, dur, spec, n == len(specs) - 1)
        scenes.append(h)
        js.append(j)
        t += dur
    grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="1920" stroke="#26356b" stroke-width="2"/>' for x in range(0, 1900, 100)) + \
           "".join(f'<line x1="0" y1="{y}" x2="1900" y2="{y}" stroke="#26356b" stroke-width="2"/>' for y in range(0, 1920, 100))
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080, height=1920">
<script src="assets/gsap.min.js"></script>
<style>
@font-face{{font-family:"Anton";src:url("assets/Anton-Regular.ttf")}}
@font-face{{font-family:"MontserratBlack";src:url("assets/Montserrat-Black.ttf")}}
{CSS}</style></head>
<body>
<div id="root" data-composition-id="cards" data-start="0" data-duration="{t:.3f}" data-width="1080" data-height="1920" data-fps="{fps}">
<div id="bg"></div><div id="glow"></div>
<svg id="grid" viewBox="0 0 1900 1920">{grid}</svg>
<div id="prog"></div>
{"".join(scenes)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
const E = (s, f, o, at, d, e) => tl.fromTo(s, f, Object.assign({{ duration: d, ease: e || "power3.out" }}, o), at);
tl.fromTo("#grid", {{ x: 0 }}, {{ x: -420, duration: {t:.3f}, ease: "none" }}, 0);
tl.fromTo("#glow", {{ scale: 0.9, opacity: 0.8 }}, {{ scale: 1.25, opacity: 1, duration: {t:.3f}, ease: "sine.inOut" }}, 0);
tl.fromTo("#prog", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {t:.3f}, ease: "none" }}, 0);
{chr(10).join(js)}
window.__timelines = window.__timelines || {{}};
window.__timelines["cards"] = tl;
tl.seek(0);
</script></body></html>"""
    (root / "index.html").write_text(page, encoding="utf-8")
    (root / "meta.json").write_text(json.dumps({"id": "cards", "name": "cards"}), encoding="utf-8")
    (root / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}), encoding="utf-8")
    return t
