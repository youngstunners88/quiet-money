"""Provider abstraction layer.

The pipeline only ever talks to four capabilities: llm, tts, image, publish.
Each capability has an ordered fallback chain configured in studio.toml.
`run_chain` tries providers in order and records which one served the request,
so swapping a vendor is a one-line config change, never a code change.
"""

from __future__ import annotations

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


def run_chain(capability: str, providers: Iterable[tuple[str, Callable[[], Any]]], job: str | None = None) -> tuple[str, Any]:
    errors = []
    for name, call in providers:
        t0 = time.time()
        try:
            result = call()
            events.emit("PROVIDER_OK", capability=capability, provider=name, job=job,
                        ms=int((time.time() - t0) * 1000))
            return name, result
        except ProviderUnavailable as e:
            errors.append(f"{name}: unavailable ({e})")
        except Exception as e:  # noqa: BLE001 - any provider failure falls through to the next
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:200]}")
            events.emit("PROVIDER_FAIL", capability=capability, provider=name, job=job,
                        error=str(e)[:300])
    raise ProviderError(f"all {capability} providers failed: " + " | ".join(errors))
