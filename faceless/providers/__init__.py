"""Provider abstraction layer.

The pipeline only ever talks to four capabilities: llm, tts, image, publish.
Each capability has an ordered fallback chain configured in studio.toml.
`run_chain` tries providers in order and records which one served the request,
so swapping a vendor is a one-line config change, never a code change.
"""

from __future__ import annotations

import re
import threading
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


# ---------------------------------------------------------------- circuit breaker
# A provider that is down for a reason that will not fix itself in a minute (a revoked key: 401/403, no credit: 402, a spent
# quota: 429, a vendor outage: 5xx) was retried on every video: ElevenLabs answered 401 sixty-three times in a row, Edge TTS 403
# seventy-four times. The breaker skips such a provider after FAIL_MAX systemic failures in a row, for COOLDOWN seconds, then lets
# ONE probe through (half-open). One success closes it. Per-input errors (a prompt the image model flagged, a malformed answer,
# a timeout) never count, because they say nothing about the provider's health. State is per process; a new daily run starts closed.

FAIL_MAX = 3
COOLDOWN = 1800.0
SYSTEMIC = re.compile(r"\b(401|402|403|429|500|502|503|504)\b")

_lock = threading.Lock()
_state: dict[tuple[str, str], dict] = {}


def _systemic(err: BaseException) -> bool:
    return bool(SYSTEMIC.search(str(err)))


def _allowed(key: tuple[str, str], now: float) -> bool:
    """True when the provider may be called. An open breaker admits one probe once the cooldown has passed."""
    with _lock:
        st = _state.get(key)
        if not st or st["fails"] < FAIL_MAX:
            return True
        if now - st["opened"] >= COOLDOWN and not st["probing"]:
            st["probing"] = True
            return True
        return False


def _record(key: tuple[str, str], ok: bool, err: BaseException | None, now: float) -> None:
    with _lock:
        st = _state.setdefault(key, {"fails": 0, "opened": 0.0, "probing": False})
        if ok:
            st.update(fails=0, opened=0.0, probing=False)
            return
        if err is not None and not _systemic(err):
            st["probing"] = False                  # a per-input failure says nothing about health; free the probe slot
            return
        st["fails"] += 1
        st["probing"] = False
        if st["fails"] >= FAIL_MAX:
            st["opened"] = now                     # (re)open: a failed probe restarts the cooldown


def reset_breakers() -> None:
    """Close every breaker (tests, and a human who has just fixed a key)."""
    with _lock:
        _state.clear()


def run_chain(capability: str, providers: Iterable[tuple[str, Callable[[], Any]]], job: str | None = None) -> tuple[str, Any]:
    errors = []
    providers = list(providers)
    for idx, (name, call) in enumerate(providers):
        t0 = time.time()
        key = (capability, name)
        last = idx == len(providers) - 1
        # an open breaker skips the provider, unless it is the last one left: a chain must try everything before it gives up
        if not _allowed(key, t0) and not last:
            errors.append(f"{name}: circuit open")
            events.emit("PROVIDER_SKIPPED", capability=capability, provider=name, job=job, reason="circuit open")
            continue
        try:
            result = call()
            _record(key, True, None, t0)
            events.emit("PROVIDER_OK", capability=capability, provider=name, job=job,
                        ms=int((time.time() - t0) * 1000))
            return name, result
        except ProviderUnavailable as e:
            errors.append(f"{name}: unavailable ({e})")
        except Exception as e:  # noqa: BLE001 - any provider failure falls through to the next
            _record(key, False, e, time.time())
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:200]}")
            events.emit("PROVIDER_FAIL", capability=capability, provider=name, job=job,
                        error=str(e)[:300])
    raise ProviderError(f"all {capability} providers failed: " + " | ".join(errors))
