"""Compression-based voice classifier: does a script read like our writing or like generic AI copy?

Method (from the AEO research in channel/seo-playbook.md, after Shannon): append the text to each reference
corpus and measure how many extra gzip bytes it costs. Text compresses best next to text it resembles, so
the smaller increase names the class. No model, no keywords, no network: free and deterministic.
Corpora live in gauntlet/corpus/<label>/*.txt; add good scripts to `quality` as the channel learns.
"""

from __future__ import annotations

import gzip
from functools import lru_cache
from pathlib import Path

from faceless.config import Paths

CORPUS = Paths.root / "gauntlet" / "corpus"


def _c(text: str) -> int:
    return len(gzip.compress(text.encode("utf-8"), 9))


@lru_cache(maxsize=4)
def _corpus(label: str) -> str:
    files = sorted((CORPUS / label).glob("*.txt"), key=lambda f: f.stat().st_mtime)[-8:]  # balanced, recent
    return "\n".join(f.read_text(encoding="utf-8").strip() for f in files)


def costs(text: str) -> dict[str, float]:
    """Extra compressed bytes per input byte when `text` joins each corpus (lower = more alike)."""
    out = {}
    n = max(1, len(text.encode("utf-8")))
    for d in sorted(p for p in CORPUS.iterdir() if p.is_dir()) if CORPUS.exists() else []:
        base = _corpus(d.name)
        if base:
            out[d.name] = round((_c(base + "\n" + text) - _c(base)) / n, 4)
    return out


def classify(text: str) -> tuple[str, float, dict]:
    """(label, margin, costs). margin = runner-up cost minus winner cost; small margins are uncertain."""
    c = costs(text)
    if len(c) < 2:
        return "unknown", 0.0, c
    ranked = sorted(c.items(), key=lambda kv: kv[1])
    return ranked[0][0], round(ranked[1][1] - ranked[0][1], 4), c


def corpus_files(label: str) -> list[Path]:
    return sorted((CORPUS / label).glob("*.txt"))


def remember(label: str, name: str, text: str) -> None:
    """Grow a corpus (e.g. every script that ships with a high score joins `quality`)."""
    d = CORPUS / label
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.txt").write_text(text.strip() + "\n", encoding="utf-8")
    _corpus.cache_clear()
