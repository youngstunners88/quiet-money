"""Recut desk: fix a finished video without making it again.

A rendered video sometimes has a few shots that do not belong (a body that moves in a way nothing explains, a figure lying on ice) while the
voice-over over them is fine. Re-rendering throws away a good take to fix a bad second, so this desk edits the file: it finds the shot
boundaries, finds the generator's watermark, and then cuts, covers, scores and brands the cut in two encode passes.

Two ways to lose a bad shot, and the difference is the whole craft:
  --drop  A-B   the seconds leave the video: picture and sound both go. Use it when the line over them is worth nothing.
  --cover A-B   the seconds keep their sound and lose their picture: the last clean frame before A is held under them with a slow push in,
                so the sentence survives and the eye sees a deliberate hold instead of a glitch. Use it when the line matters.

Joins are hard cuts (right for short form) with a 20 ms audio fade either side so no join clicks. The logo badge is drawn to the detected
watermark box, scrim first and mark on top, so the corner reads as branding and not as a patch over something.

  python -m faceless recut inspect VIDEO                     shot list, watermark box, contact sheet
  python -m faceless recut apply VIDEO --cover 12.4-15.2 --drop 31.0-34.8 --music escape --logo auto -o OUT.mp4
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from faceless import config
from faceless.config import Paths
from faceless.fsutil import write_atomic

FFMPEG_TIMEOUT = 3600
PROBE_TIMEOUT = 120
LOGO = Paths.root / "channel" / "brand-kit" / "watermark.png"
MUSIC_DIR = Paths.root / "assets" / "music"
JOIN_FADE = 0.02          # seconds of audio fade either side of a join: enough to kill a click, too short to hear
SAMPLES = 36              # frames sampled for watermark detection


# ---------------------------------------------------------------- probing

def probe(path: Path) -> dict:
    """Duration, size, frame rate and whether the file carries sound."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-show_entries", "stream=codec_type,width,height,r_frame_rate", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=PROBE_TIMEOUT, check=True).stdout
    d = json.loads(out)
    v = next((s for s in d.get("streams", []) for _ in [0] if s.get("codec_type") == "video"), {})
    num, _, den = (v.get("r_frame_rate") or "24/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 24.0
    return {"path": str(path), "seconds": float(d.get("format", {}).get("duration") or 0.0),
            "width": int(v.get("width") or 0), "height": int(v.get("height") or 0), "fps": round(fps, 3),
            "has_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


def shots(path: Path, seconds: float, threshold: float = 0.25, min_shot: float = 0.25) -> list[dict]:
    """Shot boundaries, by ffmpeg's scene score. A short-form cut lands on these; a cut anywhere else is visible.

    The scores are written to a file rather than read off the pipe: `metadata=print` goes to ffmpeg's log, not to stdout,
    so reading stdout silently returns no cuts at all and the whole video looks like one shot."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as t:
        meta = Path(t.name)
    try:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path),
             "-vf", f"select='gt(scene,{threshold})',metadata=print:file={meta}", "-an", "-f", "null", "-"],
            capture_output=True, text=True, timeout=FFMPEG_TIMEOUT, check=True)
        text = meta.read_text(encoding="utf-8", errors="replace")
    finally:
        meta.unlink(missing_ok=True)

    cuts = []
    for line in text.splitlines():
        if "pts_time:" in line:
            try:
                cuts.append(round(float(line.split("pts_time:")[1].split()[0]), 3))
            except (IndexError, ValueError):
                continue
    bounds = [0.0] + [c for c in sorted(set(cuts)) if 0.0 < c < seconds] + [round(seconds, 3)]
    # a run of near-identical frames can score over the threshold twice in a row and leave a sliver of a few frames;
    # a sliver is not a shot anyone cuts on, so it joins the shot before it
    kept = [bounds[0]]
    for b in bounds[1:-1]:
        if b - kept[-1] >= min_shot:
            kept.append(b)
    kept.append(bounds[-1])
    return [{"i": i, "start": a, "end": b, "seconds": round(b - a, 3)}
            for i, (a, b) in enumerate(zip(kept, kept[1:])) if b - a > 0.04]


# ---------------------------------------------------------------- watermark

def _sample_frames(path: Path, seconds: float, n: int = SAMPLES) -> np.ndarray:
    """n greyscale frames spread over the video, as one (n, h, w) array."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    try:
        frames = []
        for k in range(n):
            cap.set(cv2.CAP_PROP_POS_MSEC, (seconds * 1000.0) * (k + 0.5) / n)
            ok, img = cap.read()
            if ok:
                frames.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32))
    finally:
        cap.release()
    if len(frames) < 4:
        raise RuntimeError(f"could not read enough frames from {path}")
    return np.stack(frames)


def find_watermark(path: Path, seconds: float, top: int = 4) -> dict:
    """Locate a burnt-in watermark: pixels that never change while the picture behind them does, with edges of their own.

    A generator's mark is the only thing in a moving shot that is both perfectly still and not flat. Stillness alone is not
    enough (a lamp in a locked-off shot is still too), so candidates are scored on stillness, on being big enough to be a
    mark, and on sitting near an edge where marks are put. Every candidate is returned: when the top one is wrong, pass the
    right box to `apply` with --watermark-box."""
    import cv2

    g = _sample_frames(path, seconds)
    n, h, w = g.shape
    temporal = g.std(axis=0)                                   # how much each pixel moves over the video
    spatial = np.abs(cv2.Laplacian(g.mean(axis=0), cv2.CV_32F))  # how much detail sits at each pixel
    moving = float(np.median(temporal))
    if moving < 1e-3:                                          # a still picture: nothing to tell a mark apart from the rest
        return {"found": False, "reason": "the picture barely moves, so a static mark cannot be told from the shot",
                "candidates": []}
    still = temporal < max(0.35 * moving, 0.6)
    detailed = spatial > max(float(np.percentile(spatial, 92)), 1.5)
    # Opening is noise suppression, so it runs only when there is noise to suppress. On a grainy video the still-and-
    # detailed pixels cover much of the frame and closing alone would merge them into one blob that swallows the mark and
    # is then thrown out for being frame-sized; opening first drops that speckle. On a clean video the mark survives as a
    # thin scatter of edge pixels, and the same opening erases it completely, so there the mask goes straight to closing,
    # which joins the strokes into the shape. The closing kernel follows the frame, not a fixed pixel count.
    raw = (still & detailed).astype(np.uint8)
    close_k = max(5, 2 * int(min(w, h) / 140) + 1)
    if float(raw.mean()) > 0.01:
        raw = cv2.morphologyEx(raw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, np.ones((close_k, close_k), np.uint8))

    min_area = max(80.0, 0.0002 * w * h)                       # smaller than this is a highlight, not a mark
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    cands = []
    for i in range(1, count):
        x, y, bw, bh, area = (int(v) for v in stats[i])
        if area < min_area or bw > 0.6 * w or bh > 0.45 * h or bw < 0.02 * w or bh < 0.008 * h:
            continue
        cx, cy = x + bw / 2, y + bh / 2
        edge = min(cx, w - cx) / (w / 2), min(cy, h - cy) / (h / 2)
        edginess = 1.0 - min(edge)                             # 1.0 hard against an edge, 0.0 dead centre
        stillness = float(temporal[y:y + bh, x:x + bw].mean() / moving)
        score = (area / min_area) ** 0.5 * (1.0 - min(stillness, 1.0)) * (0.35 + 0.65 * edginess)
        cands.append({"box": {"x": x, "y": y, "w": bw, "h": bh}, "area_px": area,
                      "corner": ("top" if cy < h / 2 else "bottom") + "-" + ("left" if cx < w / 2 else "right"),
                      "stillness": round(stillness, 3), "edginess": round(edginess, 3), "score": round(score, 3)})
    cands.sort(key=lambda c: c["score"], reverse=True)
    if not cands:
        return {"found": False, "reason": "no still, detailed cluster big enough to be a mark: the video may carry none",
                "candidates": []}
    best = cands[0]
    return {"found": True, "frame": {"w": w, "h": h}, "candidates": cands[:top], **best}


# ---------------------------------------------------------------- contact sheet

def contact_sheet(path: Path, shot_list: list[dict], out: Path, cols: int = 6, tile: int = 220) -> Path:
    """One labelled frame per shot, tiled, so a person can name the shots to lose by number."""
    import cv2
    from PIL import Image, ImageDraw, ImageFont

    cap = cv2.VideoCapture(str(path))
    thumbs = []
    try:
        for s in shot_list:
            cap.set(cv2.CAP_PROP_POS_MSEC, (s["start"] + min(0.25, s["seconds"] / 2)) * 1000.0)
            ok, img = cap.read()
            if not ok:
                continue
            im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            im.thumbnail((tile, tile))
            thumbs.append((s, im))
    finally:
        cap.release()
    if not thumbs:
        raise RuntimeError("no frames could be read for the contact sheet")

    pad, label_h = 8, 26
    cell_w = max(im.width for _, im in thumbs) + pad
    cell_h = max(im.height for _, im in thumbs) + pad + label_h
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + pad, rows * cell_h + pad), (16, 16, 18))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(Paths.fonts / "Montserrat-ExtraBold.ttf"), 14)
    except OSError:
        font = ImageFont.load_default()
    for k, (s, im) in enumerate(thumbs):
        cx, cy = pad + (k % cols) * cell_w, pad + (k // cols) * cell_h
        sheet.paste(im, (cx, cy))
        draw.text((cx + 2, cy + im.height + 4), f"#{s['i']}  {s['start']:.2f}-{s['end']:.2f}s", (235, 200, 120), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=92)
    return out


def inspect(path: Path, out_dir: Path | None = None, threshold: float = 0.25) -> dict:
    """Everything needed to decide what to cut: shots, watermark box, contact sheet."""
    path = Path(path)
    out_dir = Path(out_dir or (Paths.root / "production" / "recut" / path.stem))
    info = probe(path)
    if info["seconds"] <= 0:
        raise RuntimeError(f"{path} has no readable duration")
    sl = shots(path, info["seconds"], threshold)
    mark = find_watermark(path, info["seconds"])
    sheet = contact_sheet(path, sl, out_dir / "shots.jpg")
    report = {"video": info, "shots": sl, "scene_threshold": threshold, "watermark": mark,
              "contact_sheet": str(sheet), "inspected": config.today_utc().isoformat()}
    write_atomic(out_dir / "inspect.json", json.dumps(report, indent=2))
    return report


# ---------------------------------------------------------------- the cut

def _ranges(specs: list[str]) -> list[tuple[float, float]]:
    """"12.4-15.2" -> (12.4, 15.2). Ranges are seconds into the source."""
    out = []
    for spec in specs or []:
        a, _, b = str(spec).partition("-")
        try:
            start, end = float(a), float(b)
        except ValueError as e:
            raise ValueError(f"range {spec!r} is not START-END in seconds") from e
        if end <= start:
            raise ValueError(f"range {spec!r} ends before it starts")
        out.append((round(start, 3), round(end, 3)))
    return sorted(out)


def plan(seconds: float, drops: list[tuple[float, float]], covers: list[tuple[float, float]]) -> list[dict]:
    """The timeline as a list of segments: play it, or cover it (its sound over a held frame)."""
    marks = sorted({0.0, round(seconds, 3)} | {t for r in drops + covers for t in r})
    marks = [m for m in marks if 0.0 <= m <= seconds]
    segs = []
    for a, b in zip(marks, marks[1:]):
        if b - a <= 0.001:
            continue
        mid = (a + b) / 2
        if any(s <= mid <= e for s, e in drops):
            continue                                            # dropped: it is not on the timeline at all
        mode = "cover" if any(s <= mid <= e for s, e in covers) else "play"
        segs.append({"start": a, "end": b, "seconds": round(b - a, 3), "mode": mode})
    if not segs:
        raise ValueError("every second of the video was dropped; nothing would be left")
    return segs


def _cut_filter(segs: list[dict], fps: float, w: int, h: int, has_audio: bool) -> tuple[str, str]:
    """filter_complex for the recut: play segments straight, cover segments as a held frame with a slow push in.

    The input is split first. A filtergraph may consume each input pad once, so writing `[0:v]trim=...` for every
    segment does not give every segment the source: ffmpeg keeps the first and silently drops the rest, and the recut
    comes out as its opening shot alone."""
    n = len(segs)
    parts = [f"[0:v]split={n}" + "".join(f"[s{k}]" for k in range(n))]
    if has_audio:
        parts.append(f"[0:a]asplit={n}" + "".join(f"[t{k}]" for k in range(n)))

    vlabels, alabels = [], []
    for k, s in enumerate(segs):
        v, a = f"v{k}", f"a{k}"
        if s["mode"] == "play":
            parts.append(f"[s{k}]trim=start={s['start']:.3f}:end={s['end']:.3f},setpts=PTS-STARTPTS[{v}]")
        else:
            # hold the last clean frame before the covered range, pushing in ~6% across it so the hold reads as a choice
            frame_at = max(0.0, s["start"] - 1.0 / fps)
            frames = max(2, int(round(s["seconds"] * fps)))
            parts.append(
                f"[s{k}]trim=start={frame_at:.3f}:duration={1.0 / fps:.5f},setpts=PTS-STARTPTS,"
                f"scale={w * 2}:{h * 2},"
                f"zoompan=z='min(1.0+0.06*on/{frames},1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames}:s={w}x{h}:fps={fps:.3f},setsar=1[{v}]")
        vlabels.append(f"[{v}]")
        if has_audio:
            fade_out = max(0.0, s["seconds"] - JOIN_FADE)
            parts.append(
                f"[t{k}]atrim=start={s['start']:.3f}:end={s['end']:.3f},asetpts=PTS-STARTPTS,"
                f"afade=t=in:st=0:d={JOIN_FADE},afade=t=out:st={fade_out:.3f}:d={JOIN_FADE}[{a}]")
            alabels.append(f"[{a}]")

    if has_audio:
        pairs = "".join(v + a for v, a in zip(vlabels, alabels))
        parts.append(f"{pairs}concat=n={n}:v=1:a=1[vcut][acut]")
        return ";".join(parts), "[vcut][acut]"
    parts.append(f"{''.join(vlabels)}concat=n={n}:v=1:a=0[vcut]")
    return ";".join(parts), "[vcut]"


def _badge(box: dict, logo: Path, work: Path, scale: float = 1.0) -> tuple[Path, int, int]:
    """A scrim with the mark on it, sized to bury the watermark box. Drawn once as a PNG so the overlay is a single step."""
    from PIL import Image, ImageDraw, ImageFilter

    pad = int(max(box["w"], box["h"]) * 0.28) + 6
    bw, bh = int((box["w"] + 2 * pad) * scale), int((box["h"] + 2 * pad) * scale)
    side = max(bw, bh)                                          # a square badge: the Q mark is square
    badge = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    scrim = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    radius = int(side * 0.3)
    ImageDraw.Draw(scrim).rounded_rectangle([0, 0, side - 1, side - 1], radius=radius, fill=(14, 15, 18, 232))
    badge.alpha_composite(scrim.filter(ImageFilter.GaussianBlur(1.2)))
    mark = Image.open(logo).convert("RGBA")
    inner = int(side * 0.62)
    mark.thumbnail((inner, inner), Image.LANCZOS)
    badge.alpha_composite(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    out = work / "badge.png"            # per video, so two recuts at once cannot overwrite each other's badge
    out.parent.mkdir(parents=True, exist_ok=True)
    badge.save(out)
    return out, side, side


def pick_music(name: str | None) -> Path | None:
    """A bed by series name ("escape"), by file path, or nothing."""
    if not name or name == "none":
        return None
    p = Path(name)
    if p.exists():
        return p
    tracks = sorted(MUSIC_DIR.glob(f"{name}-*.mp3"))
    if not tracks:
        raise ValueError(f"no music bed for {name!r}: {MUSIC_DIR} holds "
                         f"{sorted({t.stem.rsplit('-', 1)[0] for t in MUSIC_DIR.glob('*.mp3')})}")
    return tracks[0]


def apply(video: Path, out: Path, *, drops: list[str] | None = None, covers: list[str] | None = None,
          music: str | None = None, music_volume: float = 0.16, logo: str = "auto",
          watermark_box: dict | None = None, crf: int = 18) -> dict:
    """Cut, cover, score and brand a finished video. Two passes: the cut, then the overlay and the bed."""
    video, out = Path(video), Path(out)
    if not video.exists():
        raise FileNotFoundError(video)
    info = probe(video)
    drop_r, cover_r = _ranges(drops or []), _ranges(covers or [])
    for s, e in drop_r + cover_r:
        if e > info["seconds"] + 0.05:
            raise ValueError(f"range {s}-{e} runs past the end of the video ({info['seconds']:.2f}s)")
    segs = plan(info["seconds"], drop_r, cover_r)
    work = Paths.root / "production" / "recut" / video.stem
    work.mkdir(parents=True, exist_ok=True)
    stage = work / "cut.mp4"

    # pass 1: the cut
    graph, maps = _cut_filter(segs, info["fps"], info["width"], info["height"], info["has_audio"])
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-filter_complex", graph]
    for label in maps.replace("][", "] [").split():
        cmd += ["-map", label]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]
    cmd += (["-c:a", "aac", "-b:a", "192k"] if info["has_audio"] else ["-an"])
    cmd += [str(stage)]
    subprocess.run(cmd, check=True, timeout=FFMPEG_TIMEOUT)

    # pass 2: logo over the watermark, music bed ducked under the voice
    cut = probe(stage)
    box = watermark_box
    if logo != "none" and box is None:
        found = find_watermark(video, info["seconds"])
        box = found.get("box") if found.get("found") else None
    bed = pick_music(music)

    inputs, graph2, vlab, alab = ["-i", str(stage)], [], "0:v", "0:a" if cut["has_audio"] else None
    badge_used = None
    if logo != "none" and box:
        badge, bwid, _ = _badge(box, LOGO, work)
        badge_used = {"box": box, "badge_px": bwid}
        inputs += ["-i", str(badge)]
        cx, cy = box["x"] + box["w"] / 2, box["y"] + box["h"] / 2
        x, y = int(round(cx - bwid / 2)), int(round(cy - bwid / 2))
        x = min(max(x, 8), max(8, info["width"] - bwid - 8))
        y = min(max(y, 8), max(8, info["height"] - bwid - 8))
        graph2.append(f"[0:v][1:v]overlay=x={x}:y={y}:format=auto[vout]")
        vlab = "vout"
    if bed and cut["has_audio"]:
        inputs += ["-stream_loop", "-1", "-i", str(bed)]
        bed_in = len([a for a in inputs if a == "-i"]) - 1
        total = cut["seconds"]
        graph2.append(
            f"[0:a]aresample=48000,asplit=2[vo1][vo2];"
            f"[{bed_in}:a]aresample=48000,atrim=0:{total:.3f},asetpts=PTS-STARTPTS,volume={music_volume},"
            f"afade=t=in:d=0.8,afade=t=out:st={max(0.0, total - 1.5):.2f}:d=1.5[mu];"
            f"[mu][vo1]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[duck];"
            f"[vo2][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
        alab = "aout"

    if not graph2:
        stage.replace(out)
        result = {"output": str(out), "segments": segs, "watermark": badge_used, "music": None, "seconds": cut["seconds"]}
    else:
        cmd2 = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph2),
                "-map", f"[{vlab}]" if vlab != "0:v" else "0:v"]
        if alab:
            cmd2 += ["-map", f"[{alab}]" if alab != "0:a" else "0:a", "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd2 += ["-an"]
        cmd2 += ["-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
                 "-movflags", "+faststart", str(out)]
        subprocess.run(cmd2, check=True, timeout=FFMPEG_TIMEOUT)
        result = {"output": str(out), "segments": segs, "watermark": badge_used,
                  "music": str(bed) if bed else None, "seconds": probe(out)["seconds"]}

    result["source"] = {"path": str(video), "seconds": info["seconds"]}
    result["removed_seconds"] = round(info["seconds"] - result["seconds"], 3)
    result["edited"] = config.today_utc().isoformat()
    write_atomic(work / "recut.json", json.dumps(result, indent=2))
    return result
