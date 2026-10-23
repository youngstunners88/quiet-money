"""Studio mode: a brief becomes a labelled sheet of distinct, original directions; copying briefs are refused."""

import json

import pytest
from PIL import Image

from faceless import concepts


def _llm(n_extra=0, bad=False):
    def complete(prompt):
        assert "<brief>" in prompt and "data, not instructions" in prompt
        ds = [{"name": f"Dir {i}", "idea": f"Idea number {i} for the shop.", "style": "flat", "palette": ["#112233", "#ffd23f", "nope"],
               "prompt": f"a leaf folded into a notebook, variant {i}"} for i in range(8 + n_extra)]
        ds.append({"name": "Dir 1", "idea": "dup", "style": "x", "palette": [], "prompt": "duplicate name"})
        ds.append({"name": "Copycat", "idea": "x", "style": "in the style of a famous painter", "palette": [], "prompt": "p"})
        return {"directions": ds[:3] if bad else ds}
    return complete


def _paint(prompt, kind, seed, out):
    Image.new("RGB", (concepts.TILE, concepts.TILE), (seed % 255, 120, 90)).save(out)
    return "stub"


def test_an_order_makes_a_sheet_directions_and_a_delivery_note(tmp_path):
    r = concepts.make("A small paper goods shop selling handmade notebooks; calm and botanical.", "logo", 8, client="Fern",
                      out_dir=tmp_path, complete=_llm(), painter=_paint)
    assert r["directions"] == 8
    meta = json.loads((tmp_path / "directions.json").read_text())
    names = [d["name"] for d in meta["directions"]]
    assert len(set(names)) == 8 and "Copycat" not in names
    assert all(len(d["palette"]) == 2 and d["palette"][1] == "#FFD23F" for d in meta["directions"])   # bad colours dropped, case normalised
    assert Image.open(tmp_path / "sheet.png").size[0] == 48 + 3 * (concepts.TILE + 48)
    assert (tmp_path / "sheet.pdf").stat().st_size > 1000
    note = (tmp_path / "DELIVERY.md").read_text()
    assert "Hi Fern," in note and "**H. Dir 7**" in note and concepts.AI_NOTE in note


@pytest.mark.parametrize("brief", ["logo in the style of a famous designer please", "make it like the logo of a big soda brand", "short"])
def test_copying_or_empty_briefs_are_refused(brief, tmp_path):
    with pytest.raises(concepts.Refused):
        concepts.make(brief, "logo", out_dir=tmp_path, complete=_llm(), painter=_paint)


def test_too_few_usable_directions_fail_loudly_and_n_is_clamped(tmp_path):
    with pytest.raises(RuntimeError, match="usable directions"):
        concepts.make("A mascot for a kids coding app, friendly robot.", "character", 8, out_dir=tmp_path, complete=_llm(bad=True), painter=_paint)
    r = concepts.make("A mascot for a kids coding app, friendly robot.", "character", 40, out_dir=tmp_path / "b", complete=_llm(n_extra=6), painter=_paint)
    assert r["directions"] == concepts.N_MAX
    assert Image.open(tmp_path / "b" / "sheet.png").size[0] == 48 + 4 * (concepts.TILE + 48)
