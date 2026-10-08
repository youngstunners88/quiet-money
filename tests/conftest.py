"""Tests never touch the network or spend free-tier budget: the Cloudflare decision model is unavailable and semantic QA is off
unless a test turns them on."""

import pytest

from faceless import config
from faceless.providers import clef


@pytest.fixture(autouse=True)
def _no_paid_or_networked_decisions(monkeypatch):
    monkeypatch.setattr(clef, "available", lambda: False)
    monkeypatch.setitem(config.load().setdefault("qa", {}), "enabled", False)
