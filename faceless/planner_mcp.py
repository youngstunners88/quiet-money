"""quiet-planner: a small MCP server (stdio) that lets any agent run the Daily Planner's picture work and build, with the studio's rules built in.

    python -m faceless.planner_mcp          # speaks MCP (JSON-RPC 2.0, one message per line) on stdin/stdout; logs go to stderr

Tools (nothing here publishes, lists, posts or changes a price; CLAUDE.md rule 9):
  planner_status     what is in place: owner pictures, drawn days, last build, which optional services have keys (yes/no, never the key), whether the studio is paused
  planner_normalize  turn HEIC, TIFF, PSD, AVIF pictures into PNG through FreeConvert (optional, needs the owner's token, capped), into assets/planner/incoming/
  planner_ingest     number a folder of pictures into assets/planner/source/day-NNN.*
  planner_clean      remove the handle (local OpenCV), optionally review each result (local checks + a vision model through OpenRouter + the Jev gate)
  planner_review     review one day's cleaned picture
  planner_build      draw the missing days and build the Letter and A4 PDFs
  planner_check      the planner gauntlet (content, numbers, layout, files, listing copy)
  planner_cover      write the print cover as cover.png
It is written against the protocol directly (about 150 lines, no package to install) so there is nothing to review but this file. Keys are read from the
environment by the modules that need them and never appear in a reply. Spend is capped in studio.toml ([planner], [freeconvert]) and `state/PAUSE` stops it.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from faceless import config, freeconvert, planner_art, planner_clean, planner_review, safety
from faceless.config import STUDIO

PROTOCOL = "2024-11-05"
SERVER = {"name": "quiet-planner", "version": "0.1.0"}


def _rel(p: Path | str) -> str:
    try:
        return str(Path(p).resolve().relative_to(STUDIO))
    except ValueError:
        return str(p)


def _folder(arg: str) -> Path:
    p = Path(arg).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"{arg!r} is not a folder")
    return p


def _pictures(folder: Path, exts) -> list[Path]:
    return sorted((f for f in folder.iterdir() if f.is_file() and not f.is_symlink() and f.suffix.lower() in exts), key=planner_clean.natural_key)


# ---------------------------------------------------------------- tools

def t_status(_a: dict) -> dict:
    inv = planner_clean.inventory(write=False)
    build = STUDIO / "channel" / "products" / "daily-quiet-money-planner" / "build.json"
    return {"pictures": inv, "last_build": json.loads(build.read_text()) if build.exists() else None,
            "services": {"openrouter_vision_review": bool(config.env("OPENROUTER_API_KEY")), "jev_gate": bool(config.env("TYPESAFE_API_KEY")),
                         "freeconvert_normalize": freeconvert.available()},
            "paused": safety.paused()}


def t_normalize(a: dict) -> dict:
    folder = _folder(a["folder"])
    done, skipped = [], []
    for f in _pictures(folder, freeconvert.EXOTIC):
        try:
            done.append({"from": f.name, "to": _rel(freeconvert.normalize(f))})
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the rest; the reason is reported
            skipped.append({"file": f.name, "why": str(e)[:200]})
    return {"converted": done, "skipped": skipped, "next": "planner_ingest on assets/planner/incoming (plus the folder's own jpg/png/webp files)" if done else "nothing converted"}


def t_ingest(a: dict) -> dict:
    folder = _folder(a["folder"])
    done = planner_clean.ingest(folder, int(a.get("start", 1)))
    return {"copied": len(done), "first_day": done[0][0] if done else None, "last_day": done[-1][0] if done else None}


def _reviewer(use_vision: bool):
    def run(_name, before, after, found):
        r = planner_review.review(before, after, found, use_vision=use_vision)
        return {"status": r["status"], "reasons": r["reasons"], "model_looked": bool(r["vision"]), "gate": r["gate"]}
    return run


def t_clean(a: dict) -> dict:
    box = tuple(float(v) for v in a["box"].split(",")) if a.get("box") else None
    rep = planner_clean.run_clean(box, reviewer=_reviewer(bool(a.get("vision", True))) if a.get("review", True) else None)
    hit = {k: v for k, v in rep.items() if v["removed"]}
    held = sorted(k for k, v in hit.items() if (v.get("review") or {}).get("status") == "needs_human")
    return {"checked": len(rep), "handle_removed": len(hit), "needs_a_person": held, "report": "assets/planner/clean-report.json",
            "look_at": "assets/planner/clean-before-after.jpg", "note": "the owner looks at the contact sheet before the cleaned copies are trusted"}


def t_review(a: dict) -> dict:
    from PIL import Image
    day = int(a["day"])
    src = next((p for ext in planner_art.EXTS if (p := planner_art.SOURCE / f"day-{day:03d}{ext}").exists()), None)
    clean = next((p for ext in planner_art.EXTS if (p := planner_art.CLEAN / f"day-{day:03d}{ext}").exists()), None)
    if not src or not clean:
        raise ValueError(f"day {day} needs both a source and a cleaned picture; run planner_clean first")
    before, after = Image.open(src), Image.open(clean)
    found = planner_clean.detect(before)
    r = planner_review.review(before, after, found, use_vision=bool(a.get("vision", True)))
    return {"day": day, **{k: r[k] for k in ("status", "reasons", "gate")}, "local": r["local"], "vision": r["vision"]}


def t_build(a: dict) -> dict:
    from faceless import product_planner as pp
    size = a.get("size", "both")
    return pp.build(("Letter", "A4") if size == "both" else (size,), limit=a.get("days"))


def t_check(_a: dict) -> dict:
    from faceless import product_planner as pp
    gates = [{"gate": n, "ok": ok, "detail": d, "hard": h} for n, ok, d, h in pp.check()]
    return {"passed": all(g["ok"] for g in gates if g["hard"]), "gates": gates}


def t_cover(_a: dict) -> dict:
    from faceless import planner_cover, product_planner as pp
    out = STUDIO / "channel" / "products" / pp.PRODUCT / "cover.png"
    planner_cover.cover(1700, 2200).save(out)
    return {"cover": _rel(out)}


def _schema(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


TOOLS = {
    "planner_status": (t_status, "What is in place for the Daily Planner: owner pictures vs drawn days, last build, which optional services have keys, paused or not.", _schema({})),
    "planner_normalize": (t_normalize, "Convert HEIC/TIFF/PSD/AVIF pictures in a folder to PNG through FreeConvert (optional: needs the owner's FREECONVERT_API_KEY; capped). Output: assets/planner/incoming/.",
                          _schema({"folder": {"type": "string", "description": "Folder with the pictures"}}, ["folder"])),
    "planner_ingest": (t_ingest, "Copy a folder's jpg/png/webp pictures into assets/planner/source/ as day-NNN in natural file order.",
                       _schema({"folder": {"type": "string"}, "start": {"type": "integer", "description": "Day number of the first picture (default 1)"}}, ["folder"])),
    "planner_clean": (t_clean, "Remove the @handle watermark from every source picture (local OpenCV; originals untouched) and review each result. Writes a before|after contact sheet.",
                      _schema({"box": {"type": "string", "description": "x0,y0,x1,y1 as fractions of the picture, only when the handle is somewhere unusual"},
                               "review": {"type": "boolean", "description": "Review each result (default true)"},
                               "vision": {"type": "boolean", "description": "Include the vision-model look through OpenRouter (default true; capped, off without a key)"}})),
    "planner_review": (t_review, "Review one day's cleaned picture: local checks, optional vision look, decision gate.",
                       _schema({"day": {"type": "integer"}, "vision": {"type": "boolean"}}, ["day"])),
    "planner_build": (t_build, "Draw the missing days and build the planner PDFs (Letter and A4). About 90 seconds for the full year.",
                      _schema({"size": {"type": "string", "enum": ["Letter", "A4", "both"]}, "days": {"type": "integer", "description": "Build only the first N days (a quick test)"}})),
    "planner_check": (t_check, "Run the planner gauntlet: content, computed numbers, no advice, page fit, PDF pages and size, listing copy.", _schema({})),
    "planner_cover": (t_cover, "Write the print cover as channel/products/daily-quiet-money-planner/cover.png.", _schema({})),
}


# ---------------------------------------------------------------- protocol

def call(name: str, args: dict) -> dict:
    if name not in TOOLS:
        return {"content": [{"type": "text", "text": f"unknown tool {name!r}"}], "isError": True}
    try:
        out = TOOLS[name][0](args or {})
        return {"content": [{"type": "text", "text": json.dumps(out, indent=1, default=str)}], "isError": False}
    except Exception as e:  # noqa: BLE001 - the agent gets the reason, never a traceback with paths or keys
        print(traceback.format_exc(), file=sys.stderr)
        return {"content": [{"type": "text", "text": f"{type(e).__name__}: {str(e)[:300]}"}], "isError": True}


def handle(msg: dict) -> dict | None:
    """One JSON-RPC message in, the reply out (None for a notification)."""
    mid, method, params = msg.get("id"), msg.get("method", ""), msg.get("params") or {}
    if mid is None:
        return None                                                  # notifications (initialized, cancelled) get no reply
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion") or PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": SERVER}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (_f, d, s) in TOOLS.items()]}
    elif method == "tools/call":
        result = call(params.get("name", ""), params.get("arguments") or {})
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def serve(stdin=None, stdout=None) -> None:
    stdin, stdout = stdin or sys.stdin, stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            reply = handle(msg) if isinstance(msg, dict) else {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve()
