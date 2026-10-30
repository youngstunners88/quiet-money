#!/usr/bin/env python3
"""Celebration Short for the free Money Reset checklist giveaway (1,700 views). ffmpeg does the cuts, transitions, glitch and mix;
PIL only draws text/background assets and the count-up frames; numpy synthesises the sfx. No paid APIs.
usage: .venv/bin/python tools/giveaway_short.py [--out PATH] [--no-voice]"""
import argparse, subprocess, sys, tempfile, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
W, H, FPS, SR = 1080, 1920, 30, 48000
GOLD = (255, 210, 63); BLACK = (11, 11, 15); WHITE = (245, 245, 240)
FONT = str(REPO / "assets/fonts/Anton-Regular.ttf")
LOGO = REPO / "channel/brand-kit/watermark.png"
MUSIC = REPO / "assets/music/playbook-1.mp3"
T = 0.28  # transition length

# (hold seconds, transition INTO this scene, draw spec, voice key)
SCENES = [
    dict(len=2.8, tr=None,        kind="count", glitch=False),
    dict(len=2.6, tr="slideleft", lines=[("72", 330, GOLD), ("VIDEOS", 200, WHITE)], glitch=False, bg=1),
    dict(len=2.8, tr="zoomin",    lines=[("8", 330, GOLD), ("SUBSCRIBERS", 150, WHITE)], glitch=True, bg=2),
    dict(len=2.4, tr="fadewhite", lines=[("THANK", 260, WHITE), ("YOU", 260, GOLD)], glitch=False, bg=3),
    dict(len=2.4, tr="pixelize",  lines=[("HERE'S", 220, WHITE), ("A GIFT", 300, GOLD)], glitch=True, bg=4),
    dict(len=3.0, tr="radial",    lines=[("FREE", 400, GOLD), ("7-DAY MONEY", 130, WHITE), ("RESET CHECKLIST", 130, WHITE)], glitch=False, bg=5),
    dict(len=2.9, tr="slideup",   kind="list", glitch=True, bg=0),
    dict(len=2.4, tr="circleopen", lines=[("ONE BOX", 250, GOLD), ("A DAY", 250, WHITE)], glitch=False, bg=1),
    dict(len=2.6, tr="hblur",     lines=[("NO HYPE", 230, WHITE), ("NO PROMISES", 160, GOLD)], glitch=True, bg=2),
    dict(len=2.6, tr="diagtl",    lines=[("LINK", 330, GOLD), ("IN BIO", 330, WHITE)], glitch=False, bg=3),
    dict(len=2.95, tr="squeezeh",  kind="end", glitch=False, bg=4),
]
# which voice line starts with which scene (index), seconds after scene start
VOICE = [("a", 0, 0.25), ("b", 1, 0.2), ("c", 2, 0.2), ("d", 4, 0.15), ("e", 5, 0.25), ("f", 7, 0.15), ("g", 9, 0.2)]
LINES = {"a": "Quiet Money just passed seventeen hundred views.", "b": "Seventy-two videos.", "c": "Eight subscribers. Thank you.",
         "d": "So here's a gift.", "e": "A free seven-day Money Reset checklist.", "f": "One small box a day.", "g": "Link in bio."}


def run(cmd, timeout=900):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
    if r.returncode: raise RuntimeError(" ".join(map(str, cmd))[:300] + "\n" + r.stderr[-800:])
    return r


def font(sz): return ImageFont.truetype(FONT, sz)


def bg_image(variant, path):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = [(0.5, 0.45), (0.2, 0.3), (0.8, 0.6), (0.5, 0.75), (0.25, 0.7), (0.75, 0.25)][variant % 6]
    d = np.sqrt(((xx / W - cx) * 1.1) ** 2 + ((yy / H - cy) * 0.7) ** 2)
    glow = np.clip(1 - d / 0.75, 0, 1) ** 2
    img = np.zeros((H, W, 3), np.float32) + np.array(BLACK, np.float32)
    img += glow[..., None] * np.array([70, 52, 8], np.float32)
    stripe = (((xx + yy * 0.6) % 120) < 3).astype(np.float32) * 9   # faint diagonal gold hatching
    img += stripe[..., None] * np.array([1.0, 0.8, 0.2], np.float32) * (variant % 2 + 0.6)
    vig = np.clip(1 - ((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) * 1.1, 0.35, 1)
    img *= vig[..., None]
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((1242, 2208), Image.BICUBIC).save(path)


def text_png(lines, path, scale=1.25, gap=10):
    """Gold/white Anton lines, centred, soft shadow, drawn at `scale` x for supersampling."""
    w, h = int(W * scale), int(H * scale)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0)); sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    boxes = []; total = 0
    for t, sz, col in lines:
        f = font(int(sz * scale)); b = f.getbbox(t); boxes.append((t, f, col, b)); total += (b[3] - b[1]) + gap * scale
    y = (h - total) / 2
    for t, f, col, b in boxes:
        x = (w - (b[2] - b[0])) / 2 - b[0]
        ImageDraw.Draw(sh).text((x + 8, y - b[1] + 12), t, font=f, fill=(0, 0, 0, 200))
        ImageDraw.Draw(layer).text((x, y - b[1]), t, font=f, fill=col + (255,))
        y += (b[3] - b[1]) + gap * scale
    sh = sh.filter(ImageFilter.GaussianBlur(10 * scale))
    out = Image.alpha_composite(sh, layer); out.save(path)


def list_png(path, scale=1.25):
    w, h = int(W * scale), int(H * scale)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rows = ["FIND THE LEAKS", "PAY YOURSELF FIRST", "SPLIT EVERY PAYCHECK", "TACKLE THE DEBT", "BUILD A BUFFER", "STOP THE FEES", "LOCK IN RAISES"]
    d.text((w / 2, 300 * scale), "THE 7 DAYS", font=font(int(150 * scale)), fill=GOLD + (255,), anchor="mm")
    y0 = 440 * scale; step = 150 * scale
    for i, r in enumerate(rows):
        y = y0 + i * step
        d.rounded_rectangle((110 * scale, y - 44 * scale, 190 * scale, y + 36 * scale), 10 * scale, outline=GOLD + (255,), width=int(7 * scale))
        d.text((250 * scale, y - 4 * scale), f"DAY {i+1}  {r}", font=font(int(62 * scale)), fill=WHITE + (255,), anchor="lm")
    sh = im.filter(ImageFilter.GaussianBlur(8 * scale)); sh = Image.eval(sh, lambda v: v)
    black = Image.new("RGBA", (w, h), (0, 0, 0, 255)); black.putalpha(sh.getchannel("A").point(lambda a: int(a * 0.8)))
    Image.alpha_composite(black, im).save(path)


def count_frames(dirp, seconds=2.8):
    n = int(seconds * FPS); anim = int(1.7 * FPS)
    f_big, f_small = font(300), font(190)
    for i in range(n):
        p = min(1.0, i / anim); v = int(round(1700 * (1 - (1 - p) ** 3)))
        s = f"{v:,}"
        im = Image.open(dirp / "bg0.png").crop((81, 144, 81 + W, 144 + H)).convert("RGB")
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        pulse = 1 + (0.06 * max(0, 1 - (i - anim) / 6) if i >= anim else 0)
        fb = font(int(300 * pulse))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((W / 2 + 8, 860 + 12), s, font=fb, fill=(0, 0, 0, 220), anchor="mm")
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        d.text((W / 2, 860), s, font=fb, fill=GOLD + (255,), anchor="mm")
        d.text((W / 2, 1090), "VIEWS", font=f_small, fill=WHITE + (255,), anchor="mm")
        d.text((W / 2, 420), "QUIET MONEY PASSED", font=font(84), fill=WHITE + (255,), anchor="mm")
        im = Image.alpha_composite(Image.alpha_composite(im.convert("RGBA"), sh), lay).convert("RGB")
        im.save(dirp / f"c{i:04d}.png")
    return n


def synth_sfx(total, cuts, cnt_start, cnt_end):
    n = int(total * SR); out = np.zeros((n, 2), np.float32); rng = np.random.default_rng(7)
    def add(sig, t, pan=0.0):
        a = int(t * SR); b = min(n, a + len(sig))
        if a < 0 or a >= n: return
        sig = sig[: b - a]; out[a:b, 0] += sig * (1 - pan * 0.4); out[a:b, 1] += sig * (1 + pan * 0.4)
    def hit(kind):
        t = np.arange(int(0.55 * SR)) / SR
        sub = np.sin(2 * np.pi * (46 + 90 * np.exp(-t * 18)) * t) * np.exp(-t * 7)
        nz = rng.standard_normal(len(t)) * np.exp(-t * 28) * 0.35
        click = np.sin(2 * np.pi * 2100 * t) * np.exp(-t * 90) * 0.25
        mix = {"whip": sub * 0.9 + nz * 1.2, "glitch": sub * 0.7 + click * 1.6 + nz * 0.5, "flash": sub + nz * 0.6 + np.sin(2 * np.pi * 880 * t) * np.exp(-t * 14) * 0.3}[kind]
        return (mix * 0.55).astype(np.float32)
    def riser(dur, f0=180, f1=2400):
        t = np.arange(int(dur * SR)) / SR; k = t / dur
        ph = 2 * np.pi * (f0 * t + (f1 - f0) * (t * k) / 2)
        nz = rng.standard_normal(len(t)); lp = np.convolve(nz, np.ones(6) / 6, mode="same") * (k ** 2)
        return ((np.sin(ph) * 0.35 + lp * 0.45) * (k ** 1.8) * 0.5).astype(np.float32)
    kinds = ["whip", "flash", "flash", "glitch", "flash", "whip", "glitch", "flash", "glitch", "whip"]
    for i, c in enumerate(cuts):
        add(riser(min(0.75, c + 0.25), ), max(0, c - 0.75) if c >= 0.75 else 0, 0)
        add(hit(kinds[i % len(kinds)]), c, (-1) ** i * 0.5)
    # count-up ticks
    tk = np.arange(int(0.03 * SR)) / SR; tick = (np.sin(2 * np.pi * 1500 * tk) * np.exp(-tk * 200) * 0.2).astype(np.float32)
    tt = cnt_start
    while tt < cnt_end:
        add(tick, tt); p = (tt - cnt_start) / (cnt_end - cnt_start); tt += 0.045 + 0.09 * p
    # opening hit on the final 1,700
    add(hit("flash") * 1.2, cnt_end)
    # end-card chime
    t = np.arange(int(1.4 * SR)) / SR
    chime = sum(np.sin(2 * np.pi * f * t) for f in (784, 1175, 1568)) * np.exp(-t * 2.6) * 0.09
    add(chime.astype(np.float32), total - 3.15)
    return out


def read_wav(p):
    with wave.open(str(p)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
        ch = w.getnchannels()
        a = a.reshape(-1, ch)
        if ch == 1: a = np.repeat(a, 2, 1)
        assert w.getframerate() == SR, w.getframerate()
    return a


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REPO / "distribution/queue/2026-10-30/giveaway/video.mp4"))
    ap.add_argument("--no-voice", action="store_true"); ap.add_argument("--work", default="")
    args = ap.parse_args()
    work = Path(args.work or tempfile.mkdtemp(prefix="giveaway-")); work.mkdir(parents=True, exist_ok=True)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)

    for v in range(6): bg_image(v, work / f"bg{v}.png")
    # bg0 is also used 1:1 for count frames (crop of the 1.15x image)
    n_count = count_frames(work)
    clips = []
    for i, sc in enumerate(SCENES):
        L = sc["len"] + (T if i < len(SCENES) - 1 else 0)   # each clip runs through the next transition
        clip = work / f"s{i}.mp4"; kind = sc.get("kind")
        glitch = (f"[v0]rgbashift=rh=-22:bh=22:gv=10:enable='lt(t,0.32)',noise=alls=40:allf=t:enable='lt(t,0.32)'[v1]" if sc["glitch"] else "[v0]null[v1]")
        if kind == "count":
            run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", FPS, "-i", work / "c%04d.png", "-vf",
                 f"tpad=stop_mode=clone:stop={int(L*FPS)}, trim=duration={L},zoompan=z='1+0.0009*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
                 f"rgbashift=rh=-18:bh=18:enable='lt(t,0.2)'",
                 "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-r", FPS, clip])
        else:
            if kind == "list": list_png(work / f"t{i}.png")
            elif kind == "end": pass
            else: text_png(sc["lines"], work / f"t{i}.png")
            pop = "if(lt(t,0.16),0.55+0.55*t/0.16,if(lt(t,0.30),1.10-0.10*(t-0.16)/0.14,1.0+0.03*(t-0.30)))"
            bgmove = f"crop={W}:{H}:x='81+30*sin(t*0.9+{i})':y='144+40*t/{L}*{1 if i%2 else -1}+60'"
            fc = (f"[0:v]{bgmove}[bgv];"
                  f"[1:v]scale=w='iw*({pop})/1.25':h=-1:eval=frame[tx];[bgv][tx]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame[v0];")
            if kind == "end":
                # logo drops in, wordmark, offer and disclaimer
                endlay = work / "end.png"
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
                logo = Image.open(LOGO).convert("RGBA"); logo.thumbnail((420, 420)); lay.alpha_composite(logo, ((W - logo.width) // 2, 330))
                d.text((W / 2, 860), "QUIET MONEY", font=font(170), fill=GOLD + (255,), anchor="mm")
                d.text((W / 2, 1030), "FREE 7-DAY MONEY", font=font(98), fill=WHITE + (255,), anchor="mm")
                d.text((W / 2, 1140), "RESET CHECKLIST", font=font(98), fill=WHITE + (255,), anchor="mm")
                d.rounded_rectangle((150, 1270, 930, 1400), 24, fill=GOLD + (255,))
                d.text((W / 2, 1335), "LINK IN BIO", font=font(100), fill=BLACK + (255,), anchor="mm")
                d.text((W / 2, 1650), "Educational content, not financial advice.", font=ImageFont.truetype(str(REPO / "assets/fonts/Montserrat-ExtraBold.ttf"), 34), fill=(200, 200, 195, 255), anchor="mm")
                sh = lay.filter(ImageFilter.GaussianBlur(10)); blk = Image.new("RGBA", (W, H), (0, 0, 0, 255)); blk.putalpha(sh.getchannel("A").point(lambda a: int(a * 0.7)))
                Image.alpha_composite(blk, lay).save(work / f"t{i}.png")
                fc = (f"[0:v]{bgmove}[bgv];[1:v]scale=w='iw*({pop})*1.0':h=-1:eval=frame[tx];[bgv][tx]overlay=x='(W-w)/2':y='(H-h)/2':eval=frame[v0];")
            fc += glitch.replace("[v0]", "[v0]") + ";[v1]format=yuv420p[vo]"
            run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", FPS, "-t", L, "-i", work / f"bg{sc.get('bg',0)}.png",
                 "-loop", "1", "-framerate", FPS, "-t", L, "-i", work / f"t{i}.png", "-filter_complex", fc, "-map", "[vo]",
                 "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-r", FPS, clip])
        clips.append(clip)

    # xfade chain
    inputs = []; for_ = []
    for c in clips: inputs += ["-i", c]
    starts = []; cum = 0.0; prev = "0:v"; filt = []
    for i in range(1, len(SCENES)):
        cum += SCENES[i - 1]["len"]; starts.append(cum)
        lab = f"x{i}"
        filt.append(f"[{prev}][{i}:v]xfade=transition={SCENES[i]['tr']}:duration={T if SCENES[i]['tr']!='fadewhite' else 0.2}:offset={cum:.3f}[{lab}]")
        prev = lab
    total = cum + SCENES[-1]["len"]
    # brand layer: gold progress bar + corner Q watermark + short zoom pulse on every cut
    filt.append(f"[{prev}]drawbox=x=0:y=0:w='iw*t/{total:.3f}':h=12:color=0xFFD23F@1:t=fill[pb];"
                f"movie={LOGO},scale=120:-1,format=rgba,colorchannelmixer=aa=0.85[wm];[pb][wm]overlay=x=W-w-36:y=70:enable='lt(t,{starts[-1]-0.1:.3f})',format=yuv420p[vout]")
    silent = work / "silent.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[vout]", "-c:v", "libx264", "-crf", "15",
         "-preset", "slow", "-pix_fmt", "yuv420p", "-r", FPS, "-t", f"{total:.3f}", silent])

    # ---- audio ----
    cuts = [s + 0.1 for s in starts]
    cnt_end = 1.7
    sfx = synth_sfx(total, cuts, 0.15, cnt_end)
    n = sfx.shape[0]
    # bed: loop-safe slice, low-passed, faded
    bedw = work / "bed.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "4", "-i", MUSIC, "-t", f"{total+1:.2f}", "-ac", "2", "-ar", SR, "-af",
         f"lowpass=f=5200,afade=t=in:d=0.6,afade=t=out:st={total-1.6:.2f}:d=1.6", bedw])
    bed = read_wav(bedw)[:n]
    if len(bed) < n: bed = np.pad(bed, ((0, n - len(bed)), (0, 0)))
    voice = np.zeros((n, 2), np.float32); duck = np.ones(n, np.float32); vcount = 0
    if not args.no_voice:
        vdir = REPO / ".." / ".." if False else None
        from faceless import reel
        for key, si, off in VOICE:
            wav = work / f"v_{key}.wav"
            if not wav.exists():
                try: reel._voice(LINES[key], wav)
                except Exception as e: print("voice failed, skipping:", str(e)[:120]); continue
            a = read_wav(wav); t0 = starts[si - 1] + off if si > 0 else off
            a0 = int(t0 * SR); a1 = min(n, a0 + len(a))
            voice[a0:a1] += a[: a1 - a0]
            ramp = int(0.12 * SR); lo, hi = max(0, a0 - ramp), min(n, a1 + ramp * 2)
            duck[lo:hi] = np.minimum(duck[lo:hi], 0.38); vcount += 1
    # smooth duck
    k = int(0.15 * SR); duck = np.convolve(duck, np.ones(k) / k, mode="same")
    bed *= 0.50 * duck[:, None]
    voice *= 1.0
    mix = bed + voice * 1.0 + sfx * 0.95
    mixw = work / "mix.wav"
    peak = np.abs(mix).max(); mix = mix / max(1.0, peak / 0.9)
    with wave.open(str(mixw), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    # two-pass loudnorm to -14 LUFS, TP -1.5
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mixw), "-af", "loudnorm=I=-14:TP=-1.8:LRA=9:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    import json, re
    js = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    ln = (f"loudnorm=I=-14:TP=-1.8:LRA=9:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}"
          f":measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true,alimiter=limit=0.66:level=disabled:attack=2:release=60,volume=0.9dB,alimiter=limit=0.78:level=disabled")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", mixw, "-af", ln, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", SR,
         "-shortest", "-movflags", "+faststart", out])
    print(f"wrote {out} total={total:.2f}s cuts={[round(c,2) for c in cuts]} voice_lines={vcount}")


if __name__ == "__main__":
    main()
