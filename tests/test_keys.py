"""The key check asks each service one free, read-only question and must never print, log or return a key's value."""

import json

from faceless import keys

SECRET = "sk-test-0123456789-abcdef-NOT-REAL"


class Resp:
    def __init__(self, code, body=None):
        self.status_code, self._b = code, body

    def json(self):
        if self._b is None:
            raise ValueError
        return self._b


class Session:
    def __init__(self, by_url):
        self.by_url, self.calls = by_url, []

    def get(self, url, headers=None, timeout=None):
        assert timeout, "every call needs a timeout"
        self.calls.append((url, dict(headers or {})))
        r = self.by_url.get(url.split("?")[0])
        if isinstance(r, Exception):
            raise r
        return r or Resp(404, {})


def test_a_working_key_reports_its_balance_and_the_value_never_appears(monkeypatch):
    monkeypatch.setenv("MUAPI_API_KEY", SECRET)
    rows = keys.check(Session({"https://api.muapi.ai/api/v1/account/balance": Resp(200, {"balance": 20.19, "echo": SECRET})}), only="muapi")
    assert rows == [{"service": "muapi", "var": "MUAPI_API_KEY", "status": 200, "state": "works", "detail": "balance $20.19"}]
    assert SECRET not in json.dumps(rows) and SECRET not in keys.render(rows)


def test_a_rejected_key_is_named_and_an_error_body_that_echoes_the_key_is_scrubbed(monkeypatch):
    monkeypatch.setenv("TINYFISH_API_KEY", SECRET)
    monkeypatch.setenv("TINYFISH_API_kEY2", "good-key-value-1234567890")
    s = Session({"https://agent.tinyfish.ai/v1/wallet": Resp(401, {"error": f"invalid {SECRET}"})})
    rows = keys.check(s, only="tinyfish")
    assert rows[0]["state"] == "rejected" and SECRET not in json.dumps(rows) and "[redacted]" in rows[0]["detail"] or "[key]" in rows[0]["detail"]
    assert [r["var"] for r in rows] == ["TINYFISH_API_KEY", "TINYFISH_API_kEY2"]


def test_unset_variables_and_unreachable_services_do_not_stop_the_rest(monkeypatch):
    for v in ("OPENROUTER_API_KEY", "OPENROUTER_2"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("MONID_API_KEY", SECRET)
    monkeypatch.setenv("MUAPI_API_KEY", SECRET)
    s = Session({"https://api.monid.ai/v1/wallet/balance": TimeoutError("slow"), "https://api.muapi.ai/api/v1/account/balance": Resp(200, {"balance": 1})})
    rows = {(r["service"], r["var"]): r for r in keys.check(s)}
    assert rows[("openrouter", "OPENROUTER_API_KEY")]["state"] == "not set"
    assert rows[("monid", "MONID_API_KEY")]["state"] == "unreachable" and rows[("muapi", "MUAPI_API_KEY")]["state"] == "works"


def test_no_credit_is_told_apart_from_a_bad_key(monkeypatch):
    monkeypatch.setenv("XAI_API", SECRET)
    rows = keys.check(Session({"https://api.x.ai/v1/models": Resp(403, {"error": "Your team doesn't have any credits"})}), only="xai")
    assert rows[0]["state"] == "no credit"


def test_best_picks_the_first_variable_that_works(monkeypatch):
    rows = [{"service": "firecrawl", "var": "A", "state": "rejected"}, {"service": "firecrawl", "var": "B", "state": "works"}, {"service": "firecrawl", "var": "C", "state": "works"}]
    assert keys.best(rows) == {"firecrawl": "B"}


def test_every_probe_is_a_get_on_an_account_or_list_endpoint_with_a_header_and_no_secret_in_the_url():
    for p in keys.PROBES:
        assert p["url"].startswith("https://") and "key=" not in p["url"] and "token=" not in p["url"], p["service"]
        assert "{k}" in p["auth"][1] and p["vars"], p["service"]
