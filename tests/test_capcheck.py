from faceless import capcheck

ASS = "\n".join(
    "Dialogue: 1,0:00:%05.2f,0:00:%05.2f,Caption,,0,0,0,,{\\pos(540,1300)}{\\c&H0000FFFF\\fscx108\\fscy108}%s{\\c&H00FFFFFF\\fscx100\\fscy100}"
    % (t, t + 0.4, w) for t, w in [(1.0, "ONE"), (1.5, "TWO"), (2.0, "THREE"), (2.5, "FOUR")])


def heard(shift):
    return [{"w": w, "start": t + shift, "end": t + shift + 0.3} for t, w in [(1.0, "one"), (1.5, "two"), (2.0, "three"), (2.5, "four")]]


def test_active_words():
    assert capcheck.active_words(ASS)[0] == (1.0, "ONE")


def test_drift_measured():
    ds = capcheck.drifts(capcheck.active_words(ASS), heard(0.5))
    assert len(ds) == 4 and all(abs(d + 0.5) < 1e-6 for d in ds)
