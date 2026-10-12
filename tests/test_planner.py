"""The Daily Planner: content, numbers, art, the handle cleaner and the PDF layout."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from faceless import moneymath as mm
from faceless import planner_art, planner_clean, planner_content as pc


@pytest.fixture(scope="module")
def days():
    return pc.load()


def test_365_days_numbered_in_order_with_the_weekly_rhythm(days):
    assert [d.n for d in days] == list(range(1, 366))
    assert [d.kind for d in days[:7]] == list("LNDMASR") and days[-1].kind == "X"
    assert all(d.title and d.lesson and (d.task or d.kind in "SR") for d in days)
    assert len({d.lesson for d in days}) == 365


def test_every_number_is_computed_not_typed(days):
    blob = " ".join(f"{d.title} {d.lesson} {d.task}" for d in days)
    assert "{" not in blob and "}" not in blob and "nan" not in blob.lower().split()
    # spot checks against the shared math the videos use
    assert mm.money(mm.future_value_monthly(200, 0.08, 30)) in days[148].lesson           # day 149: $200 a month for 30 years
    assert mm.money(mm.capital_for_income(2000)) in days[211].lesson                       # day 212: passive income needs capital


def test_placeholders_are_a_closed_set_of_pure_arithmetic():
    assert pc.fill("{fv:200,8,30}") == mm.money(mm.future_value_monthly(200, 0.08, 30))
    assert pc.fill("{usd:2000/12}") == "$167"
    with pytest.raises(ValueError):
        pc.fill("{fv:__import__('os').getcwd(),8,30}")                                     # no names, no calls
    with pytest.raises(ValueError):
        pc.fill("{nope:1}")


def test_an_incomplete_week_is_refused(tmp_path):
    for f in pc.FILES:
        (tmp_path / f).write_text((pc.CONTENT / f).read_text(encoding="utf-8").replace("# WEEK 20 |", "# WEEK 99 |"), encoding="utf-8")
    with pytest.raises(ValueError, match="week 20"):
        pc.load(tmp_path)


def test_content_gives_no_advice_and_no_promises(days):
    from faceless import product_planner as pp
    blob = "\n".join(f"{d.title}\n{d.lesson}\n{d.task}" for d in days)
    assert not pp.ADVICE.search(blob)


def test_every_motif_draws_and_the_same_day_gives_the_same_picture():
    for m in planner_art.MOTIFS:
        im = planner_art.render_motif(m, 3)
        assert im.size == (planner_art.W, planner_art.H)
        assert np.asarray(im).max() > 150                                                   # there is gold in it
    a, b = planner_art.render_motif("stack", 9), planner_art.render_motif("stack", 9)
    assert np.array_equal(np.asarray(a), np.asarray(b))
    assert not np.array_equal(np.asarray(a), np.asarray(planner_art.render_motif("stack", 10)))


def test_an_owner_picture_beats_a_drawn_one_and_any_shape_fits_the_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(planner_art, "SOURCE", tmp_path / "source")
    monkeypatch.setattr(planner_art, "CLEAN", tmp_path / "clean")
    (tmp_path / "source").mkdir()
    Image.new("RGB", (1000, 1500), (200, 30, 30)).save(tmp_path / "source" / "day-005.png")
    im, src = planner_art.day_art(5, "stack")
    assert src == "owner" and im.size == (planner_art.W, planner_art.H)
    assert planner_art.day_art(6, "stack")[1] == "drawn"
    (tmp_path / "clean").mkdir()
    Image.new("RGB", (1000, 500), (30, 200, 30)).save(tmp_path / "clean" / "day-005.png")
    assert planner_art.owner_image(5).parent.name == "clean"                                # the cleaned copy is preferred


@pytest.mark.parametrize("where,size", [("bottom-center", 26), ("bottom-right", 22), ("top-left", 30)])
def test_the_handle_is_removed_and_nothing_else_is_touched(where, size):
    base = planner_art.render_motif("stack", 5).resize((1600, 727))
    d = ImageDraw.Draw(base)
    from PIL import ImageFont
    from faceless import brand
    f = ImageFont.truetype(str(brand.Paths.fonts / "Montserrat-ExtraBold.ttf"), size)
    text = "@youngstunnersss"
    tw = d.textlength(text, font=f)
    x, y = {"bottom-center": ((1600 - tw) / 2, 672), "bottom-right": (1600 - tw - 30, 676), "top-left": (30, 22)}[where]
    marked = base.copy()
    ov = Image.new("RGBA", marked.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((x, y), text, font=f, fill=(235, 230, 215, 200))
    marked = Image.alpha_composite(marked.convert("RGBA"), ov).convert("RGB")
    out, found = planner_clean.clean_image(marked)
    assert found
    a, b, o = (np.asarray(i).astype(int) for i in (marked, out, base))
    box = (slice(int(y) - 6, int(y) + size + 14), slice(int(x) - 6, int(x + tw) + 6))
    assert np.abs(b - o)[box].mean() < 3 < np.abs(a - o)[box].mean()                       # the text is gone, the ground is back
    changed = np.any(a != b, axis=2)
    ys, xs = np.nonzero(changed)
    assert ys.min() >= box[0].start - 30 and ys.max() <= box[0].stop + 30                  # only the strip around the handle changed
    assert xs.min() >= box[1].start - 30 and xs.max() <= box[1].stop + 30


def test_art_without_text_is_left_alone():
    base = planner_art.render_motif("rain", 4).resize((1600, 727))
    out, found = planner_clean.clean_image(base)
    assert found == [] and np.array_equal(np.asarray(out), np.asarray(base))


def test_ingest_numbers_pictures_in_natural_order(tmp_path, monkeypatch):
    monkeypatch.setattr(planner_art, "SOURCE", tmp_path / "source")
    src = tmp_path / "in"
    src.mkdir()
    for n in ("img10.png", "img2.png", "img1.png"):
        Image.new("RGB", (10, 10)).save(src / n)
    done = planner_clean.ingest(src, start=40)
    assert [d for d, _ in done] == [40, 41, 42]
    assert Image.open(tmp_path / "source" / "day-041.png").size == (10, 10) and (tmp_path / "source" / "day-042.png").exists()


def test_the_pdf_builds_with_every_page_kind_and_stays_inside_the_margins(tmp_path):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    from faceless import product_planner as pp
    every = pc.load()
    days = every[:14]
    art = {d.n: tmp_path / f"d{d.n}.jpg" for d in days}
    for d in days:
        planner_art.render_motif(d.motif, d.n).save(art[d.n], "JPEG", quality=70)
    out = pp.build_pdf("Letter", days, art, None, tmp_path / "t.pdf", pc.week_themes(every))
    r = pypdf.PdfReader(str(out))
    assert len(r.pages) == pp.FRONT + 14 + 2 + pp.BACK                 # weeks 1 and 2 each end with a wellness break page
    text = " ".join(p.extract_text() for p in r.pages)
    assert "WELLNESS BREAK" in text and "not medical advice" in text.lower() and "DAY 006" in text and "WEEKLY CHECK-IN" in text and "REFLECT AND RESET" in text and "not financial advice" in text.lower()
    assert str(out.stat().st_size) and out.stat().st_size < 3 * 2**20


def test_a_page_that_would_clip_is_refused_not_shipped(tmp_path):
    pytest.importorskip("reportlab")
    from faceless import product_planner as pp
    d = pc.load()[0]
    d.lesson = "word " * 400
    art = tmp_path / "a.jpg"
    planner_art.render_motif("coin", 1).save(art)
    with pytest.raises(pp.Overflow):
        pp.build_pdf("A4", [d], {1: art}, None, tmp_path / "x.pdf", pc.week_themes(pc.load()))


def test_the_catalog_lists_the_planner_with_both_sizes():
    from faceless import listing
    p = {q["id"]: q for q in listing.catalog()["products"]}["daily-quiet-money-planner"]
    assert p["layout"] == "planner" and len(p["etsy"]["tags"]) == 13 and p["price"] in p["price_test"]
    assert p["file"].endswith("Letter.pdf") and p["extra_files"][0].endswith("A4.pdf")
    assert {g.name: g.ok for g in listing.text_gates(p)}.get("no_income_claims") is True


def test_the_wellness_manifest_drops_the_duplicates_and_every_poster_has_a_line_and_a_file():
    from faceless import planner_wellness as w
    assert w.check() == [] and len(w.kept()) == 40
    assert set(w.DUPLICATES) == {8, 25, 30, 31} and not set(w.DUPLICATES) & set(w.kept())
    assert all(1 <= len(line.split()) <= 40 for _t, line in w.POSTERS.values())
    assert set(w.REVIEW) <= set(w.kept())                                                     # every flagged poster is one that is used
    assert w.week_poster(1) == 1 and w.week_poster(40) == 44 and w.week_poster(41) is None
    assert "not medical advice" in w.NOT_MEDICAL


def test_the_quinton_cover_renders_at_any_size_with_a_glowing_pin_and_falls_back_to_the_coin():
    import numpy as np
    from faceless import planner_cover as pc
    big = pc.cover(850, 1100)
    assert big.size == (850, 1100) and pc.cover(595, 842).size == (595, 842)
    scene = Image.open(pc.Paths.root / "assets" / "planner" / "cover" / pc.SCENES["steeple"])
    pin = pc._pin(scene)
    assert pin is not None and 0.5 < pin[0] < 0.85 and 0.45 < pin[1] < 0.8                      # the pin is on the right chest (his left lapel)
    a = np.asarray(big).astype(int)
    assert a[:int(1100 * 0.03)].mean() < 60 and a[:, :, 0].max() > 230                           # dark ground at the top, gold in the title
    assert pc.cover_coin(425, 550).size == (425, 550)
    assert pc.cover(425, 550, style="nope").size == (425, 550)                                    # an unknown style gives the coin cover, never a crash
