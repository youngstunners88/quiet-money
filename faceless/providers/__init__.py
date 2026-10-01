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
