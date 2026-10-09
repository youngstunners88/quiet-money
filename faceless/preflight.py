"""Preflight: one command that says whether today's run can succeed, before it starts, and what to do if it cannot.

`python -m faceless preflight` prints a traffic light per check (ok, warn, fail) with the fix, writes nothing, and exits 1 when anything
fails (2 with --strict when something warns). The daily routine runs it first: a failure it can repair it repairs, one it cannot it
reports, and nothing is half-started on a machine that was never going to finish. Keys are reported by name and presence only; no key,
and no part of one, is ever printed.
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from faceless import config, ledger, safety
from faceless.config import STUDIO, Paths

OK, WARN, FAIL = "ok", "warn", "fail"


@dataclass
class Check:
    name: str
    level: str
    detail: str
    fix: str = ""


def _present(*names: str) -> list[str]:
    return [n for n in names if config.env(n)]


def checks_config() -> list[Check]:
    try:
        cfg = config.load()
    except Exception as e:  # noqa: BLE001 - a broken studio.toml is the first thing to report
        return [Check("config", FAIL, f"studio.toml does not load: {type(e).__name__}: {str(e)[:100]}", "fix the TOML syntax; `git diff studio.toml` shows the last edit")]
    need = ["channel", "production", "voice", "images", "llm", "publish", "safety", "muapi", "qa"]
    gone = [s for s in need if s not in cfg]
    return [Check("config", FAIL if gone else OK, f"missing sections: {gone}" if gone else f"studio.toml loads, {len(cfg['pillars'])} pillars", "restore the sections from git history" if gone else "")]


def checks_tools() -> list[Check]:
    out = []
    for tool in ("ffmpeg", "ffprobe"):
        out.append(Check(tool, OK if shutil.which(tool) else FAIL, shutil.which(tool) or "missing", "" if shutil.which(tool) else "apt-get install -y ffmpeg"))
    for mod in ("PIL", "numpy", "cv2", "edge_tts", "requests"):
        try:
            importlib.import_module(mod)
            out.append(Check(f"python:{mod}", OK, "importable"))
        except ImportError:
            other_voice = mod == "edge_tts" and _present("ELEVENLABS_API_KEY", "GEMINI_API_KEY")           # the voice chain falls through to a keyed voice
            out.append(Check(f"python:{mod}", WARN if other_voice else FAIL, "not installed" + (" (another voice will be used)" if other_voice else ""), "pip install -r requirements.txt"))
    fonts = sorted(p.name for p in Paths.fonts.glob("*.ttf"))
    out.append(Check("fonts", OK if len(fonts) >= 4 else FAIL, f"{len(fonts)} font files", "" if len(fonts) >= 4 else "git checkout assets/fonts"))
    out.append(Check("optional:node", OK if shutil.which("npx") else WARN, "motion cards available" if shutil.which("npx") else "no Node: videos use stills only (fine)", ""))
    out.append(Check("optional:libreoffice", OK if (shutil.which("soffice") or shutil.which("libreoffice")) else WARN,
                     "products can be rebuilt and verified" if shutil.which("soffice") else "needed only to rebuild products and listing pictures", "apt-get install -y libreoffice-calc poppler-utils"))
    return out


def checks_keys() -> list[Check]:
    llm = _present("GEMINI_API_KEY", "LONGCAT_API_KEY", "OPENROUTER_API_KEY")
    img = _present("CLOUDFLARE_API_KEY", "MUAPI_API_KEY", "OPENROUTER_API_KEY")
    sketch_on = config.load()["production"].get("sketch", {}).get("mode") == "on"
    sketch = [Check("keys:sketch", OK if _present("OPENROUTER_API_KEY") else WARN, "motion scenes are on and OPENROUTER_API_KEY is set" if _present("OPENROUTER_API_KEY")
                    else "motion scenes are on but OPENROUTER_API_KEY is not set: every video keeps its stills",
                    "" if _present("OPENROUTER_API_KEY") else "add OPENROUTER_API_KEY to the environment, or set [production.sketch] mode = \"off\"")] if sketch_on else []
    return sketch + [Check("keys:llm", OK if llm else FAIL, f"{', '.join(llm)}" if llm else "no script-writing provider has a key (only the anonymous fallback is left)", "" if llm else "add GEMINI_API_KEY to the environment"),
            Check("keys:images", OK if len(img) >= 2 else WARN, f"{', '.join(img) or 'none'}; procedural art is the last resort",
                  "" if len(img) >= 2 else "a second image provider makes a day survive one outage"),
            Check("keys:qa", OK if (_present("CLOUDFLARE_API_KEY") and _present("CLOUDFLARE_ACCOUNT_ID")) or _present("MUAPI_API_KEY") else WARN,
                  "semantic QA can run (" + " and ".join(x for x, ok in (("Cloudflare Clef", _present("CLOUDFLARE_API_KEY") and _present("CLOUDFLARE_ACCOUNT_ID")), ("the Muapi judge", _present("MUAPI_API_KEY"))) if ok) + ")"
                  if (_present("CLOUDFLARE_API_KEY") and _present("CLOUDFLARE_ACCOUNT_ID")) or _present("MUAPI_API_KEY") else "semantic QA is off: stills and scripts ship unchecked", "")]


def checks_safety() -> list[Check]:
    why = safety.paused()
    spent, cap = ledger.usd_total(), safety.ceiling()
    lvl = FAIL if spent >= cap else WARN if spent >= 0.8 * cap else OK
    return [Check("kill switch", FAIL if why else OK, f"PAUSED: {why}" if why else "running", "`python -m faceless pause --resume` once the reason is dealt with" if why else ""),
            Check("spend today", lvl, f"${spent:.2f} of the ${cap:.2f} ceiling", "raise [safety] daily_usd_ceiling only with the owner's yes" if lvl != OK else "")]


def checks_wallet() -> list[Check]:
    from faceless import muapi
    if not muapi.available():
        return [Check("muapi wallet", WARN, "no MUAPI_API_KEY: images use the free tier, then OpenRouter", "")]
    bal = muapi.balance()
    if bal is None:
        return [Check("muapi wallet", WARN, "the balance call failed (network or key)", "run `python -m faceless muapi doctor`")]
    per_day = float(config.load()["images"].get("muapi_daily_usd", 1.5)) * 0.25        # real use is a fraction of the cap; the forecast measures it
    days = bal / per_day if per_day else 999
    lvl = FAIL if bal < 1 else WARN if days < 21 else OK
    return [Check("muapi wallet", lvl, f"${bal:.2f} (about {days:.0f} days at ${per_day:.2f} a day)", "the owner tops up at muapi.ai: say so in the report" if lvl != OK else "")]


def checks_quota() -> list[Check]:
    cfg = config.load()["images"]
    used, cap = ledger.used("cloudflare", "neurons"), cfg["cloudflare_daily_neurons"]
    blocked = ledger.used("cloudflare", "blocked")
    return [Check("cloudflare free pool", WARN if blocked or used > cap else OK, f"{used:.0f} of {cap} neurons used today; {cfg.get('cloudflare_qa_reserve', 0)} are reserved for QA" + ("; Cloudflare said stop" if blocked else ""), "")]


def checks_machine() -> list[Check]:
    out = []
    for label, path in (("repo", STUDIO), ("temp", "/tmp")):   # nosec B108 - only asks how much space is free
        free = shutil.disk_usage(path).free / 2**30
        out.append(Check(f"disk:{label}", FAIL if free < 1.5 else WARN if free < 4 else OK, f"{free:.1f} GB free", "delete production/output and production/cache for old days" if free < 4 else ""))
    git = STUDIO / ".git"
    stuck = [n for n in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD") if (git / n).exists()] if git.exists() else []
    out.append(Check("git state", FAIL if stuck else OK, f"unfinished operation: {stuck}" if stuck else "clean of half-done merges and rebases", "finish or abort it (`git rebase --abort`) before producing anything" if stuck else ""))
    return out


def _bad_lines(path) -> int:
    bad = 0
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    json.loads(line)
                except ValueError:
                    bad += 1
    return bad


def checks_state() -> list[Check]:
    out = []
    for path in (Paths.state / "journal.jsonl", Paths.state / "ledger.jsonl", Paths.state / "offers.jsonl"):
        if path.exists() and re.search(r"^(<{7}|={7}|>{7})", path.read_text(encoding="utf-8", errors="replace"), re.M):
            out.append(Check(f"state:{path.name}", FAIL, "merge conflict markers", "union-merge both sides, sorted by timestamp, and keep every line"))
            continue
        bad = _bad_lines(path)
        out.append(Check(f"state:{path.name}", WARN if bad else OK, f"{bad} unreadable line(s), skipped" if bad else "every line parses", "" if not bad else "readers skip them; find the writer that broke atomicity"))
    from faceless.state import scan_jobs
    _, damaged = scan_jobs()
    out.append(Check("state:jobs", FAIL if damaged else OK, f"unreadable job file(s): {damaged[:5]}" if damaged else "every job file parses",
                     "restore each from git (`git checkout -- state/jobs/<file>`); the other jobs run on without it" if damaged else ""))
    out += checks_offer()
    return out


def checks_offer() -> list[Check]:
    """Does every passed video of today carry an offer, and is there a hub page to send people to? Warnings only: an offer never blocks a video."""
    from faceless import offer
    out = []
    hub = offer.hub_url()
    out.append(Check("offer:hub", OK if hub else WARN, hub or "[site] base_url is empty", "" if hub else "set the site address in studio.toml: every video's call to action points at the hub page"))
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        missing = offer.unoffered(today)
    except Exception as e:   # noqa: BLE001 - a broken job file must not stop the traffic lights
        return out + [Check("offer:coverage", WARN, f"could not read today's jobs ({type(e).__name__})", "")]
    out.append(Check("offer:coverage", WARN if missing else OK, f"{len(missing)} passed video(s) today have no offer" if missing else "every passed video today has an offer",
                     "`python -m faceless offer --batch today` writes the missing packs and ledger rows" if missing else ""))
    return out


def last_daily() -> tuple[str, float] | None:
    days = sorted(p.stem.replace("daily-", "") for p in Paths.reports.glob("daily-*.md"))
    if not days:
        return None
    try:
        dt = datetime.strptime(days[-1], "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)      # the routine finishes around 10:00 UTC
    except ValueError:
        return None
    return days[-1], (datetime.now(timezone.utc) - dt).total_seconds() / 3600


def checks_freshness() -> list[Check]:
    ld = last_daily()
    if not ld:
        return [Check("last daily batch", WARN, "no daily report yet", "")]
    day, hours = ld
    lvl = FAIL if hours > 72 else WARN if hours > 36 else OK
    out = [Check("last daily batch", lvl, f"report for {day}, about {max(0, hours):.0f} h ago", "the routine may have stopped: check its last session" if lvl != OK else "")]
    ideas = {p.id: len(list(Paths.ideas.glob(f"{p.id}*.json"))) + len(list(Paths.ideas.glob(f"{p.id}/*.json"))) for p in config.load()["pillars"]} if Paths.ideas.exists() else {}
    out.append(Check("backlog", OK, f"idea files per pillar: {ideas or 'topics come from the live scout'}", ""))
    return out


def checks_assets() -> list[Check]:
    from faceless import musiclib, policy, skilllint
    n = len(musiclib.tracks())
    out = [Check("music library", OK if n >= 6 else WARN, f"{n} tracks", "" if n >= 6 else "`python -m faceless music --build` (free, about 90 s a track)")]
    late = policy.stale()
    out.append(Check("policy watch", WARN if late else OK, f"{len(late)} rule page(s) unread or older than 14 days" if late else "all rule pages current", "weekly session: fetch them through Exa and `policy --record`" if late else ""))
    res = skilllint.lint_all()
    bad = skilllint.failures(res)
    out.append(Check("skills", FAIL if bad else OK, f"{bad} skill problem(s)" if bad else f"{len(res)} skills lint clean", "`python -m faceless skills` lists them" if bad else ""))
    return out


def tracked_text_files() -> list:
    try:
        r = subprocess.run(["git", "ls-files", "-z"], cwd=STUDIO, capture_output=True, check=False, timeout=60)
    except subprocess.TimeoutExpired:
        return []
    names = [n for n in r.stdout.decode("utf-8", "replace").split("\0") if n]
    skip = {".png", ".jpg", ".jpeg", ".gif", ".mp3", ".mp4", ".wav", ".zip", ".pdf", ".xlsx", ".ttf", ".db", ".woff2", ".ico"}
    return [STUDIO / n for n in names if (STUDIO / n).suffix.lower() not in skip and (STUDIO / n).is_file() and (STUDIO / n).stat().st_size < 3_000_000]


def leaked_secrets() -> list[str]:
    """Tracked files that contain the VALUE of a secret from this environment. Names of files only; never the secret."""
    import os
    values = [v for n, v in os.environ.items() if v and len(v) >= 16 and config._SECRET_NAME.search(n) and not v.startswith(("/", "http"))]
    if not values:
        return []
    hits = []
    for f in tracked_text_files():
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(v in text for v in values):
            hits.append(str(f.relative_to(STUDIO)))
    return hits


def checks_secrets() -> list[Check]:
    hits = leaked_secrets()
    return [Check("secrets in git", FAIL if hits else OK, f"a live secret's value appears in: {hits[:5]}" if hits else "no value from this environment's keys appears in a tracked file",
                  "remove it, rotate the key (it is in git history), and tell the owner" if hits else "")]


GROUPS = [checks_config, checks_tools, checks_keys, checks_safety, checks_machine, checks_state, checks_freshness, checks_assets, checks_secrets, checks_quota]


def run(wallet: bool = True) -> list[Check]:
    out: list[Check] = []
    for g in GROUPS:
        try:
            out += g()
        except Exception as e:  # noqa: BLE001 - a check that crashes is itself a finding, never a crash
            out.append(Check(g.__name__.replace("checks_", ""), WARN, f"the check failed to run: {type(e).__name__}: {str(e)[:80]}"))
    if wallet:
        try:
            out += checks_wallet()
        except Exception as e:  # noqa: BLE001
            out.append(Check("muapi wallet", WARN, f"the check failed to run: {type(e).__name__}"))
    return out


# Failures that make a production run impossible or unsafe. Everything else is advice: a stale report, a leaked-secret hit, broken skills or a spent
# ceiling must be reported, but must not stop today's videos (the free providers still work, and a stalled batch is what the watchdog exists to catch).
BLOCKING = {"config", "ffmpeg", "ffprobe", "python:PIL", "python:numpy", "python:cv2", "python:requests", "fonts", "git state", "disk:repo", "disk:temp"}


def gate() -> list[Check]:
    """The blocking failures, from only the checks that can block (fast: no network, no repo scan). `daily` and `make` refuse to start while any exist."""
    out: list[Check] = []
    for g in (checks_config, checks_tools, checks_machine):
        try:
            out += g()
        except Exception as e:  # noqa: BLE001 - a check that cannot run must not stop production by itself
            out.append(Check(g.__name__.replace("checks_", ""), WARN, f"the check failed to run: {type(e).__name__}: {str(e)[:80]}"))
    return [c for c in out if c.level == FAIL and c.name in BLOCKING]


def exit_code(checks: list[Check], strict: bool = False) -> int:
    if any(c.level == FAIL for c in checks):
        return 1
    return 2 if strict and any(c.level == WARN for c in checks) else 0


def report(checks: list[Check]) -> str:
    mark = {OK: "ok  ", WARN: "WARN", FAIL: "FAIL"}
    lines = [f"Preflight {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}"]
    for c in checks:
        lines.append(f"  {mark[c.level]} {c.name}: {c.detail}")
        if c.fix and c.level != OK:
            lines.append(f"       fix: {c.fix}")
    n = {lv: sum(c.level == lv for c in checks) for lv in (OK, WARN, FAIL)}
    lines.append(f"\n{n[OK]} ok, {n[WARN]} warn, {n[FAIL]} fail")
    return "\n".join(lines)
