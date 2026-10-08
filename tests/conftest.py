"""Tests are hermetic: any attempt to reach the network is an error (a test must inject a fake session), they never spend free-tier budget, and give the same answer on a laptop full of API
keys and on a bare CI runner. Every provider key is removed from the environment, the Cloudflare decision model is unavailable and
semantic QA is off, and the journal and ledger are redirected to a temp folder, unless a test turns them on (tests that need a key set it with monkeypatch.setenv)."""

import os

import pytest
import requests.adapters

from faceless import config, events, ledger
from faceless.providers import clef

KEY_MARKERS = ("API_KEY", "_TOKEN", "API_TOKEN", "SECRET", "ACCOUNT_ID", "COMPOSIO_API", "FIRECRAWL", "ELEVENLABS", "MUAPI", "GEMINI",
               "OPENROUTER", "CLOUDFLARE", "TINYFISH", "LONGCAT", "NAMESILO", "MONID", "XAI_API", "MINSTRAL", "MISTRAL", "POSTHOG",
               "SENTRY", "GPT", "SUPA")


def _no_network(self, request, **kw):
    raise RuntimeError(f"a test tried to reach the network: {request.method} {request.url[:80]}")


@pytest.fixture(autouse=True)
def _hermetic_environment(monkeypatch, tmp_path_factory):
    for name in list(os.environ):
        if any(m in name.upper() for m in KEY_MARKERS):
            monkeypatch.delenv(name, raising=False)
    scratch = tmp_path_factory.mktemp("state")
    monkeypatch.setattr(events, "JOURNAL", scratch / "journal.jsonl")      # a test never writes the real audit trail or ledger
    monkeypatch.setattr(ledger, "LEDGER", scratch / "ledger.jsonl")
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", _no_network)
    monkeypatch.setattr(clef, "available", lambda: False)
    monkeypatch.setitem(config.load().setdefault("qa", {}), "enabled", False)
