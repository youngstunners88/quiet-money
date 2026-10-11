"""The cast: characters and small stage sets drawn in code (inline SVG parts moved by GSAP), for the drawn series.

Penny is the brand's gold Q coin with a face, arms and legs. Her mouth opens on every spoken word (the voice's own word timings), she blinks, looks
around, cheers, panics and walks. The Fee Gremlin is the thing that eats the money. Stage templates put them to work on a beat: grow a stack, nibble it,
race two coins, point at a numbered step, walk through years, gasp. Scenes alternate template and colour so no two neighbours look alike.

Rules inherited from the card renderer (HyperFrames seeks to any frame, so a scene must be a pure function of time):
only `set`/`fromTo` tweens on opacity, x, y, scale, rotation, width, height, visibility and strokeDashoffset; no onUpdate; text escaped; nothing
important in the caption band (y 1070-1280). Characters live above it (y 360-1040) except in the hook scene, where the hook headline owns the top and
Penny sits below the band.
"""

from __future__ import annotations

import html
import math

# page palettes: (top, bottom, glow, ink, soft). Neighbouring scenes never share one.
PALS = [
    ("#0b1630", "#03060f", "#ff7a2f", "#ffffff", "rgba(255,255,255,.16)"),     # night navy
    ("#ffd23f", "#e9a800", "#fff3b0", "#14110a", "rgba(20,17,10,.16)"),         # brand gold
    ("#fbf4e3", "#e9dfc4", "#ffd23f", "#14110a", "rgba(20,17,10,.12)"),         # ledger paper
    ("#0e2118", "#04100a", "#35e0a1", "#ffffff", "rgba(255,255,255,.16)"),     # money green
    ("#2a0b10", "#0a0305", "#ff4d5e", "#ffffff", "rgba(255,255,255,.16)"),     # warning red
]
GOLD, GOLD_D, RIM = "#FFD23F", "#C99A00", "#8a6500"
INK = "#1b1405"


def part(pid: str, x: float, y: float, w: float, h: float, svg: str = "", style: str = "", origin: str = "50% 50%", vb: str | None = None) -> str:
    vb = vb or f"0 0 {w:g} {h:g}"
    inner = f'<svg width="{w:g}" height="{h:g}" viewBox="{vb}" style="overflow:visible">{svg}</svg>' if svg else ""
    return (f'<div class="cp" id="{pid}" style="left:{x:g}px;top:{y:g}px;width:{w:g}px;height:{h:g}px;transform-origin:{origin};{style}">{inner}</div>')


# ------------------------------------------------------------------ Penny: the coin
def penny(pid: str, x: float, y: float, scale: float = 1.0) -> tuple[str, dict]:
    """Returns (html, ids). Local size 400x520 at (x, y); `scale` is applied by the caller through the root part."""
    gid = f"{pid}g"
    body = (f'<defs><radialGradient id="{gid}" cx="40%" cy="32%" r="75%"><stop offset="0" stop-color="#fff0a0"/><stop offset="0.45" stop-color="{GOLD}"/>'
            f'<stop offset="1" stop-color="{GOLD_D}"/></radialGradient></defs>'
            f'<circle cx="200" cy="230" r="160" fill="{RIM}"/><circle cx="200" cy="230" r="148" fill="url(#{gid})"/>'
            f'<circle cx="200" cy="230" r="124" fill="none" stroke="#e0a800" stroke-width="5" opacity=".8"/>'
            f'<text x="200" y="138" text-anchor="middle" font-family="Anton" font-size="62" fill="{RIM}" opacity=".85">Q</text>')
    eyes = ('<ellipse cx="148" cy="212" rx="33" ry="40" fill="#fff"/><ellipse cx="252" cy="212" rx="33" ry="40" fill="#fff"/>')
    pupils = (f'<g id="{pid}pu"><circle cx="152" cy="216" r="17" fill="{INK}"/><circle cx="256" cy="216" r="17" fill="{INK}"/>'
              f'<circle cx="158" cy="209" r="6" fill="#fff"/><circle cx="262" cy="209" r="6" fill="#fff"/></g>')
    lids = (f'<g id="{pid}ey" style="visibility:hidden"><path d="M115 214 Q148 232 181 214" stroke="{INK}" stroke-width="9" fill="{GOLD}" stroke-linecap="round"/>'
            f'<path d="M219 214 Q252 232 285 214" stroke="{INK}" stroke-width="9" fill="{GOLD}" stroke-linecap="round"/></g>')
    brows = (f'<g id="{pid}br"><path d="M112 160 Q146 142 182 160" stroke="{INK}" stroke-width="10" fill="none" stroke-linecap="round"/>'
             f'<path d="M218 160 Q254 142 288 160" stroke="{INK}" stroke-width="10" fill="none" stroke-linecap="round"/></g>')
    cheeks = '<circle cx="104" cy="286" r="20" fill="#ff8f6b" opacity=".55"/><circle cx="296" cy="286" r="20" fill="#ff8f6b" opacity=".55"/>'
    m_closed = f'<g id="{pid}m0"><path d="M152 292 Q200 330 248 292" stroke="{INK}" stroke-width="10" fill="none" stroke-linecap="round"/></g>'
    m_open = (f'<g id="{pid}m1" style="visibility:hidden"><path d="M146 290 Q200 372 254 290 Z" fill="{INK}"/>'
              f'<path d="M168 330 Q200 350 232 330 Q200 318 168 330Z" fill="#ff6b6b"/></g>')
    m_half = (f'<g id="{pid}m2" style="visibility:hidden"><ellipse cx="200" cy="312" rx="30" ry="17" fill="{INK}"/></g>')
    m_o = (f'<g id="{pid}m3" style="visibility:hidden"><ellipse cx="200" cy="326" rx="24" ry="36" fill="{INK}"/></g>')
    sweat = (f'<g id="{pid}sw" style="visibility:hidden"><path d="M338 120 Q352 150 338 164 Q324 150 338 120Z" fill="#7cd4ff" stroke="#2d8fc4" stroke-width="3"/></g>')
    face = body + eyes + pupils + lids + brows + cheeks + m_closed + m_open + m_half + m_o + sweat
    limb = lambda x1, y1, x2, y2: f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>'
    leg = lambda: (limb(24, 10, 24, 84) + f'<ellipse cx="38" cy="96" rx="34" ry="15" fill="{INK}"/>')
    arm = lambda s: (f'<path d="M30 8 Q{30 + s * 36} 70 {30 + s * 10} 130" stroke="{INK}" stroke-width="16" stroke-linecap="round" fill="none"/>'
                     f'<circle cx="{30 + s * 10}" cy="138" r="21" fill="#fff" stroke="{INK}" stroke-width="6"/>')
    out = (part(f"{pid}lgL", 112, 372, 76, 110, leg(), origin="32% 6%") + part(f"{pid}lgR", 212, 372, 76, 110, leg(), origin="32% 6%")
           + part(f"{pid}bd", 0, 0, 400, 520, face, origin="50% 44%")
           + part(f"{pid}aL", 6, 236, 70, 160, arm(1), origin="43% 5%") + part(f"{pid}aR", 324, 236, 70, 160, arm(-1), origin="43% 5%"))
    root = part(pid, x, y, 400, 520, "", style="", origin="50% 100%")
    return root.replace("</div>", out + "</div>", 1), {k: f"{pid}{k}" for k in ("lgL", "lgR", "aL", "aR", "bd", "pu", "ey", "br", "m0", "m1", "m2", "m3", "sw")}


# ------------------------------------------------------------------ the Fee Gremlin
def gremlin(pid: str, x: float, y: float) -> tuple[str, dict]:
    spikes = " ".join(f"{200 + (150 if k % 2 == 0 else 112) * math.cos(math.radians(k * 15 - 90)):.0f},{210 + (150 if k % 2 == 0 else 112) * math.sin(math.radians(k * 15 - 90)):.0f}"
                      for k in range(24))
    body = (f'<polygon points="{spikes}" fill="#b3203a" stroke="#5c0d1c" stroke-width="8" stroke-linejoin="round"/>'
            f'<circle cx="200" cy="230" r="96" fill="#d63a55"/>'
            f'<ellipse cx="156" cy="196" rx="30" ry="34" fill="#ffe86b"/><ellipse cx="244" cy="196" rx="30" ry="34" fill="#ffe86b"/>'
            f'<circle cx="160" cy="202" r="12" fill="#2a0610"/><circle cx="240" cy="202" r="12" fill="#2a0610"/>'
            f'<path d="M118 150 L184 176 M282 150 L216 176" stroke="#2a0610" stroke-width="12" stroke-linecap="round"/>'
            f'<text x="200" y="130" text-anchor="middle" font-family="Anton" font-size="46" fill="#ffe86b">%</text>')
    jaw = ('<path d="M96 0 Q160 80 224 0 Z" fill="#2a0610"/>'
           '<path d="M112 0 L126 38 L140 0Z M180 0 L194 38 L208 0Z" fill="#fff"/>')
    out = part(f"{pid}bd", 0, 0, 400, 420, body, origin="50% 55%") + part(f"{pid}jw", 104, 252, 224, 90, jaw, origin="50% 0%")
    root = part(pid, x, y, 400, 420, "", origin="50% 100%", style="opacity:0")
    return root.replace("</div>", out + "</div>", 1), {k: f"{pid}{k}" for k in ("bd", "jw")}


def coin(pid: str, x: float, y: float, d: float = 150) -> str:
    return part(pid, x, y, d, d * 0.62,
                f'<ellipse cx="{d / 2}" cy="{d * 0.43}" rx="{d / 2 - 3}" ry="{d * 0.19}" fill="{RIM}"/>'
                f'<rect x="3" y="{d * 0.24}" width="{d - 6}" height="{d * 0.19}" fill="{GOLD_D}"/>'
                f'<ellipse cx="{d / 2}" cy="{d * 0.24}" rx="{d / 2 - 3}" ry="{d * 0.19}" fill="{GOLD}" stroke="{RIM}" stroke-width="4"/>'
                f'<ellipse cx="{d / 2}" cy="{d * 0.24}" rx="{d / 2 - 28}" ry="{d * 0.11}" fill="none" stroke="#e0a800" stroke-width="3"/>',
                style="opacity:0")


# ------------------------------------------------------------------ timeline helpers
def tw(sel: str, a: dict, b: dict, t: float, dur: float = 0.4, ease: str = "power2.out") -> str:
    fa = ",".join(f"{k}:{v!r}" if isinstance(v, str) else f"{k}:{v:g}" for k, v in a.items())
    fb = ",".join(f"{k}:{v!r}" if isinstance(v, str) else f"{k}:{v:g}" for k, v in b.items())
    return f'tl.fromTo("#{sel}",{{{fa}}},{{{fb},duration:{dur:.3f},ease:"{ease}"}},{t:.3f});'


def st(sel: str, props: str, t: float) -> str:
    return f'tl.set("#{sel}",{{{props}}},{t:.3f});'


def talk(ids: dict, words: list[tuple[float, float]], t0: float, dur: float, mood: str = "happy") -> list[str]:
    """Mouth open on every word (alternating wide and half so it does not read as a metronome), shut between; blinks every couple of seconds."""
    js = []
    for k, (a, b) in enumerate(words):
        if a >= dur - 0.05:
            break
        kind = "m1" if (k % 3 != 1) else "m2"
        js += [st(ids["m0"], "visibility:'hidden'", t0 + a), st(ids[kind], "visibility:'visible'", t0 + a),
               st(ids[kind], "visibility:'hidden'", t0 + min(b, dur - 0.02)), st(ids["m0"], "visibility:'visible'", t0 + min(b, dur - 0.02))]
    b = 0.9 + (len(words) % 3) * 0.3
    while b < dur - 0.3:
        js += [st(ids["ey"], "visibility:'visible'", t0 + b), st(ids["pu"], "visibility:'hidden'", t0 + b),
               st(ids["ey"], "visibility:'hidden'", t0 + b + 0.13), st(ids["pu"], "visibility:'visible'", t0 + b + 0.13)]
        b += 2.1 + (int(b * 10) % 5) * 0.2
    return js


def bob(sel: str, t0: float, dur: float, amp: float = 14, period: float = 0.9, y0: float = 0) -> list[str]:
    js, t, up = [], 0.0, True
    while t < dur - 0.05:
        seg = min(period / 2, dur - t)
        js.append(tw(sel, {"y": y0 + (0 if up else -amp)}, {"y": y0 + (-amp if up else 0)}, t0 + t, seg, "sine.inOut"))
        t += seg
        up = not up
    return js


def enter(sel: str, t: float, frm: dict | None = None) -> str:
    frm = frm or {"y": 380, "scale": 0.5, "opacity": 0}
    return tw(sel, frm, {"y": 0, "scale": 1, "opacity": 1}, t, 0.5, "back.out(1.6)")


def fmt(v: float, dec: int = 0) -> str:
    return f"{v:,.{dec}f}"


def counter(sid: str, value: float, pre: str, suf: str, dec: int, t0: float, dur: float, size: int, color: str = "") -> tuple[str, list[str]]:
    steps = max(8, min(40, round(dur * 12)))
    spans, js = [], []
    for s in range(steps + 1):
        p = s / steps
        v = value * (1 - (1 - p) ** 3) if s < steps else value
        spans.append(f'<span class="cn" id="{sid}n{s}" style="font-size:{size}px;{color}">{html.escape(pre + fmt(v, dec) + suf)}</span>')
        a = t0 + 0.15 + (dur * 0.6) * s / (steps + 1)
        js += [st(f"{sid}n{s}", "visibility:'hidden'", t0), st(f"{sid}n{s}", "visibility:'visible'", a)]
        if s < steps:
            js.append(st(f"{sid}n{s}", "visibility:'hidden'", t0 + 0.15 + (dur * 0.6) * (s + 1) / (steps + 1)))
    return f'<div class="cw" style="height:{size}px">{"".join(spans)}</div>', js


def label(sid: str, text: str, t: float, size: int = 74, top: int = 1560, hi: bool = False) -> tuple[str, list[str]]:
    mark = '<div class="hl" id="%shl"></div>' % sid if hi else ""
    h = f'<div class="lb" id="{sid}lb" style="top:{top}px;font-size:{size}px">{mark}<span>{html.escape(text)}</span></div>'
    js = [tw(f"{sid}lb", {"opacity": 0, "y": 40}, {"opacity": 1, "y": 0}, t, 0.4)]
    if hi:
        js.append(tw(f"{sid}hl", {"scaleX": 0}, {"scaleX": 1}, t + 0.15, 0.5, "power3.out"))
    return h, js


# ------------------------------------------------------------------ stage templates: each returns (html, js)
def _floaters(sid: str, t0: float, dur: float, n: int = 9, glyph: str = "$") -> tuple[str, list[str]]:
    h, js = [], []
    for k in range(n):
        x, y = (k * 211 + 70) % 980, 380 + (k * 317) % 1100
        h.append(f'<div class="fl" id="{sid}f{k}" style="left:{x}px;top:{y}px;font-size:{50 + (k % 3) * 18}px">{glyph}</div>')
        js.append(tw(f"{sid}f{k}", {"y": 0, "opacity": 0, "rotation": -12}, {"y": -150 - k * 12, "opacity": 0.22, "rotation": 12}, t0 + (k % 4) * 0.1, dur, "sine.inOut"))
    return "".join(h), js


def stage_hero(sid, t0, dur, spec, words, hook=False):
    """Penny says the beat. In the hook she sits below the caption band and the headline owns the top."""
    y = 1320 if hook else 420
    p, ids = penny(f"{sid}p", 340, y)
    big = 1.15 if hook else 1.0
    js = [tw(f"{sid}p", {"y": 380, "scale": 0.5, "opacity": 0}, {"y": 0, "scale": big, "opacity": 1}, t0 + 0.05, 0.5, "back.out(1.6)")]
    js += bob(f"{sid}bd", t0 + 0.6, dur - 0.6, 12) + talk(ids, words, t0, dur)
    js += [tw(ids["aL"], {"rotation": 10}, {"rotation": -28}, t0 + 0.6, 0.45, "sine.inOut"), tw(ids["aR"], {"rotation": -10}, {"rotation": 28}, t0 + 0.6, 0.45, "sine.inOut")]
    js += [tw(ids["pu"], {"x": 0}, {"x": 10}, t0 + 0.8, 0.5, "sine.inOut"), tw(ids["pu"], {"x": 10}, {"x": -10}, t0 + 1.5, 0.6, "sine.inOut")]
    h, jl = "", []
    if not hook and spec.get("text"):
        h, jl = label(sid, spec["text"], t0 + 0.35, 96 if len(spec["text"]) < 22 else 78, 1330, hi=True)
    fh, fj = _floaters(sid, t0, dur)
    return fh + p + h, js + jl + fj


def stage_stack(sid, t0, dur, spec, words):
    """The number counts up while coins drop onto a stack and Penny cheers."""
    n = spec["num"]
    coins = min(9, max(5, int(math.log10(max(10, n["value"])) * 2)))
    h, js = [], []
    for k in range(coins):
        cx = 520 + (k % 2) * 6
        cy = 880 - k * 56
        h.append(coin(f"{sid}c{k}", cx, cy, 190))
        js.append(tw(f"{sid}c{k}", {"y": -700, "opacity": 0, "rotation": -20 + k % 3 * 20}, {"y": 0, "opacity": 1, "rotation": 0}, t0 + 0.25 + k * dur * 0.5 / coins, 0.42, "bounce.out"))
    p, ids = penny(f"{sid}p", 50, 520)
    js += [tw(f"{sid}p", {"x": -460, "opacity": 0, "scale": 0.8}, {"x": 0, "opacity": 1, "scale": 0.8}, t0 + 0.05, 0.5, "back.out(1.4)")]
    js += talk(ids, words, t0, dur)
    js += [tw(ids["aL"], {"rotation": 10}, {"rotation": 150}, t0 + dur * 0.5, 0.35, "back.out(2)"), tw(ids["aR"], {"rotation": -10}, {"rotation": -150}, t0 + dur * 0.5, 0.35, "back.out(2)")]
    js += bob(f"{sid}bd", t0 + dur * 0.5, dur * 0.5, 22, 0.5)
    js += [st(ids["br"], "y:-16", t0 + dur * 0.5)]
    num, nj = counter(sid, n["value"], n["prefix"], n["suffix"], n["decimals"], t0, dur, min(250, int(930 / (max(3, len(fmt(n["value"], n["decimals"]) + n["prefix"] + n["suffix"])) * 0.47))))
    lab, lj = label(sid, n.get("label") or "", t0 + 0.5, 70, 1680, hi=True) if n.get("label") else ("", [])
    box = f'<div class="nb" style="top:1330px">{num}</div>'
    js += nj + lj + [tw(f"{sid}nb", {"scale": 0.8, "opacity": 0.3}, {"scale": 1, "opacity": 1}, t0, 0.45, "back.out(1.6)")]
    fh, fj = _floaters(sid, t0, dur, 8)
    return fh + "".join(h) + p + box.replace('class="nb"', f'class="nb" id="{sid}nb"') + lab, js + fj


def stage_fee(sid, t0, dur, spec, words):
    """The Fee Gremlin jumps in and eats the coin stack; Penny panics."""
    coins = 8
    h, js = [], []
    for k in range(coins):
        h.append(coin(f"{sid}c{k}", 540 + (k % 2) * 6, 900 - k * 54, 190))
        js.append(tw(f"{sid}c{k}", {"y": -600, "opacity": 0}, {"y": 0, "opacity": 1}, t0 + 0.1 + k * 0.07, 0.35, "bounce.out"))
        gone = t0 + dur * 0.35 + (coins - 1 - k) * dur * 0.5 / coins
        js.append(tw(f"{sid}c{k}", {"scale": 1, "opacity": 1, "x": 0}, {"scale": 0.2, "opacity": 0, "x": -140}, gone, 0.3, "power3.in"))
    g, gi = gremlin(f"{sid}g", 600, 590)
    js += [tw(f"{sid}g", {"x": 520, "y": -200, "opacity": 0, "scale": 0.5}, {"x": 0, "y": 0, "opacity": 1, "scale": 1}, t0 + dur * 0.28, 0.45, "back.out(1.8)")]
    k = 0
    while t0 + dur * 0.4 + k * 0.32 < t0 + dur - 0.2:
        js.append(tw(gi["jw"], {"rotation": 0}, {"rotation": -26}, t0 + dur * 0.4 + k * 0.32, 0.16, "power1.inOut"))
        js.append(tw(gi["jw"], {"rotation": -26}, {"rotation": 0}, t0 + dur * 0.4 + k * 0.32 + 0.16, 0.16, "power1.inOut"))
        k += 1
    js += bob(gi["bd"], t0 + dur * 0.5, dur * 0.5, 16, 0.4)
    p, ids = penny(f"{sid}p", 50, 520)
    js += [tw(f"{sid}p", {"x": -440, "opacity": 0, "scale": 0.8}, {"x": 0, "opacity": 1, "scale": 0.8}, t0 + 0.05, 0.5, "back.out(1.4)")]
    js += talk(ids, words, t0, dur * 0.4)
    panic = t0 + dur * 0.4
    js += [st(ids["m0"], "visibility:'hidden'", panic), st(ids["m3"], "visibility:'visible'", panic), st(ids["sw"], "visibility:'visible'", panic),
           tw(ids["br"], {"y": 0}, {"y": -22}, panic, 0.2), tw(ids["aL"], {"rotation": 10}, {"rotation": 130}, panic, 0.25, "back.out(2)"),
           tw(ids["aR"], {"rotation": -10}, {"rotation": -130}, panic, 0.25, "back.out(2)")]
    j = 0
    while panic + j * 0.14 < t0 + dur - 0.15:
        js.append(tw(f"{sid}bd", {"x": -9 if j % 2 == 0 else 9}, {"x": 9 if j % 2 == 0 else -9}, panic + j * 0.14, 0.14, "none"))
        j += 1
    n = spec.get("num")
    text = spec.get("text") or (n["prefix"] + fmt(n["value"], n["decimals"]) + n["suffix"] if n else "")
    lab, lj = label(sid, text, t0 + 0.3, 110 if len(text) < 12 else 84, 1400, hi=True)
    fh, fj = _floaters(sid, t0, dur, 8, "%")
    return fh + "".join(h) + p + g + lab, js + lj + fj


def stage_race(sid, t0, dur, spec, words):
    """Two coins race along two lanes to lengths set by the two amounts."""
    c = spec["cmp"]
    hi = max(c["va"], c["vb"])
    la = 0.4 + 0.6 * c["va"] / hi
    lb = 0.4 + 0.6 * c["vb"] / hi
    h, js, first = [], [], None
    for k, (name, frac, y, col) in enumerate(((c["a"], la, 470, GOLD), (c["b"], lb, 760, "#9aa3b2"))):
        h.append(f'<div class="ln2" style="top:{y + 190}px"></div>')
        p, ids = penny(f"{sid}r{k}", 20, y - 120)
        first = first or ids
        h.append(p)
        js.append(tw(f"{sid}r{k}", {"x": 0, "scale": 0.55, "opacity": 0}, {"x": 0, "scale": 0.55, "opacity": 1}, t0, 0.2))
        js.append(tw(f"{sid}r{k}", {"x": 0, "scale": 0.55}, {"x": 430 * frac, "scale": 0.55}, t0 + 0.4, dur * 0.55, "power2.inOut"))
        js += [tw(ids["lgL"], {"rotation": 25}, {"rotation": -25}, t0 + 0.4 + q * 0.2, 0.2, "none") for q in range(int(dur * 0.55 / 0.2))]
        js += [tw(ids["lgR"], {"rotation": -25}, {"rotation": 25}, t0 + 0.4 + q * 0.2, 0.2, "none") for q in range(int(dur * 0.55 / 0.2))]
        h.append(f'<div class="rv" id="{sid}v{k}" style="top:{y + 20}px;left:520px;color:{col if k == 0 else "var(--ink)"}">{html.escape(name)}</div>')
        js.append(tw(f"{sid}v{k}", {"opacity": 0, "x": 40}, {"opacity": 1, "x": 0}, t0 + 0.5 + dur * 0.5 + k * 0.15, 0.4))
    lab, lj = label(sid, spec.get("text", "") or "WHO WINS?", t0 + 0.3, 90, 1400, hi=True)
    js += talk(first, words, t0, dur)
    fh, fj = _floaters(sid, t0, dur, 6)
    return fh + "".join(h) + lab, js + lj + fj


def stage_step(sid, t0, dur, spec, words):
    """Penny points at a numbered board."""
    s = spec["step"]
    circ = round(2 * math.pi * 150)
    board = (f'<div class="bd2" id="{sid}b" style="left:470px;top:430px;width:520px;height:560px">'
             f'<svg width="520" height="560" viewBox="0 0 520 560"><rect x="8" y="8" width="504" height="544" rx="34" fill="rgba(0,0,0,.18)" stroke="var(--ink)" stroke-width="8"/>'
             f'<circle cx="260" cy="230" r="150" fill="none" stroke="var(--soft)" stroke-width="16"/>'
             f'<circle id="{sid}o" cx="260" cy="230" r="150" fill="none" stroke="{GOLD}" stroke-width="16" stroke-linecap="round" stroke-dasharray="{circ}" '
             f'stroke-dashoffset="{circ}" transform="rotate(-90 260 230)"/></svg><div class="rn2">{s["n"]}</div>'
             f'<div class="sw2">STEP {html.escape(s["word"])}</div></div>')
    p, ids = penny(f"{sid}p", 40, 520)
    js = [tw(f"{sid}p", {"x": -420, "opacity": 0, "scale": 0.82}, {"x": 0, "opacity": 1, "scale": 0.82}, t0 + 0.05, 0.5, "back.out(1.4)"),
          tw(f"{sid}b", {"scale": 0.4, "opacity": 0, "rotation": -8}, {"scale": 1, "opacity": 1, "rotation": 0}, t0 + 0.2, 0.5, "back.out(1.7)"),
          tw(f"{sid}o", {"strokeDashoffset": circ}, {"strokeDashoffset": 0}, t0 + 0.5, dur * 0.55, "power2.inOut"),
          tw(ids["aR"], {"rotation": -10}, {"rotation": -105}, t0 + 0.5, 0.4, "back.out(1.6)")]
    js += [tw(ids["aR"], {"rotation": -105}, {"rotation": -90}, t0 + 0.9, 0.5, "sine.inOut")] + talk(ids, words, t0, dur) + bob(f"{sid}bd", t0 + 0.6, dur - 0.6, 10)
    js += [tw(ids["pu"], {"x": 0}, {"x": 14}, t0 + 0.5, 0.3)]
    lab, lj = label(sid, s.get("gist", ""), t0 + 0.6, 66, 1380, hi=False)
    fh, fj = _floaters(sid, t0, dur, 6, "✓")
    return fh + p + board + lab, js + lj + fj


def stage_years(sid, t0, dur, spec, words):
    """Penny walks along a path while the years count up."""
    n = spec["num"]
    p, ids = penny(f"{sid}p", 40, 500)
    steps = max(4, int(dur * 5))
    js = [tw(f"{sid}p", {"x": 0, "scale": 0.8, "opacity": 0}, {"x": 0, "scale": 0.8, "opacity": 1}, t0, 0.2),
          tw(f"{sid}p", {"x": 0}, {"x": 520}, t0 + 0.3, dur * 0.7, "none")]
    js += [tw(ids["lgL"], {"rotation": 30}, {"rotation": -30}, t0 + 0.3 + q * 0.25, 0.25, "none") for q in range(int(dur * 0.7 / 0.25))]
    js += [tw(ids["lgR"], {"rotation": -30}, {"rotation": 30}, t0 + 0.3 + q * 0.25, 0.25, "none") for q in range(int(dur * 0.7 / 0.25))]
    js += talk(ids, words, t0, dur) + bob(f"{sid}bd", t0 + 0.3, dur * 0.7, 10, 0.5)
    path = f'<div class="pth" id="{sid}pt"></div>'
    flags = "".join(f'<div class="fg" id="{sid}fg{k}" style="left:{140 + k * 190}px">{k * (int(n["value"]) // 4 or 1)}</div>' for k in range(5))
    js += [tw(f"{sid}pt", {"scaleX": 0}, {"scaleX": 1}, t0 + 0.1, dur * 0.75, "none")]
    js += [tw(f"{sid}fg{k}", {"opacity": 0, "y": 30}, {"opacity": 1, "y": 0}, t0 + 0.3 + dur * 0.7 * k / 4, 0.3) for k in range(5)]
    num, nj = counter(sid, n["value"], "", "", 0, t0, dur, 260)
    lab, lj = label(sid, (n.get("label") or "YEARS"), t0 + 0.5, 84, 1690, hi=True)
    fh, fj = _floaters(sid, t0, dur, 6, "⏳")
    box = f'<div class="nb" id="{sid}nb" style="top:1330px">{num}</div>'
    return fh + path + flags + p + box + lab, js + nj + lj + fj + [tw(f"{sid}nb", {"scale": 0.8, "opacity": 0.3}, {"scale": 1, "opacity": 1}, t0, 0.4, "back.out(1.6)")]


def stage_shock(sid, t0, dur, spec, words):
    """Penny gasps at the beat's key phrase."""
    p, ids = penny(f"{sid}p", 340, 430)
    shake = t0 + 0.35
    js = [tw(f"{sid}p", {"y": 380, "scale": 0.5, "opacity": 0}, {"y": 0, "scale": 1.12, "opacity": 1}, t0 + 0.05, 0.4, "back.out(2)"),
          st(ids["m0"], "visibility:'hidden'", shake), st(ids["m3"], "visibility:'visible'", shake), st(ids["sw"], "visibility:'visible'", shake + 0.3),
          tw(ids["br"], {"y": 0}, {"y": -24}, shake, 0.2), tw(ids["aL"], {"rotation": 10}, {"rotation": 120}, shake, 0.25, "back.out(2)"),
          tw(ids["aR"], {"rotation": -10}, {"rotation": -120}, shake, 0.25, "back.out(2)")]
    j = 0
    while shake + j * 0.12 < t0 + dur * 0.55:
        js.append(tw(f"{sid}bd", {"x": -8 if j % 2 == 0 else 8}, {"x": 8 if j % 2 == 0 else -8}, shake + j * 0.12, 0.12, "none"))
        j += 1
    js += [st(ids["m3"], "visibility:'hidden'", t0 + dur * 0.55), st(ids["m0"], "visibility:'visible'", t0 + dur * 0.55)]
    js += talk(ids, [w for w in words if w[0] > dur * 0.55], t0, dur)
    lab, lj = label(sid, spec.get("text", ""), t0 + 0.3, 104 if len(spec.get("text", "")) < 18 else 80, 1340, hi=True)
    fh, fj = _floaters(sid, t0, dur, 8, "!")
    return fh + p + lab, js + lj + fj


def stage_think(sid, t0, dur, spec, words):
    """Penny thinks: pupils up, a thought cloud grows with the phrase inside."""
    p, ids = penny(f"{sid}p", 340, 700)
    text = html.escape(spec.get("text", ""))
    cloud = (f'<div class="cl" id="{sid}cl" style="left:90px;top:360px;width:900px;height:300px"><svg width="900" height="300" viewBox="0 0 900 300">'
             f'<ellipse cx="450" cy="150" rx="430" ry="130" fill="var(--ink)" opacity=".95"/></svg><div class="ct" style="color:var(--bgc)">{text}</div></div>'
             f'<div class="cd" id="{sid}d1" style="left:520px;top:640px;width:46px;height:46px"></div><div class="cd" id="{sid}d2" style="left:490px;top:700px;width:30px;height:30px"></div>')
    js = [tw(f"{sid}p", {"y": 300, "opacity": 0, "scale": 0.7}, {"y": 0, "opacity": 1, "scale": 0.9}, t0 + 0.05, 0.45, "back.out(1.6)"),
          tw(f"{sid}d2", {"scale": 0, "opacity": 0}, {"scale": 1, "opacity": 1}, t0 + 0.4, 0.25, "back.out(2)"), tw(f"{sid}d1", {"scale": 0, "opacity": 0}, {"scale": 1, "opacity": 1}, t0 + 0.55, 0.25, "back.out(2)"),
          tw(f"{sid}cl", {"scale": 0.2, "opacity": 0}, {"scale": 1, "opacity": 1}, t0 + 0.7, 0.55, "back.out(1.5)"),
          tw(ids["pu"], {"x": 0, "y": 0}, {"x": 8, "y": -26}, t0 + 0.3, 0.3), tw(ids["aR"], {"rotation": -10}, {"rotation": -150}, t0 + 0.4, 0.4, "back.out(1.5)")]
    js += talk(ids, words, t0, dur) + bob(f"{sid}bd", t0 + 0.6, dur - 0.6, 10)
    fh, fj = _floaters(sid, t0, dur, 6, "?")
    return fh + cloud + p, js + fj


def stage_sign(sid, t0, dur, spec, words):
    """Penny holds up a sign with the phrase: it swings in, she points."""
    p, ids = penny(f"{sid}p", 60, 520)
    words_ = spec.get("text", "").split()
    text = html.escape(" ".join(words_[:5]))            # a board holds five words
    size = 78 if len(words_[:5]) <= 3 else 56
    sign = (f'<div class="sg" id="{sid}sg" style="left:480px;top:430px;width:520px;height:480px;transform-origin:50% 0%"><div class="post"></div>'
            f'<div class="brd"><div class="bt" style="font-size:{size}px">{text}</div></div></div>')
    js = [tw(f"{sid}p", {"x": -420, "opacity": 0, "scale": 0.82}, {"x": 0, "opacity": 1, "scale": 0.82}, t0 + 0.05, 0.5, "back.out(1.4)"),
          tw(f"{sid}sg", {"rotation": -35, "opacity": 0, "y": -140}, {"rotation": 0, "opacity": 1, "y": 0}, t0 + 0.3, 0.7, "bounce.out"),
          tw(ids["aR"], {"rotation": -10}, {"rotation": -100}, t0 + 0.7, 0.4, "back.out(1.6)"), tw(ids["pu"], {"x": 0}, {"x": 14}, t0 + 0.6, 0.3)]
    js += talk(ids, words, t0, dur) + bob(f"{sid}bd", t0 + 0.7, dur - 0.7, 9)
    fh, fj = _floaters(sid, t0, dur, 6, "$")
    return fh + p + sign, js + fj


TEMPLATES = {"think": stage_think, "sign": stage_sign, "hero": stage_hero, "stack": stage_stack, "fee": stage_fee, "race": stage_race, "step": stage_step, "years": stage_years, "shock": stage_shock}
FEE_WORDS = ("FEE", "COST", "TAX", "DEBT", "INTEREST", "DRAIN", "LOSS", "LOSE", "TRAP", "CHARGE", "INFLATION", "MINIMUM")


def _phrase(beat: dict, call: str) -> str:
    """What a scene writes in big type: the callout, else the first eight spoken words (a drawn series has room for a fuller line than a card)."""
    if call:
        return call.upper()
    words = [w for w in beat.get("say", "").replace("\u2014", " ").split() if w]
    return " ".join(words[:8]).upper().rstrip(".,;:!?")


def choose(script: dict, pillar_id: str = "ledger") -> dict[int, dict]:
    """Template and colour for every beat. Numbers get a number stage, comparisons a race, STEP n a board, '… YEARS' a walk, money-draining words
    the gremlin; the rest alternate between Penny talking and Penny gasping. No two neighbours share a template or a colour."""
    from faceless.pipeline import cards
    out: dict[int, dict] = {}
    last_tpl, last_pal = None, -1
    rot = ["hero", "think", "shock", "sign"]
    fees = 0
    for i, beat in enumerate(script["beats"]):
        call = (beat.get("callout") or "").strip()
        num = cards.parse_number(call)
        cmp_ = cards.parse_compare(call)
        stp = cards.parse_step(call, beat.get("say", ""))
        text = _phrase(beat, call)
        say_up = beat.get("say", "").upper()
        if i == 0:
            tpl, spec = "hero", {"text": ""}
        elif stp:
            tpl, spec = "step", {"step": stp}
        elif cmp_ and cmp_["numeric"]:
            tpl, spec = "race", {"cmp": cmp_, "text": text if not call else ""}
        elif num and "YEAR" in (num.get("label") or "") and not num["static"]:
            tpl, spec = "years", {"num": num}
        elif num and not num["static"] and any(w in say_up for w in FEE_WORDS) and fees < 2:
            tpl, spec = "fee", {"num": num, "text": call.upper()}
            fees += 1
        elif num and not num["static"]:
            tpl, spec = "stack", {"num": num, "text": text}
        elif any(w in say_up for w in FEE_WORDS) and fees < 2:
            tpl, spec = "fee", {"text": text}
            fees += 1
        else:
            tpl, spec = rot[i % len(rot)], {"text": text}
        if tpl == last_tpl:
            tpl = rot[(rot.index(tpl) + 1) % len(rot)] if tpl in rot else "hero"
            spec = {"text": text}
        pal = (i * 2 + 1) % len(PALS)
        if pal == last_pal:
            pal = (pal + 1) % len(PALS)
        if tpl == "hero" and i == 0:
            pal = 0
        out[i] = {"kind": "stage", "tpl": tpl, "pal": pal, **spec}
        last_tpl, last_pal = tpl, pal
    return out


def build(sid: str, t0: float, dur: float, spec: dict) -> tuple[str, list[str], tuple]:
    """(html, js, palette) for one stage scene. spec['words'] = [(start, end)] relative to the scene start (the voice's word timings)."""
    words = spec.get("words", [])
    fn = TEMPLATES[spec["tpl"]]
    if spec["tpl"] == "hero":
        h, js = stage_hero(sid, t0, dur, spec, words, hook=spec.get("hook", False))
    else:
        h, js = fn(sid, t0, dur, spec, words)
    belt = "".join(coin(f"{sid}bc{k}", 40 + k * 190, 1830, 90) for k in range(7))
    for k in range(7):
        js.append(tw(f"{sid}bc{k}", {"x": 0, "opacity": 0.85}, {"x": -190, "opacity": 0.85}, t0, dur, "none"))
    h = h + belt
    swipe = f'<div class="sw0" id="{sid}sw0"></div>'
    js.append(tw(f"{sid}sw0", {"x": -1200}, {"x": 1300}, t0, 0.45, "power2.inOut"))
    js.append(tw(f"{sid}w", {"scale": 1.0}, {"scale": 1.07}, t0, dur, "none"))
    world = f'<div class="wd" id="{sid}w">{h}</div>'
    return world + swipe, js, PALS[spec["pal"] % len(PALS)]


CSS = """
.cp{position:absolute}
.wd{position:absolute;inset:0;transform-origin:50% 38%}
.cn{position:absolute;left:0;width:1080px;top:0;text-align:center;font:400 250px/1 "Anton";color:var(--ink);letter-spacing:-3px;visibility:hidden}
.cw{position:relative}
.nb{position:absolute;left:0;width:1080px;opacity:0}
.lb{position:absolute;left:60px;width:960px;text-align:center;font:400 74px/1.05 "Anton";letter-spacing:5px;color:var(--ink);opacity:0;text-transform:uppercase}
.lb span{position:relative;z-index:2}
.hl{position:absolute;left:12%;right:12%;bottom:-26px;height:20px;background:#FFD23F;opacity:.95;border-radius:11px;transform-origin:left center;z-index:1}
.fl{position:absolute;font:400 60px/1 "Anton";color:var(--ink);opacity:0}
.ln2{position:absolute;left:60px;width:960px;height:8px;background:var(--soft);border-radius:4px}
.rv{position:absolute;font:400 100px/1 "Anton";letter-spacing:-1px;opacity:0}
.sw0{position:absolute;left:0;top:0;width:1080px;height:1920px;background:linear-gradient(100deg,transparent 0,#FFD23F 35%,#FFD23F 65%,transparent 100%);opacity:.95;transform:translateX(-1200px)}
.bd2{position:absolute;opacity:0}
.rn2{position:absolute;left:0;right:0;top:92px;text-align:center;font:400 230px/1 "Anton";color:var(--ink)}
.sw2{position:absolute;left:0;right:0;top:440px;text-align:center;font:400 70px/1 "Anton";letter-spacing:8px;color:var(--ink)}
.pth{position:absolute;left:80px;top:990px;width:920px;height:10px;background:var(--ink);opacity:.55;border-radius:5px;transform-origin:left center}
.cl{position:absolute;opacity:0}
.ct{position:absolute;left:60px;right:60px;top:70px;text-align:center;font:400 84px/1.05 "Anton";letter-spacing:3px;text-transform:uppercase}
.cd{position:absolute;border-radius:50%;background:var(--ink);opacity:0}
.sg{position:absolute;opacity:0}
.post{position:absolute;left:236px;top:300px;width:48px;height:300px;background:#8a6500;border-radius:10px}
.brd{position:absolute;left:0;top:0;width:520px;height:330px;background:#FFD23F;border:12px solid #8a6500;border-radius:28px;display:flex;align-items:center;justify-content:center}
.bt{font:400 78px/1.05 "Anton";letter-spacing:3px;color:#1b1405;text-align:center;text-transform:uppercase;padding:0 24px}
.cv0{position:absolute;top:1790px;opacity:.9}
.fg{position:absolute;top:1030px;font:400 44px/1 "Anton";color:var(--ink);opacity:0}
"""
