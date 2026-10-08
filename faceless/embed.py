"""Semantic embeddings for duplicate detection and the variety audit (the EmbeddingGemma family, with a free fallback).

Why: the lexical similarity gate misses a paraphrase ("debt snowball vs avalanche" written two ways), and YouTube's monetization policy
penalizes channels whose videos feel interchangeable. Vectors answer both. Chain (free first): Gemini embeddings (free tier, no neurons),
then Cloudflare Workers AI `@cf/google/embeddinggemma-300m` (EmbeddingGemma 1; swap the model name in [embed] when Cloudflare hosts
EmbeddingGemma 2, released 2026-10-06 under Apache-2.0). Vectors are truncated (Matryoshka) to 256 dimensions, normalized, cached in
SQLite by text hash, and never required: no vector means the lexical gates decide alone.
"""

from __future__ import annotations

import hashlib
import math
import sqlite3
import struct

from faceless import config
from faceless.config import Paths
from faceless.providers import ProviderUnavailable, http

DB = Paths.state / "embeddings.db"       # derived data: gitignored, rebuilt on demand
DIM = 256


def cfg() -> dict:
    return {"chain": ["gemini", "cloudflare"], "gemini_model": "gemini-embedding-001", "cloudflare_model": "@cf/google/embeddinggemma-300m",
            **config.load().get("embed", {})}


def _norm(v: list[float]) -> list[float]:
    v = v[:DIM]
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _gemini(texts: list[str], model: str) -> list[list[float]]:
    key = config.env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if not key:
        raise ProviderUnavailable("GEMINI_API_KEY not set")
    r = http().post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents", headers={"x-goog-api-key": key}, timeout=60,
                    json={"requests": [{"model": f"models/{model}", "content": {"parts": [{"text": t}]}, "taskType": "SEMANTIC_SIMILARITY",
                                        "outputDimensionality": DIM} for t in texts]})
    if r.status_code != 200:
        raise ProviderUnavailable(f"gemini embeddings {r.status_code}")
    return [_norm(e["values"]) for e in r.json()["embeddings"]]


def _cloudflare(texts: list[str], model: str) -> list[list[float]]:
    key, acct = config.env("CLOUDFLARE_API_KEY", "CLOUDFLARE_API_TOKEN"), config.env("CLOUDFLARE_ACCOUNT_ID")
    if not key or not acct:
        raise ProviderUnavailable("Cloudflare keys not set")
    r = http().post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}", headers={"Authorization": f"Bearer {key}"}, timeout=60,
                    json={"text": ["task: sentence similarity | query: " + t for t in texts]})
    if r.status_code != 200:
        raise ProviderUnavailable(f"cloudflare embeddings {r.status_code}")
    return [_norm(v) for v in r.json()["result"]["data"]]


def _db() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("create table if not exists vec (k text primary key, v blob)")
    return con


def embed(texts: list[str]) -> list[list[float]] | None:
    """Unit vectors for each text, or None when no provider can serve (callers fall back to lexical checks)."""
    c = cfg()
    texts = [t[:6000] for t in texts]
    con = _db()
    out: list[list[float] | None] = [None] * len(texts)
    keys = [hashlib.sha1(f"{DIM}:{t}".encode()).hexdigest() for t in texts]
    for i, k in enumerate(keys):
        row = con.execute("select v from vec where k=?", (k,)).fetchone()
        if row:
            out[i] = list(struct.unpack(f"{DIM}e", row[0]))
    todo = [i for i, v in enumerate(out) if v is None]
    for start in range(0, len(todo), 50):
        part = todo[start:start + 50]
        vecs = None
        for name in c["chain"]:
            try:
                vecs = (_gemini if name == "gemini" else _cloudflare)([texts[i] for i in part], c[f"{name}_model"])
                break
            except Exception:  # noqa: BLE001 - any provider failure falls through to the next
                continue
        if vecs is None:
            con.close()
            return None
        for i, v in zip(part, vecs):
            out[i] = v
            con.execute("insert or replace into vec values (?,?)", (keys[i], struct.pack(f"{DIM}e", *v)))
    con.commit()
    con.close()
    return out  # type: ignore[return-value]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def nearest(text: str, corpus: list[str], k: int = 3) -> list[tuple[float, str]] | None:
    """The k corpus texts most similar to `text`, as (cosine, text); None without embeddings."""
    vecs = embed([text] + corpus)
    if vecs is None:
        return None
    sims = sorted(((cosine(vecs[0], v), t) for v, t in zip(vecs[1:], corpus)), reverse=True)
    return sims[:k]


def centered(vecs: list[list[float]], reference: list[list[float]] | None = None) -> list[list[float]]:
    """Subtract the mean of `reference` (default: vecs) and renormalize. Raw cosines of same-domain texts all sit near 0.85; centering
    removes the shared 'personal finance' component so a near-duplicate stands out (0.7 or more) from an ordinary neighbour (under 0.3)."""
    ref = reference or vecs
    d = len(ref[0])
    mean = [sum(v[k] for v in ref) / len(ref) for k in range(d)]
    out = []
    for v in vecs:
        c = [a - b for a, b in zip(v, mean)]
        n = math.sqrt(sum(x * x for x in c)) or 1.0
        out.append([x / n for x in c])
    return out
