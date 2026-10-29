from faceless import ttpolicy


def test_removed_hero_caption_is_flagged():
    cap = "Every month something quietly bleeds you. Spot the leak, stop paying the toll, start the climb. Free money Reset checklist: link in bio."
    sev = {f.severity for f in ttpolicy.scan(cap)}
    assert "block" in sev and "warn" in sev
    assert ttpolicy.needs_commercial_disclosure(cap)


def test_clean_caption_passes():
    cap = "Every month a small cost quietly drains you. Spot it, cancel it. Free Reset checklist: link in bio. #money #personalfinance"
    assert not ttpolicy.blockers(cap)


def test_story_death_is_watch_only():
    fs = ttpolicy.scan("Ronald Read, a janitor, died with $8 million.")
    assert fs and all(f.severity == "watch" for f in fs)
    assert not ttpolicy.blockers("Ronald Read, a janitor, died with $8 million.")


def test_scam_phrases_block():
    assert ttpolicy.blockers("Guaranteed to double your money, no risk")
