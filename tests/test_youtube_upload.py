"""The YouTube uploader: it must refuse the wrong channel before sending anything, and send the whole file once."""

import pytest

from faceless.providers import ProviderError
from faceless.providers import composio_tools as ct

CH = "UC9B1QBr3_8Eulok8IdQbCqQ"


class FakeStarted:
    headers = {"location": "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&upload_id=x"}


class FakeResp:
    status_code = 200

    def json(self):
        return {"id": "vid123", "snippet": {"channelId": CH}, "status": {"privacyStatus": "public"}}


def _wire(monkeypatch, channels, sent):
    monkeypatch.setattr(ct, "_ensure_key", lambda: None)
    monkeypatch.setattr(ct, "connected_toolkits", lambda: {"youtube": "ca_test"})
    monkeypatch.setattr(ct, "execute", lambda slug, args=None, job=None: {"data": {"items": [{"id": c} for c in channels]}})
    monkeypatch.setattr(ct, "_start_youtube_session", lambda account, body, size: sent.setdefault("body", body) and FakeStarted())

    class Session:
        def put(self, url, data=None, headers=None, timeout=None):
            sent["bytes"] = data.read()
            sent["headers"] = headers
            assert timeout
            return FakeResp()

    monkeypatch.setattr(ct, "http", lambda: Session())


def test_wrong_channel_uploads_nothing(monkeypatch, tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x" * 100)
    sent = {}
    _wire(monkeypatch, ["UCxBalkIv0Z0rf_MwPNXMvIw"], sent)
    with pytest.raises(ProviderError, match="nothing was uploaded"):
        ct.youtube_upload(str(video), "t", "d", expected_channel_id=CH)
    assert "bytes" not in sent and "body" not in sent


def test_whole_file_sent_once_with_ai_label(monkeypatch, tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"y" * 4096)
    sent = {}
    _wire(monkeypatch, [CH], sent)
    out = ct.youtube_upload(str(video), "Title", "Desc", ["a"], expected_channel_id=CH)
    assert out == {"video_id": "vid123", "channel_id": CH, "privacy": "public"}
    assert sent["bytes"] == b"y" * 4096
    assert sent["headers"]["Content-Length"] == "4096"
    assert sent["body"]["status"]["containsSyntheticMedia"] is True
