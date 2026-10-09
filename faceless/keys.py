"""Credential health: which key of each service works, and what is left on it.

The environment holds several keys for some services (spare copies, restricted keys, keys of other projects). Which variable is the live one is
not guessable from its name, so this asks each service one free, read-only question per variable: who am I, or what is my balance. Nothing is
spent, nothing is written, and a key's value is never printed, logged or returned: only the variable's name, the answer's status and a short
non-secret fact (a balance, a plan, a model count).

    python -m faceless keys            # the table
    python -m faceless keys --json
"""

from __future__ import annotations

import json
import os

from faceless.config import redact
from faceless.providers import http


def _count(key: str):
    return lambda j: f"{len(j.get(key, []))} models"


# service -> (variables to try, request builder, fact to show). Every request is a GET on an account or model-list endpoint that costs nothing.
# `scope` says what a 200 proves; an ElevenLabs key can be valid for models and still refuse the account page (a restricted key).
PROBES: list[dict] = [
    {"service": "firecrawl", "vars": ["FIRECRAWL", "FIRECRAWL_API_KEY"], "url": "https://api.firecrawl.dev/v1/team/credit-usage",
     "auth": ("Authorization", "Bearer {k}"), "fact": lambda j: f"credits left {j.get('data', {}).get('remaining_credits')}"},
    {"service": "elevenlabs", "vars": ["ELEVENLABS_API", "ELEVENLABS_API_KEY", "ELEVENLABS_api_KEY2", "ELEVENLABS_2"], "url": "https://api.elevenlabs.io/v1/models",
     "auth": ("xi-api-key", "{k}"), "fact": lambda j: f"{len(j)} models" if isinstance(j, list) else ""},
    {"service": "tinyfish", "vars": ["TINYFISH_API_KEY", "TINYFISH_API_kEY2"], "url": "https://agent.tinyfish.ai/v1/wallet", "auth": ("X-API-Key", "{k}"), "fact": None},
    {"service": "browser-use", "vars": ["BROWSER_USE_API_KEY", "BROWSERUSE"], "url": "https://api.browser-use.com/api/v2/billing/account",
     "auth": ("X-Browser-Use-API-Key", "{k}"), "fact": lambda j: f"credits ${j.get('totalCreditsBalanceUsd')}"},
    {"service": "tripo", "vars": ["TRIPO_API"], "url": "https://api.tripo3d.ai/v2/openapi/user/balance", "auth": ("Authorization", "Bearer {k}"),
     "fact": lambda j: f"balance {j.get('data')}"},
    {"service": "monid", "vars": ["MONID_API_KEY"], "url": "https://api.monid.ai/v1/wallet/balance", "auth": ("Authorization", "Bearer {k}"),
     "fact": lambda j: f"balance ${(j.get('balance') or {}).get('value')}"},
    {"service": "muapi", "vars": ["MUAPI_API_KEY"], "url": "https://api.muapi.ai/api/v1/account/balance", "auth": ("x-api-key", "{k}"),
     "fact": lambda j: f"balance ${j.get('balance')}"},
    {"service": "mistral", "vars": ["MINSTRAL_API_KEY", "MINSTRAL_API_KEY2"], "url": "https://api.mistral.ai/v1/models", "auth": ("Authorization", "Bearer {k}"),
     "fact": _count("data")},
    {"service": "xai", "vars": ["XAI_API"], "url": "https://api.x.ai/v1/models", "auth": ("Authorization", "Bearer {k}"), "fact": None},
    {"service": "vercel", "vars": ["VERCEL"], "url": "https://api.vercel.com/v2/user", "auth": ("Authorization", "Bearer {k}"),
     "fact": lambda j: f"user {(j.get('user') or {}).get('username')}"},
    {"service": "v0", "vars": ["V0DEV_API"], "url": "https://api.v0.dev/v1/user", "auth": ("Authorization", "Bearer {k}"), "fact": None},
    {"service": "openrouter", "vars": ["OPENROUTER_API_KEY", "OPENROUTER_2"], "url": "https://openrouter.ai/api/v1/credits", "auth": ("Authorization", "Bearer {k}"),
     "fact": lambda j: f"credits left ${round((j.get('data') or {}).get('total_credits', 0) - (j.get('data') or {}).get('total_usage', 0), 2)}"},
    {"service": "gemini", "vars": ["GEMINI_API_KEY", "GEMINI"], "url": "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1", "auth": ("x-goog-api-key", "{k}"),
     "fact": None},
    {"service": "cloudflare", "vars": ["CLOUDFLARE_API_KEY", "CLOUDFLARE_API_KEY2", "CLOUDFLARE_API_TOKEN", "CLAUDECLOUDFLARE_API"],
     "url": "https://api.cloudflare.com/client/v4/user/tokens/verify", "auth": ("Authorization", "Bearer {k}"), "fact": lambda j: f"token {(j.get('result') or {}).get('status')}"},
    {"service": "github", "vars": ["GITHUB_TOKEN", "GH_TOKEN", "GITHUB_API_KEY"], "url": "https://api.github.com/user", "auth": ("Authorization", "Bearer {k}"),
     "fact": lambda j: f"login {j.get('login')}"},
    {"service": "posthog", "vars": ["POSTHOG_PERSONAL_API_KEY"], "url": "https://us.posthog.com/api/users/@me/", "auth": ("Authorization", "Bearer {k}"), "fact": None},
    {"service": "sentry", "vars": ["SENTRY_TOKEN", "SENTRY_ORGANISATION_TOKEN"], "url": "https://sentry.io/api/0/organizations/", "auth": ("Authorization", "Bearer {k}"),
     "fact": lambda j: f"{len(j)} org(s)" if isinstance(j, list) else ""},
    {"service": "composio", "vars": ["COMPOSIO_API"], "url": "https://backend.composio.dev/api/v3/connected_accounts?limit=1", "auth": ("x-api-key", "{k}"), "fact": None},
    {"service": "agentmail", "vars": ["AGENT_MAIL_API_KEY"], "url": "https://api.agentmail.to/v0/inboxes?limit=1", "auth": ("Authorization", "Bearer {k}"), "fact": None},
    {"service": "pixellab", "vars": ["PIXELLAB_SECRET"], "url": "https://api.pixellab.ai/v1/balance", "auth": ("Authorization", "Bearer {k}"), "fact": lambda j: f"balance ${j.get('usd')}"},
]


def _one(probe: dict, var: str, key: str, session) -> dict:
    header, template = probe["auth"]
    try:
        r = session.get(probe["url"], headers={header: template.format(k=key)}, timeout=20)
        code = r.status_code
        try:
            body = r.json()
        except ValueError:
            body = {}
    except Exception as e:  # noqa: BLE001 - one unreachable service must not hide the others
        return {"service": probe["service"], "var": var, "status": 0, "state": "unreachable", "detail": type(e).__name__}
    fact = ""
    if code == 200 and probe.get("fact"):
        try:
            fact = str(probe["fact"](body))
        except (AttributeError, TypeError, ValueError):
            fact = ""
    state = "works" if code == 200 else "no credit" if code in (402, 403) and "credit" in json.dumps(body).lower() else "rejected" if code in (400, 401) else "forbidden" if code == 403 else f"http {code}"
    detail = fact if code == 200 else redact(json.dumps(body)[:100] if body else "")
    return {"service": probe["service"], "var": var, "status": code, "state": state, "detail": detail.replace(key, "[key]")}


def check(session=None, only: str | None = None) -> list[dict]:
    """One row per variable that is set, plus a row for each that is not. Free and read-only."""
    session = session or http()
    rows = []
    for probe in PROBES:
        if only and probe["service"] != only:
            continue
        for var in probe["vars"]:
            key = (os.environ.get(var) or "").strip()
            if not key:
                rows.append({"service": probe["service"], "var": var, "status": None, "state": "not set", "detail": ""})
            else:
                rows.append(_one(probe, var, key, session))
    return rows


def best(rows: list[dict]) -> dict[str, str]:
    """service -> the first variable that works: the one code and routines should read."""
    out: dict[str, str] = {}
    for r in rows:
        if r["state"] == "works":
            out.setdefault(r["service"], r["var"])
    return out


def render(rows: list[dict]) -> str:
    out = []
    for r in rows:
        out.append(f"{r['service']:12} {r['var']:28} {r['state']:12} {r['detail']}".rstrip())
    dead = sorted({r["service"] for r in rows} - set(best(rows)) - {r["service"] for r in rows if r["state"] == "not set" and not any(x["service"] == r["service"] and x["state"] != "not set" for x in rows)})
    if dead:
        out.append("\nno working key for: " + ", ".join(dead))
    return "\n".join(out)
