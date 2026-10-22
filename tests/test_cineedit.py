from faceless import cineedit


def test_ramp_slows_into_the_hit_then_snaps_through_it():
    segs = cineedit.ramp_plan(10.0, 8.9)
    speeds = {round(a, 2): s for a, b, s in segs}
    assert speeds[7.9] == cineedit.SLOW < 1.0, "the second before the hit runs in slow motion"
    assert speeds[8.9] == 2.0, "the strike itself snaps past"


def test_slow_motion_is_interpolated_not_frame_doubled():
    """Repeating frames is what made the first batch judder; a slowed segment is rebuilt with optical flow."""
    import inspect
    seg_src = inspect.getsource(cineedit._segments)
    assert "SMOOTH" in seg_src and "speed < 1.0" in seg_src
    assert cineedit.SLOW > 0.5, "too deep a slow shows its seams even interpolated"


def test_every_speed_is_usable_by_atempo():
    for impact in (2.0, 5.0, 8.9, 9.8):
        for _a, _b, speed in cineedit.ramp_plan(10.0, impact):
            assert 0.5 <= speed <= 2.0


def test_build_is_compressed_so_the_hit_arrives_early():
    segs = cineedit.ramp_plan(10.0, 8.9)
    assert sum((b - a) / s for a, b, s in segs) < 9.0


def test_hit_lands_where_the_ramp_puts_it():
    segs = [(0.0, 2.0, 2.0), (2.0, 3.0, 0.5)]        # 1.0s then 2.0s on the edited timeline
    assert abs(cineedit._impact_after_ramp(segs, 2.0) - 1.0) < 1e-6
    assert abs(cineedit._impact_after_ramp(segs, 3.0) - 3.0) < 1e-6


def test_a_dark_clip_is_not_crushed_like_a_bright_one():
    night, night_name, night_flash = cineedit.grade_for(50.0)
    day, day_name, day_flash = cineedit.grade_for(110.0)
    assert (night_name, day_name) == ("night", "day")
    assert night != day
    assert night_flash < day_flash, "a dark clip needs a softer flash or it blows out"
