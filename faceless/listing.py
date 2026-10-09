"""Storefront listings: from one catalog (channel/shop/catalog.json) to everything the owner needs to open an Etsy or Gumroad listing.

`python -m faceless listing build [product|all]` writes, per product, into channel/shop/<product>/:
  etsy/        title.txt, description.txt, tags.txt, details.md, images/01..NN.jpg (2800x2100), video.mp4 (silent, square)
  gumroad/     name.txt, summary.txt, description.md, tags.txt, after-purchase.txt, cover.jpg (1920x1080), thumbnail.jpg (1200 square)
  CHECKLIST.md the click-by-click steps, report.md the gauntlet result

Every picture is drawn from the real product file (see mockup.py) and every claim in the copy is checked by the listing gauntlet below
before anything is written as "ready": platform rules from channel/compliance/platform-rules.md (Etsy: AI disclosure, tag and title
limits, no trademark tags; Gumroad: no credit-repair language), our own rules (no income claims, no fake scarcity or reviews, "not
financial advice" present, an AI line present), and the numbers rules (a compatibility claim must be one we verified; a "checked
against independent math" claim must still be true when the listing is built). Nothing here publishes: creating or editing a listing
on a shop is the owner's act (or, with their token, a draft the owner publishes).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from faceless import mockup
from faceless.config import STUDIO, Paths

CATALOG = STUDIO / "channel" / "shop" / "catalog.json"
OUT = STUDIO / "channel" / "shop"
ETSY_FILE_TYPES = {".pdf", ".zip", ".xlsx", ".xls", ".doc", ".docx", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".mp3", ".mp4", ".txt", ".epub"}
ETSY_TAG_OK = re.compile(r"^[a-z0-9][a-z0-9 \-']{0,19}$")


@dataclass
class Gate:
    name: str
    ok: bool
    detail: str = ""
    hard: bool = True


# ---------------------------------------------------------------- catalog

def catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def products(only: str | None = None) -> list[dict]:
    ps = catalog()["products"]
    if only and only != "all":
        ps = [p for p in ps if p["id"] == only]
        if not ps:
            raise SystemExit(f"unknown product {only!r}; known: {', '.join(p['id'] for p in catalog()['products'])}")
    return ps


def copy_blob(p: dict) -> dict[str, str]:
    """Every customer-facing string, by where it is shown."""
    e, g = p["etsy"], p["gumroad"]
    return {"etsy title": e["title"], "etsy tags": " ; ".join(e["tags"]), "etsy description": e["description"], "gumroad name": g["name"],
            "gumroad summary": g["summary"], "gumroad description": g["description"], "gumroad tags": " ; ".join(g["tags"]),
            "after purchase": g["after_purchase"], "subtitle": p["subtitle"],
            "images": " ; ".join([p["name"], p["subtitle"], *p["chips"], *p.get("notes", []), p.get("grid_sub", "")]
                                 + [x for f in p.get("features", []) for x in [f["headline"], *f["bullets"]]] + [s for st in p["steps"] for s in st])}


# ---------------------------------------------------------------- text gates

INCOME_CLAIMS = re.compile(
    r"get rich|rich quick|quit your (day )?job|replace your (income|salary|paycheck)|make money|earn \$|earn \d|"
    r"(guaranteed|promised) (income|return|profit|results)|risk[- ]free|can'?t lose|double your money|financial freedom (in|within) \d|"
    r"passive income (of|from|worth)|\$\d[\d,]*\s*(a|per|/)\s*(day|week|month)", re.I)
CREDIT_REPAIR = re.compile(r"credit[- ]repair|improve your credit|boost your credit|raise your (credit )?score|credit score (boost|improvement)|fix your credit", re.I)
FAKE_PROOF = re.compile(r"best[- ]?seller|#\s?1\b|thousands of (customers|buyers|sold)|as seen (on|in)|5[- ]star|testimonial|limited time|only \d+ left|sale ends|hurry|last chance|selling fast", re.I)
TRADEMARKS = re.compile(r"dave ramsey|ynab|you need a budget|\bmint\b|quicken|mvelopes|\bnotion\b|\bcanva\b|microsoft|\bapple\b|turbotax|suze orman|robert kiyosaki|alex hormozi|dan pena|rich dad", re.I)
APP_NAMES = {"Excel": r"\bExcel\b", "Google Sheets": r"\bGoogle Sheets\b|\bSheets\b", "LibreOffice": r"\bLibre ?Office\b", "Numbers": r"\bApple Numbers\b|\bNumbers app\b|,\s*Numbers\b|\bor Numbers\b",
             "OpenOffice": r"\bOpen ?Office\b", "Airtable": r"\bAirtable\b"}
NEGATED_GUARANTEE = re.compile(r"\b(never|not|no|nor|without)\s+(a\s+)?(guarantee\w*|promis\w*)|\bguarantee[ds]?\s+(by|from)\b", re.I)


def text_gates(p: dict) -> list[Gate]:
    e, g, out = p["etsy"], p["gumroad"], []
    blob = copy_blob(p)
    everything = "\n".join(blob.values())
    scrub = NEGATED_GUARANTEE.sub("", everything)
    out.append(Gate("etsy_title_length", len(e["title"]) <= 140, f"{len(e['title'])} of 140 characters"))
    bad_tags = [t for t in e["tags"] if not ETSY_TAG_OK.match(t)]
    out.append(Gate("etsy_tags_valid", len(e["tags"]) == 13 and len(set(e["tags"])) == 13 and not bad_tags,
                    f"{len(e['tags'])} tags (13 allowed, all used), each 20 characters or fewer; bad: {bad_tags or 'none'}"))
    found = [m.group(0) for m in INCOME_CLAIMS.finditer(scrub)]
    out.append(Gate("no_income_claims", not found, f"found: {found[:4]}" if found else "none"))
    cr = [m.group(0) for m in CREDIT_REPAIR.finditer(everything)]
    out.append(Gate("no_credit_repair_language", not cr, f"found: {cr[:3]}" if cr else "none (Gumroad bans credit-repair products and talk)"))
    fp = [m.group(0) for m in FAKE_PROOF.finditer(everything)]
    out.append(Gate("no_fake_proof_or_scarcity", not fp, f"found: {fp[:3]}" if fp else "none"))
    tm_title = [m.group(0) for m in TRADEMARKS.finditer(e["title"] + " " + " ".join(e["tags"]) + " " + g["name"] + " " + " ".join(g["tags"]))]
    out.append(Gate("no_trademarks_in_title_or_tags", not tm_title, f"found: {tm_title[:3]}" if tm_title else "none"))
    tm_body = [m.group(0) for m in TRADEMARKS.finditer(e["description"] + " " + g["description"])]
    out.append(Gate("no_trademarks_in_description", not tm_body, f"found: {tm_body[:3]}" if tm_body else "none", hard=False))
    for label, desc in (("etsy", e["description"]), ("gumroad", g["description"])):
        out.append(Gate(f"{label}_not_financial_advice", bool(re.search(r"not financial advice", desc, re.I)), "the line is present" if re.search(r"not financial advice", desc, re.I) else "missing"))
        out.append(Gate(f"{label}_ai_disclosure", bool(re.search(r"AI assistance|AI-assisted|made with AI", desc, re.I)), "disclosure line present" if re.search(r"AI assistance|AI-assisted", desc, re.I) else "missing (Etsy and our own rule)"))
    claimed = [name for name, rx in APP_NAMES.items() if re.search(rx, everything)]
    unverified = [n for n in claimed if n not in p["verified_compat"]]
    out.append(Gate("compatibility_claims_verified", not unverified, f"claims {claimed}; not verified: {unverified or 'none'}"))
    out.append(Gate("price_set", p["price"] > 0 and p["price"] in p["price_test"], f"${p['price']} within test range {p['price_test']}", hard=True))
    out.append(Gate("refund_promise_in_copy", bool(re.search(r"refund", e["description"], re.I)), "the Etsy description states the refund promise", hard=False))
    out.append(Gate("example_numbers_labelled", p["kind"] != "spreadsheet" or bool(re.search(r"example", e["description"], re.I)), "the copy says the numbers shown are examples", hard=False))
    return out


def math_gate(p: dict) -> Gate | None:
    """A 'checked against independent math' claim is only allowed while it is true: re-run the product's own verification."""
    if p["kind"] != "spreadsheet" or not re.search(r"independent (math|simulation)", copy_blob(p)["etsy description"], re.I):
        return None
    from faceless import product_debt, products as prod
    fn = {"rat-race-escape-planner": prod.verify_escape, "debt-payoff-planner": product_debt.verify_debt}.get(p["id"])
    if fn is None:
        return None
    try:
        res = fn(STUDIO / p["file"])
    except Exception as ex:  # noqa: BLE001 - a verifier that cannot run is reported, not hidden
        return Gate("independent_math_verified", False, f"verifier could not run: {type(ex).__name__}", hard=False)
    return Gate("independent_math_verified", bool(res.get("ok")), f"{len(res.get('rows', []))} figures compared with independent math, errors: {res.get('errors') or 'none'}")


# ---------------------------------------------------------------- file, image and video gates

def ensure_files(p: dict) -> list[str]:
    """The kit's zip is a gitignored build output, so a clean checkout has its parts but not the bundle: assemble it from the committed parts.
    Returns the files it made. A part that is missing too is left for the files_exist gate to report."""
    made = []
    for rel in [p["file"], *p.get("extra_files", [])]:
        if not (STUDIO / rel).exists() and Path(rel).name == "Money-Reset-Kit.zip":
            from faceless import product_print
            try:
                product_print.assemble_kit()
                made.append(rel)
            except FileNotFoundError:
                pass
    return made


def file_gates(p: dict) -> list[Gate]:
    files = [STUDIO / p["file"], *[STUDIO / f for f in p.get("extra_files", [])]]
    out = [Gate("files_exist", all(f.exists() for f in files), ", ".join(f.name for f in files))]
    if all(f.exists() for f in files):
        big = [f.name for f in files if f.stat().st_size > 20 * 2**20]
        ext = [f.name for f in files if f.suffix.lower() not in ETSY_FILE_TYPES]
        out.append(Gate("etsy_file_limits", len(files) <= 5 and not big and not ext, f"{len(files)} file(s) of 5 allowed; over 20 MB: {big or 'none'}; unsupported type: {ext or 'none'}"))
    return out


def image_stats(path: Path) -> dict:
    im = Image.open(path).convert("L")
    a = np.asarray(im.resize((im.width // 4, im.height // 4)), dtype=np.float32)
    lap = a[1:-1, 1:-1] * 4 - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    return {"size": Image.open(path).size, "mean": float(a.mean()), "sharp": float(lap.var())}


def image_gates(images: list[Path], cover: Path | None, thumb: Path | None) -> list[Gate]:
    out = []
    if not images:
        return [Gate("etsy_images_present", False, "no images were built")]
    stats = [image_stats(i) for i in images]
    small = [i.name for i, s in zip(images, stats) if min(s["size"]) < 2000]
    out.append(Gate("etsy_images_2000px", not small, f"{len(images)} images, smallest side {min(min(s['size']) for s in stats)} px (Etsy asks for 2000+); too small: {small or 'none'}"))
    out.append(Gate("etsy_image_count", 5 <= len(images) <= 20, f"{len(images)} images (Etsy allows 20; 5 or more sells better)", hard=False))
    h = stats[0]
    out.append(Gate("etsy_main_image_landscape_or_square", h["size"][0] >= h["size"][1], f"{h['size'][0]}x{h['size'][1]}"))
    out.append(Gate("etsy_main_image_not_dark", 55 <= h["mean"] <= 200, f"mean brightness {h['mean']:.0f} of 255 (Etsy ranks dark main images lower)"))
    out.append(Gate("etsy_main_image_sharp", h["sharp"] > 40, f"edge energy {h['sharp']:.0f} (blurry main images rank lower)"))
    if cover:
        cs = Image.open(cover).size
        out.append(Gate("gumroad_cover_16x9", cs[0] >= 1280 and abs(cs[0] / cs[1] - 16 / 9) < 0.01, f"{cs[0]}x{cs[1]}"))
    if thumb:
        ts = Image.open(thumb).size
        out.append(Gate("gumroad_thumbnail_square", ts[0] == ts[1] and ts[0] >= 600 and thumb.stat().st_size <= 5 * 2**20, f"{ts[0]}x{ts[1]}, {thumb.stat().st_size // 1024} KB (square, 600+, under 5 MB)"))
    return out


def video_gates(video: Path | None) -> list[Gate]:
    if not video or not video.exists():
        return [Gate("etsy_video", False, "no video was built (needs ffmpeg)", hard=False)]
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(video)], capture_output=True, text=True, timeout=60, check=False)
        info = json.loads(r.stdout)
        dur = float(info["format"]["duration"])
        streams = info["streams"]
        v = next(s for s in streams if s["codec_type"] == "video")
        audio = any(s["codec_type"] == "audio" for s in streams)
    except Exception as ex:  # noqa: BLE001
        return [Gate("etsy_video", False, f"could not read the video: {type(ex).__name__}", hard=False)]
    return [Gate("etsy_video_length", 3 <= dur <= 15, f"{dur:.1f} s (Etsy: 3 to 15)"),
            Gate("etsy_video_size", video.stat().st_size <= 100 * 2**20 and min(v["width"], v["height"]) >= 500, f"{v['width']}x{v['height']}, {video.stat().st_size / 2**20:.1f} MB (limit 100 MB, 500 px minimum, 1080 ideal)"),
            Gate("etsy_video_silent", not audio, "no audio track (Etsy drops audio anyway)", hard=False)]


def passed(gates: list[Gate]) -> bool:
    return all(g.ok for g in gates if g.hard)


def gates_md(gates: list[Gate]) -> str:
    rows = ["| gate | result | detail |", "|---|---|---|"]
    rows += [f"| {g.name}{'' if g.hard else ' (soft)'} | {'pass' if g.ok else 'FAIL'} | {g.detail} |" for g in gates]
    return "\n".join(rows)


# ---------------------------------------------------------------- the build

def _page_images(p: dict) -> list[Image.Image]:
    """The product's own pages (spreadsheets through LibreOffice, printables through pdftoppm), cached by file mtime."""
    src = STUDIO / p["file"]
    cache = Paths.cache / "shop" / p["id"]
    cache.mkdir(parents=True, exist_ok=True)
    stamp = cache / "stamp.txt"
    n = max(p["pages"].values())
    want = f"{src.stat().st_mtime_ns}:{n}"
    pages = sorted(cache.glob("pg-*.png"))
    if pages and stamp.exists() and stamp.read_text() == want and len(pages) >= n:
        return [Image.open(x).convert("RGB") for x in pages[:n]]
    for x in cache.glob("pg-*.png"):
        x.unlink()
    imgs = mockup.render_pdf(src, dpi=110, first=1, last=n) if src.suffix == ".pdf" else mockup.render_pages(src, dpi=230, first=1, last=n, workdir=cache / "lo")
    for i, im in enumerate(imgs, 1):
        im.save(cache / f"pg-{i:02d}.png")
    stamp.write_text(want)
    return imgs


def _tabs(p: dict) -> tuple[str, ...]:
    from faceless import product_debt, products as prod
    return tuple({"rat-race-escape-planner": prod.SHEETS, "debt-payoff-planner": product_debt.SHEETS[:5]}.get(p["id"], ()))


def _save(im: Image.Image, path: Path, quality: int = 88) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return path


def _spreadsheet_images(p: dict, pages: list[Image.Image]) -> list[tuple[str, Image.Image]]:
    tabs, fname = _tabs(p), Path(p["file"]).name
    pg = p["pages"]
    main = pg.get("numbers") or pg.get("debts") or 2
    imgs = [("hero", mockup.hero(p["name"], p["subtitle"], pages[main - 1], p["chips"], tabs=tabs, active=main - 1, file_name=fname))]
    words = {5: "Five", 6: "Six", 7: "Seven"}
    n_tabs = len(tabs)
    imgs.append(("inside", mockup.inside_grid(f"{words.get(n_tabs, str(n_tabs))} tabs, one clear plan", [(t, pages[i]) for i, t in enumerate(tabs)], sub=p.get("grid_sub", ""), footer="Excel  ·  Google Sheets  ·  LibreOffice")))
    total = 2 + len(p["features"]) + 2
    for k, f in enumerate(p["features"], 3):
        imgs.append((f"feature-{k - 2}", mockup.feature(f["headline"], f["bullets"], pages[f["page"] - 1], k, total, tabs=tabs, active=f["page"] - 1, file_name=fname)))
    imgs.append(("steps", mockup.steps_image("Ready in five minutes", p["steps"])))
    imgs.append(("notes", mockup.notes_image("Honest by design", p["notes"], footer="Personal use for you and your household. Please do not resell or share the file.")))
    return imgs


def _printable_images(p: dict, pages: list[Image.Image]) -> list[tuple[str, Image.Image]]:
    imgs = [("hero", mockup.hero_pages(p["name"], p["subtitle"], [pages[1], pages[2], pages[3]], p["chips"]))]
    labels = ["How to use", "Paycheck split", "Subscription audit", "Sinking funds", "Debt list", "Net worth"]
    imgs.append(("inside", mockup.paper_grid("Six pages, ten minutes each", list(zip(labels, pages)), sub=p.get("grid_sub", ""), footer="US Letter  ·  A4  ·  PDF")))
    total = 2 + len(p["features"]) + 2
    for k, f in enumerate(p["features"], 3):
        imgs.append((f"feature-{k - 2}", mockup.feature_page(f["headline"], f["bullets"], pages[f["page"] - 1], k, total)))
    imgs.append(("steps", mockup.steps_image("Ready in five minutes", p["steps"])))
    imgs.append(("notes", mockup.notes_image("Honest by design", p["notes"], footer="Personal use for you and your household. Please do not resell or share the files.")))
    return imgs


def _bundle_images(p: dict, shots: dict[str, list[Image.Image]]) -> list[tuple[str, Image.Image]]:
    """The kit's images: its own hero and contents image, one close-up from each part (numbered for THIS pack), the steps and the notes."""
    cat = {q["id"]: q for q in catalog()["products"]}
    rr, dp, pr = shots["rat-race-escape-planner"], shots["debt-payoff-planner"], shots["money-reset-printables"]
    det = p["parts_detail"]
    total = 2 + len(p["parts"]) + 2
    imgs = [("hero", mockup.hero_bundle(p["name"], p["subtitle"], rr[1], dp[2], [pr[1], pr[2], pr[3]], p["chips"]))]
    imgs.append(("inside", mockup.bundle_inside("What is in the kit", [
        (det["rat-race-escape-planner"]["label"], det["rat-race-escape-planner"]["lines"], rr[1], False),
        (det["debt-payoff-planner"]["label"], det["debt-payoff-planner"]["lines"], dp[1], False),
        (det["money-reset-printables"]["label"], det["money-reset-printables"]["lines"], pr[1], True)], sub=p.get("grid_sub", ""))))
    a, b, c = cat["rat-race-escape-planner"], cat["debt-payoff-planner"], cat["money-reset-printables"]
    fa, fb, fc = a["features"][0], b["features"][1], c["features"][0]
    imgs.append(("part-1", mockup.feature(fa["headline"], fa["bullets"], rr[fa["page"] - 1], 3, total, tabs=_tabs(a), active=fa["page"] - 1, file_name=Path(a["file"]).name)))
    imgs.append(("part-2", mockup.feature(fb["headline"], fb["bullets"], dp[fb["page"] - 1], 4, total, tabs=_tabs(b), active=fb["page"] - 1, file_name=Path(b["file"]).name)))
    imgs.append(("part-3", mockup.feature_page(fc["headline"], fc["bullets"], pr[fc["page"] - 1], 5, total)))
    imgs.append(("steps", mockup.steps_image("Ready in one weekend", p["steps"])))
    imgs.append(("notes", mockup.notes_image("Honest by design", p["notes"], footer="Personal use for you and your household. Please do not resell or share the files.")))
    return imgs


def build(only: str | None = None, video: bool = True) -> dict[str, dict]:
    """Build every pack (or one). Returns {product: {"gates": [...], "passed": bool, "folder": path, "images": n, "video": bool}}."""
    results = {}
    by_id = {q["id"]: q for q in catalog()["products"]}
    for p in products(only):
        folder = OUT / p["id"]
        ensure_files(p)
        (folder / "etsy" / "images").mkdir(parents=True, exist_ok=True)
        (folder / "gumroad").mkdir(parents=True, exist_ok=True)
        if p["kind"] == "bundle":
            shots = {pid: _page_images(by_id[pid]) for pid in p["parts"]}
            named = _bundle_images(p, shots)
            pages = shots["rat-race-escape-planner"]
            hero_shot = pages[1]
        else:
            pages = _page_images(p)
            named = _spreadsheet_images(p, pages) if p["kind"] == "spreadsheet" else _printable_images(p, pages)
            hero_shot = pages[(p["pages"].get("numbers") or p["pages"].get("debts") or 2) - 1] if p["kind"] == "spreadsheet" else pages[1]
        for old in (folder / "etsy" / "images").glob("*.jpg"):
            old.unlink()
        files = [_save(mockup.deliver(im), folder / "etsy" / "images" / f"{i:02d}-{name}.jpg", 86) for i, (name, im) in enumerate(named, 1)]
        tabs = _tabs(p)
        if p["kind"] == "printable":
            cover_im = mockup.cover_pages(p["name"], p["subtitle"], [pages[1], pages[2], pages[3]], p["chips"])
        else:
            cover_im = mockup.cover_wide(p["name"], p["subtitle"], hero_shot, p["chips"], tabs=tabs, active=1 if tabs else 0, file_name=Path(p["file"]).name)
        cover = _save(cover_im, folder / "gumroad" / "cover.jpg", 88)
        thumb = _save(mockup.square_thumb(hero_shot, p["name"]), folder / "gumroad" / "thumbnail.jpg", 88)
        vid = folder / "etsy" / "video.mp4"
        made_video = False
        vid.unlink(missing_ok=True)
        if video:
            pick = [files[0]] + files[2:-2][:4] + [files[-2]]
            made_video = mockup.video(pick, vid, seconds_each=2.2, size=(1080, 1080))
        _write_copy(p, folder)
        gates = text_gates(p) + file_gates(p) + image_gates(files, cover, thumb) + video_gates(vid if made_video else None)
        mg = math_gate(p)
        if mg:
            gates.append(mg)
        (folder / "report.md").write_text(f"# Listing gauntlet: {p['name']}\n\n{'PASSED' if passed(gates) else 'FAILED'} ({sum(g.ok for g in gates)} of {len(gates)} gates; soft gates do not block)\n\n{gates_md(gates)}\n", encoding="utf-8")
        (folder / "CHECKLIST.md").write_text(checklist(p, files, made_video), encoding="utf-8")
        results[p["id"]] = {"gates": gates, "passed": passed(gates), "folder": str(folder), "images": len(files), "video": made_video}
    return results


def check(only: str | None = None) -> dict[str, list[Gate]]:
    """The text, file and (when a pack is already built) image gates, without rendering anything."""
    out = {}
    for p in products(only):
        folder = OUT / p["id"]
        ensure_files(p)
        gates = text_gates(p) + file_gates(p)
        imgs = sorted((folder / "etsy" / "images").glob("*.jpg"))
        if imgs:
            gates += image_gates(imgs, folder / "gumroad" / "cover.jpg" if (folder / "gumroad" / "cover.jpg").exists() else None,
                                 folder / "gumroad" / "thumbnail.jpg" if (folder / "gumroad" / "thumbnail.jpg").exists() else None)
            gates += video_gates(folder / "etsy" / "video.mp4")
        mg = math_gate(p)
        if mg:
            gates.append(mg)
        out[p["id"]] = gates
    return out


def _write_copy(p: dict, folder: Path) -> None:
    e, g = p["etsy"], p["gumroad"]
    (folder / "etsy" / "title.txt").write_text(e["title"] + "\n", encoding="utf-8")
    (folder / "etsy" / "description.txt").write_text(e["description"] + "\n", encoding="utf-8")
    (folder / "etsy" / "tags.txt").write_text("\n".join(e["tags"]) + "\n", encoding="utf-8")
    (folder / "etsy" / "details.md").write_text(
        f"# Etsy listing details: {p['name']}\n\n- **Price:** ${p['price']} (test range {', '.join('$' + str(x) for x in p['price_test'])}; change only after about 20 views)\n"
        f"- **Type:** {e['type']} (no shipping)\n- **Who made it:** {e['who_made']}\n- **What is it:** {e['what_is_it']}\n- **When was it made:** {e['when_made']}\n"
        f"- **Quantity:** 999 (digital)\n- **Renewal:** automatic\n- **Files to attach:** " + ", ".join(Path(f).name for f in [p["file"], *p.get("extra_files", [])]) + "\n"
        "- **AI disclosure:** the description carries the line \"Designed by Quiet Money with AI assistance.\" Re-read Etsy's current Creativity Standards in the listing form before you publish.\n", encoding="utf-8")
    (folder / "gumroad" / "name.txt").write_text(g["name"] + "\n", encoding="utf-8")
    (folder / "gumroad" / "summary.txt").write_text(g["summary"] + "\n", encoding="utf-8")
    (folder / "gumroad" / "description.md").write_text(g["description"] + "\n", encoding="utf-8")
    (folder / "gumroad" / "tags.txt").write_text("\n".join(g["tags"]) + "\n", encoding="utf-8")
    (folder / "gumroad" / "after-purchase.txt").write_text(g["after_purchase"] + "\n", encoding="utf-8")


def checklist(p: dict, files: list[Path], video: bool) -> str:
    names = ", ".join(Path(f).name for f in [p["file"], *p.get("extra_files", [])])
    return f"""# Listing day: {p['name']}

Everything below is ready in this folder. Nothing was published; you press the buttons. About 15 minutes per shop.

## Etsy (Shop Manager > Listings > Add a listing)
1. **Photos:** upload `etsy/images/` in file-name order ({len(files)} images; the first one is the main photo). Use "Adjust thumbnail" and keep the headline and device inside the middle.
2. **Video:** {'upload `etsy/video.mp4` (silent, square, about 12 seconds).' if video else 'no video was built here (needs ffmpeg); skip it.'}
3. **Title:** paste `etsy/title.txt`. **Tags:** paste the 13 lines of `etsy/tags.txt` one by one.
4. **About this listing:** {p['etsy']['who_made']} / {p['etsy']['what_is_it']} / {p['etsy']['when_made']}. If the form asks about AI-generated content, answer truthfully (the pictures are drawn from the real product files; the copy and the product were made with AI assistance).
5. **Description:** paste `etsy/description.txt`.
6. **Type:** Digital download. Attach: {names}. **Price:** ${p['price']} (test range {', '.join('$' + str(x) for x in p['price_test'])}).
7. **Save as draft first**, look at the preview on your phone, then publish. Etsy charges a 20 cent listing fee per listing.

## Gumroad (Products > New product > Digital product)
1. **Name:** `gumroad/name.txt`. **Price:** ${p['price']}.
2. **Cover:** `gumroad/cover.jpg`. **Thumbnail:** `gumroad/thumbnail.jpg`. **Extra images:** the files in `etsy/images/` (Gumroad accepts them as they are).
3. **Summary:** `gumroad/summary.txt`. **Description:** paste `gumroad/description.md` (Gumroad understands the bold and bullet marks).
4. **Content:** upload {names}. **Tags:** `gumroad/tags.txt`.
5. **After purchase message:** `gumroad/after-purchase.txt`. **Refund policy:** 30 days.
6. Save, view the product page as a customer would, then publish.

## Before you press publish
- Read `report.md`: every hard gate must say pass.
- The price is a test. Change it only after about 20 views, never to chase a sale that has not happened.
- No testimonials, no countdowns, no "selling fast": none of that is true, so none of it goes on the page.
"""


def report(results: dict[str, dict]) -> str:
    lines = []
    for pid, r in results.items():
        bad = [g for g in r["gates"] if not g.ok]
        lines.append(f"{'PASS' if r['passed'] else 'FAIL'}  {pid}: {r['images']} images, video {'yes' if r['video'] else 'no'}, {sum(g.ok for g in r['gates'])}/{len(r['gates'])} gates -> {r['folder']}")
        lines += [f"        {'hard' if g.hard else 'soft'}: {g.name}: {g.detail}" for g in bad]
    return "\n".join(lines)
