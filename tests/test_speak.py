"""The command center's voice: Quinton's anchor as the reference, the key never in the page, voice input off until the owner says, and a
spoken command can only propose what a button can already do. Offline: Fish and Gemini are fake sessions."""

import base64
import json
import threading
import urllib.error
import urllib.request

import pytest

from faceless import events, ledger, serve, speak

SECRET = "fish-" + "k3y" * 12
TOKEN = "t" * 32


class Reply:
    def __init__(self, code, content=b"", body=None, text=""):
        self.status_code, self.content, self._body, self.text = code, content, body, text

    def json(self):
        return self._body


class Session:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def post(self, url, **kw):
        self.calls.append((url, kw))
        return self.reply


@pytest.fixture
def voice(tmp_path, monkeypatch):
    monkeypatch.setattr(speak, "CACHE", tmp_path / "voice")
    anchor = tmp_path / "anchor.wav"
    anchor.write_bytes(b"RIFF....WAVEfmt quinton")
    monkeypatch.setattr(speak, "ANCHOR", anchor)
    host = tmp_path / "host.json"
    host.write_text(json.dumps({"videos": [{"line": "Welcome to Quiet Money. I'm Quinton."}]}))
    monkeypatch.setattr(speak, "HOST", host)
    return tmp_path


SNAP = {"money": {"usd": 0, "receipts": 0}, "shipped": {"today": 2, "target": 5, "week": 13}, "youCount": 3,
        "crew": [{"name": "OpenCode", "lamp": "live"}, {"name": "Hermes", "lamp": "idle"}],
        "next": {"text": "Post 40 videos on X", "action": "Open the DM desk and send by hand", "do": None}}


def test_messagepack_encodes_the_request_types_exactly():
    assert speak.pack(None) == b"\xc0" and speak.pack(True) == b"\xc3" and speak.pack(5) == b"\x05" and speak.pack(-3) == b"\xfd"
    assert speak.pack("ab") == b"\xa2ab" and speak.pack("x" * 40) == b"\xd9\x28" + b"x" * 40 and speak.pack(b"\x01\x02") == b"\xc4\x02\x01\x02"
    assert speak.pack(b"z" * 300)[:3] == b"\xc5\x01\x2c" and speak.pack([1, "a"]) == b"\x92\x01\xa1a"
    assert speak.pack({"a": 1}) == b"\x81\xa1a\x01"
    with pytest.raises(TypeError):
        speak.pack(1.5)


def test_the_words_come_from_the_snapshot_and_invent_nothing():
    w = speak.words("summary", SNAP)
    assert "0.00 dollars from 0 receipts" in w and "2 of 5" in w and "1 agent at work: OpenCode" in w and "3 things wait for you" in w
    assert speak.words("summary", {**SNAP, "money": {"usd": None}}).startswith("Money in this month is unknown")
    assert speak.words("next", SNAP) == "Next: Post 40 videos on X. Open the DM desk and send by hand."


def test_quinton_says_it_with_his_anchor_and_the_key_stays_here(voice, monkeypatch):
    with pytest.raises(RuntimeError, match="no Fish Audio key"):
        speak.say("summary", SNAP, session=Session(Reply(200, b"ID3audio")))
    monkeypatch.setenv("FISH_AUDIO_API_KEY", SECRET)
    s = Session(Reply(200, b"ID3audio"))
    p = speak.say("summary", SNAP, session=s)
    url, kw = s.calls[0]
    assert url == "https://api.fish.audio/v1/tts" and kw["headers"]["Content-Type"] == "application/msgpack"
    assert kw["headers"]["Authorization"] == f"Bearer {SECRET}" and kw["headers"]["model"] == "s2.1-pro-free"
    assert b"references" in kw["data"] and b"RIFF....WAVEfmt quinton" in kw["data"] and b"I'm Quinton." in kw["data"]
    assert speak.latest("summary")[0] == b"ID3audio" and p["voice"] == "channel/host/voice-anchor.wav"
    again = Session(Reply(500))
    assert speak.say("summary", SNAP, session=again)["cached"] is True and again.calls == []              # the same sentence is never paid for twice
    for text in (json.dumps(p), (speak.CACHE / "latest-summary.json").read_text(), events.JOURNAL.read_text() if events.JOURNAL.exists() else ""):
        assert SECRET not in text
    assert ledger.used("fishaudio", "chars") == len(p["text"])
    monkeypatch.setitem(speak.DEFAULTS, "tts_daily_chars", 10)
    with pytest.raises(RuntimeError, match="allowance"):
        speak.say("next", SNAP, session=Session(Reply(200, b"x")))
    with pytest.raises(RuntimeError, match="answered 401"):
        monkeypatch.setitem(speak.DEFAULTS, "tts_daily_chars", 4000)
        speak.say("next", SNAP, session=Session(Reply(401, text=f"bad key {SECRET}")))


def test_a_spoken_command_only_proposes_what_a_button_can_do():
    assert speak.propose("please re-check the keys", SNAP)["name"] == "keys_probe"
    assert speak.propose("take the missions back", SNAP)["name"] == "crew_reap"
    assert speak.propose("how are we doing", SNAP) == {"name": "voice_say", "args": {"what": "summary"}, "label": "Read out the summary", "confirm": True}
    assert speak.propose("post everything to TikTok and send the DMs", SNAP) is None
    assert speak.propose("do the next thing", SNAP)["name"] is None                                     # the next item has no button here
    with_btn = {**SNAP, "next": {**SNAP["next"], "do": {"name": "mission", "args": {"mission": "phone-lane"}, "label": "Send to Claude Code"}}}
    p = speak.propose("do the next thing", with_btn)
    assert p["name"] == "mission" and p["confirm"] is True
    from faceless import actions
    for phrase in ("re-check keys", "take back", "status", "what's next", "send it"):
        got = speak.propose(phrase, with_btn)
        assert got is None or got["name"] is None or got["name"] in actions.ACTIONS


def test_voice_input_is_off_until_the_owner_turns_it_on(monkeypatch):
    with pytest.raises(PermissionError, match="off"):
        speak.transcribe(b"x" * 100, "audio/webm", session=Session(Reply(200)))
    monkeypatch.setitem(speak.DEFAULTS, "listen", True)
    with pytest.raises(PermissionError, match="GEMINI_API_KEY"):
        speak.transcribe(b"x" * 100, "audio/webm", session=Session(Reply(200)))
    monkeypatch.setenv("GEMINI_API_KEY", "g" * 39)
    with pytest.raises(ValueError):
        speak.transcribe(b"x" * 100, "text/html", session=Session(Reply(200)))
    body = {"candidates": [{"content": {"parts": [{"text": "re-check the keys"}]}}], "usageMetadata": {"promptTokenCount": 330, "candidatesTokenCount": 6}}
    s = Session(Reply(200, body=body))
    got = speak.transcribe(b"opus-bytes", "audio/webm;codecs=opus", session=s)
    url, kw = s.calls[0]
    assert "gemini-3.5-flash-lite:generateContent" in url and kw["headers"]["x-goog-api-key"] == "g" * 39 and "key=" not in url
    part = kw["json"]["contents"][0]["parts"][1]["inline_data"]
    assert part["mime_type"] == "audio/webm" and base64.b64decode(part["data"]) == b"opus-bytes"
    assert got["transcript"] == "re-check the keys" and got["usd"] == pytest.approx((330 * 0.30 + 6 * 2.50) / 1e6)
    assert any(e["type"] == "CC_VOICE" and e["heard"] == "re-check the keys" for e in events.read())


def _req(base, path, method="GET", data=None, headers=None):
    req = urllib.request.Request(base + path, method=method, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:   # noqa: S310 - loopback test server
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type"), e.read()


def test_the_server_doors_for_voice_are_locked_like_the_action_door(voice, monkeypatch):
    doc = {"generatedAt": "2026-01-01T00:00:00Z", "day": "2026-01-01", "jobs": None, "missions": None, "alerts": []}
    src = serve.Source(lambda: doc)
    httpd = serve.make_server("127.0.0.1", 0, TOKEN, build=src.build, panel=serve.Panel(src, background=False))
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    base, auth = f"http://127.0.0.1:{httpd.server_address[1]}", {"Authorization": f"Bearer {TOKEN}"}
    try:
        assert _req(base, "/voice/summary.mp3")[0] == 401
        assert _req(base, "/voice/summary.mp3", headers=auth)[0] == 404                                  # nothing said yet
        monkeypatch.setenv("FISH_AUDIO_API_KEY", SECRET)
        speak.say("summary", SNAP, session=Session(Reply(200, b"ID3audio")))
        code, ctype, body = _req(base, "/voice/summary.mp3", headers=auth)
        assert (code, ctype, body) == (200, "audio/mpeg", b"ID3audio")
        assert _req(base, "/voice/../../etc/passwd.mp3", headers=auth)[0] in (401, 404)
        assert _req(base, "/voice-in", "POST", b"abc", {"Content-Type": "audio/webm"})[0] == 401
        assert _req(base, "/voice-in", "POST", b"abc", {**auth, "Content-Type": "text/plain"})[0] == 400
        assert _req(base, "/voice-in", "POST", b"abc", {**auth, "Content-Type": "audio/webm", "Origin": "http://evil.example"})[0] == 403
        code, _, body = _req(base, "/voice-in", "POST", b"abc", {**auth, "Content-Type": "audio/webm"})
        assert code == 403 and "off" in json.loads(body)["error"]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_page_keeps_voice_off_and_the_mic_behind_a_secure_context():
    from faceless import hud
    html = hud.render()
    assert "LS.get('qm_voice_out')==='1'" in html and 'aria-pressed="false">🔈 Voice off' in html
    assert "window.isSecureContext" in html and "15000" in html and "● Recording" in html and "Sending the clip to Gemini" in html
    assert "Nothing runs until you hold the button" in html and "voice_say:1" in html and SECRET not in html
