"""Muapi desk: one audited way to use any of Muapi's 750+ models (image, edit, video, audio, TTS, LLM, OCR, SEO data, social publishing).

Muapi is a single x-api-key over one submit-then-poll API. Per-beat image generation (providers/images.py) and the hook clip
(hookclip.py) are specialised callers of it; this module is the general one, so any new job (a product mockup, a listing video, a
voice sample, an OCR check, a keyword volume) is one `run()` call with the same protections:

  * the key comes from the environment only (MUAPI_API_KEY); it is never written to a file or printed
  * the catalog is public: models are found, priced and schema-checked before a cent is spent
  * every run is estimated first and refused above the per-call limit, the desk's daily budget, the kill switch, or the studio's
    daily ceiling (see safety.py); spend is recorded in the ledger under provider "muapi", unit "desk_usd"
  * results are downloaded immediately (Muapi keeps them 30 days) and text results are returned inline
  * a failed job that Muapi refunds is credited back in the ledger

Unavailable (no key, no credit, paused, over a limit) raises ProviderUnavailable; a real failure raises ProviderError.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from faceless import config, events, ledger, safety
from faceless.config import Paths
from faceless.providers import ProviderError, ProviderUnavailable, http

BASE = "https://api.muapi.ai/api/v1"
UNIT = "desk_usd"
CACHE_TTL = 24 * 3600
SNAPSHOT = Paths.root / "assets" / "muapi" / "catalog.json"        # compact copy of the public catalog: offline and CI fallback
MAX_UPLOAD = {"image": 10 * 2**20, "video": 50 * 2**20, "other": 10 * 2**20}


def cfg() -> dict:
    return {"daily_usd": 2.0, "per_call_usd": 0.5, "poll_seconds": 3.0, "timeout": 600, **config.load().get("muapi", {})}


def key() -> str | None:
    return config.env("MUAPI_API_KEY")


def available() -> bool:
    return bool(key())


# ---------------------------------------------------------------- catalog (public, no key)

def _cache_path() -> Path:
    return Paths.cache / "muapi-catalog.v2.json"


def slug(m: dict) -> str:
    """The path segment a model is submitted to. The catalog has two fields: `endpoint_url` is the real slug (it can differ from the model's
    name: `ai-image-upscaler` is posted to `ai-image-upscale`), `endpoint` is the older full path ("/api/v1/<name>") kept for compatibility."""
    u = (m.get("endpoint_url") or m.get("endpoint") or m["name"]).strip("/")
    return u[len("api/v1/"):] if u.startswith("api/v1/") else u


def _compact(m: dict) -> dict:
    return {"name": m["name"], "category": m.get("category"), "family": m.get("family"), "cost": m.get("cost"),
            "dynamic": bool(m.get("dynamic_pricing")), "required": list(m.get("required_fields") or []),
            "fields": list(m.get("input_fields") or []), "endpoint": slug(m),
            "desc": (m.get("description") or "")[:160]}


def _load_rows(path: Path) -> list[dict]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not (isinstance(rows, list) and rows and isinstance(rows[0], dict) and "name" in rows[0]):
            return []
        return [{**m, "endpoint": slug(m)} for m in rows]
    except (OSError, ValueError):
        return []


def catalog(refresh: bool = False) -> list[dict]:
    """Enabled models as compact rows. Order of trust: a cache under 24 h old, the live catalog, a stale cache, the committed snapshot."""
    p = _cache_path()
    if not refresh and p.exists() and time.time() - p.stat().st_mtime < CACHE_TTL:
        rows = _load_rows(p)
        if rows:
            return rows
    try:
        r = http().get(f"{BASE}/models", timeout=60)
        if r.status_code == 200:
            rows = [_compact(m) for m in r.json().get("models", []) if m.get("is_enabled", True) and not m.get("is_coming_soon")]
            if rows:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(rows), encoding="utf-8")
                return rows
    except Exception:  # noqa: BLE001 - the catalog is advice; fall through to older copies
        pass
    return _load_rows(p) or _load_rows(SNAPSHOT)


def get(name: str) -> dict | None:
    return next((m for m in catalog() if m["name"] == name), None)


def find(query: str = "", *, category: str | None = None, family: str | None = None, max_usd: float | None = None, limit: int = 15) -> list[dict]:
    """Models whose name, description, category or family contain every word of `query`, best match then cheapest first."""
    words = [w for w in re.split(r"[\s,]+", query.lower()) if w]
    out = []
    for m in catalog():
        if category and (m["category"] or "").lower() != category.lower():
            continue
        if family and (m["family"] or "").lower() != family.lower():
            continue
        if max_usd is not None and (m["cost"] is None or m["cost"] > max_usd):
            continue
        hay = " ".join([m["name"], m["desc"], m["category"] or "", m["family"] or ""]).lower()
        if not all(w in hay for w in words):
            continue
        score = sum(3 if w in m["name"].lower() else 1 for w in words)
        out.append((-score, m["cost"] if m["cost"] is not None else 9e9, m["name"], m))
    out.sort(key=lambda t: t[:3])
    return [t[3] for t in out[:limit]]


def detail(name: str) -> dict:
    """Full model record from the API, including `input_schema` (types, enums, defaults). Public."""
    r = http().get(f"{BASE}/models/{name}", timeout=30)
    if r.status_code != 200:
        raise ProviderError(f"muapi model {name}: HTTP {r.status_code}")
    return r.json()


def params(name: str) -> list[dict]:
    """The request fields of a model as [{name, type, required, default, enum, description}], read live from its schema."""
    d = detail(name)
    sch = (d.get("input_schema") or {}).get("schemas", {}).get("input_data", {})
    req = set(sch.get("required") or d.get("required_fields") or [])
    rows = []
    for k in sch.get("x-order-properties") or list(sch.get("properties", {})):
        p = sch.get("properties", {}).get(k, {})
        rows.append({"name": k, "type": p.get("type") or ("enum" if p.get("enum") else ""), "required": k in req,
                     "default": p.get("default"), "enum": p.get("enum"), "description": (p.get("description") or "")[:140]})
    return rows


def estimate(name: str, payload: dict | None = None) -> float | None:
    """Exact USD price of this request from Muapi's public estimate endpoint (no inference runs); the catalog price if that fails."""
    try:
        r = http().post(f"{BASE}/models/{name}/estimate-cost", json=payload or {}, timeout=20)
        if r.status_code == 200:
            return float(r.json()["cost"])
    except Exception:  # noqa: BLE001 - an estimate is advice; the caps still protect the wallet
        pass
    m = get(name)
    return float(m["cost"]) if m and m.get("cost") is not None else None


# ---------------------------------------------------------------- account and files (need the key)

def _headers() -> dict:
    k = key()
    if not k:
        raise ProviderUnavailable("MUAPI_API_KEY not set")
    return {"x-api-key": k}


def balance() -> float | None:
    """Wallet balance in USD, or None when there is no key or the call fails."""
    if not key():
        return None
    try:
        r = http().get(f"{BASE}/account/balance", headers=_headers(), timeout=20)
        return float(r.json()["balance"]) if r.status_code == 200 else None
    except Exception:  # noqa: BLE001 - a status call must never break anything
        return None


def upload(path: str | Path) -> str:
    """Upload a local file (image up to 10 MB, video up to 50 MB) and return the hosted URL to pass as an input. Free; needs a balance above zero."""
    p = Path(path)
    kind = "video" if p.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv") else "image" if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif") else "other"
    if not p.is_file():
        raise ProviderError(f"upload: {p} is not a file")
    if p.stat().st_size > MAX_UPLOAD[kind]:
        raise ProviderError(f"upload: {p.name} is {p.stat().st_size / 2**20:.1f} MB, over the {MAX_UPLOAD[kind] // 2**20} MB limit for {kind} files")
    with open(p, "rb") as fh:
        r = http().post(f"{BASE}/upload_file", headers=_headers(), files={"file": (p.name, fh)}, timeout=120)
    if r.status_code != 200 or "url" not in (r.json() if r.headers.get("content-type", "").startswith("application/json") else {}):
        raise ProviderError(f"upload: HTTP {r.status_code}")
    return r.json()["url"]


# ---------------------------------------------------------------- run

def _ext(url: str, content_type: str = "") -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix and len(suffix) <= 5:
        return suffix
    return {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "video/mp4": ".mp4", "audio/mpeg": ".mp3", "audio/wav": ".wav"}.get(content_type.split(";")[0], ".bin")


def _download(url: str, dest_stem: Path) -> Path:
    if urlparse(url).scheme != "https":
        raise ProviderError(f"refusing a non-https result URL: {url[:60]}")
    r = http().get(url, timeout=300)
    if r.status_code != 200 or not r.content:
        raise ProviderError(f"download failed: HTTP {r.status_code}")
    dest = dest_stem.with_suffix(_ext(url, r.headers.get("content-type", "")))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


def _poll(request_id: str, timeout: float, every: float) -> dict:
    t0 = time.time()
    wait = every
    while True:
        res = http().get(f"{BASE}/predictions/{request_id}/result", headers=_headers(), timeout=30).json()
        if res.get("status") in ("completed", "failed", "cancelled"):
            return res
        if time.time() - t0 > timeout:
            raise ProviderError(f"muapi job {request_id} still {res.get('status')} after {int(timeout)} s (fetch it later with `muapi result {request_id}`)")
        time.sleep(wait)
        wait = min(wait * 1.3, 10.0)


def result(request_id: str, out_dir: str | Path | None = None, *, label: str = "muapi", job: str | None = None, allow_flagged: bool = False) -> dict:
    """Finish a run: poll until done, download file outputs, return text outputs inline."""
    c = cfg()
    res = _poll(request_id, float(c["timeout"]), float(c["poll_seconds"]))
    cost = res.get("cost") or {}
    if res.get("status") != "completed":
        if cost.get("refunded") and cost.get("amount_usd"):
            ledger.spend("muapi", UNIT, -float(cost["amount_usd"]), usd=-float(cost["amount_usd"]), job=job)
        raise ProviderError(f"muapi job {res.get('status')}: {str(res.get('error') or 'no reason given')[:200]}")
    if any(res.get("has_nsfw_contents") or []) and not allow_flagged:
        raise ProviderError("muapi flagged the output as unsafe; not saved")
    outputs = res.get("outputs") or ([res["output"]] if res.get("output") else [])
    out_dir = Path(out_dir) if out_dir else Paths.cache / "muapi"
    files, urls, text, data = [], [], [], []
    for i, o in enumerate(outputs):
        if isinstance(o, str) and o.startswith("http"):
            urls.append(o)
            files.append(_download(o, out_dir / f"{label}-{request_id[:8]}-{i}"))
        elif isinstance(o, str):
            text.append(o)
        else:
            data.append(o)
    if isinstance(res.get("output"), dict) and not outputs:
        data.append(res["output"])
    if text or data:                                   # an answer you paid for is never lost: it is saved next to the media
        saved = out_dir / f"{label}-{request_id[:8]}.json"
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(json.dumps({"request_id": request_id, "text": text, "data": data}, ensure_ascii=False, indent=1), encoding="utf-8")
        files.append(saved)
    return {"request_id": request_id, "files": [str(f) for f in files], "urls": urls, "text": text, "data": data,
            "seconds": round((res.get("executionTime") or 0) / 1000, 1)}


def run(name: str, payload: dict, out_dir: str | Path | None = None, *, job: str | None = None, max_usd: float | None = None,
        label: str | None = None, wait: bool = True, allow_flagged: bool = False) -> dict:
    """Estimate, check every limit, submit, poll, download. Returns {model, request_id, usd, balance, files, urls, text, data, seconds}.
    With wait=False it returns right after the submit (use `result()` later)."""
    _headers()                                                    # raises ProviderUnavailable without a key
    row = get(name)
    if row is None:
        raise ProviderError(f"unknown Muapi model {name!r}: `python -m faceless muapi find <words>` lists real ones")
    missing = [f for f in row["required"] if f not in payload]
    if missing:
        raise ProviderError(f"{name} needs {missing} (see `python -m faceless muapi inspect {name}`)")
    c = cfg()
    est = estimate(name, payload)
    est = row["cost"] if est is None else est
    if est is None:
        raise ProviderUnavailable(f"{name}: no price available, so no spend")
    limit = float(max_usd if max_usd is not None else c["per_call_usd"])
    if est > limit:
        raise ProviderUnavailable(f"{name}: estimated ${est:.4f} is over the ${limit:.2f} per-call limit (raise it with max_usd for one call)")
    safety.guard(f"muapi {name}", est)
    if ledger.used("muapi", "blocked"):
        raise ProviderUnavailable("muapi credit exhausted earlier today")
    if ledger.used("muapi", UNIT) + est > float(c["daily_usd"]):
        raise ProviderUnavailable(f"muapi desk budget ${float(c['daily_usd']):.2f}/day reached")
    r = http().post(f"{BASE}/{row['endpoint']}", json=payload, headers=_headers(), timeout=60)
    if r.status_code in (401, 402, 403) and any(t in r.text.lower() for t in ("credit", "balance", "insufficient", "payment")):
        ledger.spend("muapi", "blocked", 1)
        raise ProviderUnavailable("muapi credit exhausted")
    if r.status_code == 429:
        raise ProviderUnavailable("muapi rate limited")
    if r.status_code != 200:
        raise ProviderError(f"muapi {name} {r.status_code}: {r.text[:200]}")
    d = r.json()
    rid = d.get("request_id")
    if not rid:
        raise ProviderError(f"muapi {name}: no request_id in {str(d)[:160]}")
    paid = float((d.get("cost") or {}).get("amount_usd", est))
    ledger.spend("muapi", UNIT, paid, usd=paid, job=job)           # billed on submit
    bal = r.headers.get("X-Account-Balance")
    events.emit("MUAPI_RUN", job=job, model=name, usd=round(paid, 4), request=rid[:12], balance=bal)
    out = {"model": name, "request_id": rid, "usd": paid, "balance": float(bal) if bal else None, "files": [], "urls": [], "text": [], "data": [], "seconds": 0}
    if not wait:
        return out
    out.update(result(rid, out_dir, label=label or name, job=job, allow_flagged=allow_flagged))
    return out


# ---------------------------------------------------------------- reports

def runway(daily_usd: float) -> float | None:
    """Days of spend the wallet covers at `daily_usd` a day."""
    bal = balance()
    return None if bal is None or daily_usd <= 0 else round(bal / daily_usd, 1)


def digest(rows: list[dict] | None = None, per_category: int = 12) -> str:
    """A dated markdown table of the cheapest enabled models per category (written into the skill's references by `muapi snapshot`)."""
    rows = rows or catalog()
    by: dict[str, list[dict]] = {}
    for m in rows:
        by.setdefault(m["category"] or "other", []).append(m)
    lines = [f"# Muapi catalog digest ({time.strftime('%Y-%m-%d', time.gmtime())})", "",
             f"{len(rows)} enabled models. Prices are USD per call from the public catalog; `~` means the price depends on the request, "
             "so run `python -m faceless muapi estimate <model>` for the exact figure. This is a snapshot: names and prices change, so "
             "`muapi find` and `muapi inspect` read the live catalog.", ""]
    for cat, ms in sorted(by.items(), key=lambda kv: -len(kv[1])):
        ms = sorted(ms, key=lambda m: (m["cost"] if m["cost"] is not None else 9e9, m["name"]))
        lines += [f"## {cat} ({len(ms)} models, cheapest {min(per_category, len(ms))} shown)", "| model | price | needs | what it is |", "|---|---|---|---|"]
        for m in ms[:per_category]:
            price = "n/a" if m["cost"] is None else f"{'~' if m['dynamic'] else ''}${m['cost']:.4g}"
            lines.append(f"| `{m['name']}` | {price} | {', '.join(m['required'][:4])} | {m['desc'][:90].replace('|', '/')} |")
        lines.append("")
    return "\n".join(lines)


def write_snapshot(rows: list[dict] | None = None) -> int:
    rows = rows or catalog(refresh=True)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(sorted(rows, key=lambda m: m["name"]), separators=(",", ":")), encoding="utf-8")
    return len(rows)
