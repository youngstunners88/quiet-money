"""The owner's wellness posters: bring them in, take the @handle off, keep the originals.

    assets/planner/wellness/original/wellness-NNN.jpg   as the owner made them (never changed)
    assets/planner/wellness/cropped/wellness-NNN.jpg    handle removed (cropped in Photopea, or repainted when it sits on plain white inside the poster)
    assets/planner/wellness/report.json                 what was done to each picture, by which engine, and why

Per picture: planner_locate finds the handle (pixels first, a vision model through OpenRouter as the second opinion), planner_photopea crops it off the way the owner
does by hand, and the result is checked against a plain crop. A picture where the pixels and the model disagree is not touched: it is listed as `needs_human`.
`manual_cuts` ({"wellness-023": 0.966}) gives a cut line (fraction of the height) for the few handles that sit right against the poster; `paint` ({"wellness-038":
[x0, y0, x1, y1]} as fractions) repaints a handle that is on the poster itself. Nothing here posts or lists anything.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
from pathlib import Path

from PIL import Image

from faceless import planner_clean, planner_locate, planner_photopea
from faceless.config import STUDIO
from faceless.fsutil import write_atomic

ROOT = STUDIO / "assets" / "planner" / "wellness"
ORIGINAL, CROPPED, REPORT = ROOT / "original", ROOT / "cropped", ROOT / "report.json"
EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def ingest(folder: Path, skip: tuple[int, ...] = ()) -> list[Path]:
    """Copy a folder's pictures into original/ as wellness-NNN.<ext> in natural file order. `skip` lists 1-based positions that are not posters (a logo, a banner)."""
    files = sorted((f for f in Path(folder).iterdir() if f.is_file() and not f.is_symlink() and f.suffix.lower() in EXTS), key=planner_clean.natural_key)
    out, k = [], 0
    for pos, f in enumerate(files, 1):
        if pos in skip:
            continue
        k += 1
        dest = ORIGINAL / f"wellness-{k:03d}{f.suffix.lower()}"
        _write(dest, f.read_bytes())
        out.append(dest)
    return out


def _encode(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=95, subsampling=0)
    return buf.getvalue()


def process(files: list[Path] | None = None, *, use_model: bool = True, manual_cuts: dict[str, float] | None = None, paint: dict[str, list[float]] | None = None,
            engine: str = "photopea", job: str | None = None) -> dict:
    files = files or sorted(ORIGINAL.glob("wellness-*.*"), key=planner_clean.natural_key)
    manual_cuts, paint, report = manual_cuts or {}, paint or {}, {}
    pp = None
    if engine == "photopea" and any(True for _ in files):
        try:
            pp = planner_photopea.Photopea().__enter__()
        except planner_photopea.PhotopeaError as e:
            report["_engine_note"] = f"Photopea unavailable ({e}); crops were made with Pillow"
    try:
        for f in files:
            stem, data = f.stem, f.read_bytes()
            im = Image.open(io.BytesIO(data))
            w, h = im.size
            model = planner_locate.ask_model(im, job=job) if use_model else None
            plan = planner_locate.plan_crop(im, model)
            row = {"size": [w, h], "model": {k: model[k] for k in ("handle_present", "handle_top", "model", "usd")} if model else None, "plan": plan["why"]}
            if stem in paint:
                x0, y0, x1, y1 = paint[stem]
                cleaned, found = planner_clean.clean_image(im, [(int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))])
                _write(CROPPED / f"{stem}.jpg", _encode(cleaned))
                row.update(action="painted", engine="opencv-inpaint", why="handle is on the poster itself (plain white): repainted, nothing else touched")
            elif stem in manual_cuts or plan["action"] == "crop":
                y = int(manual_cuts[stem] * h) if stem in manual_cuts else plan["y"]
                box = (0, 0, w, y)
                ref = planner_photopea.pillow_crop(data, box)
                out, used = ref, "pillow"
                if pp is not None:
                    try:
                        cand = pp.crop(data, box)
                        if planner_photopea.agrees(cand, ref):
                            out, used = cand, "photopea"
                        else:
                            row["note"] = "Photopea's crop did not match the reference crop; the reference was used"
                    except planner_photopea.PhotopeaError as e:
                        row["note"] = f"Photopea failed ({str(e)[:80]}); the Pillow crop was used"
                _write(CROPPED / f"{stem}.jpg", out)
                row.update(action="cropped", engine=used, cut_row=y, removed=f"{1 - y / h:.1%}", **({"manual": True} if stem in manual_cuts else {}))
            elif plan["action"] == "keep":
                _write(CROPPED / f"{stem}.jpg", _encode(im))
                row.update(action="kept", engine="none", why="no handle on this picture")
            else:
                row.update(action="needs_human", why=plan["why"])
            report[stem] = row
    finally:
        if pp is not None:
            pp.__exit__()
    write_atomic(REPORT, json.dumps(report, indent=1, default=str) + "\n")
    return report


def summary(report: dict) -> dict:
    rows = {k: v for k, v in report.items() if not k.startswith("_")}
    by = {}
    for k, v in rows.items():
        by.setdefault(v["action"], []).append(k)
    return {a: len(v) for a, v in by.items()} | {"needs_human_list": by.get("needs_human", []), "note": report.get("_engine_note")}
