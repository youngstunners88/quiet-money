"""Planner artwork intake: number the owner's pictures by day, remove a handle watermark from them cleanly, and say which days still need a drawn picture.

The owner's pictures sometimes carry the @youngstunnersss handle. This is a local, scripted, repeatable step (Pillow + OpenCV, no uploads, no cost):

    python -m faceless planner ingest <folder> [--start N]   copy the pictures into assets/planner/source/day-NNN.<ext> in natural file-name order
    python -m faceless planner clean [--box x0,y0,x1,y1]     find the handle and inpaint it; originals are never touched; cleaned copies go to assets/planner/clean/
    python -m faceless planner inventory                     which days use the owner's picture and which are drawn (writes assets/planner/INVENTORY.md)

How the cleaner works: thin text is found with morphological top-hat (bright text) and black-hat (dark text) filters inside the six places a handle usually sits
(corners and the middle of the bottom and top edges). Letters are merged into a line, and a line of the right size and shape becomes the mask. Only the mask
(plus a small margin) is repainted with cv2.inpaint, so every pixel outside the box is byte-identical to the original; `clean` proves it. Pass `--box` (as fractions
of the picture) when the handle is somewhere unusual or the picture has real text nearby. A contact sheet (before | after) is written so the owner can check it by eye:
automation can remove a handle, only a person can say the picture still looks right.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from faceless import planner_art
from faceless.config import STUDIO
from faceless.fsutil import write_atomic

ZONES = {                          # fractions x0, y0, x1, y1 of the picture where a corner handle usually sits
    "bottom-right": (0.50, 0.90, 1.00, 1.00), "bottom-left": (0.00, 0.90, 0.50, 1.00), "bottom-center": (0.25, 0.90, 0.75, 1.00),
    "top-right": (0.50, 0.00, 1.00, 0.10), "top-left": (0.00, 0.00, 0.50, 0.10), "top-center": (0.25, 0.00, 0.75, 0.10),
}
INVENTORY = STUDIO / "assets" / "planner" / "INVENTORY.md"
REPORT = STUDIO / "assets" / "planner" / "clean-report.json"


@dataclass
class Found:
    zone: str
    box: tuple[int, int, int, int]            # pixel box x0, y0, x1, y1 (tight around the text, before the margin)
    parts: int


def _response(gray: np.ndarray, w: int) -> np.ndarray:
    k = max(5, int(w * 0.012) | 1)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    return np.maximum(cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, ker), cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, ker))


def _text_mask(resp: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    crop = resp[y0:y1, x0:x1].astype(np.uint8)
    otsu, _ = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t = max(14.0, min(float(otsu) * 0.6, 80.0))                    # Otsu splits text from ground; 60% of it keeps the soft anti-aliased edge too
    return (crop > t).astype(np.uint8) * 255


def detect(im: Image.Image) -> list[Found]:
    """Lines of small, thin text in the usual handle zones. Textured art (many marks) is ignored on purpose."""
    rgb = np.array(im.convert("RGB"))
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    resp = _response(gray, w)
    found = []
    for name, (a, b, c, d) in ZONES.items():
        box = (int(a * w), int(b * h), int(c * w), int(d * h))
        m = _text_mask(resp, box)
        merged = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(w * 0.014)), 3)))
        n, _lab, stats, _c = cv2.connectedComponentsWithStats(merged)
        lines = []
        for s in stats[1:]:
            if not (0.006 * h <= s[3] <= 0.05 * h and 0.04 * w <= s[2] <= 0.45 * w):
                continue
            fill = s[4] / float(s[2] * s[3])
            if 0.25 <= fill <= 0.8:                                # letters leave gaps (about 0.6 of the line box); a solid sliver of a coin or a rule is nearly full
                lines.append(s)
        if not lines or len(stats) - 1 > 8:                       # nothing text-shaped, or too busy to be a watermark: leave it alone
            continue
        x0 = min(s[0] for s in lines) + box[0]
        y0 = min(s[1] for s in lines) + box[1]
        x1 = max(s[0] + s[2] for s in lines) + box[0]
        y1 = max(s[1] + s[3] for s in lines) + box[1]
        found.append(Found(name, (x0, y0, x1, y1), len(lines)))
    return found


def clean_image(im: Image.Image, boxes: list[tuple[int, int, int, int]] | None = None) -> tuple[Image.Image, list[Found]]:
    """Return (cleaned picture, what was removed). With `boxes` (pixels) nothing is searched: those areas are cleaned as given."""
    rgb = np.array(im.convert("RGB"))
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    resp = _response(gray, w)
    found = [Found("manual", b, 1) for b in boxes] if boxes else detect(im)
    if not found:
        return im.convert("RGB"), []
    mask = np.zeros((h, w), np.uint8)
    pad = max(4, int(h * 0.006))
    for f in found:
        x0, y0, x1, y1 = f.box
        bx = (max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad))
        sub = _text_mask(resp, bx)
        sub = cv2.dilate(sub, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(3, int(w * 0.006)) | 1,) * 2))
        mask[bx[1]:bx[3], bx[0]:bx[2]] |= sub
    out = cv2.inpaint(rgb, mask, max(3, int(w * 0.004)), cv2.INPAINT_TELEA)
    keep = mask == 0
    out[keep] = rgb[keep]                                           # outside the mask, the pixels are exactly the originals
    return Image.fromarray(out), found


# ---------------------------------------------------------------- folders

def natural_key(p: Path) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def ingest(folder: Path, start: int = 1) -> list[tuple[int, Path]]:
    files = sorted((f for f in folder.iterdir() if f.suffix.lower() in planner_art.EXTS), key=natural_key)
    planner_art.SOURCE.mkdir(parents=True, exist_ok=True)
    out = []
    for i, f in enumerate(files):
        day = start + i
        if day > 365:
            break
        dest = planner_art.SOURCE / f"day-{day:03d}{f.suffix.lower()}"
        dest.write_bytes(f.read_bytes())
        out.append((day, dest))
    return out


def run_clean(boxes_frac: tuple[float, float, float, float] | None = None, sheet: bool = True, reviewer=None) -> dict:
    files = sorted(planner_art.SOURCE.glob("day-*.*"), key=natural_key)
    planner_art.CLEAN.mkdir(parents=True, exist_ok=True)
    report, pairs = {}, []
    for f in files:
        if f.suffix.lower() not in planner_art.EXTS:
            continue
        src = Image.open(f)
        boxes = None
        if boxes_frac:
            w, h = src.size
            boxes = [(int(boxes_frac[0] * w), int(boxes_frac[1] * h), int(boxes_frac[2] * w), int(boxes_frac[3] * h))]
        cleaned, found = clean_image(src, boxes)
        dest = planner_art.CLEAN / f.name
        ext = f.suffix.lower()
        cleaned.save(dest, "JPEG" if ext in (".jpg", ".jpeg") else ext[1:].upper(), **({"quality": 95} if ext in (".jpg", ".jpeg") else {}))
        a, b = np.array(src.convert("RGB")), np.array(cleaned)
        changed = np.any(a != b, axis=2)
        report[f.name] = {"removed": [{"zone": x.zone, "box": list(map(int, x.box))} for x in found], "pixels_changed": int(changed.sum()),
                          "residual": [x.zone for x in detect(cleaned)] if found and not boxes else []}
        if found:
            pairs.append((src, cleaned))
            if reviewer:
                report[f.name]["review"] = reviewer(f.name, src, cleaned, found)
    write_atomic(REPORT, json.dumps(report, indent=1) + "\n")
    if sheet and pairs:
        _sheet(pairs)
    return report


def _sheet(pairs: list[tuple[Image.Image, Image.Image]], cell: int = 360) -> Path:
    rows = pairs[:20]
    sheet = Image.new("RGB", (cell * 2 + 30, (cell + 10) * len(rows)), (20, 20, 22))
    for i, (a, b) in enumerate(rows):
        for j, im in enumerate((a, b)):
            t = im.convert("RGB")
            t.thumbnail((cell, cell))
            sheet.paste(t, (10 + j * (cell + 10), i * (cell + 10)))
    out = STUDIO / "assets" / "planner" / "clean-before-after.jpg"
    sheet.save(out, quality=88)
    return out


def inventory(total: int = 365, write: bool = True) -> dict:
    have = sorted(int(m.group(1)) for f in planner_art.SOURCE.glob("day-*.*") if (m := re.match(r"day-(\d+)", f.name)))
    cleaned = {int(m.group(1)) for f in planner_art.CLEAN.glob("day-*.*") if (m := re.match(r"day-(\d+)", f.name))}
    missing = [d for d in range(1, total + 1) if d not in have]
    lines = ["# Planner artwork inventory", "",
             f"- Owner pictures: **{len(have)}** of {total} days (cleaned copies: {len(cleaned & set(have))}).",
             f"- Days drawn in code by `planner_art.py`: **{len(missing)}**.", "",
             "Run `python -m faceless planner build` to rebuild the PDFs. A drawn day is replaced the moment a `day-NNN` picture appears in `assets/planner/source/`.", ""]
    if have:
        lines += ["## Owner pictures", ", ".join(map(str, have)), ""]
    lines += ["## Drawn days", ", ".join(map(str, missing)) if missing else "none", ""]
    if write:
        write_atomic(INVENTORY, "\n".join(lines))
    return {"owner": len(have), "drawn": len(missing), "cleaned": len(cleaned & set(have)), "owner_days": have}
