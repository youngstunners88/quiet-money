"""The Muapi desk and the safety layer: every limit refuses before a cent moves, and every result is saved or returned."""

import json

import pytest

from faceless import config, events, ledger, muapi, safety
from faceless.config import Paths
from faceless.providers import ProviderError, ProviderUnavailable

CATALOG = {"models": [
    {"name": "m-img", "category": "Text to Image", "family": "flux", "cost": 0.01, "dynamic_pricing": False, "required_fields": ["prompt"],
     "input_fields": ["prompt", "aspect_ratio"], "endpoint": "m-img", "description": "A cheap image model", "is_enabled": True},
    {"name": "m-txt", "category": "Text to Text", "family": "text-generation", "cost": 0.0002, "dynamic_pricing": True, "required_fields": ["prompt"],
     "input_fields": ["prompt"], "endpoint": "m-txt", "description": "A tiny language model", "is_enabled": True},
    {"name": "m-vid", "category": "Image to Video", "family": "seedance", "cost": 0.9, "dynamic_pricing": True, "required_fields": ["prompt", "image_url"],
     "input_fields": ["prompt", "image_url"], "endpoint": "m-vid", "description": "An expensive video model", "is_enabled": True},
    {"name": "m-slug", "category": "Image to Image", "family": "upscale", "cost": 0.02, "dynamic_pricing": False, "required_fields": ["image_url"],
     "input_fields": ["image_url"], "endpoint": "/api/v1/m-slug", "endpoint_url": "m-slug-real", "description": "Name and submit slug differ", "is_enabled": True},
    {"name": "m-off", "category": "Text to Image", "cost": 0.01, "required_fields": [], "input_fields": [], "endpoint": "m-off", "is_enabled": False},
]}


class _Resp:
    def __init__(self, code=200, body=None, content=b"", headers=None, text=None):
        self.status_code, self._body, self.content, self.headers = code, body, content, headers or {"content-type": "application/json"}
        self.text = text if text is not None else json.dumps(body or {})

    def json(self):
        return self._body


class _Muapi:
    """A stand-in for api.muapi.ai: catalog, estimate, submit, poll, download."""

    def __init__(self, outputs=("https://cdn.example/out.png",), status="completed", cost=0.01, nsfw=False, submit_code=200, submit_text="", refunded=False):
        self.outputs, self.status, self.cost, self.nsfw, self.submit_code, self.submit_text, self.refunded = list(outputs), status, cost, nsfw, submit_code, submit_text, refunded
        self.calls, self.polls = [], 0

    def get(self, url, **kw):
        self.calls.append(("GET", url))
        if url.endswith("/models"):
            return _Resp(200, CATALOG)
        if "/models/" in url:
            return _Resp(200, {"name": "m-img", "required_fields": ["prompt"], "input_schema": {"schemas": {"input_data": {
                "x-order-properties": ["prompt", "aspect_ratio"], "required": ["prompt"],
                "properties": {"prompt": {"type": "string", "description": "what to draw"}, "aspect_ratio": {"enum": ["1:1", "9:16"], "default": "1:1"}}}}}})
        if "/predictions/" in url:
            self.polls += 1
            if self.polls < 2:
                return _Resp(200, {"status": "processing"})
            body = {"status": self.status, "outputs": self.outputs, "has_nsfw_contents": [self.nsfw], "executionTime": 2500,
                    "error": "bad prompt" if self.status == "failed" else "", "cost": {"amount_usd": self.cost, "refunded": self.refunded}}
            return _Resp(200, body)
        if url.startswith("https://"):
            return _Resp(200, content=b"\x89PNGdata", headers={"content-type": "image/png"})
        raise AssertionError(url)

    def post(self, url, **kw):
        self.calls.append(("POST", url))
        if url.endswith("/estimate-cost"):
            return _Resp(200, {"cost": self.cost})
        if url.endswith("/upload_file"):
            return _Resp(200, {"url": "https://s3/up.jpg"})
        if self.submit_code != 200:
            return _Resp(self.submit_code, {}, text=self.submit_text)
        return _Resp(200, {"request_id": "req-12345678", "status": "processing", "cost": {"amount_usd": self.cost}}, headers={"content-type": "application/json", "X-Account-Balance": "19.5"})


@pytest.fixture
def desk(tmp_path, monkeypatch):
    sess = _Muapi()
    monkeypatch.setenv("MUAPI_API_KEY", "test-key-not-real")
    monkeypatch.setattr(Paths, "cache", tmp_path / "cache")
    monkeypatch.setattr(Paths, "state", tmp_path / "state")
    monkeypatch.setattr(muapi, "SNAPSHOT", tmp_path / "snapshot.json")
    monkeypatch.setattr(muapi, "http", lambda: sess)
    monkeypatch.setattr(muapi.time, "sleep", lambda s: None)
    monkeypatch.setitem(config.load(), "muapi", {"daily_usd": 1.0, "per_call_usd": 0.5})
    monkeypatch.setitem(config.load(), "safety", {"daily_usd_ceiling": 3.0})
    return sess


def test_catalog_hides_disabled_models_and_find_matches_every_word_cheapest_first(desk):
    names = [m["name"] for m in muapi.catalog(refresh=True)]
    assert names == ["m-img", "m-txt", "m-vid", "m-slug"]
    assert [m["name"] for m in muapi.find("image")] == ["m-img", "m-slug", "m-vid"]          # "image" is in other models' categories too; cheapest first
    assert [m["name"] for m in muapi.find("tiny language")] == ["m-txt"]
    assert muapi.find("", category="Image to Video")[0]["name"] == "m-vid"
    assert muapi.find("", max_usd=0.05)[0]["name"] == "m-txt" and all(m["cost"] <= 0.05 for m in muapi.find("", max_usd=0.05))


def test_catalog_falls_back_to_the_committed_snapshot_when_the_network_is_down(desk, monkeypatch):
    muapi.SNAPSHOT.write_text(json.dumps([muapi._compact(CATALOG["models"][0])]), encoding="utf-8")
    monkeypatch.setattr(muapi, "http", lambda: (_ for _ in ()).throw(OSError("offline")))
    assert [m["name"] for m in muapi.catalog(refresh=True)] == ["m-img"]


def test_params_reads_the_live_schema(desk):
    ps = muapi.params("m-img")
    assert [(p["name"], p["required"]) for p in ps] == [("prompt", True), ("aspect_ratio", False)]
    assert ps[1]["enum"] == ["1:1", "9:16"] and ps[1]["default"] == "1:1"


def test_run_downloads_the_result_records_spend_and_returns_the_balance(desk, tmp_path):
    out = muapi.run("m-img", {"prompt": "a mug"}, tmp_path / "out", job="j1")
    assert out["usd"] == 0.01 and out["balance"] == 19.5 and out["request_id"] == "req-12345678"
    assert len(out["files"]) == 1 and out["files"][0].endswith(".png") and (tmp_path / "out" / "m-img-req-1234-0.png").read_bytes().startswith(b"\x89PNG")
    assert ledger.used("muapi", muapi.UNIT) == 0.01 and ledger.usd_total() >= 0.01
    assert any(e["type"] == "MUAPI_RUN" and e["model"] == "m-img" for e in events.read())


def test_text_models_return_their_answer_inline_and_download_nothing(desk, tmp_path):
    desk.outputs, desk.cost = ["ok"], 0.0002
    out = muapi.run("m-txt", {"prompt": "say ok"}, tmp_path)
    assert out["text"] == ["ok"] and not any(m == "GET" and u.startswith("https://cdn") for m, u in desk.calls)          # nothing to download
    assert len(out["files"]) == 1 and out["files"][0].endswith(".json") and json.loads(open(out["files"][0]).read())["text"] == ["ok"]   # but the answer is saved


def test_nothing_is_spent_when_a_limit_says_no(desk, tmp_path, monkeypatch):
    with pytest.raises(ProviderError):
        muapi.run("m-img", {}, tmp_path)                                               # missing required field
    with pytest.raises(ProviderError):
        muapi.run("nope", {"prompt": "x"}, tmp_path)                                   # unknown model
    desk.cost = 0.9
    with pytest.raises(ProviderUnavailable, match="per-call limit"):
        muapi.run("m-vid", {"prompt": "x", "image_url": "https://a/b.jpg"}, tmp_path)  # $0.90 > $0.50
    assert ("POST", "https://api.muapi.ai/api/v1/m-vid") not in desk.calls and ledger.used("muapi", muapi.UNIT) == 0
    monkeypatch.setitem(config.load(), "muapi", {"daily_usd": 0.015, "per_call_usd": 0.5})
    desk.cost = 0.01
    muapi.run("m-img", {"prompt": "one"}, tmp_path)
    with pytest.raises(ProviderUnavailable, match="desk budget"):
        muapi.run("m-img", {"prompt": "two"}, tmp_path)                                # second call would pass the $0.015 day budget


def test_the_kill_switch_and_the_studio_ceiling_stop_a_run(desk, tmp_path, monkeypatch):
    safety.pause("owner stopped the studio")
    with pytest.raises(ProviderUnavailable, match="paused"):
        muapi.run("m-img", {"prompt": "x"}, tmp_path)
    assert safety.resume() and safety.paused() is None
    monkeypatch.setitem(config.load(), "safety", {"daily_usd_ceiling": 0.005})
    with pytest.raises(ProviderUnavailable, match="ceiling"):
        muapi.run("m-img", {"prompt": "x"}, tmp_path)
    assert ledger.used("muapi", muapi.UNIT) == 0


def test_out_of_credit_marks_the_provider_blocked_for_the_day(desk, tmp_path):
    desk.submit_code, desk.submit_text = 402, '{"detail": "Insufficient credits"}'
    with pytest.raises(ProviderUnavailable, match="credit"):
        muapi.run("m-img", {"prompt": "x"}, tmp_path)
    assert ledger.used("muapi", "blocked") == 1
    desk.submit_code = 200
    with pytest.raises(ProviderUnavailable, match="earlier today"):
        muapi.run("m-img", {"prompt": "x"}, tmp_path)


def test_a_failed_job_that_muapi_refunds_is_credited_back(desk, tmp_path):
    desk.status, desk.outputs, desk.refunded = "failed", [], True
    with pytest.raises(ProviderError, match="bad prompt"):
        muapi.run("m-img", {"prompt": "x"}, tmp_path)
    assert ledger.used("muapi", muapi.UNIT) == 0                                      # +0.01 on submit, -0.01 on the refund


def test_unsafe_outputs_are_not_saved_unless_allowed(desk, tmp_path):
    desk.nsfw = True
    with pytest.raises(ProviderError, match="unsafe"):
        muapi.run("m-img", {"prompt": "x"}, tmp_path / "a")
    assert not (tmp_path / "a").exists()
    desk.polls = 0
    assert muapi.run("m-img", {"prompt": "x"}, tmp_path / "b", allow_flagged=True)["files"]


def test_only_https_results_are_downloaded(desk, tmp_path):
    desk.outputs = ["http://cdn.example/out.png"]
    with pytest.raises(ProviderError, match="non-https"):
        muapi.run("m-img", {"prompt": "x"}, tmp_path)


def test_wait_false_returns_after_the_submit_and_result_finishes_it_later(desk, tmp_path):
    out = muapi.run("m-img", {"prompt": "x"}, tmp_path, wait=False)
    assert out["files"] == [] and desk.polls == 0
    done = muapi.result(out["request_id"], tmp_path)
    assert done["files"] and desk.polls >= 1


def test_no_key_means_unavailable_not_a_crash(desk, tmp_path, monkeypatch):
    monkeypatch.delenv("MUAPI_API_KEY")
    with pytest.raises(ProviderUnavailable):
        muapi.run("m-img", {"prompt": "x"}, tmp_path)
    assert muapi.balance() is None and not muapi.available()


def test_upload_checks_size_and_type_before_sending(desk, tmp_path):
    big = tmp_path / "big.jpg"
    big.write_bytes(b"0" * (11 * 2**20))
    with pytest.raises(ProviderError, match="over the 10 MB"):
        muapi.upload(big)
    small = tmp_path / "ok.jpg"
    small.write_bytes(b"jpg")
    assert muapi.upload(small) == "https://s3/up.jpg"
    with pytest.raises(ProviderError, match="not a file"):
        muapi.upload(tmp_path / "missing.png")


def test_digest_lists_cheapest_models_per_category(desk):
    text = muapi.digest(muapi.catalog(refresh=True), per_category=1)
    assert "## Text to Image (1 models" in text and "`m-img`" in text and "~$0.9" in text


def test_pause_file_round_trip_and_headroom(desk, monkeypatch):
    assert safety.paused() is None and safety.headroom() == 3.0
    ledger.spend("x", "calls", 1, usd=1.25)
    assert safety.headroom() == 1.75
    safety.guard("a free thing")                                                        # free work is never blocked by the ceiling
    with pytest.raises(ProviderUnavailable):
        safety.guard("a paid thing", 2.0)
    safety.pause("line one\nline two")
    assert safety.paused() == "line one"
    monkeypatch.setitem(config.load(), "safety", {"paused": True})
    safety.resume()
    assert safety.paused() == "[safety] paused = true"


def test_the_submit_path_is_the_endpoint_slug_not_the_model_name_or_the_old_full_path(desk, tmp_path):
    rows = {m["name"]: m for m in muapi.catalog(refresh=True)}
    assert rows["m-slug"]["endpoint"] == "m-slug-real" and rows["m-img"]["endpoint"] == "m-img"      # "/api/v1/m-img" is reduced to its slug
    muapi.run("m-slug", {"image_url": "https://a/b.jpg"}, tmp_path)
    assert ("POST", "https://api.muapi.ai/api/v1/m-slug-real") in desk.calls
    assert not any("/api/v1//api/v1" in u for _, u in desk.calls)


def test_an_older_snapshot_with_full_paths_still_works(desk, tmp_path, monkeypatch):
    old = [{"name": "m-img", "category": "Text to Image", "family": "flux", "cost": 0.01, "dynamic": False, "required": ["prompt"], "fields": ["prompt"],
            "endpoint": "/api/v1/m-img", "desc": "old copy"}]
    muapi.SNAPSHOT.write_text(json.dumps(old), encoding="utf-8")
    monkeypatch.setattr(muapi, "http", lambda: (_ for _ in ()).throw(OSError("offline")))
    assert muapi.catalog(refresh=True)[0]["endpoint"] == "m-img"
