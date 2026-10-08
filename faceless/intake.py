"""Intake: look at an outside tool before anyone installs it.

The owner regularly hands over lists of repos, packages and install lines. This reads only public metadata and text over HTTPS from a short allowlist
of hosts (GitHub's API and raw files, the npm and PyPI registries). It never clones, installs, executes or follows a link out of what it fetched.
Everything fetched is untrusted data: it is summarised, scanned for the things that bite (install-time scripts, pipe-to-shell lines, requests for
secrets, text addressed to an AI agent, hidden comments) and written to a dossier that a person or the review step turns into a verdict.

    python -m faceless intake https://github.com/owner/repo "npx some-cli@latest" ...      # dossiers -> repo-farm/intake/<day>/

Pages that are not on the allowlist are listed as "read with a research tool" and are not fetched here.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from faceless.config import STUDIO

OUT = STUDIO / "repo-farm" / "intake"
HOSTS = {"api.github.com", "raw.githubusercontent.com", "registry.npmjs.org", "api.npmjs.org", "pypi.org"}
MAX_BYTES = 1_500_000
README_NAMES = ("README.md", "readme.md", "Readme.md", "README.rst", "README.txt", "README")
MANIFESTS = ("package.json", "pyproject.toml", "setup.py", "install.sh", "Dockerfile", "SKILL.md")

SKILLS_ADD = re.compile(r"\bskills\s+add\s+(?:https?://github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?=$|[/#?\s])")
GITHUB_URL = re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?=$|[/#?\s\"'<>)])")
NPM_LINE = re.compile(r"\b(?:npx|npm\s+(?:i|install)|pnpm\s+(?:add|dlx)|bunx)\b(?:\s+-[-\w]+)*\s+((?:@[\w.-]+/)?[\w.-]+)(?:@[\w.-]+)?")
PIP_LINE = re.compile(r"\b(?:pip3?|uv\s+pip|pipx|uvx)\s+(?:install\s+)?(?:-[-\w]+\s+)*([A-Za-z0-9][\w.-]*)")

# What each flag looks for. The first element is the severity: high means "do not run anything until a person has read the code".
PIPE_TO_SHELL = re.compile(r"(?:curl|wget|iwr|Invoke-WebRequest)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b|\|\s*iex\b", re.I)
UNPINNED = re.compile(r"\bnpx\s+(?:-y\s+)?[@\w./-]+(?:@latest)?(?=\s|$)|pip3?\s+install\s+git\+|npm\s+(?:i|install)\s+-g\s+[@\w./-]+(?:@latest)?(?=\s|$)", re.I)
SECRET_ASK = re.compile(r"\b(?:paste|enter|provide|share|send)\s+(?:your\s+)?(?:api[ _-]?key|private key|seed phrase|recovery phrase|password|secret|token)\b", re.I)
AGENT_DIRECTIVE = re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions|disregard\s+(?:the\s+)?(?:above|previous)|you\s+are\s+now\s+(?:a|an|in)\b|"
                             r"do\s+not\s+(?:tell|inform|mention\s+(?:this\s+)?to)\s+the\s+user|(?:as|if you are)\s+an?\s+(?:ai|llm)\s+(?:agent|assistant|model)[, ]+(?:you\s+)?(?:must|should|need to)|"
                             r"\bsystem\s+prompt\b.{0,40}\b(?:reveal|print|send)|<\s*/?\s*system\s*>|\[INST\]", re.I | re.S)
HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
BINARY = re.compile(r"releases/download|\.(?:exe|dmg|pkg|msi|AppImage)\b", re.I)
TELEMETRY = re.compile(r"\b(?:telemetry|usage analytics|anonymous(?:ly)? (?:usage|statistics)|phone[s]? home)\b", re.I)
BRAND_RISK = re.compile(r"\b(?:airdrop|memecoin|pump and dump|forex signals?|get[- ]rich[- ]quick|guaranteed (?:profit|returns?)|trading bot|crypto sniper|wallet drainer)\b", re.I)
KEYS = re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)*_(?:API_KEY|TOKEN|SECRET|KEY)\b")
RESTRICTIVE = re.compile(r"\b(?:AGPL|GPL-3|GPL-2|SSPL|BUSL|CC-BY-NC|non[- ]commercial|noncommercial)\b", re.I)
INSTALL_HOOKS = ("preinstall", "install", "postinstall", "prepare", "prepublish")
LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING")
LICENSE_SIGNS = [("AGPL-3.0", r"gnu affero general public license"), ("LGPL", r"gnu lesser general public license"), ("GPL-3.0", r"gnu general public license[\s,]+version 3"),
                 ("GPL-2.0", r"gnu general public license[\s,]+version 2"), ("Apache-2.0", r"apache license[\s,]+version 2\.0"), ("MPL-2.0", r"mozilla public license"),
                 ("MIT", r"permission is hereby granted, free of charge"), ("ISC", r"permission to use, copy, modify, and/or distribute this software for any purpose"),
                 ("BSD", r"redistribution and use in source and binary forms"), ("Unlicense", r"free and unencumbered software released into the public domain"),
                 ("non-commercial", r"non[- ]?commercial")]


# ---------------------------------------------------------------- fetching (the only place that touches the network)

def http_get(url: str) -> tuple[int, str]:
    """GET one allowlisted https URL, capped at 1.5 MB. Returns (status, text); (0, reason) when it could not be fetched."""
    import requests
    from urllib.parse import urlparse
    u = urlparse(url)
    if u.scheme != "https" or u.hostname not in HOSTS:
        return 0, f"not fetched: {u.hostname} is not on the intake allowlist"
    try:
        with requests.get(url, headers={"User-Agent": "quiet-money-intake", "Accept": "application/json, text/plain, */*"}, timeout=25, stream=True, allow_redirects=False) as r:
            if 300 <= r.status_code < 400:
                return r.status_code, "redirect not followed"
            body = r.raw.read(MAX_BYTES, decode_content=True) if r.status_code == 200 else b""
            return r.status_code, body.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - one dead host must not stop a list of twenty
        return 0, f"fetch failed: {type(e).__name__}"


def _json(get, url: str) -> tuple[int, dict]:
    code, text = get(url)
    try:
        return code, json.loads(text) if code == 200 else {}
    except ValueError:
        return code, {}


# ---------------------------------------------------------------- what is this input?

def classify(item: str) -> dict:
    """A GitHub repo, an npm or PyPI package named by an install line, or some other page."""
    item = item.strip()
    if m := GITHUB_URL.search(item) or SKILLS_ADD.search(item):         # `npx skills add owner/repo` copies skill files out of that GitHub repo
        return {"kind": "github", "owner": m.group(1), "repo": m.group(2), "input": item}
    if m := NPM_LINE.search(item):
        return {"kind": "npm", "name": m.group(1), "input": item}
    if m := PIP_LINE.search(item):
        return {"kind": "pypi", "name": m.group(1), "input": item}
    return {"kind": "web", "input": item}


def slug(c: dict) -> str:
    raw = f"{c['owner']}-{c['repo']}" if c["kind"] == "github" else c.get("name") or re.sub(r"[^a-z0-9]+", "-", c["input"].lower())[:50]
    return re.sub(r"[^a-z0-9.]+", "-", raw.lower()).strip("-")


# ---------------------------------------------------------------- facts per source

def detect_license(text: str) -> str | None:
    """Name the licence a LICENSE file carries, from its own wording (used when the API is not reachable)."""
    low = re.sub(r"\s+", " ", text[:12000].lower())
    return next((name for name, rx in LICENSE_SIGNS if re.search(rx, low)), None)


def github_facts(owner: str, repo: str, get=http_get) -> dict:
    f: dict = {"kind": "github", "name": f"{owner}/{repo}", "url": f"https://github.com/{owner}/{repo}", "texts": {}, "notes": []}
    code, meta = _json(get, f"https://api.github.com/repos/{owner}/{repo}")
    f["api_ok"] = code == 200
    if code == 200:
        f.update(stars=meta.get("stargazers_count"), forks=meta.get("forks_count"), license=(meta.get("license") or {}).get("spdx_id"), pushed=meta.get("pushed_at"),
                 created=meta.get("created_at"), archived=meta.get("archived"), language=meta.get("language"), size_kb=meta.get("size"), topics=meta.get("topics") or [],
                 issues=meta.get("open_issues_count"), description=meta.get("description") or "", branch=meta.get("default_branch") or "HEAD", fork=meta.get("fork"))
    else:
        f["notes"].append(f"GitHub API answered {code} (rate limited, private or gone): facts below come from raw files only")
        f["branch"] = "HEAD"
    code, listing = get(f"https://api.github.com/repos/{owner}/{repo}/contents/")
    if code == 200:
        try:
            f["top_level"] = sorted(e["name"] + ("/" if e.get("type") == "dir" else "") for e in json.loads(listing))[:60]
        except (ValueError, TypeError, KeyError):
            pass
    base = f"https://raw.githubusercontent.com/{owner}/{repo}/{f['branch']}/"
    for name in README_NAMES:
        code, text = get(base + name)
        if code == 200:
            f["texts"]["README"] = text
            break
    for name in MANIFESTS:
        code, text = get(base + name)
        if code == 200:
            f["texts"][name] = text
    if not f.get("license"):                                    # the API names the licence; without it, read the file
        for name in LICENSE_FILES:
            code, text = get(base + name)
            if code == 200:
                found = detect_license(text)
                f["license"] = f"{found} (read from {name})" if found else f"unrecognised text in {name}"
                f["license_file"] = True
                break
    try:                                                         # a published package gives download counts and a last-publish date even when the API is closed
        pkg = json.loads(f["texts"].get("package.json", "{}"))
    except ValueError:
        pkg = {}
    if pkg.get("name") and not pkg.get("private"):
        npm = npm_facts(pkg["name"], get)
        if npm.get("version"):
            f.update(npm_name=pkg["name"], weekly_downloads=npm.get("weekly_downloads"), npm_published=npm.get("pushed"), npm_version=npm.get("version"))
            f.setdefault("pushed", npm.get("pushed"))
    return f


def npm_facts(name: str, get=http_get) -> dict:
    f: dict = {"kind": "npm", "name": name, "url": f"https://www.npmjs.com/package/{name}", "texts": {}, "notes": []}
    code, doc = _json(get, f"https://registry.npmjs.org/{quote(name, safe='@')}")
    if code != 200 or not doc:
        f["notes"].append(f"npm registry answered {code}: no such package, or unreachable")
        return f
    latest = (doc.get("dist-tags") or {}).get("latest")
    v = (doc.get("versions") or {}).get(latest, {})
    t = doc.get("time") or {}
    f.update(version=latest, license=v.get("license") if isinstance(v.get("license"), str) else None, created=t.get("created"), pushed=t.get("modified"),
             description=v.get("description") or "", scripts=v.get("scripts") or {}, bin=sorted((v.get("bin") or {}) if isinstance(v.get("bin"), dict) else [v.get("bin")] if v.get("bin") else []),
             deps=sorted((v.get("dependencies") or {}))[:40], maintainers=[m.get("name") for m in (doc.get("maintainers") or [])][:8],
             repo_url=(v.get("repository") or {}).get("url") if isinstance(v.get("repository"), dict) else v.get("repository"), versions=len(doc.get("versions") or {}))
    code, dl = _json(get, f"https://api.npmjs.org/downloads/point/last-week/{quote(name, safe='@')}")
    f["weekly_downloads"] = dl.get("downloads") if code == 200 else None
    f["texts"]["README"] = (doc.get("readme") or "")[:60_000]
    return f


def pypi_facts(name: str, get=http_get) -> dict:
    f: dict = {"kind": "pypi", "name": name, "url": f"https://pypi.org/project/{name}/", "texts": {}, "notes": []}
    code, doc = _json(get, f"https://pypi.org/pypi/{quote(name)}/json")
    if code != 200 or not doc:
        f["notes"].append(f"PyPI answered {code}: no such package, or unreachable")
        return f
    info, files = doc.get("info") or {}, doc.get("urls") or []
    wheels = [u for u in files if u.get("packagetype") == "bdist_wheel"]
    f.update(version=info.get("version"), license=info.get("license") or None, description=info.get("summary") or "", pushed=max((u.get("upload_time_iso_8601") or "" for u in files), default=None) or None,
             deps=[d.split(";")[0].strip() for d in (info.get("requires_dist") or [])][:40], project_urls=info.get("project_urls") or {}, sdist_only=bool(files) and not wheels)
    f["texts"]["README"] = (info.get("description") or "")[:60_000]
    return f


# ---------------------------------------------------------------- flags

def _days(iso: str | None) -> float | None:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 86400 if iso else None
    except (ValueError, AttributeError):
        return None


def flags(f: dict) -> list[tuple[str, str, str]]:
    """(severity, code, message). `high` means nothing runs until a person has read the code."""
    out: list[tuple[str, str, str]] = []
    texts = f.get("texts", {})
    all_text = "\n".join(texts.values())
    pkg = {}
    if "package.json" in texts:
        try:
            pkg = json.loads(texts["package.json"])
        except ValueError:
            out.append(("low", "bad-manifest", "package.json does not parse"))
    scripts = {**(pkg.get("scripts") or {}), **(f.get("scripts") or {})}
    hooks = {k: v for k, v in scripts.items() if k in INSTALL_HOOKS}
    if hooks:
        out.append(("high", "install-hook", "runs code when installed: " + "; ".join(f"{k}: {str(v)[:80]}" for k, v in hooks.items())))
    if "install.sh" in texts or f.get("sdist_only") or "setup.py" in texts:
        out.append(("med", "build-time-code", "installs by running its own script (install.sh / setup.py / source-only release): read it before use"))
    if PIPE_TO_SHELL.search(all_text):
        out.append(("high", "pipe-to-shell", "tells you to pipe a download into a shell"))
    if SECRET_ASK.search(all_text):
        out.append(("high", "asks-for-secrets", "asks you to paste a key, password or seed phrase"))
    if AGENT_DIRECTIVE.search(all_text):
        out.append(("high", "agent-directive", "contains text addressed to an AI agent that tries to change its behaviour (prompt injection pattern)"))
    for c in HTML_COMMENT.findall(all_text):
        if len(c.strip()) > 60:
            out.append(("med", "hidden-comment", f"a {len(c.strip())}-character HTML comment, invisible when rendered: read it"))
            break
    if UNPINNED.search(all_text):
        out.append(("med", "unpinned-run", "runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version"))
    if BINARY.search(all_text):
        out.append(("med", "binary-download", "ships or downloads prebuilt binaries: unreviewed code"))
    if TELEMETRY.search(all_text):
        out.append(("low", "telemetry", "mentions telemetry or usage analytics: find out what is sent"))
    if BRAND_RISK.search(all_text):
        out.append(("med", "brand-risk", "promotes get-rich-quick, trading-bot or crypto-promotion content: wrong for a money-education brand"))
    if RESTRICTIVE.search(f"{f.get('license') or ''}\n{all_text[:6000]}"):
        out.append(("med", "restrictive-license", "copyleft or non-commercial terms: read before using in a paid product"))
    if f["kind"] == "github" and not f.get("license"):
        if f.get("api_ok"):
            out.append(("med", "no-license", "no licence declared: no right to use it"))
        else:
            out.append(("low", "license-unknown", "no LICENSE file at the top level and the API was not reachable: check by hand"))
    if f.get("archived"):
        out.append(("high", "archived", "the repository is archived (read-only, unmaintained)"))
    age = _days(f.get("pushed"))
    if age is not None and age > 365:
        out.append(("med", "stale", f"last change {age / 365:.1f} years ago"))
    born = _days(f.get("created"))
    if born is not None and born < 60:
        out.append(("low", "young", f"created {born:.0f} days ago: popularity and stability not yet proven"))
    if f["kind"] == "github" and f.get("api_ok") and (f.get("stars") or 0) < 25:
        out.append(("low", "tiny", f"{f.get('stars') or 0} stars: few other people have looked at it"))
    if f["kind"] == "npm" and f.get("weekly_downloads") is not None and f["weekly_downloads"] < 200:
        out.append(("low", "tiny", f"{f['weekly_downloads']} downloads last week"))
    keys = sorted(set(KEYS.findall(all_text)))[:8]
    if keys:
        out.append(("info", "needs-keys", "mentions keys: " + ", ".join(keys)))
    for n in f.get("notes", []):
        out.append(("low", "partial", n))
    order = {"high": 0, "med": 1, "low": 2, "info": 3}
    return sorted(out, key=lambda x: order[x[0]])


# ---------------------------------------------------------------- dossier

def _excerpt(text: str, n: int = 1400) -> str:
    """The README start, with invisible comments and agent-directed sentences removed so a later reader is never handed an injection."""
    text = HTML_COMMENT.sub("", text)
    text = AGENT_DIRECTIVE.sub("[removed: text addressed to an AI agent]", text)
    text = text.replace("```", "'''")
    return text.strip()[:n]


def commands_in(text: str) -> list[str]:
    """The shell lines the README tells a reader to run (for the reviewer to read, never to execute)."""
    lines = []
    for line in text.splitlines():
        s = line.strip().lstrip("$ ").strip()
        if re.match(r"(?:npx|npm|pnpm|yarn|bunx|pip3?|pipx|uv|uvx|curl|wget|brew|apt(?:-get)?|git clone|docker|cargo|go install|gh|claude|python3?)\b", s):
            lines.append(s[:140])
    seen, out = set(), []
    for s in lines:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:14]


def dossier(f: dict, fl: list[tuple[str, str, str]]) -> str:
    facts = [(k, f.get(k)) for k in ("version", "npm_name", "stars", "forks", "license", "created", "pushed", "archived", "language", "size_kb", "weekly_downloads", "versions", "maintainers", "issues") if f.get(k) not in (None, "", [])]
    if f["kind"] == "github" and not f.get("api_ok"):
        facts.append(("stars, dates, forks", "unknown: GitHub's API is not reachable from this machine for this repository"))
    lines = [f"# Intake: {f['name']}", "", f"- **Source:** {f['url']}", f"- **Looked at:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} (public metadata and text only; nothing was cloned, installed or run)",
             f"- **What it says it is:** {f.get('description') or 'n/a'}", ""]
    if facts:
        lines += ["| fact | value |", "|---|---|", *[f"| {k} | {v} |" for k, v in facts], ""]
    if f.get("top_level"):
        lines += ["**Top level:** " + ", ".join(f"`{n}`" for n in f["top_level"][:40]), ""]
    lines += ["## Red flags", ""]
    lines += [f"- **{sev.upper()} `{code}`:** {msg}" for sev, code, msg in fl] or ["- none found by the automatic scan (that is not a clean bill of health: read the code before running anything)"]
    cmds = commands_in("\n".join(f.get("texts", {}).values()))
    if cmds:
        lines += ["", "## Commands its docs tell you to run (read, do not run)", "", "```", *cmds, "```"]
    if f.get("texts", {}).get("README"):
        lines += ["", "## Start of its README (untrusted data; hidden comments and agent-directed text removed)", "", "```", _excerpt(f["texts"]["README"]), "```"]
    lines += ["", "## Verdict (a person or the review step fills this in)", "",
              "- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)",
              "- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide",
              "- [ ] **PARK**: useful later; name the phase",
              "- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it", "",
              "Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? "
              "Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- orchestration

def inspect_one(item: str, get=http_get) -> dict:
    c = classify(item)
    if c["kind"] == "github":
        f = github_facts(c["owner"], c["repo"], get)
    elif c["kind"] == "npm":
        f = npm_facts(c["name"], get)
    elif c["kind"] == "pypi":
        f = pypi_facts(c["name"], get)
    else:
        return {"input": item, "kind": "web", "slug": slug(c), "name": item, "url": item, "flags": [], "markdown": "", "note": "a web page: read it with a research tool (Exa, Firecrawl, TinyFish) and treat it as data"}
    fl = flags(f)
    return {"input": item, "kind": c["kind"], "slug": slug(c), "name": f["name"], "url": f["url"], "flags": fl, "markdown": dossier(f, fl), "facts": {k: v for k, v in f.items() if k != "texts"}}


def run(items: list[str], out_dir: Path | None = None, get=http_get, workers: int = 6) -> list[dict]:
    """Inspect every input (in parallel), write one dossier each plus index.md, return the rows."""
    out_dir = Path(out_dir) if out_dir else OUT / time.strftime("%Y-%m-%d", time.gmtime())
    out_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(items) or 1))) as pool:
        rows = list(pool.map(lambda i: inspect_one(i, get), items))
    seen: set[str] = set()
    for r in rows:
        if r["markdown"]:
            name = r["slug"]
            while name in seen:
                name += "-2"
            seen.add(name)
            r["file"] = str(out_dir / f"{name}.md")
            Path(r["file"]).write_text(r["markdown"], encoding="utf-8")
    (out_dir / "index.md").write_text(index_md(rows), encoding="utf-8")
    return rows


def index_md(rows: list[dict]) -> str:
    lines = [f"# Intake {time.strftime('%Y-%m-%d', time.gmtime())}", "", "| input | kind | stars / downloads | licence | last change | high flags | other flags | dossier |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f = r.get("facts", {})
        pop = f.get("stars") if f.get("stars") is not None else f.get("weekly_downloads", "")
        high = ", ".join(c for s, c, _ in r["flags"] if s == "high") or "none"
        rest = ", ".join(c for s, c, _ in r["flags"] if s != "high") or "none"
        last = (f.get("pushed") or "")[:10]
        lines.append(f"| {r['name'][:60]} | {r['kind']} | {pop} | {f.get('license') or ''} | {last} | {high} | {rest} | {Path(r['file']).name if r.get('file') else r.get('note', '')} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- verdicts

VERDICTS = ("USE", "TRIAL", "PARK", "KILL")


def load_verdicts(folder: Path) -> dict:
    return json.loads((Path(folder) / "verdicts.json").read_text(encoding="utf-8"))


def dossier_files(folder: Path, item_id: str) -> list[Path]:
    """The dossier for an id plus numbered twins (`x.md`, `x-2.md`): one decision can cover an npm package and its repository."""
    folder = Path(folder)
    return [p for p in sorted(folder.glob(f"{item_id}*.md")) if p.stem == item_id or re.fullmatch(rf"{re.escape(item_id)}-\d+", p.stem)]


def apply_verdicts(folder: Path) -> dict[str, int]:
    """Tick the verdict box in each dossier and add a Decision block (why, what to steal, what only the owner can do). Idempotent."""
    folder = Path(folder)
    data = load_verdicts(folder)
    written, missing = 0, 0
    for it in data["items"]:
        files = dossier_files(folder, it["id"])
        if not files:
            missing += 1
            continue
        if it["verdict"] not in VERDICTS:
            raise ValueError(f"{it['id']}: verdict must be one of {VERDICTS}")
        for f in files:
            text = f.read_text(encoding="utf-8")
            text = re.sub(r"- \[[ x]\] \*\*(USE|TRIAL|PARK|KILL)\*\*", lambda m: f"- [{'x' if m.group(1) == it['verdict'] else ' '}] **{m.group(1)}**", text)
            text = text.split("\n## Decision")[0].rstrip("\n") + "\n"
            block = [f"\n## Decision ({data['date']})", "", f"**{it['verdict']}**, pipeline stage: {it.get('stage') or 'none'}.", "", it["why"]]
            if it.get("steal") and it["steal"].lower() not in ("none", "n/a", "none needed"):
                block += ["", f"**Worth taking:** {it['steal']}"]
            if it.get("owner"):
                block += ["", f"**Only the owner can:** {it['owner']}"]
            f.write_text(text + "\n".join(block) + "\n", encoding="utf-8")
            written += 1
    return {"dossiers": written, "ids_without_dossier": missing}


def verdict_table(data: dict, heading_level: str = "##") -> str:
    """The decisions as Markdown tables for channel/empire/RESOURCES.md: repositories and packages first, then pages and services."""
    mark = {"USE": "**use**", "TRIAL": "**trial**", "PARK": "**park**", "KILL": "**kill**"}
    out = [f"{heading_level} Quiet Money 3 and setup lists ({data['date']})", "",
           "Read with `python -m faceless intake` (dossiers in `repo-farm/intake/%s/`). %s" % (data["date"], data["source"].split(". ", 1)[-1]), "",
           "| resource | verdict | stage | why | worth taking |", "|---|---|---|---|---|"]
    for it in data["items"] + data["web"]:
        steal = it.get("steal") or ""
        steal = "" if steal.lower() in ("none", "n/a", "none needed") else steal
        out.append(f"| {it['name']} | {mark[it['verdict']]} | {it.get('stage') or ''} | {it['why']} | {steal} |")
    asks = [(it["name"], it["owner"]) for it in data["items"] + data["web"] if it.get("owner")]
    if asks:
        out += ["", f"{heading_level}# Decisions only the owner can make", ""] + [f"- **{n}:** {o}" for n, o in asks]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- the registers

RESOURCES = STUDIO / "channel" / "empire" / "RESOURCES.md"
REGISTRY = STUDIO / "repo-farm" / "registry.md"


def _first_sentence(text: str, cap: int = 230) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return (m.group(1) if m else text)[:cap]


def registry_section(data: dict, folder_name: str | None = None) -> str:
    """The compact verified rows for repo-farm/registry.md: adopted, parked and rejected, one line of reason each."""
    where = folder_name or data["date"]
    out = [f"## Intake {data['date']} (verified from dossiers in `repo-farm/intake/{where}/`)", "",
           "Each row was read from the project's own README, manifest, licence file or registry entry; nothing was installed or run. "
           "Stars and dates were unavailable where the GitHub API is closed to this machine.", ""]
    for verdict, title in (("USE", "Active or adopted"), ("TRIAL", "On trial"), ("PARK", "Parked (named condition)"), ("KILL", "Rejected (recorded so nobody re-evaluates)")):
        rows = [it for it in data["items"] + data["web"] if it["verdict"] == verdict]
        if rows:
            out += [f"### {title}", "", "| Tool | Stage | Why |", "|---|---|---|"] + [f"| {it['name']} | {it.get('stage') or ''} | {_first_sentence(it['why'])} |" for it in rows] + [""]
    return "\n".join(out)


def _replace_section(path: Path, marker: str, new: str) -> None:
    """Put `new` (which starts with `marker`) at the end of the file, dropping an earlier copy of the same section. Idempotent."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    text = text.split(marker)[0].rstrip("\n")
    path.write_text((text + "\n\n" if text else "") + new.rstrip("\n") + "\n", encoding="utf-8")


def refresh_registers(folder: Path, resources: Path = RESOURCES, registry: Path = REGISTRY) -> None:
    """Write the decisions into channel/empire/RESOURCES.md (full table) and repo-farm/registry.md (compact rows)."""
    data = load_verdicts(folder)
    _replace_section(resources, f"## Quiet Money 3 and setup lists ({data['date']})", verdict_table(data))
    _replace_section(registry, f"## Intake {data['date']} (verified", registry_section(data, Path(folder).name))
