"""Tests are hermetic: they never touch the network, never spend free-tier budget, and give the same answer on a laptop full of API
keys and on a bare CI runner. Every provider key is removed from the environment, the Cloudflare decision model is unavailable and
semantic QA is off, unless a test turns them on (tests that need a key set it with monkeypatch.setenv)."""

import os

import pytest

from faceless import config
from faceless.providers import clef

KEY_MARKERS = ("API_KEY", "_TOKEN", "API_TOKEN", "SECRET", "ACCOUNT_ID", "COMPOSIO_API", "FIRECRAWL", "ELEVENLABS", "MUAPI", "GEMINI",
               "OPENROUTER", "CLOUDFLARE", "TINYFISH", "LONGCAT", "NAMESILO", "MONID", "XAI_API", "MINSTRAL", "MISTRAL", "POSTHOG",
               "SENTRY", "GPT", "SUPA")


@pytest.fixture(autouse=True)
def _hermetic_environment(monkeypatch):
    for name in list(os.environ):
        if any(m in name.upper() for m in KEY_MARKERS):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(clef, "available", lambda: False)
    monkeypatch.setitem(config.load().setdefault("qa", {}), "enabled", False)
