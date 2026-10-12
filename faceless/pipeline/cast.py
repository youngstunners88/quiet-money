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
    ("#0f4a57", "#04181d", "#3ad0d0", "#ffffff", "rgba(255,255,255,.16)"),     # teal
    ("#fbf4e3", "#e9dfc4", "#ffd23f", "#14110a", "rgba(20,17,10,.12)"),         # ledger paper
    ("#0e2118", "#04100a", "#35e0a1", "#ffffff", "rgba(255,255,255,.16)"),     # money green
    ("#2a0b10", "#0a0305", "#ff4d5e", "#ffffff", "rgba(255,255,255,.16)"),     # warning red
]
GOLD, GOLD_D, RIM = "#FFD23F", "#E8A800", "#B07C00"
SKIN, SKIN_L, EDGE = "#FFD23F", "#FFE680", "#C99400"
BROWN = "#3a2410"
INK = "#1b1405"


def part(pid: str, x: float, y: float, w: float, h: float, svg: str = "", style: str = "", origin: str = "50% 50%", vb: str | None = None) -> str:
    vb = vb or f"0 0 {w:g} {h:g}"
    inner = f'<svg width="{w:g}" height="{h:g}" viewBox="{vb}" style="overflow:visible">{svg}</svg>' if svg else ""
    return (f'<div class="cp" id="{pid}" style="left:{x:g}px;top:{y:g}px;width:{w:g}px;height:{h:g}px;transform-origin:{origin};{style}">{inner}</div>')


# ------------------------------------------------------------------ Penny: the coin
def _limb(x1, y1, x2, y2, w=30):
    """A rounded gold tube with a thin darker outline (outline = the same stroke, wider, underneath)."""
    return (f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{EDGE}" stroke-width="{w + 7}" stroke-linecap="round"/>'
            f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{SKIN}" stroke-width="{w}" stroke-linecap="round"/>')


def _hand(cx, cy, r=25, side=1):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r + 3}" fill="{EDGE}"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="{SKIN}"/>'
            f'<circle cx="{cx + side * r * 0.85}" cy="{cy - r * 0.35}" r="{r * 0.42}" fill="{SKIN}" stroke="{EDGE}" stroke-width="3"/>')


def penny(pid: str, x: float, y: float, scale: float = 1.0) -> tuple[str, dict]:
    """Penny, 420x560 local. Parts (all addressable by `ids`): bd (body+face), lgL/lgR, aL/aR (upper arms) with fL/fR (forearms, nested), and inside
    the face: lk (look direction), pu (pupils), ey (closed lids), eh (half lids), br (brows), mouths m0 smile, m1 talk, m2 small, m3 gasp O, m4 cheer, m5 think, sw sweat."""
    g = f"{pid}g"
    face = (f'<defs><radialGradient id="{g}" cx="36%" cy="30%" r="80%"><stop offset="0" stop-color="{SKIN_L}"/><stop offset="0.5" stop-color="{SKIN}"/>'
            f'<stop offset="1" stop-color="{GOLD_D}"/></radialGradient></defs>'
            f'<ellipse cx="226" cy="244" rx="150" ry="166" fill="{EDGE}"/>'                               # the coin's edge: thickness on the right
            f'<ellipse cx="210" cy="240" rx="150" ry="166" fill="url(#{g})" stroke="{EDGE}" stroke-width="5"/>'
            f'<ellipse cx="210" cy="240" rx="128" ry="144" fill="none" stroke="{GOLD_D}" stroke-width="5" opacity=".75"/>'
            f'<path d="M92 170 Q104 108 168 92" stroke="#fff" stroke-width="9" fill="none" stroke-linecap="round" opacity=".5"/>'     # rim highlight
            f'<text x="312" y="118" text-anchor="middle" font-family="Anton" font-size="46" fill="{RIM}" opacity=".8">Q</text>')
    eyes = (f'<ellipse cx="156" cy="210" rx="36" ry="45" fill="#fff" stroke="{EDGE}" stroke-width="3"/>'
            f'<ellipse cx="264" cy="210" rx="36" ry="45" fill="#fff" stroke="{EDGE}" stroke-width="3"/>')
    pupils = (f'<g id="{pid}lk"><g id="{pid}pu"><circle cx="160" cy="218" r="23" fill="{BROWN}"/><circle cx="268" cy="218" r="23" fill="{BROWN}"/>'
              f'<circle cx="168" cy="207" r="8" fill="#fff"/><circle cx="276" cy="207" r="8" fill="#fff"/><circle cx="153" cy="228" r="4" fill="#fff" opacity=".8"/>'
              f'<circle cx="261" cy="228" r="4" fill="#fff" opacity=".8"/></g></g>')
    lid = lambda cx: (f'<ellipse cx="{cx}" cy="210" rx="38" ry="47" fill="{SKIN}"/><path d="M{cx - 34} 216 Q{cx} 238 {cx + 34} 216" stroke="{BROWN}" stroke-width="7" fill="none" stroke-linecap="round"/>')
    half = lambda cx: (f'<path d="M{cx - 38} 212 A38 47 0 0 1 {cx + 38} 212 Z" fill="{SKIN}"/><path d="M{cx - 36} 214 L{cx + 36} 214" stroke="{BROWN}" stroke-width="6" stroke-linecap="round"/>')
    lids = f'<g id="{pid}ey" style="visibility:hidden">{lid(156)}{lid(264)}</g><g id="{pid}eh" style="visibility:hidden">{half(156)}{half(264)}</g>'
    brows = (f'<g id="{pid}br"><path d="M118 148 Q154 128 192 146" stroke="{BROWN}" stroke-width="9" fill="none" stroke-linecap="round"/>'
             f'<path d="M228 146 Q266 128 302 148" stroke="{BROWN}" stroke-width="9" fill="none" stroke-linecap="round"/></g>')
    blush = '<ellipse cx="104" cy="272" rx="24" ry="16" fill="#FF8F6B" opacity=".6"/><ellipse cx="316" cy="272" rx="24" ry="16" fill="#FF8F6B" opacity=".6"/>'
    mouth = lambda i, body, hide=True: f'<g id="{pid}m{i}"' + (' style="visibility:hidden"' if hide else "") + f'>{body}</g>'
    tongue = lambda cy, rx=34, ry=16: f'<ellipse cx="210" cy="{cy}" rx="{rx}" ry="{ry}" fill="#FF6F7D"/>'
    mouths = (mouth(0, f'<path d="M166 292 Q210 326 254 292" stroke="{BROWN}" stroke-width="8" fill="none" stroke-linecap="round"/>', False)
              + mouth(1, f'<path d="M158 284 Q210 384 262 284 Q210 300 158 284Z" fill="#5a1a22"/>' + tongue(338))
              + mouth(2, f'<ellipse cx="210" cy="314" rx="30" ry="20" fill="#5a1a22"/>' + tongue(324, 20, 9))
              + mouth(3, f'<ellipse cx="210" cy="330" rx="25" ry="36" fill="#5a1a22"/>' + tongue(348, 16, 9))
              + mouth(4, f'<path d="M146 276 Q210 410 274 276 Z" fill="#5a1a22"/>' + tongue(352, 40, 20))
              + mouth(5, f'<path d="M176 308 Q214 316 252 296" stroke="{BROWN}" stroke-width="8" fill="none" stroke-linecap="round"/>'))
    sweat = f'<g id="{pid}sw" style="visibility:hidden"><path d="M356 120 Q372 154 356 170 Q340 154 356 120Z" fill="#7cd4ff" stroke="#2d8fc4" stroke-width="3"/></g>'
    parts = (part(f"{pid}lgL", 130, 396, 70, 150, _limb(35, 6, 35, 100, 28) + f'<ellipse cx="22" cy="118" rx="42" ry="20" fill="{EDGE}"/><ellipse cx="22" cy="116" rx="39" ry="17" fill="{SKIN}"/>', origin="50% 4%")
             + part(f"{pid}lgR", 220, 396, 70, 150, _limb(35, 6, 35, 100, 28) + f'<ellipse cx="48" cy="118" rx="42" ry="20" fill="{EDGE}"/><ellipse cx="48" cy="116" rx="39" ry="17" fill="{SKIN}"/>', origin="50% 4%")
             + part(f"{pid}bd", 0, 0, 420, 560, face + eyes + pupils + lids + brows + blush + mouths + sweat, origin="50% 44%")
             + _arm(pid, "L", 52, 286, 1) + _arm(pid, "R", 368, 286, -1))
    wrap = part(f"{pid}w", 0, 0, 420, 560, "", origin="50% 100%").replace("</div>", parts + "</div>", 1)     # w: whole-character emphasis (hops, breathing) without fighting the body's own tweens
    root = part(pid, x, y, 420, 560, "", origin="50% 100%")
    ids = {k: f"{pid}{k}" for k in ("w", "lgL", "lgR", "aL", "aR", "fL", "fR", "bd", "lk", "pu", "ey", "eh", "br", "m0", "m1", "m2", "m3", "m4", "m5", "sw")}
    return root.replace("</div>", wrap + "</div>", 1), ids


def _arm(pid: str, side: str, sx: float, sy: float, sgn: int) -> str:
    """Two-part arm: the upper arm hangs from the shoulder (origin at its top); the forearm is nested inside it and bends at the elbow."""
    fore = part(f"{pid}f{side}", 0, 86, 70, 130, _limb(35, 8, 35, 70, 26) + _hand(35, 96, 25, -sgn), origin="50% 6%")
    up = part(f"{pid}a{side}", sx - 35, sy - 12, 70, 220, _limb(35, 12, 35, 90, 28), origin="50% 6%")
    return up.replace("</div>", fore + "</div>", 1)


# ------------------------------------------------------------------ the Fee Gremlin
def gremlin(pid: str, x: float, y: float) -> tuple[str, dict]:
    """A hunched, round purple villain with a huge mouth of coin-shaped gold teeth. Parts: bd (body+head+upper teeth), jw (lower jaw), bl (belly, bulges when it
    swallows), aL/aR (grabbing arms), eyes glare. Cartoonish, not scary: round, expressive, a little silly."""
    B, SH, BE, MO, TO = "#7B2150", "#5A1640", "#933069", "#3b0d26", "#B0457F"
    teeth = "".join(f'<rect x="{112 + k * 38}" y="{228 + (6 if k in (0, 5) else 0)}" width="34" height="{44 - (6 if k in (0, 5) else 0)}" rx="12" fill="#F2B705" stroke="#B88400" stroke-width="3"/>'
                    for k in range(6))
    body = (f'<ellipse cx="236" cy="396" rx="150" ry="22" fill="rgba(0,0,0,.25)"/>'
            f'<ellipse cx="230" cy="262" rx="196" ry="176" fill="{SH}"/><ellipse cx="226" cy="256" rx="190" ry="170" fill="{B}"/>'
            f'<polygon points="64,150 30,84 132,112" fill="{B}" stroke="{SH}" stroke-width="5"/><polygon points="396,150 430,84 328,112" fill="{B}" stroke="{SH}" stroke-width="5"/>'
            f'<polygon points="140,120 168,36 204,108" fill="{B}"/><polygon points="196,104 238,22 274,104" fill="{B}"/><polygon points="262,108 306,40 324,122" fill="{B}"/>'
            f'<path d="M84 238 Q226 176 376 238 Q392 330 232 350 Q70 330 84 238Z" fill="{MO}"/>'
            f'<ellipse cx="232" cy="322" rx="80" ry="26" fill="{TO}"/>{teeth}'
            f'<ellipse cx="156" cy="168" rx="46" ry="32" fill="#fff" transform="rotate(-14 156 168)"/><ellipse cx="304" cy="168" rx="46" ry="32" fill="#fff" transform="rotate(14 304 168)"/>'
            f'<circle cx="170" cy="172" r="17" fill="#F2B705"/><circle cx="290" cy="172" r="17" fill="#F2B705"/><circle cx="174" cy="174" r="9" fill="#111"/><circle cx="286" cy="174" r="9" fill="#111"/>'
            f'<path d="M96 122 L206 166" stroke="{MO}" stroke-width="20" stroke-linecap="round"/><path d="M364 122 L254 166" stroke="{MO}" stroke-width="20" stroke-linecap="round"/>')
    jaw = (f'<path d="M110 8 Q232 96 354 8 L340 56 Q232 130 120 56Z" fill="{B}" stroke="{SH}" stroke-width="5"/>'
           + "".join(f'<rect x="{150 + k * 46}" y="-2" width="30" height="34" rx="11" fill="#F2B705" stroke="#B88400" stroke-width="3"/>' for k in range(4)))
    belly = f'<ellipse cx="226" cy="322" rx="110" ry="66" fill="{BE}" opacity=".9"/>'
    arm = lambda sgn: (f'<path d="M60 24 Q60 96 54 128" stroke="{SH}" stroke-width="62" stroke-linecap="round" fill="none"/>'
                       f'<path d="M60 24 Q60 96 54 128" stroke="{B}" stroke-width="54" stroke-linecap="round" fill="none"/>'
                       f'<circle cx="50" cy="140" r="38" fill="{B}" stroke="{SH}" stroke-width="5"/>'
                       f'<path d="M26 156 L22 184 M48 164 L48 194 M70 156 L78 184" stroke="#F2E6C8" stroke-width="9" stroke-linecap="round"/>')
    out = (part(f"{pid}bd", 0, 0, 460, 440, body, origin="50% 70%") + part(f"{pid}bl", 0, 0, 460, 440, belly, origin="50% 76%")
           + part(f"{pid}jw", 0, 282, 460, 140, jaw, origin="50% 0%")
           + part(f"{pid}aL", 120, 300, 120, 220, arm(1), origin="50% 8%") + part(f"{pid}aR", 340, 300, 120, 220, arm(-1), origin="50% 8%"))
    root = part(pid, x, y, 460, 440, "", origin="50% 100%", style="opacity:0")
    return root.replace("</div>", out + "</div>", 1), {k: f"{pid}{k}" for k in ("bd", "bl", "jw", "aL", "aR")}


def coin(pid: str, x: float, y: float, d: float = 150) -> str:
    return part(pid, x, y, d, d * 0.62,
                f'<ellipse cx="{d / 2}" cy="{d * 0.43}" rx="{d / 2 - 3}" ry="{d * 0.19}" fill="{RIM}"/>'
                f'<rect x="3" y="{d * 0.24}" width="{d - 6}" height="{d * 0.19}" fill="{GOLD_D}"/>'
                f'<ellipse cx="{d / 2}" cy="{d * 0.24}" rx="{d / 2 - 3}" ry="{d * 0.19}" fill="{GOLD}" stroke="{RIM}" stroke-width="4"/>'
                f'<ellipse cx="{d / 2}" cy="{d * 0.24}" rx="{d / 2 - 28}" ry="{d * 0.11}" fill="none" stroke="#e0a800" stroke-width="3"/>'
                f'<text x="{d / 2}" y="{d * 0.3}" text-anchor="middle" font-family="Anton" font-size="{d * 0.2:.0f}" fill="{RIM}">Q</text>',
                style="opacity:0")


# ------------------------------------------------------------------ timeline helpers
def tw(sel: str, a: dict, b: dict, t: float, dur: float = 0.4, ease: str = "power2.out") -> str:
    fa = ",".join(f"{k}:{v!r}" if isinstance(v, str) else f"{k}:{v:g}" for k, v in a.items())
    fb = ",".join(f"{k}:{v!r}" if isinstance(v, str) else f"{k}:{v:g}" for k, v in b.items())
    return f'tl.fromTo("#{sel}",{{{fa}}},{{{fb},duration:{dur:.3f},ease:"{ease}"}},{t:.3f});'


def st(sel: str, props: str, t: float) -> str:
    return f'tl.set("#{sel}",{{{props}}},{t:.3f});'


def land(sel: str, t: float, squash: float = 0.84) -> str:
    """Squash and stretch on landing: flatten and widen, then spring back with an elastic overshoot."""
    return tw(sel, {"scaleY": squash, "scaleX": 2 - squash + 0.06}, {"scaleY": 1, "scaleX": 1}, t, 0.55, "elastic.out(1,0.45)")


def breathe(sel: str, t0: float, dur: float, amp: float = 0.022, period: float = 1.6) -> list[str]:
    """Idle breathing: a slow squash and stretch on the whole character."""
    js, t, up = [], 0.0, True
    while t < dur - 0.05:
        seg = min(period / 2, dur - t)
        js.append(tw(sel, {"scaleY": 1 if up else 1 + amp, "scaleX": 1 if up else 1 - amp / 2}, {"scaleY": 1 + amp if up else 1, "scaleX": 1 - amp / 2 if up else 1}, t0 + t, seg, "sine.inOut"))
        t += seg
        up = not up
    return js


def hop(sel: str, t: float, h: float = 16) -> list[str]:
    """A small emphasis hop (up fast, down with a bounce) for a stressed word."""
    return [tw(sel, {"y": 0}, {"y": -h}, t, 0.1, "power2.out"), tw(sel, {"y": -h}, {"y": 0}, t + 0.1, 0.22, "bounce.out")]


def burst(sid: str, t: float, cx: float, cy: float, n: int = 26, colors: tuple = ("#FFD23F", "#ffffff", "#ff7a2f", "#3ad0d0", "#ff4d5e")) -> tuple[str, list[str]]:
    """Confetti: n bits fly out from (cx, cy), spin, fall and fade. Positions are a fixed function of the index, so a frame always looks the same.
    Each bit is hidden until its moment (immediateRender off), so nothing sits at the origin before the burst."""
    h, js = [], []
    for k in range(n):
        ang = (k / n) * 2 * math.pi + (k % 3) * 0.2
        dist = 190 + (k * 37) % 230
        dx, dy = math.cos(ang) * dist, math.sin(ang) * dist - 80
        w, hh = 20 + k % 3 * 8, 14 + k % 2 * 10
        h.append(f'<div class="cf" id="{sid}k{k}" style="left:{cx:g}px;top:{cy:g}px;background:{colors[k % len(colors)]};width:{w}px;height:{hh}px"></div>')
        js.append(f'tl.fromTo("#{sid}k{k}",{{x:0,y:0,rotation:0,opacity:1}},{{x:{dx:.0f},y:{dy + 300:.0f},rotation:{360 + k * 40},opacity:0,duration:1.1,ease:"power2.out",immediateRender:false}},{t:.3f});')
    return "".join(h), js


def ev(spec: dict, t0: float, t: float, kind: str) -> None:
    """Note a sound-effect moment (seconds into the scene) for the audio mix: spec['_ev'] is read back by the reel renderer."""
    spec.setdefault("_ev", []).append((round(max(0.0, t - t0), 3), kind))


def talk(ids: dict, words: list[tuple[float, float]], t0: float, dur: float) -> list[str]:
    """Lip sync from the voice's own word timings: the mouth shape follows the word (long word wide, middling open, short small), shut between words.
    Blinks vary (full, half) and every few blinks Penny glances left or right."""
    js = []
    for k, (a, b) in enumerate(words):
        if a >= dur - 0.05:
            break
        d = b - a
        kind = "m4" if d > 0.5 else ("m1" if d > 0.27 else "m2")
        if k % 5 == 4:
            kind = "m2"
        end = min(b, dur - 0.02)
        if d > 0.5 and "w" in ids and a > 0.6:                  # a stressed (long) word: a small hop
            js += hop(ids["w"], t0 + a, 14)
        js += [st(ids["m0"], "visibility:'hidden'", t0 + a), st(ids[kind], "visibility:'visible'", t0 + a),
               st(ids[kind], "visibility:'hidden'", t0 + end), st(ids["m0"], "visibility:'visible'", t0 + end)]
    t, n = 0.8 + (len(words) % 3) * 0.3 + (sum(map(ord, ids['bd'])) % 7) * 0.12, 0       # a different blink rhythm in every scene
    while t < dur - 0.4:
        v = n % 4
        if v in (0, 3):                               # full blink
            js += [st(ids["ey"], "visibility:'visible'", t0 + t), st(ids["ey"], "visibility:'hidden'", t0 + t + 0.14)]
        elif v == 1:                                  # half blink
            js += [st(ids["eh"], "visibility:'visible'", t0 + t), st(ids["eh"], "visibility:'hidden'", t0 + t + 0.2)]
        else:                                         # a glance
            dx = 14 if (n // 4) % 2 == 0 else -14
            js += [tw(ids["lk"], {"x": 0}, {"x": dx}, t0 + t, 0.2, "power2.out"), tw(ids["lk"], {"x": dx}, {"x": 0}, t0 + t + 0.9, 0.25, "power2.inOut")]
        t += 1.7 + (n % 3) * 0.35
        n += 1
    return js


def mood(ids: dict, t: float, face: str, brow: float = 0.0) -> list[str]:
    """Hold an expression from time t: face is one of m3 (gasp), m4 (cheer), m5 (think); brow lifts the eyebrows."""
    js = [st(ids["m0"], "visibility:'hidden'", t), st(ids[face], "visibility:'visible'", t)]
    if brow:
        js.append(tw(ids["br"], {"y": 0}, {"y": brow}, t, 0.18))
    return js


def arms(ids: dict, t: float, left: tuple[float, float] | None, right: tuple[float, float] | None, dur: float = 0.35, ease: str = "back.out(1.8)") -> list[str]:
    """Pose the arms: (upper, forearm) angles in degrees; positive swings the left arm outward/up, negative the right one."""
    js = []
    rest = 8 if "fL" in ids else 0           # Penny's arms hang a little out; the gremlin's (no forearm) hang straight
    if left is not None:
        js.append(tw(ids["aL"], {"rotation": rest}, {"rotation": left[0]}, t, dur, ease))
        if "fL" in ids:
            js.append(tw(ids["fL"], {"rotation": 0}, {"rotation": left[1]}, t, dur, ease))
    if right is not None:
        js.append(tw(ids["aR"], {"rotation": -rest}, {"rotation": right[0]}, t, dur, ease))
        if "fR" in ids:
            js.append(tw(ids["fR"], {"rotation": 0}, {"rotation": right[1]}, t, dur, ease))
    return js


def walk(ids: dict, root: str, t0: float, dur: float, step: float = 0.28, lift: float = 14) -> list[str]:
    """A walk cycle: legs swing in opposition, the body bobs on each step, arms counter-swing."""
    js, k, t = [], 0, 0.0
    while t < dur - 0.05:
        seg = min(step, dur - t)
        a = 26 if k % 2 == 0 else -26
        js += [tw(ids["lgL"], {"rotation": a}, {"rotation": -a}, t0 + t, seg, "sine.inOut"), tw(ids["lgR"], {"rotation": -a}, {"rotation": a}, t0 + t, seg, "sine.inOut"),
               tw(ids["aL"], {"rotation": -a * 0.8}, {"rotation": a * 0.8}, t0 + t, seg, "sine.inOut"), tw(ids["aR"], {"rotation": -a * 0.8 - 6}, {"rotation": a * 0.8 - 6}, t0 + t, seg, "sine.inOut"),
               tw(ids["bd"], {"y": 0}, {"y": -lift}, t0 + t, seg / 2, "sine.out"), tw(ids["bd"], {"y": -lift}, {"y": 0}, t0 + t + seg / 2, seg / 2, "sine.in")]
        t += seg
        k += 1
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
    y = 1290 if hook else 400
    big = 1.1 if hook else 0.95
    p, ids = penny(f"{sid}p", 330, y)
    js = [tw(f"{sid}p", {"y": 380, "scale": 0.5, "opacity": 0}, {"y": 0, "scale": big, "opacity": 1}, t0 + 0.05, 0.5, "back.out(1.6)")]
    js += [land(ids["bd"], t0 + 0.5)] + breathe(ids["w"], t0 + 0.9, dur - 0.9) + bob(ids["bd"], t0 + 0.6, dur - 0.6, 12) + talk(ids, words, t0, dur)
    js += arms(ids, t0 + 0.5, (28, -20), (-150, 28))                       # a wave
    k, t = 0, t0 + 1.0
    while t < t0 + dur - 0.4:
        js.append(tw(ids["fR"], {"rotation": 28 if k % 2 == 0 else -22}, {"rotation": -22 if k % 2 == 0 else 28}, t, 0.3, "sine.inOut"))
        t += 0.3
        k += 1
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
        h.append(coin(f"{sid}c{k}", 560 + (k % 2) * 6, 880 - k * 56, 190))
        js.append(tw(f"{sid}c{k}", {"y": -700, "opacity": 0, "rotation": -20 + k % 3 * 20}, {"y": 0, "opacity": 1, "rotation": 0}, t0 + 0.25 + k * dur * 0.5 / coins, 0.42, "bounce.out"))
        ev(spec, t0, t0 + 0.55 + k * dur * 0.5 / coins, "coin")
    p, ids = penny(f"{sid}p", 20, 400)
    js += [tw(f"{sid}p", {"x": -460, "opacity": 0, "scale": 0.82}, {"x": 0, "opacity": 1, "scale": 0.82}, t0 + 0.05, 0.5, "back.out(1.4)")]
    js += talk(ids, words, t0, dur * 0.55)
    cheer = t0 + dur * 0.55
    js += mood(ids, cheer, "m4", -14) + arms(ids, cheer, (145, 24), (-145, -24), 0.35, "back.out(2.2)") + bob(ids["bd"], cheer, dur * 0.45, 24, 0.5)
    js += [land(ids["bd"], cheer + 0.2), tw(ids["lk"], {"x": 0}, {"x": 14}, t0 + 0.3, 0.3)] + breathe(ids["w"], t0 + 0.9, dur - 0.9)
    bh, bj = burst(sid, cheer, 230, 500, 26)
    h.append(bh)
    js += bj
    ev(spec, t0, cheer, "ding")
    num, nj = counter(sid, n["value"], n["prefix"], n["suffix"], n["decimals"], t0, dur, min(250, int(930 / (max(3, len(fmt(n["value"], n["decimals"]) + n["prefix"] + n["suffix"])) * 0.47))))
    lab, lj = label(sid, n.get("label") or "", t0 + 0.5, 70, 1680, hi=True) if n.get("label") else ("", [])
    box = f'<div class="nb" id="{sid}nb" style="top:1330px">{num}</div>'
    js += nj + lj + [tw(f"{sid}nb", {"scale": 0.8, "opacity": 0.3}, {"scale": 1, "opacity": 1}, t0, 0.45, "back.out(1.6)")]
    fh, fj = _floaters(sid, t0, dur, 8)
    return fh + "".join(h) + p + box + lab, js + fj


def stage_fee(sid, t0, dur, spec, words):
    """The Fee Gremlin eats the coin stack in three beats per coin: it hops in and leans (approach), the jaw snaps as a coin leaps into its mouth (bite),
    the belly bulges and the stack drops a coin (swallow). Penny panics. At most two of these a video."""
    coins = 7
    h, js = [], []
    base_y, cx = 900, 380
    for k in range(coins):
        h.append(coin(f"{sid}c{k}", cx + (k % 2) * 6, base_y - k * 54, 190))
        js.append(tw(f"{sid}c{k}", {"y": -600, "opacity": 0}, {"y": 0, "opacity": 1}, t0 + 0.1 + k * 0.07, 0.35, "bounce.out"))
    g, gi = gremlin(f"{sid}g", 470, 520)
    enter_t = t0 + dur * 0.25
    js += [tw(f"{sid}g", {"x": 560, "y": -260, "opacity": 0, "scale": 0.5}, {"x": 0, "y": 0, "opacity": 1, "scale": 0.8}, enter_t, 0.5, "back.out(1.7)")]
    js += arms(gi, enter_t + 0.4, (60, 0), (-30, 0), 0.3)        # arms: aL reaches toward the stack (positive swings it left)
    eats = min(coins, max(3, int((dur * 0.7) / 0.55)))
    for e in range(eats):
        k = coins - 1 - e                                           # top coin first
        t = enter_t + 0.55 + e * ((dur * 0.72 - 0.55) / eats)
        js += [tw(gi["jw"], {"y": 0}, {"y": 46}, t, 0.12, "power1.out"),                                    # open
               tw(f"{sid}c{k}", {"x": 0, "y": 0, "scale": 1, "opacity": 1, "rotation": 0}, {"x": 190, "y": -60 - e * 10, "scale": 0.25, "opacity": 0, "rotation": 240}, t + 0.05, 0.3, "power2.in"),
               tw(gi["jw"], {"y": 46}, {"y": 0}, t + 0.2, 0.1, "power3.in"),                                # bite
               tw(gi["bl"], {"scale": 1}, {"scale": 1.12}, t + 0.3, 0.12, "power2.out"), tw(gi["bl"], {"scale": 1.12}, {"scale": 1}, t + 0.42, 0.14, "sine.inOut"),   # swallow
               tw(gi["bd"], {"y": 0, "scaleY": 1}, {"y": 8, "scaleY": 0.96}, t, 0.12, "power1.out"), tw(gi["bd"], {"y": 8, "scaleY": 0.96}, {"y": 0, "scaleY": 1}, t + 0.2, 0.16, "back.out(2)"),
               tw(f"{sid}s", {"x": 0}, {"x": 9}, t + 0.2, 0.05, "none"), tw(f"{sid}s", {"x": 9}, {"x": -9}, t + 0.25, 0.06, "none"), tw(f"{sid}s", {"x": -9}, {"x": 0}, t + 0.31, 0.06, "none")]
        ev(spec, t0, t + 0.2, "chomp")
        ev(spec, t0, t + 0.38, "gulp")
    p, ids = penny(f"{sid}p", 10, 400)
    js += [tw(f"{sid}p", {"x": -440, "opacity": 0, "scale": 0.8}, {"x": 0, "opacity": 1, "scale": 0.8}, t0 + 0.05, 0.5, "back.out(1.4)")]
    js += talk(ids, words, t0, dur * 0.25)
    panic = enter_t
    js += mood(ids, panic, "m3", -22) + [st(ids["sw"], "visibility:'visible'", panic + 0.2)] + arms(ids, panic + 0.1, (30, -140), (-30, 140), 0.25, "back.out(2.4)")
    j = 0
    while panic + j * 0.13 < t0 + dur - 0.15:
        js.append(tw(ids["bd"], {"x": -8 if j % 2 == 0 else 8}, {"x": 8 if j % 2 == 0 else -8}, panic + j * 0.13, 0.13, "none"))
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
    la, lb = 0.4 + 0.6 * c["va"] / hi, 0.4 + 0.6 * c["vb"] / hi
    h, js, first = [], [], None
    for k, (name, frac, y, col) in enumerate(((c["a"], la, 440, GOLD), (c["b"], lb, 730, "#9aa3b2"))):
        h.append(f'<div class="ln2" style="top:{y + 270}px"></div>')
        p, ids = penny(f"{sid}r{k}", 20, y - 160)
        first = first or ids
        h.append(p)
        js.append(tw(f"{sid}r{k}", {"x": 0, "scale": 0.55, "opacity": 0}, {"x": 0, "scale": 0.55, "opacity": 1}, t0, 0.2))
        js.append(tw(f"{sid}r{k}", {"x": 0, "scale": 0.55}, {"x": 400 * frac, "scale": 0.55}, t0 + 0.4, dur * 0.55, "power2.inOut"))
        js += walk(ids, f"{sid}r{k}", t0 + 0.4, dur * 0.55, 0.22, 10)
        h.append(f'<div class="rv" id="{sid}v{k}" style="top:{y + 20}px;left:520px;color:{col if k == 0 else "var(--ink)"}">{html.escape(name)}</div>')
        js.append(tw(f"{sid}v{k}", {"opacity": 0, "x": 40}, {"opacity": 1, "x": 0}, t0 + 0.5 + dur * 0.5 + k * 0.15, 0.4))
    lab, lj = label(sid, spec.get("text", "") or "WHO WINS?", t0 + 0.3, 90, 1400, hi=True)
    ev(spec, t0, t0 + 0.3, "pop")
    ev(spec, t0, t0 + 0.4 + dur * 0.55, "ding")
    js += talk(first, words, t0, dur)
    fh, fj = _floaters(sid, t0, dur, 6)
    return fh + "".join(h) + lab, js + lj + fj


def stage_step(sid, t0, dur, spec, words):
    """Penny presents a numbered board: the arm sweeps out to it, then points."""
    s = spec["step"]
    circ = round(2 * math.pi * 150)
    board = (f'<div class="bd2" id="{sid}b" style="left:480px;top:430px;width:520px;height:560px">'
             f'<svg width="520" height="560" viewBox="0 0 520 560"><rect x="8" y="8" width="504" height="544" rx="34" fill="rgba(0,0,0,.18)" stroke="var(--ink)" stroke-width="8"/>'
             f'<circle cx="260" cy="230" r="150" fill="none" stroke="var(--soft)" stroke-width="16"/>'
             f'<circle id="{sid}o" cx="260" cy="230" r="150" fill="none" stroke="{GOLD}" stroke-width="16" stroke-linecap="round" stroke-dasharray="{circ}" '
             f'stroke-dashoffset="{circ}" transform="rotate(-90 260 230)"/></svg><div class="rn2">{s["n"]}</div>'
             f'<div class="sw2">STEP {html.escape(s["word"])}</div></div>')
    p, ids = penny(f"{sid}p", 40, 400)
    js = [tw(f"{sid}p", {"x": -420, "opacity": 0, "scale": 0.82}, {"x": 0, "opacity": 1, "scale": 0.82}, t0 + 0.05, 0.5, "back.out(1.4)"),
          tw(f"{sid}b", {"scale": 0.4, "opacity": 0, "rotation": -8}, {"scale": 1, "opacity": 1, "rotation": 0}, t0 + 0.2, 0.5, "back.out(1.7)"),
          tw(f"{sid}o", {"strokeDashoffset": circ}, {"strokeDashoffset": 0}, t0 + 0.5, dur * 0.55, "power2.inOut")]
    js += arms(ids, t0 + 0.5, None, (-100, 10), 0.45) + [land(ids["bd"], t0 + 0.55)] + breathe(ids["w"], t0 + 0.9, dur - 0.9)               # presenting arm
    ev(spec, t0, t0 + 0.4, "pop")
    ev(spec, t0, t0 + 0.5 + dur * 0.55, "ding")
    js += talk(ids, words, t0, dur) + bob(ids["bd"], t0 + 0.6, dur - 0.6, 10)
    js += [tw(ids["lk"], {"x": 0}, {"x": 16}, t0 + 0.5, 0.3)]
    lab, lj = label(sid, s.get("gist", ""), t0 + 0.6, 66, 1380, hi=False)
    fh, fj = _floaters(sid, t0, dur, 6, "✓")
    return fh + p + board + lab, js + lj + fj


def stage_years(sid, t0, dur, spec, words):
    """Penny walks along a path while the years count up."""
    n = spec["num"]
    p, ids = penny(f"{sid}p", 40, 380)
    js = [tw(f"{sid}p", {"x": 0, "scale": 0.8, "opacity": 0}, {"x": 0, "scale": 0.8, "opacity": 1}, t0, 0.2),
          tw(f"{sid}p", {"x": 0}, {"x": 520}, t0 + 0.3, dur * 0.7, "none")]
    js += walk(ids, f"{sid}p", t0 + 0.3, dur * 0.7) + talk(ids, words, t0, dur)
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
    """Penny gasps at the beat's key phrase: hands to her cheeks, eyebrows up, a shake, a sweat drop."""
    p, ids = penny(f"{sid}p", 330, 380)
    shake = t0 + 0.35
    js = [tw(f"{sid}p", {"y": 380, "scale": 0.5, "opacity": 0}, {"y": 0, "scale": 1.0, "opacity": 1}, t0 + 0.05, 0.4, "back.out(2)")]
    js += mood(ids, shake, "m3", -24) + [st(ids["sw"], "visibility:'visible'", shake + 0.3)] + arms(ids, shake, (30, -140), (-30, 140), 0.25, "back.out(2.4)")
    js += [land(ids["bd"], shake, 0.78)] + breathe(ids["w"], t0 + 1.0, dur - 1.0)
    ev(spec, t0, shake, "gasp")
    j = 0
    while shake + j * 0.12 < t0 + dur * 0.55:
        js.append(tw(ids["bd"], {"x": -8 if j % 2 == 0 else 8}, {"x": 8 if j % 2 == 0 else -8}, shake + j * 0.12, 0.12, "none"))
        j += 1
    rec = t0 + dur * 0.55
    js += [st(ids["m3"], "visibility:'hidden'", rec), st(ids["m0"], "visibility:'visible'", rec), st(ids["sw"], "visibility:'hidden'", rec)]
    js += talk(ids, [(a, b) for a, b in words if a > dur * 0.55], t0, dur)
    lab, lj = label(sid, spec.get("text", ""), t0 + 0.3, 104 if len(spec.get("text", "")) < 18 else 80, 1340, hi=True)
    fh, fj = _floaters(sid, t0, dur, 8, "!")
    return fh + p + lab, js + lj + fj


def stage_think(sid, t0, dur, spec, words):
    """Penny thinks: pupils up, a hand to her chin, a thought cloud grows with the phrase inside."""
    p, ids = penny(f"{sid}p", 330, 680)
    words_ = spec.get("text", "").split()
    text = html.escape(" ".join(words_[:6]))
    tsize = 84 if len(words_[:6]) <= 3 else 62
    cloud = (f'<div class="cl" id="{sid}cl" style="left:90px;top:360px;width:900px;height:300px"><svg width="900" height="300" viewBox="0 0 900 300">'
             f'<ellipse cx="450" cy="150" rx="430" ry="130" fill="var(--ink)" opacity=".95"/></svg><div class="ct" style="color:var(--bgc);font-size:{tsize}px">{text}</div></div>'
             f'<div class="cd" id="{sid}d1" style="left:520px;top:640px;width:46px;height:46px"></div><div class="cd" id="{sid}d2" style="left:490px;top:700px;width:30px;height:30px"></div>')
    js = [tw(f"{sid}p", {"y": 300, "opacity": 0, "scale": 0.7}, {"y": 0, "opacity": 1, "scale": 0.85}, t0 + 0.05, 0.45, "back.out(1.6)"),
          tw(f"{sid}d2", {"scale": 0, "opacity": 0}, {"scale": 1, "opacity": 1}, t0 + 0.4, 0.25, "back.out(2)"), tw(f"{sid}d1", {"scale": 0, "opacity": 0}, {"scale": 1, "opacity": 1}, t0 + 0.55, 0.25, "back.out(2)"),
          tw(f"{sid}cl", {"scale": 0.2, "opacity": 0}, {"scale": 1, "opacity": 1}, t0 + 0.7, 0.55, "back.out(1.5)"),
          tw(ids["pu"], {"x": 0, "y": 0}, {"x": 10, "y": -28}, t0 + 0.3, 0.3)]
    js += arms(ids, t0 + 0.4, None, (-25, 128), 0.4, "back.out(1.4)") + [st(ids["m0"], "visibility:'hidden'", t0 + 0.4), st(ids["m5"], "visibility:'visible'", t0 + 0.4)]
    js += bob(ids["bd"], t0 + 0.6, dur - 0.6, 10) + breathe(ids["w"], t0 + 0.9, dur - 0.9)
    ev(spec, t0, t0 + 0.5, "pop")
    ev(spec, t0, t0 + 0.8, "pop")
    fh, fj = _floaters(sid, t0, dur, 6, "?")
    return fh + cloud + p, js + fj


def stage_sign(sid, t0, dur, spec, words):
    """Penny points at a sign with the phrase: it swings in on its post."""
    p, ids = penny(f"{sid}p", 40, 400)
    words_ = spec.get("text", "").split()
    first = " ".join(words_).replace("! ", ". ").replace("? ", ". ").split(". ")[0]      # prefer the beat's first whole sentence over a cut-off one
    cut = first.split() if len(first.split()) <= 7 else words_[:7]
    text = html.escape(" ".join(cut))                    # a board holds seven words
    size = 78 if len(cut) <= 3 else 60 if len(cut) <= 5 else 50
    sign = (f'<div class="sg" id="{sid}sg" style="left:490px;top:430px;width:520px;height:480px;transform-origin:50% 0%"><div class="post"></div>'
            f'<div class="brd"><div class="bt" style="font-size:{size}px">{text}</div></div></div>')
    js = [tw(f"{sid}p", {"x": -420, "opacity": 0, "scale": 0.82}, {"x": 0, "opacity": 1, "scale": 0.82}, t0 + 0.05, 0.5, "back.out(1.4)"),
          tw(f"{sid}sg", {"rotation": -35, "opacity": 0, "y": -140}, {"rotation": 0, "opacity": 1, "y": 0}, t0 + 0.3, 0.7, "bounce.out")]
    js += arms(ids, t0 + 0.7, None, (-95, 6), 0.4) + [tw(ids["lk"], {"x": 0}, {"x": 16}, t0 + 0.6, 0.3), land(ids["bd"], t0 + 0.8)] + breathe(ids["w"], t0 + 1.0, dur - 1.0)
    ev(spec, t0, t0 + 0.95, "thud")
    js += talk(ids, words, t0, dur) + bob(ids["bd"], t0 + 0.7, dur - 0.7, 9)
    fh, fj = _floaters(sid, t0, dur, 6, "$")
    return fh + p + sign, js + fj


TEMPLATES = {"think": stage_think, "sign": stage_sign, "hero": stage_hero, "stack": stage_stack, "fee": stage_fee, "race": stage_race, "step": stage_step, "years": stage_years, "shock": stage_shock}
DROP_LABELS = ("DROP", "LOSS", "LOST", "COST", "FEE", "DRAIN")     # a number that is money going away: the gremlin eats it, the stack never rises for it
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
        elif num and not num["static"] and (any(w in say_up for w in FEE_WORDS) or any(w in (num.get("label") or "") for w in DROP_LABELS)) and fees < 2:
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
        out[i] = {"kind": "stage", "tpl": tpl, "pal": pal, "cam": ("push", "pan", "pull", "tilt")[i % 4], "trans": ("wipe", "iris", "slide", "flip")[(i + 1) % 4], **spec}
        last_tpl, last_pal = tpl, pal
    return out


def _camera(sid: str, t0: float, dur: float, kind: str) -> list[str]:
    w = f"{sid}w"
    if kind == "pull":
        return [tw(w, {"scale": 1.1}, {"scale": 1.0}, t0, dur, "none")]
    if kind == "pan":
        return [tw(w, {"scale": 1.06, "x": -30}, {"scale": 1.06, "x": 30}, t0, dur, "none")]
    if kind == "tilt":
        return [tw(w, {"scale": 1.05, "rotation": -1.4}, {"scale": 1.05, "rotation": 1.4}, t0, dur, "none")]
    return [tw(w, {"scale": 1.0}, {"scale": 1.08}, t0, dur, "none")]


def _transition(sid: str, t0: float, kind: str) -> tuple[str, list[str]]:
    """What covers the cut into this scene: a gold wipe, a gold iris, a dark panel sliding up, or a spinning coin."""
    if kind == "iris":
        return (f'<div class="tr-iris" id="{sid}tr"></div>',
                [st(f"{sid}tr", "opacity:1", t0), tw(f"{sid}tr", {"scale": 0.05}, {"scale": 4.2}, t0, 0.42, "power2.in"), st(f"{sid}tr", "opacity:0", t0 + 0.43)])
    if kind == "slide":
        return (f'<div class="tr-slide" id="{sid}tr"></div>', [tw(f"{sid}tr", {"y": 1960}, {"y": -1960}, t0, 0.5, "power2.inOut")])
    if kind == "flip":
        return (f'<div class="tr-flip" id="{sid}tr"><svg width="520" height="520" viewBox="0 0 520 520"><circle cx="260" cy="260" r="236" fill="{RIM}"/>'
                f'<circle cx="260" cy="260" r="216" fill="{GOLD}"/><circle cx="260" cy="260" r="180" fill="none" stroke="{GOLD_D}" stroke-width="10"/>'
                f'<text x="260" y="330" text-anchor="middle" font-family="Anton" font-size="230" fill="{RIM}">Q</text></svg></div>',
                [st(f"{sid}tr", "opacity:1", t0), tw(f"{sid}tr", {"scaleX": 0, "scaleY": 0.6}, {"scaleX": 1, "scaleY": 1.5}, t0, 0.22, "power2.out"),
                 tw(f"{sid}tr", {"scaleX": 1, "scaleY": 1.5}, {"scaleX": 0, "scaleY": 1.9}, t0 + 0.22, 0.22, "power2.in"), st(f"{sid}tr", "opacity:0", t0 + 0.45)])
    return (f'<div class="sw0" id="{sid}tr"></div>', [tw(f"{sid}tr", {"x": -1200}, {"x": 1300}, t0, 0.45, "power2.inOut")])


def build(sid: str, t0: float, dur: float, spec: dict) -> tuple[str, list[str], tuple]:
    """(html, js, palette) for one stage scene. spec['words'] = [(start, end)] relative to the scene start (the voice's word timings)."""
    words = spec.get("words", [])
    fn = TEMPLATES[spec["tpl"]]
    spec["_ev"] = []
    if spec["tpl"] == "hero":
        h, js = stage_hero(sid, t0, dur, spec, words, hook=spec.get("hook", False))
    else:
        h, js = fn(sid, t0, dur, spec, words)
    belt = "".join(coin(f"{sid}bc{k}", 40 + k * 190, 1830, 90) for k in range(7))
    for k in range(7):
        js.append(tw(f"{sid}bc{k}", {"x": 0, "opacity": 0.85}, {"x": -190, "opacity": 0.85}, t0, dur, "none"))
    tr_html, tr_js = _transition(sid, t0, spec.get("trans", "wipe"))
    js += tr_js + _camera(sid, t0, dur, spec.get("cam", "push"))
    world = f'<div class="wd" id="{sid}w"><div class="wd" id="{sid}s">{h}{belt}</div></div>'
    return world + tr_html, js, PALS[spec["pal"] % len(PALS)]


CSS = """
.cp{position:absolute}
.cf{position:absolute;opacity:0;border-radius:3px}
.tr-iris{position:absolute;left:240px;top:660px;width:600px;height:600px;border-radius:50%;background:#FFD23F;opacity:0}
.tr-slide{position:absolute;left:0;top:0;width:1080px;height:1920px;background:#101018;transform:translateY(1960px)}
.tr-flip{position:absolute;left:280px;top:700px;width:520px;height:520px;opacity:0}
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
