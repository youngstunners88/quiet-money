"""The toolbox: a local, searchable copy of the Awesome REA catalog (https://github.com/reacher-z/Awesome-REA, MIT), so an agent that
needs a tool for understanding a website, an app, a file format or a protocol finds a reviewed one in one command instead of spending
tokens searching the web.

    python -m faceless toolbox find "capture app traffic and write an OpenAPI spec" [--target app] [-n 8]
    python -m faceless toolbox show <id>
    python -m faceless toolbox sync [--from <checkout>]      refresh the local copy (network: two public JSON files, nothing is sent)
    python -m faceless toolbox status

The copy lives in `state/tmp/toolbox.json` (gitignored): tools, integrations, guides and collections; the catalog's thousands of case
studies are counted but left out, and searched only with `--cases`. Search is plain word overlap: 0 tokens.

Finding a tool is not permission to run it. Anything from outside goes through `python -m faceless intake <url>` first, and nothing
here is for getting past a login, a block, a rate limit or a paywall (CLAUDE.md rules 9 and 10).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from faceless import events
from faceless.config import Paths
from faceless.fsutil import write_atomic

RAW = "https://raw.githubusercontent.com/reacher-z/Awesome-REA/main/data/"
FILES = ("tool-resources.json", "rea-resources.json")
STORE = Paths.state / "tmp" / "toolbox.json"
MAX_BYTES = 40 * 2**20
KEEP = ("id", "name", "url", "category", "kind", "targets", "description_en", "requirements", "verified_at")
TARGETS = ("website", "game", "app", "binary", "firmware", "protocol")
_WORD = re.compile(r"[a-z0-9]{2,}")
_STOP = frozenset("the a an and or of to for in on with from that this is are be it as by at into how what which tool tools need want".split())
# words agents use -> words the catalog uses
ALIASES = {"api": ["openapi", "endpoint", "rest", "graphql"], "traffic": ["http", "proxy", "mitm", "capture"], "android": ["apk", "adb", "frida"],
           "phone": ["android", "apk", "adb"], "site": ["website", "browser", "web"], "scrape": ["crawl", "browser", "capture"],
           "mcp": ["agent", "server"], "decompile": ["decompiler"], "ios": ["ipa", "iphone"], "electron": ["asar", "javascript"]}


def _slim(item: dict) -> dict:
    out = {k: item.get(k) for k in KEEP if item.get(k) not in (None, "", [])}
    out["requirements"] = [str(r)[:200] for r in (out.get("requirements") or [])][:3]
    return out


def _fetch(name: str) -> list:
    import requests
    with requests.get(RAW + name, timeout=60, stream=True, headers={"User-Agent": "quiet-money-toolbox"}) as r:
        r.raise_for_status()
        body = b""
        for chunk in r.iter_content(2**16):
            body += chunk
            if len(body) > MAX_BYTES:
                raise ValueError(f"{name} is larger than {MAX_BYTES // 2**20} MB; refusing to read on")
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{name} is not a list")
    return data


def build(lists: list[list]) -> dict:
    """The slim copy from the catalog's own lists. Outside text is data: only known fields are kept, as plain strings."""
    seen, tools, cases = set(), [], []
    for items in lists:
        for it in items:
            if not isinstance(it, dict) or not it.get("id") or not str(it.get("url") or "").startswith("https://") or it["id"] in seen:
                continue
            seen.add(it["id"])
            (cases if it.get("kind") == "case-study" else tools).append(_slim(it))
    return {"source": "https://github.com/reacher-z/Awesome-REA", "license": "MIT", "synced_at": events.now_iso(), "tools": tools, "cases": cases}


def sync(checkout: Path | None = None) -> dict:
    """Refresh the local copy from the public catalog, or from a checkout already on disk."""
    lists = []
    for name in FILES:
        if checkout:
            lists.append(json.loads((Path(checkout) / "data" / name).read_text(encoding="utf-8")))
        else:
            lists.append(_fetch(name))
    box = build(lists)
    if len(box["tools"]) < 100:
        raise ValueError(f"only {len(box['tools'])} tools read; keeping the copy already on disk")
    write_atomic(STORE, json.dumps(box, ensure_ascii=False))
    events.emit("TOOLBOX_SYNC", tools=len(box["tools"]), cases=len(box["cases"]))
    return {"tools": len(box["tools"]), "cases": len(box["cases"]), "synced_at": box["synced_at"]}


def load() -> dict | None:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _terms(text: str) -> set[str]:
    words = {w for w in _WORD.findall(text.lower()) if w not in _STOP}
    for w in list(words):
        words.update(ALIASES.get(w, ()))
        if w.endswith("s") and len(w) > 4:
            words.add(w[:-1])
    return words


def find(query: str, target: str | None = None, limit: int = 8, cases: bool = False, box: dict | None = None) -> list[dict]:
    """The entries that share the most words with the need, name matches counting double; a tool before a guide before a list, case studies last."""
    box = box or load()
    if not box:
        return []
    want = _terms(query)
    rank = {"tool": 0, "integration": 0, "project": 1, "documentation": 2, "learning-resource": 2, "research": 3, "collection": 3, "case-study": 4}
    hits = []
    for it in box["tools"] + (box["cases"] if cases else []):
        if target and target not in (it.get("targets") or []):
            continue
        name = set(_WORD.findall(str(it.get("name", "")).lower()))
        body = _terms(" ".join([str(it.get("description_en", "")), str(it.get("category", "")), " ".join(it.get("targets") or [])]))
        score = 2 * len(want & name) + len(want & body)
        if score:
            hits.append((it.get("kind") == "case-study", -score, rank.get(it.get("kind"), 3), it["id"], it))
    return [h[4] for h in sorted(hits, key=lambda h: h[:4])[:max(1, limit)]]


def show(item_id: str, box: dict | None = None) -> dict | None:
    box = box or load()
    return next((it for it in (box["tools"] + box["cases"]) if it["id"] == item_id), None) if box else None


def line(it: dict) -> str:
    return (f"{it['id']}  [{it.get('kind', '?')} · {', '.join(it.get('targets') or []) or 'any'}]\n    {it.get('name', '')}: "
            f"{str(it.get('description_en', ''))[:220]}\n    {it['url']}")


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="python -m faceless toolbox")
    p.add_argument("action", choices=["find", "show", "sync", "status"])
    p.add_argument("query", nargs="*")
    p.add_argument("--target", choices=TARGETS)
    p.add_argument("-n", type=int, default=8)
    p.add_argument("--cases", action="store_true", help="also search the case studies")
    p.add_argument("--from", dest="checkout", help="a local checkout of the catalog instead of the network")
    a = p.parse_args(argv)
    if a.action == "sync":
        try:
            print(json.dumps(sync(Path(a.checkout) if a.checkout else None)))
        except Exception as e:   # noqa: BLE001 - a network or format fault is the answer, not a traceback
            print(f"refused: {str(e)[:200]}")
            return 1
        return 0
    box = load()
    if not box:
        print("no local copy yet: run `python -m faceless toolbox sync`")
        return 1
    if a.action == "status":
        print(json.dumps({"tools": len(box["tools"]), "cases": len(box["cases"]), "synced_at": box["synced_at"], "source": box["source"]}))
        return 0
    if a.action == "show":
        it = show(" ".join(a.query), box)
        print(json.dumps(it, indent=1, ensure_ascii=False) if it else "no entry with that id")
        return 0 if it else 1
    hits = find(" ".join(a.query), a.target, a.n, a.cases, box)
    if not hits:
        print("nothing in the catalog matches; say what you need with `python -m faceless crew ask research \"...\"`")
        return 1
    print("\n".join(line(it) for it in hits))
    print("\nBefore installing any of these: python -m faceless intake <url>")
    return 0
