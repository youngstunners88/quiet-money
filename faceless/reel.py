"""Three Flow clips compiled into one video: a voiceover threads them and lands a call to action.

The day's three clips are not three posts. They are three acts of one story, so the prompts are written as a set
(.claude/skills/faceless-flow) and this compiles them: each clip is edited by faceless/cineedit, joined with a short dip
through black, and carried by one quiet narration line per act over a music bed, ending on the CTA card.

The voice stays under the action on purpose: it is the thread, not the show. Clip sound keeps the hits; the bed fills
the gaps; the narration ducks everything else only while it speaks.

The ending is its own act (.claude/skills/faceless-rhythm). The card has no clip sound, so without help the energy falls
off a cliff at the last cut and the closing line sounds thin; the bed swells under it instead. The card holds for a beat
after the last word, then fades to black, so the sentence lands rather than being chopped by the end of the file.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from faceless import brand, cineedit

W, H, FPS = cineedit.W, cineedit.H, cineedit.FPS
DIP = 0.18                   # seconds of dip-to-black between acts: a breath, not a transition anyone notices
VO_DELAY = 0.45              # the line starts just after the cut, never on it
VO_GAIN, CLIP_GAIN, BED_GAIN = 1.0, 0.5, 0.17
DUCK = 0.35                  # what the clip sound and bed drop to while the voice speaks
# Every narration line is levelled to the same loudness before the mix: a TTS read falls away at the end of a sentence,
# and the closing line has no hits under it, so without this the CTA, the line that matters most, came out the quietest.
VO_LUFS = -16.0
CTA_VO_GAIN = 1.2            # +1.6 dB on the closing line: it is the payoff and nothing under it competes
CTA_BED_GAIN = 0.34          # the bed swells under the card so the last act is not a hole after the last hit
CTA_LEAD, CTA_HOLD = 0.35, 1.3   # the line starts after the card lands; the card holds this long after the last word
END_FADE = 0.7               # picture and sound fade out together; a hard stop on a live bed reads as a chopped sentence
# The platform standard the rest of the channel is mastered to (faceless/pipeline/render.py), applied in two passes so
# the gain is linear: single-pass loudnorm rides the level dynamically and pumped the bed back up at the very end.
TARGET_I, TARGET_TP, TARGET_LRA = -14.0, -1.5, 11.0
LOUDNESS = f"loudnorm=I={TARGET_I:g}:TP={TARGET_TP:g}:LRA={TARGET_LRA:g}"
TIMEOUT = cineedit.ENCODE_TIMEOUT
# The card lands on a sound, not into one (lesson L3): a whoosh into the cut, a low impact on it and a coin ping as the
# coin appears. Without it the last cut measured a 10 LU hole for a breath before the closing line started.
STING_GAIN = 0.5


def _run(cmd: list[str]) -> None:
    cineedit._run(cmd)


def cta_card(out: Path, headline: str, sub: str) -> Path:
    """The closing frame: the gold coin, the one line that asks for the follow, and the handle."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), (9, 9, 11))
    d = ImageDraw.Draw(im)
    coin = brand.coin(300)
    im.paste(coin, ((W - 300) // 2, 360), coin)
    rows = [(headline, brand.font("Anton-Regular.ttf", 76), 730, (255, 210, 63)),
            (sub, brand.font("Montserrat-ExtraBold.ttf", 34), 840, (232, 230, 225)),
            ("@quietmoneyrule", brand.font("Montserrat-Black.ttf", 40), 930, (255, 210, 63))]
    for text, font, y, fill in rows:
        wdt = d.textbbox((0, 0), text, font=font)[2]
        d.text(((W - wdt) // 2, y), text, font=font, fill=fill)
    im.save(out)
    return out


# Silence around a read is cut before timing anything: each voice provider pads its files differently, and padding
# counted as speech made every hold and every "line ends before its cut" measurement wrong (lesson L10).
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse,apad=pad_dur=0.08")


def _voice(text: str, out: Path) -> tuple[float, str]:
    """One narration line: trimmed to the speech, levelled to VO_LUFS so every line sits at the same height in the mix.
    Returns (spoken length, the provider that voiced it)."""
    from faceless.providers import tts
    raw = out.with_name(out.stem + "-raw.wav")
    provider, _timings = tts.synthesize(text, raw)
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
          "-af", f"{TRIM},loudnorm=I={VO_LUFS}:TP=-2:LRA=7,aresample=48000", "-ac", "2", str(out)])
    return cineedit.probe_duration(out), provider


def _dip(src: Path, out: Path, seconds: float = DIP) -> None:
    """Fade the tail of an act to black so the cut lands as a beat rather than a jolt."""
    dur = cineedit.probe_duration(src)
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
          "-vf", f"fade=t=out:st={max(0.0, dur - seconds):.3f}:d={seconds}",
          "-af", f"afade=t=out:st={max(0.0, dur - seconds):.3f}:d={seconds}",
          "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", str(out)])


def card_seconds_for(line_seconds: float, minimum: float = 3.2) -> float:
    """How long the CTA card stays up: the lead-in, the whole line, then a held beat before the fade."""
    return round(max(minimum, CTA_LEAD + line_seconds + CTA_HOLD), 2)


def card_sting(out: Path) -> float:
    """Whoosh, impact and coin ping for the card landing, written to `out`. Returns where the impact sits in the file,
    so the caller can place it exactly on the cut."""
    import wave

    import numpy as np

    from faceless.pipeline import music
    sr, lead = music.SR, 0.32
    rng = np.random.default_rng(7)
    n = int((lead + 1.4) * sr)
    a = np.zeros(n)
    wl = int(0.42 * sr)
    whoosh = music._bandpass(rng.normal(0, 1, wl), 500, 5000) * np.sin(np.linspace(0, np.pi, wl)) ** 2 * np.linspace(0.4, 1.0, wl)
    whoosh /= np.abs(whoosh).max() + 1e-9
    w0 = int((lead - 0.3) * sr)
    a[w0:w0 + wl] += whoosh * 0.5
    il = int(0.9 * sr)
    it = np.arange(il) / sr
    impact = np.sin(2 * np.pi * (40 + 70 * np.exp(-it * 18)) * it) * np.exp(-it * 4.5)
    i0 = int(lead * sr)
    a[i0:i0 + il] += impact * 0.9
    ping = music.hit("coin", rng)
    p0 = int((lead + 0.12) * sr)
    a[p0:p0 + len(ping)] += ping[: n - p0] * 1.2
    a /= max(1.0, float(np.abs(a).max()))
    pcm = (np.repeat(a[:, None], 2, axis=1) * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return lead


def _master(mix_wav: Path, out_wav: Path, total: float) -> dict:
    """Two-pass loudness: measure, then apply one linear gain to hit the target, then the end fade."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mix_wav), "-af", f"{LOUDNESS}:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=TIMEOUT)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    second = (f"{LOUDNESS}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mix_wav), "-af",
          f"{second},afade=t=out:st={max(0.0, total - END_FADE):.3f}:d={END_FADE},aresample=48000", str(out_wav)])
    return {"measured_i": float(m["input_i"]), "offset": float(m["target_offset"])}


def build(acts: list[dict], out: Path, *, cta_line: str, cta_headline: str = "ONE MONEY RULE A DAY",
          cta_sub: str = "Real numbers. No hype.", bed: Path | None = None, cta_seconds: float = 3.2) -> dict:
    """acts: [{"src": clip, "impact": seconds, "line": narration}]. Returns what was built and how it measures."""
    out = Path(out)
    work = Path(tempfile.mkdtemp(prefix="reel-"))
    try:
        bodies, starts, t = [], [], 0.0
        for i, act in enumerate(acts):
            body = work / f"act{i}.mp4"
            cineedit.edit(Path(act["src"]), body, impact=float(act["impact"]), card_seconds=0)
            dipped = work / f"act{i}d.mp4"
            _dip(body, dipped)
            starts.append(t)
            t += cineedit.probe_duration(dipped)
            bodies.append(dipped)

        # The closing line is voiced first, because its length decides how long the card stays up.
        cta_wav = work / "vo-cta.wav"
        cta_len, cta_voice = _voice(cta_line, cta_wav)
        card_len = card_seconds_for(cta_len, cta_seconds)
        card_png = cta_card(work / "cta.png", cta_headline, cta_sub)
        card = work / "cta.mp4"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-t", f"{card_len}",
              "-i", str(card_png), "-f", "lavfi", "-t", f"{card_len}", "-i", "anullsrc=r=48000:cl=stereo",
              "-filter_complex",
              f"[0:v]fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.25,"
              f"fade=t=out:st={card_len - END_FADE:.3f}:d={END_FADE}[v]",
              "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
              "-c:a", "aac", "-b:a", "192k", "-shortest", str(card)])
        card_start = t
        bodies.append(card)

        listing = work / "acts.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in bodies), encoding="utf-8")
        joined = work / "joined.mp4"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
              "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", str(joined)])
        total = cineedit.probe_duration(joined)

        # One narration line per act, placed just after each cut, plus the closing line over the card.
        vo, spoken = [], []
        for i, a in enumerate(acts):
            if not a.get("line"):
                continue
            wav = work / f"vo{i}.wav"
            length, voice = _voice(a["line"], wav)
            at = starts[i] + VO_DELAY
            vo.append((at, wav, VO_GAIN))
            spoken.append({"at": round(at, 2), "seconds": round(length, 2), "ends": round(at + length, 2),
                           "act_ends": round(starts[i + 1] if i + 1 < len(starts) else card_start, 2), "line": a["line"],
                           "voice": voice})
        cta_at = card_start + CTA_LEAD
        vo.append((cta_at, cta_wav, VO_GAIN * CTA_VO_GAIN))
        spoken.append({"at": round(cta_at, 2), "seconds": round(cta_len, 2), "ends": round(cta_at + cta_len, 2),
                       "act_ends": round(total, 2), "line": cta_line, "cta": True, "voice": cta_voice})

        inputs, chain, vo_labels = ["-i", str(joined)], [], []
        for n, (at, wav, gain) in enumerate(vo, start=1):
            inputs += ["-i", str(wav)]
            ms = int(at * 1000)
            chain.append(f"[{n}:a]volume={gain},adelay={ms}|{ms},apad[vo{n}]")
            vo_labels.append(f"[vo{n}]")
        chain.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:normalize=0[vo]")
        chain.append("[vo]asplit=2[vomix][vokey]")
        nxt, under = len(vo) + 1, ["[clip]"]
        chain.append(f"[0:a]volume={CLIP_GAIN}[clip]")
        if bed and Path(bed).exists():
            inputs += ["-stream_loop", "-1", "-i", str(bed)]
            # The bed rides up over 0.5s into the card so the last act has body under the closing line.
            ramp = f"{BED_GAIN}+({CTA_BED_GAIN}-{BED_GAIN})*clip((t-{card_start - 0.5:.3f})/0.5\\,0\\,1)"
            chain.append(f"[{nxt}:a]atrim=0:{total:.3f},asetpts=N/SR/TB,volume='{ramp}':eval=frame[bed]")
            under.append("[bed]")
            nxt += 1
        sting_wav = work / "sting.wav"
        sting_at = max(0.0, card_start - card_sting(sting_wav))
        inputs += ["-i", str(sting_wav)]
        ms = int(sting_at * 1000)
        chain.append(f"[{nxt}:a]aresample=48000,volume={STING_GAIN},adelay={ms}|{ms},apad[sting]")
        under.append("[sting]")
        chain.append(f"{''.join(under)}amix=inputs={len(under)}:normalize=0:duration=first[under]")
        chain.append("[under][vokey]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400:makeup=1[ducked]")
        chain.append(f"[ducked][vomix]amix=inputs=2:normalize=0,atrim=0:{total:.3f},asetpts=N/SR/TB[mix]")
        mix_wav = work / "mix.wav"
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
              "-filter_complex", ";".join(chain), "-map", "[mix]", "-ar", "48000", str(mix_wav)])

        master_wav = work / "master.wav"
        mastering = _master(mix_wav, master_wav, total)
        out.parent.mkdir(parents=True, exist_ok=True)
        _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(joined), "-i", str(master_wav),
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart", str(out)])
        return {"out": str(out), "seconds": round(cineedit.probe_duration(out), 2), "acts": len(acts),
                "act_starts": [round(s, 2) for s in starts], "cta_at": round(card_start, 2),
                "card_seconds": card_len, "bed": str(bed) if bed else None, "sting_at": round(sting_at, 2),
                "narration": spoken,
                "mastering": mastering}
    finally:
        shutil.rmtree(work, ignore_errors=True)
