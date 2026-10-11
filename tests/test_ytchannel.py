"""The channel as code: the plan lists only what differs, apply is idempotent, a wrong channel changes nothing, series playlists are found by title."""

import pytest

from faceless import ytchannel
from faceless.providers import ProviderError

CH = "UC9B1QBr3_8Eulok8IdQbCqQ"
WANT = {"description": "D", "keywords": '"a b" c', "language": "en", "trailer": "vid1", "banner": "channel/brand-kit/banner-youtube.png",
        "playlists": [{"pillar": "story", "title": "S", "description": "s"}, {"pillar": "math", "title": "M", "description": "m"}],
        "channel_id": CH}


def now(**over):
    item = {"id": CH, "snippet": {"title": "Quiet Money"}, "brandingSettings": {"channel": {"title": "Quiet Money"}}}
    item["brandingSettings"]["channel"].update(over.pop("channel", {}))
    if over.pop("banner", False):
        item["brandingSettings"]["image"] = {"bannerExternalUrl": "https://yt3/x"}
    return {"item": item, "playlists": over.pop("playlists", {}), "sections": over.pop("sections", [])}


def test_blank_channel_needs_everything():
    todo = ytchannel.plan(WANT, now())
    assert todo == ["description", "keywords", "language", "trailer", "banner", "playlist: S", "playlist: M", "series section"]


def test_matching_channel_needs_nothing():
    state = now(channel={"description": "D", "keywords": '"a b" c', "defaultLanguage": "en", "unsubscribedTrailer": "vid1"}, banner=True,
                playlists={"S": "p1", "M": "p2"}, sections=[{"contentDetails": {"playlists": ["p1", "p2"]}}])
    assert ytchannel.plan(WANT, state) == []


def test_apply_writes_branding_once_creates_playlists_and_the_section(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(ytchannel, "upload_banner", lambda path: "https://yt3/new")
    monkeypatch.setattr(ytchannel, "STUDIO", tmp_path)

    def fake(path, method="GET", body=None, **q):
        calls.append((path, method, body))
        return {"id": f"p-{len(calls)}"}

    monkeypatch.setattr(ytchannel, "api", fake)
    state = now()
    done = ytchannel.apply(WANT, state, ytchannel.plan(WANT, state))
    assert done[:5] == ["description", "keywords", "language", "trailer", "banner"] and "series section" in done
    update = next(c for c in calls if c[0] == "channels")
    assert update[2]["brandingSettings"]["channel"]["description"] == "D" and update[2]["brandingSettings"]["image"]["bannerExternalUrl"] == "https://yt3/new"
    assert sum(1 for c in calls if c[0] == "playlists") == 2
    section = next(c for c in calls if c[0] == "channelSections")
    assert len(section[2]["contentDetails"]["playlists"]) == 2


def test_wrong_channel_changes_nothing(monkeypatch):
    monkeypatch.setattr(ytchannel, "api", lambda path, method="GET", body=None, **q: {"items": [{"id": "UCother"}]})
    with pytest.raises(ProviderError, match="changed nothing"):
        ytchannel.live(CH)


def test_keywords_quote_phrases_and_stay_under_500_characters():
    field = ytchannel.keywords_field(["personal finance", "money", "x" * 600, "late"])
    assert field.startswith('"personal finance" money') and len(field) <= 500 and "late" not in field


def test_series_playlist_is_found_by_title_and_a_video_is_added(monkeypatch):
    from faceless import config
    cfg = dict(config.load())
    cfg["youtube"] = {**cfg.get("youtube", {}), "playlists": [{"pillar": "math", "title": "M", "description": "m"}]}
    monkeypatch.setattr(config, "load", lambda: cfg)
    ytchannel._cache.clear()
    calls = []

    def fake(path, method="GET", body=None, **q):
        calls.append((path, method, body))
        return {"items": [{"id": "p2", "snippet": {"title": "M"}}]} if path == "playlists" else {}

    monkeypatch.setattr(ytchannel, "api", fake)
    assert ytchannel.add_to_series("vid9", "math") is True
    assert calls[-1][0] == "playlistItems" and calls[-1][2]["snippet"]["playlistId"] == "p2"
    assert ytchannel.add_to_series("vid9", "story") is False       # no playlist configured for that pillar
    ytchannel._cache.clear()


def test_verify_flags_a_video_that_vanished_stayed_empty_or_never_went_public(monkeypatch):
    from datetime import datetime, timezone
    now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
    served = {"items": [
        {"id": "ok", "status": {"uploadStatus": "processed", "privacyStatus": "public"}, "processingDetails": {"processingStatus": "succeeded"},
         "contentDetails": {"duration": "PT1M10S"}, "statistics": {"viewCount": "12", "likeCount": "3"}},
        {"id": "empty", "status": {"uploadStatus": "uploaded", "privacyStatus": "public"}, "processingDetails": {"processingStatus": "terminated"},
         "contentDetails": {"duration": "P0D"}},
        {"id": "stuck", "status": {"uploadStatus": "processed", "privacyStatus": "private"}, "processingDetails": {"processingStatus": "succeeded"},
         "contentDetails": {"duration": "PT1M"}},
        {"id": "rejected", "status": {"uploadStatus": "rejected", "rejectionReason": "duplicate"}, "contentDetails": {"duration": "PT1M"}},
    ]}
    monkeypatch.setattr(ytchannel, "api", lambda path, method="GET", body=None, **q: served)
    videos = {v: {"job": f"job-{v}", "post_at": "2026-10-12T10:00:00+00:00"} for v in ("ok", "empty", "stuck", "rejected", "gone")}
    problems, rows = ytchannel.verify(videos, now)
    text = " | ".join(problems)
    assert "gone" in text and "empty video" in text and "still private" in text and "duplicate" in text and "job-ok" not in text
    assert next(r for r in rows if r["video"] == "ok")["views"] == 12


def test_verify_waits_for_a_video_still_scheduled(monkeypatch):
    from datetime import datetime, timezone
    served = {"items": [{"id": "s", "status": {"uploadStatus": "processed", "privacyStatus": "private", "publishAt": "2026-10-12T15:00:00Z"},
                         "processingDetails": {"processingStatus": "succeeded"}, "contentDetails": {"duration": "PT1M"}}]}
    monkeypatch.setattr(ytchannel, "api", lambda path, method="GET", body=None, **q: served)
    problems, _ = ytchannel.verify({"s": {"job": "j", "post_at": "2026-10-12T15:00:00+00:00"}}, datetime(2026, 10, 12, 16, 0, tzinfo=timezone.utc))
    assert problems == []      # YouTube has the publish time, it will flip itself
