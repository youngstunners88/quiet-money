import pytest

from faceless import brain

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
<entry><yt:videoId>abcDEF12345</yt:videoId><title>A video</title><published>2026-10-19T10:00:00+00:00</published></entry>
<entry><yt:videoId>bad id; drop</yt:videoId><title>x</title></entry>
</feed>"""


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(brain, "SOURCES", tmp_path / "sources")
    monkeypatch.setattr(brain, "RAW", tmp_path / "raw")
    monkeypatch.setattr(brain, "INDEX", tmp_path / "INDEX.md")
    return tmp_path


def test_ingest_keeps_raw_text_out_of_the_notes_and_refuses_a_duplicate(home):
    note = brain.ingest("https://youtu.be/abcDEF12345", "word " * 50, "exa", "Some Speaker", "A title")
    assert note.exists() and not (home / "raw").joinpath(note.stem + ".txt").read_text().strip() == ""
    assert "word word word" not in note.read_text()
    with pytest.raises(ValueError, match="already"):
        brain.ingest("https://youtu.be/abcDEF12345", "again", "exa")


def test_check_flags_an_empty_reject_long_quotes_promises_and_keys(home):
    note = brain.ingest("https://example.com/v", "text", "owner")
    bad = brain.check([note])[note.name]
    assert any("Reject" in b for b in bad)
    text = note.read_text().replace("## Reject\n", "## Reject\nFake urgency.\n").replace(
        "## How Quiet Money could use it\n", "## How Quiet Money could use it\nYou will make $5,000 a month.\n")
    text += '\n"' + "word " * 30 + '"\nsk-' + "a" * 24 + "\n"
    note.write_text(text)
    bad = brain.check([note])[note.name]
    assert any("income promise" in b for b in bad) and any("quote over" in b for b in bad) and any("key-shaped" in b for b in bad)


def test_feed_parse_reads_only_valid_ids():
    got = brain.parse_feed(FEED)
    assert [v["video_id"] for v in got] == ["abcDEF12345"] and got[0]["url"] == "https://youtu.be/abcDEF12345"


def test_index_keeps_this_week_and_search_finds_a_note(home):
    (home / "INDEX.md").write_text("# old\n\n## This week (proposals, owners)\n1. keep me\n")
    note = brain.ingest("https://example.com/w", "x", "owner", title="Story loops")
    note.write_text(note.read_text().replace("## In one line\n", "## In one line\nStakes, a question, a twist, a re-hook.\n"))
    assert brain.index() == 1 and "keep me" in (home / "INDEX.md").read_text()
    assert brain.search("twist re-hook")[0]["note"] == note.name


def test_the_paid_fetch_refuses_a_bad_id():
    with pytest.raises(ValueError):
        brain.fetch_paid("../../etc")
