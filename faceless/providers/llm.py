"""Text generation providers. All return parsed JSON for structured prompts."""

from __future__ import annotations

import json
import re

import requests

from faceless import config, ledger
from faceless.providers import ProviderError, ProviderUnavailable, http, run_chain

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _extract_json(text: str):
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        a, b = text.find(open_c), text.rfind(close_c)
        if a != -1 and b > a:
            try:
                return json.loads(text[a:b + 1])
            except json.JSONDecodeError:
                continue
    raise ProviderError(f"no JSON in response: {text[:160]!r}")


def gemini(prompt: str, *, system: str | None, want_json: bool, temperature: float) -> str:
    key = config.env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if not key:
        raise ProviderUnavailable("GEMINI_API_KEY not set")
    cfg = config.load()["llm"]
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if want_json:
        body["generationConfig"]["responseMimeType"] = "application/json"
    errs = []
    s = http()
    for model in cfg["gemini_models"]:
        try:
            # key in a header, never the URL: urllib3 errors quote the URL, and errors land in the committed journal
            r = s.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": key}, json=body, timeout=75)
        except requests.RequestException as e:   # a hung model shouldn't cost the whole chain 3 minutes
            errs.append(f"{model}:{type(e).__name__}")
            continue
        if r.status_code != 200:
            errs.append(f"{model}:{r.status_code}")
            continue
        d = r.json()
        try:
            parts = d["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        except (KeyError, IndexError):
            errs.append(f"{model}:empty")
            continue
        usage = d.get("usageMetadata", {})
        ledger.spend("gemini", "tokens", usage.get("totalTokenCount", 0))
        return text
    raise ProviderError("gemini: " + ",".join(errs))


def openrouter(prompt: str, *, system: str | None, want_json: bool, temperature: float) -> str:
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    cfg = config.load()["llm"]
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    errs = []
    s = http()
    for model in cfg["openrouter_models"]:
        body = {"model": model, "messages": msgs, "temperature": temperature}
        if want_json:
            body["response_format"] = {"type": "json_object"}
        try:
            r = s.post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=180,
                       headers={"Authorization": f"Bearer {key}"})
        except requests.RequestException as e:   # one hung model shouldn't skip the rest of the list
            errs.append(f"{model}:{type(e).__name__}")
            continue
        if r.status_code != 200:
            errs.append(f"{model}:{r.status_code}")
            continue
        d = r.json()
        try:
            return d["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            errs.append(f"{model}:empty")
    raise ProviderError("openrouter: " + ",".join(errs))


def pollinations(prompt: str, *, system: str | None, want_json: bool, temperature: float) -> str:
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    r = http().post("https://text.pollinations.ai/openai", json={"model": "openai", "messages": msgs,
                                                                 "temperature": temperature}, timeout=180)
    if r.status_code != 200:
        raise ProviderError(f"pollinations {r.status_code}")
    return r.json()["choices"][0]["message"]["content"]


PROVIDERS = {"gemini": gemini, "openrouter": openrouter, "pollinations": pollinations}


def complete(prompt: str, *, system: str | None = None, want_json: bool = False,
             temperature: float | None = None, job: str | None = None):
    cfg = config.load()["llm"]
    temp = cfg.get("temperature", 0.8) if temperature is None else temperature

    def make(fn):
        def call():
            text = fn(prompt, system=system, want_json=want_json, temperature=temp)
            return _extract_json(text) if want_json else text.strip()
        return call

    _, out = run_chain("llm", [(n, make(PROVIDERS[n])) for n in cfg["chain"] if n in PROVIDERS], job=job)
    return out
