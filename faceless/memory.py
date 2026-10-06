"""Searchable memory of everything the studio has made: scripts, outcomes, and why videos were held.

SQLite FTS5 + BM25 (built into Python), rebuilt from the committed files in a second, so there is nothing to
keep in sync and no new dependency. Same idea as the Leviathan agent-memory tool, without installing a binary.
Use it to ask "have we covered this angle?", "which videos were held for word_count?", "what did our best
psychology scripts open with?" before writing or scanning. The index is derived data (gitignored).
"""

from __future__ import annotations

import json
import re
import sqlite3

from faceless.config import Paths

DB = Paths.state / "memory.db"


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9$%]+", text.lower())


def build(db=None) -> int:
    """Rebuild the index from script-lab/final, state/jobs and gauntlet/reports. Returns documents indexed."""
    db = db or DB
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.executescript("drop table if exists docs; drop table if exists fts;"
                      "create table docs(job text primary key, pillar text, status text, score real, day text, title text);"
                      "create virtual table fts using fts5(job unindexed, body, tokenize='porter unicode61');")
    n = 0
    for f in sorted(Paths.final.glob("*.json")):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        job = f.stem
        meta = {}
        jp = Paths.jobs / f"{job}.json"
        if jp.exists():
            try:
                meta = json.loads(jp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        failing = []
        rp = Paths.reports / f"{job}.json"
        if rp.exists():
            try:
                failing = [g["name"] for g in json.loads(rp.read_text(encoding="utf-8")).get("gates", []) if not g.get("passed")]
            except (json.JSONDecodeError, KeyError):
                pass
        narration = " ".join(b.get("say", "") for b in s.get("beats", []) if isinstance(b, dict))
        body = " ".join([s.get("title", ""), s.get("hook_text", ""), narration, "failed gates: " + " ".join(failing),
                         " ".join(meta.get("notes", []))])
        con.execute("insert into docs values(?,?,?,?,?,?)", (
            job, s.get("pillar") or meta.get("pillar", ""), meta.get("status", "unknown"),
            (meta.get("scores") or {}).get("gauntlet"), meta.get("day", job[:10]), s.get("title", "")))
        con.execute("insert into fts values(?,?)", (job, body))
        n += 1
    con.commit()
    con.close()
    return n


def search(query: str, pillar: str | None = None, status: str | None = None, n: int = 5, db=None) -> list[dict]:
    """Top n matches by BM25 (any query word counts; more matches rank higher), optionally filtered by pillar/status."""
    db = db or DB
    words = _words(query)
    if not words or not db.exists():
        return []
    q = " OR ".join(f'"{w}"' for w in words)
    sql = ("select d.job, d.pillar, d.status, d.score, d.day, d.title, snippet(fts, 1, '[', ']', '...', 14) "
           "from fts join docs d on d.job = fts.job where fts match ? ")
    args: list = [q]
    if pillar:
        sql += "and d.pillar = ? "
        args.append(pillar)
    if status:
        sql += "and d.status = ? "
        args.append(status)
    sql += "order by bm25(fts) limit ?"
    args.append(n)
    con = sqlite3.connect(db)
    rows = con.execute(sql, args).fetchall()
    con.close()
    return [dict(zip(("job", "pillar", "status", "score", "day", "title", "match"), r)) for r in rows]
