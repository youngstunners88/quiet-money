"""The listing gauntlet and the picture toolkit: the mistakes that get a shop warned are caught before anything is uploaded."""

import copy
import shutil
import zipfile

import pytest
from PIL import Image, ImageDraw

from faceless import listing, mockup


@pytest.fixture(scope="module")
def products():
    return listing.catalog()["products"]


def failing(gates):
    return {g.name for g in gates if not g.ok and g.hard}


def test_the_real_catalog_passes_every_text_and_file_gate(products):
    for p in products:
        listing.ensure_files(p)                      # the kit zip is a gitignored build output: a clean checkout (CI) has to assemble it
        assert failing(listing.text_gates(p) + listing.file_gates(p)) == set(), p["id"]


def test_a_missing_kit_zip_is_assembled_from_the_committed_parts(tmp_path, monkeypatch):
    from faceless import product_print
    root = tmp_path / "channel" / "products"
    for rel in ("rat-race-escape-planner/Rat-Race-Escape-Planner.xlsx", "debt-payoff-planner/Debt-Payoff-and-Compound-Interest-Planner.xlsx",
                "money-reset-printables/Money-Reset-Printables-Letter.pdf", "money-reset-printables/Money-Reset-Printables-A4.pdf"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"part " + rel.encode())
    monkeypatch.setattr(listing, "STUDIO", tmp_path)
    monkeypatch.setattr(product_print, "OUT", root)
    p = {"file": "channel/products/money-reset-kit/Money-Reset-Kit.zip", "extra_files": []}
    assert {g.name: g.ok for g in listing.file_gates(p)}["files_exist"] is False
    assert listing.ensure_files(p) == [p["file"]]
    with zipfile.ZipFile(tmp_path / p["file"]) as zf:
        names = zf.namelist()
    assert "Money-Reset-Kit/READ-ME-FIRST.txt" in names and sum(n.endswith((".xlsx", ".pdf")) for n in names) == 4
    assert {g.name: g.ok for g in listing.file_gates(p)}["files_exist"] is True
    assert listing.ensure_files(p) == []             # nothing left to make


def test_a_kit_with_a_part_missing_is_reported_not_faked(tmp_path, monkeypatch):
    from faceless import product_print
    monkeypatch.setattr(listing, "STUDIO", tmp_path)
    monkeypatch.setattr(product_print, "OUT", tmp_path / "channel" / "products")
    p = {"file": "channel/products/money-reset-kit/Money-Reset-Kit.zip", "extra_files": []}
    assert listing.ensure_files(p) == []
    assert {g.name: g.ok for g in listing.file_gates(p)}["files_exist"] is False


def test_every_product_has_the_fields_a_listing_needs(products):
    assert len(products) == 4 and {p["kind"] for p in products} == {"spreadsheet", "printable", "bundle"}
    for p in products:
        assert len(p["etsy"]["title"]) <= 140 and len(p["etsy"]["tags"]) == 13 and p["gumroad"]["after_purchase"]
        assert p["price"] in p["price_test"] and len(p["chips"]) == 3 and p["steps"] and p["notes"]
        if p["kind"] != "bundle":
            assert p["features"] and all(1 <= f["page"] <= max(p["pages"].values()) for f in p["features"])


def mutate(p, **changes):
    q = copy.deepcopy(p)
    for path, value in changes.items():
        node = q
        *head, last = path.split(".")
        for k in head:
            node = node[k]
        node[last] = value
    return q


def test_the_gauntlet_catches_what_gets_listings_removed(products):
    p = products[0]
    cases = {
        "no_income_claims": mutate(p, **{"etsy.description": p["etsy"]["description"] + "\nGet rich quick and quit your job."}),
        "no_credit_repair_language": mutate(p, **{"gumroad.description": p["gumroad"]["description"] + " Improve your credit score fast."}),
        "no_fake_proof_or_scarcity": mutate(p, **{"gumroad.summary": "Bestseller! Only 3 left, sale ends tonight."}),
        "no_trademarks_in_title_or_tags": mutate(p, **{"etsy.tags": p["etsy"]["tags"][:12] + ["dave ramsey"]}),
        "etsy_tags_valid": mutate(p, **{"etsy.tags": p["etsy"]["tags"] + ["one too many"]}),
        "etsy_title_length": mutate(p, **{"etsy.title": "x" * 141}),
        "etsy_ai_disclosure": mutate(p, **{"etsy.description": p["etsy"]["description"].replace("Designed by Quiet Money with AI assistance.", "")}),
        "etsy_not_financial_advice": mutate(p, **{"etsy.description": p["etsy"]["description"].replace("not financial advice", "a great plan")}),
        "compatibility_claims_verified": mutate(p, **{"etsy.description": p["etsy"]["description"] + "\nWorks in Apple Numbers and Airtable."}),
        "price_set": mutate(p, price=0),
    }
    for gate, q in cases.items():
        assert gate in failing(listing.text_gates(q)), gate


def test_a_negated_guarantee_is_fine_but_a_promised_one_is_not(products):
    p = products[0]
    ok = mutate(p, **{"etsy.description": p["etsy"]["description"] + "\nReturns are never guaranteed and nothing here is a guarantee."})
    assert "no_income_claims" not in failing(listing.text_gates(ok))
    bad = mutate(p, **{"etsy.description": p["etsy"]["description"] + "\nGuaranteed returns for everyone."})
    assert "no_income_claims" in failing(listing.text_gates(bad))


def test_a_missing_product_file_blocks_the_listing(products):
    q = mutate(products[0], file="channel/products/nope.xlsx")
    assert "files_exist" in failing(listing.file_gates(q))


def picture(path, size, shade=40, noise=True):
    im = Image.new("RGB", size, (shade, shade, shade))
    if noise:
        d = ImageDraw.Draw(im)
        for x in range(0, size[0], 40):
            d.line([(x, 0), (x, size[1])], fill=(shade + 150, shade + 150, shade + 150), width=3)
    im.save(path, "JPEG", quality=92)
    return path


def test_image_gates_flag_small_dark_and_blurry_main_images(tmp_path):
    good = picture(tmp_path / "good.jpg", (2800, 2100), shade=90)
    small = picture(tmp_path / "small.jpg", (1800, 1350), shade=90)
    dark = picture(tmp_path / "dark.jpg", (2800, 2100), shade=3, noise=False)
    flat = picture(tmp_path / "flat.jpg", (2800, 2100), shade=120, noise=False)
    assert failing(listing.image_gates([good] * 5, None, None)) == set()
    assert "etsy_images_2000px" in failing(listing.image_gates([small] + [good] * 4, None, None))
    assert "etsy_main_image_not_dark" in failing(listing.image_gates([dark] + [good] * 4, None, None))
    assert "etsy_main_image_sharp" in failing(listing.image_gates([flat] + [good] * 4, None, None))
    portrait = picture(tmp_path / "portrait.jpg", (2100, 2800), shade=90)
    assert "etsy_main_image_landscape_or_square" in failing(listing.image_gates([portrait] + [good] * 4, None, None))


def test_cover_and_thumbnail_shapes_are_checked(tmp_path):
    cover = picture(tmp_path / "c.jpg", (1920, 1080), shade=90)
    thumb = picture(tmp_path / "t.jpg", (1200, 1200), shade=90)
    bad_cover = picture(tmp_path / "bc.jpg", (1600, 1200), shade=90)
    bad_thumb = picture(tmp_path / "bt.jpg", (1200, 900), shade=90)
    imgs = [picture(tmp_path / f"i{i}.jpg", (2800, 2100), shade=90) for i in range(5)]
    assert failing(listing.image_gates(imgs, cover, thumb)) == set()
    assert failing(listing.image_gates(imgs, bad_cover, bad_thumb)) == {"gumroad_cover_16x9", "gumroad_thumbnail_square"}


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg is not installed")
def test_the_listing_video_is_short_silent_and_square(tmp_path):
    frames = [picture(tmp_path / f"f{i}.jpg", (2800, 2100), shade=60 + i * 20) for i in range(4)]
    out = tmp_path / "v.mp4"
    assert mockup.video(frames, out, seconds_each=2.2, size=(540, 540))
    gates = {g.name: g for g in listing.video_gates(out)}
    assert gates["etsy_video_length"].ok and gates["etsy_video_silent"].ok and gates["etsy_video_size"].ok       # 540 px clears Etsy's 500 px minimum
    assert "540x540" in gates["etsy_video_size"].detail


def test_delivered_images_are_at_least_2000_px_on_both_sides():
    im = mockup.deliver(Image.new("RGB", (mockup.W, mockup.H), (10, 10, 10)))
    assert im.size == (2800, 2100) and min(im.size) >= 2000


def test_headlines_shrink_to_fit_and_never_exceed_two_lines():
    im = Image.new("RGB", (mockup.W, mockup.H))
    d = ImageDraw.Draw(im)
    y0 = 100
    y1 = mockup.headline(d, y0, "Debt Payoff & Compound Interest Planner for people who want a plan", 176, mockup.SAFE_R - mockup.SAFE_L + 200)
    assert y0 < y1 < 700


def test_window_keeps_the_page_proportions_and_shows_the_real_tabs():
    page = Image.new("RGB", (2000, 800), "white")
    win = mockup.window(page, 1000, title="x.xlsx", tabs=("Start here", "1 Your numbers"), active=1)
    assert win.mode == "RGBA" and win.width == 1000 and win.height > 400          # 400 for the page, bars on top
    assert win.getpixel((0, 0))[3] == 0                                           # rounded corners are transparent


def test_autocrop_trims_page_margins_but_keeps_air():
    pg = Image.new("RGB", (1000, 800), "white")
    ImageDraw.Draw(pg).rectangle([300, 200, 600, 400], fill="black")
    c = mockup.autocrop(pg, pad=20)
    assert c.size == (341, 241)


def test_the_paper_fan_is_a_cropped_transparent_layer():
    fan = mockup.paper_fan([Image.new("RGB", (850, 1100), "white")] * 3, width=300)
    assert fan.mode == "RGBA" and fan.width > 600 and fan.height > 300


def test_checklist_names_the_files_and_the_approval_steps(products):
    text = listing.checklist(products[0], [listing.OUT / "x.jpg"] * 9, True)
    assert "Rat-Race-Escape-Planner.xlsx" in text and "Nothing was published" in text and "etsy/video.mp4" in text and "gumroad/cover.jpg" in text
