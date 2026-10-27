#!/usr/bin/env python3
"""Quiet Money hero edit: four Flow clips as one escalating piece, cut on the beat, with sound design, punch text, one global grade and a QA readout.
Applies .claude/skills/faceless-capcut-mastery. usage: .venv/bin/python tools/hero_edit.py [--out PATH] [--bed PATH] [--no-voice]"""
import argparse, json, re, shutil, subprocess, sys, tempfile, wave
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
import beats
from faceless import cineedit, reel
from faceless.pipeline import music

W, H, FPS, SR = 1080, 1920, 24, 48000
GOLD = "0xFFD23F"
INBOX = REPO / "channel" / "flow" / "inbox"
FONT = str(REPO / "assets" / "fonts" / "Anton-Regular.ttf")
CLIP_LUFS = -21.0

# source seconds of each clip; `elastic` is the segment whose speed is nudged so the hit lands on a beat
ACTS = [
    dict(name="leak", src="playbook-20261027-1.mp4", impact=6.2, elastic=1, text="THE LEAK",
         line="Every month, something quietly bleeds you.", line_at="early",
         segs=[(0, 1.2, 1.0), (1.2, 5.2, 1.5), (5.2, 6.2, 0.65), (6.2, 8.0, 1.0)]),
    dict(name="myth", src="myth-20261027-2.mp4", impact=2.3, elastic=0, text="THE MYTH CRACKS",
         line="The story you were sold cracks open.", line_at="after_hit",
         segs=[(0, 1.3, 1.0), (1.3, 2.3, 0.65), (2.3, 2.7, 2.0), (2.7, 4.6, 1.1), (4.6, 6.4, 1.6)]),
    dict(name="toll", src="story-20261027-3.mp4", impact=7.1, elastic=1, text="NO MORE TOLLS",
         line="Then you stop paying the toll.", line_at="early",
         segs=[(0, 1.4, 1.0), (1.4, 6.0, 2.0), (6.0, 7.1, 0.65), (7.1, 8.0, 0.6)]),
    dict(name="climb", src="escape-20261027-1.mp4", impact=4.9, elastic=1, text="THE CLIMB",
         line="And the climb finally begins.", line_at="early",
         segs=[(0, 1.0, 1.0), (1.0, 3.9, 1.8), (3.9, 4.9, 0.65), (4.9, 5.6, 1.0), (5.6, 8.0, 1.0)]),
]
CTA_LINE, CTA_HEAD, CTA_SUB = "One money rule a day. Follow Quiet Money.", "ONE MONEY RULE A DAY", "Real numbers. No hype."


def run(cmd, timeout=900):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode: raise RuntimeError(" ".join(map(str, cmd))[:300] + "\n" + r.stderr[-600:])
    return r


def seglens(segs): return [(b - a) / s for a, b, s in segs]


def plan_acts(tb):
    """Nudge each act so its hit, then its last frame, land on a beat. tb = beat times on the video timeline."""
    cum, plans = 0.0, []
    for act in ACTS:
        segs = [list(s) for s in act["segs"]]
        e = act["elastic"]
        hit_rel = cineedit._impact_after_ramp([tuple(s) for s in segs], act["impact"])
        natural = cum + hit_rel
        lens = seglens(segs)
        for b in sorted([b for b in tb if abs(b - natural) <= 0.5], key=lambda b: abs(b - natural)):
            need = (b - cum) - (hit_rel - lens[e])
            a0, b0, _ = segs[e]
            if need > 0.2 and 0.85 <= (b0 - a0) / need <= 2.0:
                segs[e][2] = round((b0 - a0) / need, 4); break
        hit_rel = cineedit._impact_after_ramp([tuple(s) for s in segs], act["impact"])
        end = cum + sum(seglens(segs))
        under = [b for b in tb if end - 0.8 < b <= end + 1e-6]
        if under:
            trim = end - max(under)
            a, b, s = segs[-1]
            if b - trim * s > a + 0.3: segs[-1][1] = round(b - trim * s, 4)
        dur = sum(seglens(segs))
        plans.append(dict(act=act, segs=[tuple(s) for s in segs], start=cum, dur=dur, hit=cum + hit_rel, hit_rel=hit_rel))
        cum += dur
    return plans, cum


def render_act(p, work, i):
    act = p["act"]; src = INBOX / act["src"]
    sw = work / f"a{i}"; sw.mkdir(parents=True, exist_ok=True)
    ramped = cineedit._segments(src, p["segs"], sw)
    n = int(round(p["dur"] * FPS)); hf = int(round(p["hit_rel"] * FPS))
    luma = cineedit.mean_luma(src)
    grade, gname, alpha = cineedit.grade_for(luma)
    zexpr = f"1.0+0.05*on/{n}+0.09*exp(-on/6)+if(gte(on,{hf}),0.07*exp(-(on-{hf})/5),0)"
    mark = REPO / "channel" / "brand-kit" / "watermark.png"
    chain = [f"[0:v]fps={FPS},scale=1620:2880:flags=lanczos,zoompan=z='{zexpr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
             f"{grade},format=yuv420p[base]",
             f"color=c={GOLD}:s={W}x{H}:d={p['dur'] + 0.5:.3f}:r={FPS},format=rgba,colorchannelmixer=aa={alpha}[fl]",
             f"[base][fl]overlay=enable='between(t,{p['hit_rel']:.3f},{p['hit_rel'] + 2 / FPS:.3f})'[fx]"]
    inputs = ["-i", str(ramped)]
    last = "[fx]"
    if mark.exists():
        inputs += ["-i", str(mark)]
        chain.append("[1:v]scale=iw*1.5:-1[mk]"); chain.append("[fx][mk]overlay=W-w-42:H-h-60:format=auto[br]"); last = "[br]"
    # level the clip's own sound to a common loudness (Flow clips arrive between -23 and -12 LUFS)
    m = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ramped), "-af", "ebur128", "-f", "null", "-"]).stderr
    lufs = float(re.findall(r"I:\s*(-?[\d.]+) LUFS", m)[-1])
    gain = max(-12.0, min(12.0, CLIP_LUFS - lufs))
    out = work / f"act{i}.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(chain),
         "-map", last, "-map", "0:a", "-af", f"volume={gain:.2f}dB", "-t", f"{p['dur']:.3f}", "-c:v", "libx264", "-crf", "15", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", str(out)], timeout=1800)
    return out, dict(grade=gname, clip_lufs=round(lufs, 1), gain_db=round(gain, 1))


def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def riser(length, rng):
    n = int(length * SR); p = np.arange(n) / n
    noise = rng.normal(0, 1, n)
    sig = band(noise, 200, 2500) * (1 - p) + band(noise, 2500, 9000) * p
    sig /= np.abs(sig).max() + 1e-9
    f = 150 * (900 / 150) ** p
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.28
    out = (sig * 0.8 + tone) * p ** 2.2
    out[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
    return out / (np.abs(out).max() + 1e-9)


def hit(rng):
    n = int(1.3 * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (38 + 90 * np.exp(-t * 22)) * t) * np.exp(-t * 3.2)
    crack = band(rng.normal(0, 1, n), 800, 7000) * np.exp(-t * 30) * 0.6
    body = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 8) * 0.5
    out = sub + crack + body
    return out / (np.abs(out).max() + 1e-9)


def whoosh(rng, length=0.5):
    n = int(length * SR)
    w = band(rng.normal(0, 1, n), 500, 5000) * np.sin(np.linspace(0, np.pi, n)) ** 2 * np.linspace(0.4, 1.0, n)
    return w / (np.abs(w).max() + 1e-9)


def build_sfx(plans, total, out):
    rng = np.random.default_rng(11)
    a = np.zeros(int((total + 1.5) * SR))
    def put(x, at, g):
        s = int(max(0, at) * SR); a[s:s + len(x)] += x[: max(0, len(a) - s)] * g
    for i, p in enumerate(plans):
        put(riser(1.1, rng), p["hit"] - 1.1, 0.50)
        put(hit(rng), p["hit"], 0.65)
        if i > 0: put(whoosh(rng), p["start"] - 0.30, 0.42)
    a /= max(1.0, float(np.abs(a).max()))
    pcm = (np.repeat(a[:, None], 2, axis=1) * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def text_filters(plans):
    parts, base = [], "[v0]"
    for i, p in enumerate(plans):
        t0, t1 = p["start"] + 0.15, p["start"] + 2.1
        txt = p["act"]["text"]
        parts.append(f"{base}drawtext=fontfile='{FONT}':text='{txt}':fontsize=124:fontcolor={GOLD}:borderw=0:shadowcolor=black@0.75:shadowx=6:shadowy=8:"
                     f"x=(w-text_w)/2:y='h*0.13+46*pow(1-min((t-{t0:.3f})/0.32\\,1)\\,2)':"
                     f"alpha='min((t-{t0:.3f})/0.25\\,1)*min(({t1:.3f}-t)/0.35\\,1)':enable='between(t,{t0:.3f},{t1:.3f})'[v{i + 1}]")
        base = f"[v{i + 1}]"
    return parts, base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "channel" / "flow" / "hero" / "qm-hero-20261027.mp4"))
    ap.add_argument("--bed", default=str(REPO / "assets" / "music" / "escape-1.mp3"))
    ap.add_argument("--no-voice", action="store_true")
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    bed = Path(args.bed)
    ba = beats.analyse(bed)
    bed_ss = float(ba["beats"][0])
    tb = [float(b - bed_ss) for b in ba["beats"] if b >= bed_ss]
    print(f"bed {bed.name}: {ba['bpm']} BPM, pulse {ba['strength']}, beat period {ba['period']:.3f}s")
    plans, body_end = plan_acts(tb)
    for p in plans:
        print(f"  act {p['act']['name']:6s} start {p['start']:.2f}s dur {p['dur']:.2f}s hit {p['hit']:.2f}s")
    work = Path(tempfile.mkdtemp(prefix="hero-"))
    try:
        bodies, info = [], []
        for i, p in enumerate(plans):
            f, d = render_act(p, work, i); bodies.append(f); info.append(d); print("  rendered", p["act"]["name"], d)
        # voice lines (just after the cut, or just after the hit when the hit comes early), then the closing line
        vo, spoken = [], []
        if not args.no_voice:
            for i, p in enumerate(plans):
                wav = work / f"vo{i}.wav"
                length, prov = reel._voice(p["act"]["line"], wav)
                at = p["start"] + reel.VO_DELAY if p["act"]["line_at"] == "early" else p["hit"] + 0.35
                nxt = plans[i + 1]["hit"] - 1.1 if i + 1 < len(plans) else body_end
                vo.append((at, wav, reel.VO_GAIN))
                spoken.append(dict(at=round(at, 2), ends=round(at + length, 2), act_ends=round(p["start"] + p["dur"], 2), line=p["act"]["line"], provider=prov,
                                   fits=(at + length) < (p["start"] + p["dur"] + 0.2) and (at + length) < p["hit"] - 1.1 + 0.05 + (99 if p["act"]["line_at"] == "after_hit" else 0)))
            cta_wav = work / "vo-cta.wav"
            cta_len, prov = reel._voice(CTA_LINE, cta_wav)
        else:
            cta_len, cta_wav = 1.8, None
        card_len = reel.card_seconds_for(cta_len, 3.2)
        png = reel.cta_card(work / "cta.png", CTA_HEAD, CTA_SUB)
        card = work / "cta.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-t", f"{card_len}", "-i", str(png), "-f", "lavfi", "-t", f"{card_len}",
             "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex",
             f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.25,fade=t=out:st={card_len - reel.END_FADE:.3f}:d={reel.END_FADE}[v]",
             "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-shortest", str(card)])
        card_start = body_end
        total = card_start + card_len
        if cta_wav: vo.append((card_start + reel.CTA_LEAD, cta_wav, reel.VO_GAIN * reel.CTA_VO_GAIN))
        listing = work / "acts.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in bodies + [card]), encoding="utf-8")
        joined = work / "joined.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)])
        # picture: text, one global grade, unsharp for the upscale, grain, vignette
        tf, last = text_filters(plans)
        g = [f"[0:v]eq=saturation=1.07:contrast=1.04,colorbalance=rs=-0.03:bs=0.04:rh=0.04:bh=-0.03,unsharp=5:5:0.35,noise=alls=4:allf=t+u,vignette=PI/5[v0]", *tf]
        script = work / "pic.txt"; script.write_text(";".join(g), encoding="utf-8")
        vid = work / "pic.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined), "-filter_complex", script.read_text(encoding="utf-8"), "-map", last, "-an",
             "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS), "-maxrate", "16M", "-bufsize", "32M", str(vid)], timeout=1800)
        # sound: clip audio, bed on the beat grid, sfx, sting, voice with sidechain ducking
        sfx = work / "sfx.wav"; build_sfx(plans, total, sfx)
        sting = work / "sting.wav"; sting_at = max(0.0, card_start - reel.card_sting(sting))
        inputs, chain, labels = ["-i", str(joined)], [], []
        for n, (at, wav, gain) in enumerate(vo, start=1):
            inputs += ["-i", str(wav)]; ms = int(at * 1000)
            chain.append(f"[{n}:a]volume={gain},adelay={ms}|{ms},apad[vo{n}]"); labels.append(f"[vo{n}]")
        nxt = len(vo) + 1
        if labels:
            chain.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0[vo]"); chain.append("[vo]asplit=2[vomix][vokey]")
        chain.append(f"[0:a]volume={reel.CLIP_GAIN}[clip]")
        under = ["[clip]"]
        inputs += ["-ss", f"{bed_ss:.3f}", "-stream_loop", "-1", "-i", str(bed)]
        ramp = f"0.26+({reel.CTA_BED_GAIN}-0.26)*clip((t-{card_start - 0.5:.3f})/0.5\\,0\\,1)"
        chain.append(f"[{nxt}:a]aresample=48000,atrim=0:{total:.3f},asetpts=N/SR/TB,volume='{ramp}':eval=frame[bed]"); under.append("[bed]"); nxt += 1
        inputs += ["-i", str(sfx)]; chain.append(f"[{nxt}:a]aresample=48000,volume=0.9[sfx]"); under.append("[sfx]"); nxt += 1
        inputs += ["-i", str(sting)]; ms = int(sting_at * 1000)
        chain.append(f"[{nxt}:a]aresample=48000,volume={reel.STING_GAIN},adelay={ms}|{ms},apad[sting]"); under.append("[sting]")
        chain.append(f"{''.join(under)}amix=inputs={len(under)}:normalize=0:duration=first[under]")
        if labels:
            chain.append("[under][vokey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400:makeup=1[ducked]")
            chain.append(f"[ducked][vomix]amix=inputs=2:normalize=0,atrim=0:{total:.3f},asetpts=N/SR/TB[mix]")
        else:
            chain.append(f"[under]atrim=0:{total:.3f},asetpts=N/SR/TB[mix]")
        mix = work / "mix.wav"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[mix]", "-ar", "48000", str(mix)])
        master = work / "master.wav"
        mastering = reel._master(mix, master, total)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(vid), "-i", str(master), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out)])
        report = dict(out=str(out), seconds=round(cineedit.probe_duration(out), 2), bed=bed.name, bpm=ba["bpm"], acts=[
            dict(name=p["act"]["name"], start=round(p["start"], 2), dur=round(p["dur"], 2), hit=round(p["hit"], 2), segs=[[round(a, 2), round(b, 2), round(s, 3)] for a, b, s in p["segs"]], **info[i])
            for i, p in enumerate(plans)], cta_at=round(card_start, 2), narration=spoken, mastering=mastering)
        (out.with_suffix(".json")).write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(json.dumps(report, indent=1)[:2500])
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
