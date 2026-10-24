"""Provider abstraction layer.

The pipeline only ever talks to four capabilities: llm, tts, image, publish.
Each capability has an ordered fallback chain configured in studio.toml.
`run_chain` tries providers in order and records which one served the request,
so swapping a vendor is a one-line config change, never a code change.
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable, Iterable

import requests

from faceless import events
from faceless.config import ca_bundle


class ProviderError(RuntimeError):
    """A provider could not serve the request; the chain should try the next one."""


class ProviderUnavailable(ProviderError):
    """Provider is not configured (missing key) or out of quota; skip silently."""


MAX_DOWNLOAD = 300 * 2**20   # no image, clip or page we fetch is anywhere near this


def fetch_bytes(url: str, *, session=None, timeout: float = 120, limit: int = MAX_DOWNLOAD, headers: dict | None = None) -> tuple[bytes, str]:
    """GET an address a vendor handed back and return (body, content-type). https only (a result URL pointing at plain http or a local service is
    refused), and the body is read in pieces and cut off at `limit`, so a wrong or hostile address cannot fill the disk or the memory of a routine."""
    from urllib.parse import urlparse
    if urlparse(url).scheme != "https":
        raise ProviderError(f"refusing a non-https result URL: {url[:60]}")
    extra = {"headers": headers} if headers else {}
    r = (session or http()).get(url, timeout=timeout, stream=True, **extra)
    if r.status_code != 200:
        raise ProviderError(f"download failed: HTTP {r.status_code}")
    declared = str(r.headers.get("content-length", ""))
    if declared.isdigit() and int(declared) > limit:
        raise ProviderError(f"download is {int(declared) // 2**20} MB, over the {limit // 2**20} MB limit")
    chunks = getattr(r, "iter_content", None)
    if chunks is None:                      # a response-like object that has already read its body
        body = r.content
    else:
        buf = bytearray()
        for chunk in chunks(1 << 16):
            buf += chunk
            if len(buf) > limit:
                r.close()
                raise ProviderError(f"download is over the {limit // 2**20} MB limit")
        body = bytes(buf)
    if len(body) > limit:
        raise ProviderError(f"download is over the {limit // 2**20} MB limit")
    return body, str(r.headers.get("content-type", ""))


def http() -> requests.Session:
    s = requests.Session()
    bundle = ca_bundle()
    if bundle:
        s.verify = bundle
    s.headers["User-Agent"] = "0.1"
    return s


# Circuit breaker (audit 2026-10-24: ElevenLabs returned 401 on 69 straight attempts, Edge 403 on 74). Stdlib only. A provider that fails
# BREAKER_FAILS times in a row with a systemic error (401/402/403/429/5xx) is skipped for BREAKER_COOLDOWN seconds, then one probe goes
# through. Per-input errors (a 400 flagged prompt, bad JSON, a timeout) never count: they say nothing about the provider's health.
BREAKER_FAILS = 3
BREAKER_COOLDOWN = 1800
_SYSTEMIC = re.compile(r"\b(401|402|403|429|5\d\d)\b")
_breaker: dict[tuple[str, str], dict] = {}


def _breaker_open(key: tuple[str, str]) -> bool:
    st = _breaker.get(key)
    if not st or st["fails"] < BREAKER_FAILS:
        return False
    if time.time() - st["opened"] >= BREAKER_COOLDOWN:      # cooldown over: let one probe through; a failure re-opens it
        st["opened"] = time.time()
        return False
    return True


def _breaker_note(key: tuple[str, str], error: Exception | None) -> None:
    st = _breaker.setdefault(key, {"fails": 0, "opened": 0.0})
    if error is None:
        st["fails"] = 0
    elif _SYSTEMIC.search(str(error)):
        st["fails"] += 1
        if st["fails"] == BREAKER_FAILS:
            st["opened"] = time.time()


def run_chain(capability: str, providers: Iterable[tuple[str, Callable[[], Any]]], job: str | None = None) -> tuple[str, Any]:
    errors = []
    chain = list(providers)
    for i, (name, call) in enumerate(chain):
        key = (capability, name)
        if i < len(chain) - 1 and _breaker_open(key):         # the last provider in a chain is always tried
            errors.append(f"{name}: skipped (circuit open)")
            events.emit("PROVIDER_SKIPPED", capability=capability, provider=name, job=job)
            continue
        t0 = time.time()
        try:
            result = call()
            _breaker_note(key, None)
            events.emit("PROVIDER_OK", capability=capability, provider=name, job=job,
                        ms=int((time.time() - t0) * 1000))
            return name, result
        except ProviderUnavailable as e:
            errors.append(f"{name}: unavailable ({e})")
        except Exception as e:  # noqa: BLE001 - any provider failure falls through to the next
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:200]}")
            _breaker_note(key, e)
            events.emit("PROVIDER_FAIL", capability=capability, provider=name, job=job,
                        error=str(e)[:300])
    raise ProviderError(f"all {capability} providers failed: " + " | ".join(errors))
