"""Serve the command center to the owner's phone over Wi-Fi or Tailscale. No USB, no adb, no shell on the phone.

    python -m faceless serve --init-token      # once: makes QM_DASH_TOKEN and saves it in ~/.config/quiet-money/env (never printed)
    python -m faceless serve                   # binds this machine's LAN address on port 8787 and prints the address and a QR code
    python -m faceless serve --host 127.0.0.1  # behind `tailscale serve 8787` (HTTPS and identity from Tailscale, no open port)

What the server does and does not do:
  * Reads are GET. `/` is the head-up display (`faceless/hud.py`), which polls `/instruments.json` (`faceless/instruments.py`: crew,
    limits, keys, spend, feed) every five seconds; `/desk` is the action desk (`faceless/dashboard.py`, the page with the buttons) and
    `/overview.json` its data, computed from the repo on request (cached for a few seconds). All refused with 401 without the token.
    The overview takes many seconds to build, so the instrument's slow lane is refreshed by a background thread and never by a poll. `/actions.json` is what the action desk is running and the newest clicks from the journal;
    `/job.json?id=` is one job's own history and gauntlet report. The manifest, the two icons and the service worker hold no state and
    need no token, because a browser fetches them without one. `/healthz` answers "ok" and nothing else.
  * One write door: `POST /action` with `{"name": ..., "args": {...}}`. The name must be on the allowlist in `faceless/actions.py`, each
    of which runs one existing `python -m faceless ...` or `herdr ...` command; nothing else can be run from the page. The token must
    come in the Authorization header (never the query), the body must be JSON, and a request from another origin is refused, so a link
    or a form on some other page cannot press a button. `{"name": "nonstop_tick"}` is the open page asking whether the phone lane
    should be advanced (Non-stop). Every other method, and POST anywhere else, is 405.
  * The token comes in as `?t=` on the first visit (that is what the QR code carries), is kept by the page in the browser's own storage,
    and is sent as an Authorization header afterwards. No cookie is ever set.
  * Every reply carries `Cache-Control: no-store` and `X-Robots-Tag: noindex`. Requests are counted per address: too many, or a run of
    wrong tokens, gets 429.
  * It binds the LAN address by default, not every interface, and refuses to start without a token of at least 16 characters.
  * The server itself still writes nothing: not a job, not the ledger, not even its own overview file. State changes only because an
    action's command ran, and each click is one line in the journal (`CC_ACTION`). The kill switch (`state/PAUSE`) refuses every
    action that moves the pipeline.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import socket
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from faceless import config

ENV_FILE = Path.home() / ".config" / "quiet-money" / "env"
TOKEN_NAME = "QM_DASH_TOKEN"
DEFAULT_PORT = 8787
MIN_TOKEN = 16
CACHE_SECONDS = 15
RATE_PER_MINUTE = 120
BAD_TOKENS_PER_MINUTE = 10
PUBLIC = ("manifest.webmanifest", "sw.js", "icon-192.png", "icon-512.png")
HEADERS = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive", "X-Content-Type-Options": "nosniff",
           "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
           "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self'; connect-src 'self'; "
                                      "manifest-src 'self'; worker-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"}
# What an address without the token gets: no state, and a way back in for a phone that already holds the token (a launch from the home screen).
DENIED = ("<!doctype html><meta charset=utf-8><meta name=robots content=noindex><meta name=viewport content='width=device-width,initial-scale=1'>"
          "<title>401</title><body style='background:#0e0f11;color:#9aa0a8;font:16px sans-serif;padding:24px'>401. This page needs its token. "
          "Scan the QR code shown by <code>python -m faceless serve</code>."
          "<script>try{var t=localStorage.getItem('qm_t');if(t&&!/[?&]t=/.test(location.search)&&!sessionStorage.getItem('qm_r')){sessionStorage.setItem('qm_r','1');"
          "location.replace(location.pathname+'?t='+encodeURIComponent(t))}}catch(e){}</script>")


def token() -> str | None:
    """The dashboard token from the environment, else from ~/.config/quiet-money/env. Never printed, never written anywhere else."""
    if not os.environ.get(TOKEN_NAME):
        config.load_dotenv(ENV_FILE)
    return os.environ.get(TOKEN_NAME) or None


def init_token(path: Path | None = None) -> str:
    """Make a token once and save it with owner-only permissions. Returns what happened, not the token."""
    path = Path(path or ENV_FILE)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    if any(line.strip().removeprefix("export ").startswith(TOKEN_NAME + "=") for line in text.splitlines()):
        return f"{TOKEN_NAME} is already in {path}; left as it is"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(("" if not text or text.endswith("\n") else "\n") + f"{TOKEN_NAME}={secrets.token_urlsafe(24)}\n")
    os.chmod(path, 0o600)
    return f"saved a new {TOKEN_NAME} in {path} (owner-only file; the value is not shown)"


def lan_ip() -> str | None:
    """This machine's address on the local network. Opens a UDP socket toward a private address to learn the route; sends nothing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = None
    finally:
        s.close()
    return ip if ip and not ip.startswith("127.") else None


class Limiter:
    """Requests per address in the last minute; a separate, smaller count for wrong tokens."""

    def __init__(self, per_minute: int = RATE_PER_MINUTE, bad_per_minute: int = BAD_TOKENS_PER_MINUTE, clock=time.monotonic):
        self.per_minute, self.bad_per_minute, self.clock = per_minute, bad_per_minute, clock
        self.hits: dict[str, list[float]] = {}
        self.bad: dict[str, list[float]] = {}
        self.lock = threading.Lock()

    def _count(self, book: dict, ip: str, add: bool) -> int:
        now = self.clock()
        with self.lock:
            if len(book) > 2048:                             # a scan from many addresses must not grow this without bound
                book.clear()
            recent = [t for t in book.get(ip, []) if now - t < 60]
            if add:
                recent.append(now)
            book[ip] = recent
            return len(recent)

    def allow(self, ip: str) -> bool:
        return self._count(self.bad, ip, False) < self.bad_per_minute and self._count(self.hits, ip, True) <= self.per_minute

    def wrong(self, ip: str) -> None:
        self._count(self.bad, ip, True)


class Source:
    """The overview and the page, rebuilt from the repo at most every few seconds. Reads only."""

    def __init__(self, build=None, seconds: float = CACHE_SECONDS):
        self.build, self.seconds, self.at, self.doc, self.lock = build, seconds, 0.0, None, threading.Lock()

    def get(self) -> dict:
        with self.lock:
            if self.doc is None or time.monotonic() - self.at > self.seconds:
                if self.build is None:
                    from faceless import overview
                    self.build = overview.build
                self.doc, self.at = self.build(), time.monotonic()
            return self.doc

    def expire(self) -> None:
        """An action just changed the repo: the next request rebuilds instead of showing the cached copy."""
        with self.lock:
            self.at = 0.0


class Panel:
    """The instrument snapshot for the head-up display. The fast lane is rebuilt at most every few seconds; the slow lane (the
    overview) and key health are refreshed in one background thread, so a five-second poll never waits on a twenty-second build."""

    def __init__(self, source: Source, build=None, slow_seconds: float = 12.0, seconds: float = 3.0, background: bool = True):
        self.source, self.build, self.slow_seconds, self.seconds, self.background = source, build, slow_seconds, seconds, background
        self.started = time.time()
        self.slow, self.slow_at, self.busy, self.snap, self.snap_at, self.lock = None, 0.0, False, None, 0.0, threading.Lock()

    def refresh(self) -> None:
        from faceless import instruments
        try:
            self.slow = instruments.save_slow(self.source.get())
            instruments.keyhealth(refresh="stale")
        except Exception as e:   # noqa: BLE001 - the panel keeps its last slow lane and says how old it is
            print(f"instrument slow lane failed: {type(e).__name__}", flush=True)
        finally:
            self.slow_at, self.busy = time.monotonic(), False

    def expire(self) -> None:
        """An action just ran: the next poll rebuilds the snapshot and refreshes the slow lane."""
        with self.lock:
            self.snap_at, self.slow_at = 0.0, 0.0

    def get(self) -> dict:
        from faceless import instruments
        with self.lock:
            if not self.busy and (self.slow is None or time.monotonic() - self.slow_at > self.slow_seconds):
                self.busy = True
                if self.background:
                    threading.Thread(target=self.refresh, daemon=True).start()
                else:
                    self.refresh()
            if self.snap is None or time.monotonic() - self.snap_at > self.seconds:
                started = datetime.fromtimestamp(self.started, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                build = self.build or instruments.build
                self.snap, self.snap_at = build(self.slow, server={"state": "up", "startedAt": started}), time.monotonic()
            return self.snap


MAX_BODY = 4096


def make_handler(tok: str, source: Source, limiter: Limiter, static: dict, models_source: Source | None = None, desk=None, panel: Panel | None = None):
    from faceless import actions, dashboard, hud
    if desk is None:
        desk = actions.Desk(on_done=lambda result: (source.expire(), panel.expire()))
    if panel is None:
        panel = Panel(source)

    class Handler(BaseHTTPRequestHandler):
        server_version, sys_version, protocol_version = "qm-cc", "", "HTTP/1.1"

        def log_message(self, fmt, *args):                   # one line per request, with the query (the token) left out
            print(f"{self.address_string()} {self.command} {urlsplit(self.path).path} {args[1] if len(args) > 1 else ''}", flush=True)

        def reply(self, code: int, ctype: str, body: bytes, head: bool = False) -> None:
            self.send_response(code)
            for k, v in HEADERS.items():
                self.send_header(k, v)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            if code == 401:
                self.send_header("WWW-Authenticate", "Bearer")
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def authed(self, url) -> bool:
            given = (parse_qs(url.query).get("t") or [""])[0]
            header = self.headers.get("Authorization") or ""
            if header.lower().startswith("bearer "):
                given = header[7:].strip() or given
            return bool(given) and hmac.compare_digest(given.encode("utf-8"), tok.encode("utf-8"))

        def serve(self, head: bool) -> None:
            ip = self.client_address[0]
            url = urlsplit(self.path)
            path = url.path.lstrip("/")
            if path == "healthz":
                return self.reply(200, "text/plain; charset=utf-8", b"ok\n", head)
            if not limiter.allow(ip):
                return self.reply(429, "text/plain; charset=utf-8", b"too many requests; wait a minute\n", head)
            if path in static:
                return self.reply(200, static[path][0], static[path][1], head)
            if path not in ("", "index.html", "desk", "overview.json", "instruments.json", "models.json", "actions.json", "job.json"):
                return self.reply(404, "text/plain; charset=utf-8", b"not found\n", head)
            if not self.authed(url):
                limiter.wrong(ip)
                return self.reply(401, "text/html; charset=utf-8", DENIED.encode("utf-8"), head)
            try:
                if path in ("", "index.html"):               # the head-up display holds no data of its own; its first poll fills it
                    return self.reply(200, "text/html; charset=utf-8", hud.render().encode("utf-8"), head)
                if path == "instruments.json":
                    return self.json(200, panel.get(), head)
                if path == "models.json":
                    if models_source is None:
                        from faceless import models
                        doc = models.catalog()
                    else:
                        doc = models_source.get()
                    return self.reply(200, "application/json; charset=utf-8", json.dumps(doc, ensure_ascii=False).encode("utf-8"), head)
                if path == "actions.json":
                    return self.json(200, {**desk.snapshot(), "nonstop": desk.plan(), "actions": actions.catalog()}, head)
                if path == "job.json":
                    from faceless import overview
                    doc = overview.job_detail((parse_qs(url.query).get("id") or [""])[0])
                    return self.json(200 if doc else 404, doc or {"error": "no such job"}, head)
                doc = source.get()
            except Exception as e:   # noqa: BLE001 - the phone gets a plain error, and keeps showing its saved copy
                return self.reply(500, "text/plain; charset=utf-8", f"projection failed: {type(e).__name__}\n".encode(), head)
            if path == "overview.json":
                return self.reply(200, "application/json; charset=utf-8", json.dumps(doc, ensure_ascii=False).encode("utf-8"), head)
            return self.reply(200, "text/html; charset=utf-8", dashboard.render(doc).encode("utf-8"), head)

        def json(self, code: int, doc: dict, head: bool = False) -> None:
            self.reply(code, "application/json; charset=utf-8", json.dumps(doc, ensure_ascii=False).encode("utf-8"), head)

        def act(self) -> None:
            """The one write door. Header token, JSON body, same origin, an allowlisted name: anything else is refused before it runs."""
            ip = self.client_address[0]
            url = urlsplit(self.path)
            self.close_connection = True                     # a refusal leaves the body unread: never let it be parsed as the next request
            if url.path.lstrip("/") != "action":
                return self.refuse()
            if not limiter.allow(ip):
                return self.reply(429, "text/plain; charset=utf-8", b"too many requests; wait a minute\n")
            header = self.headers.get("Authorization") or ""
            given = header[7:].strip() if header.lower().startswith("bearer ") else ""
            if not given or not hmac.compare_digest(given.encode("utf-8"), tok.encode("utf-8")):
                limiter.wrong(ip)
                return self.json(401, {"error": "this needs the token in the Authorization header"})
            origin = self.headers.get("Origin")
            if origin and urlsplit(origin).netloc != (self.headers.get("Host") or ""):
                return self.json(403, {"error": "actions are accepted from the command center page only"})
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                return self.json(400, {"error": "send a small JSON body: {\"name\": ..., \"args\": {...}}"})
            try:
                raw = self.rfile.read(length)
                self.close_connection = False
                body = json.loads(raw.decode("utf-8"))
                name, args = body["name"], body.get("args") or {}
                if not isinstance(name, str) or not isinstance(args, dict):
                    raise ValueError
            except (ValueError, KeyError, TypeError, UnicodeDecodeError):
                return self.json(400, {"error": "send a small JSON body: {\"name\": ..., \"args\": {...}}"})
            try:
                result = desk.tick() if name == "nonstop_tick" else desk.auto() if name == "autopilot_tick" else desk.start(name, args)
            except Exception as e:   # noqa: BLE001 - the page shows the failure instead of a hung button
                result = {"action": name, "state": "done", "ok": False, "exit": None, "summary": f"the action desk failed: {type(e).__name__}"}
            return self.json(200, result)

        def do_GET(self):   # noqa: N802
            self.serve(False)

        def do_POST(self):   # noqa: N802
            self.act()

        def do_HEAD(self):   # noqa: N802
            self.serve(True)

        def refuse(self):
            self.reply(405, "text/plain; charset=utf-8", b"GET and HEAD read; POST /action is the only write door\n")

        do_PUT = do_DELETE = do_PATCH = do_OPTIONS = refuse   # noqa: N815

    return Handler


def make_server(host: str, port: int, tok: str, build=None, limiter: Limiter | None = None, desk=None, panel: Panel | None = None) -> ThreadingHTTPServer:
    if not tok or len(tok) < MIN_TOKEN:
        raise ValueError(f"{TOKEN_NAME} is missing or shorter than {MIN_TOKEN} characters: run `python -m faceless serve --init-token` once")
    from faceless import dashboard, models
    model_source = Source(build=models.catalog, seconds=60)
    httpd = ThreadingHTTPServer((host, port), make_handler(tok, Source(build), limiter or Limiter(), dashboard.assets(), model_source, desk, panel))
    httpd.daemon_threads = True
    return httpd


def tailscale_note(port: int) -> str:
    return (f"Away from home: `tailscale serve --bg {port}` on this computer (with `serve --host 127.0.0.1`), then open the https://<machine>.<tailnet>.ts.net "
            "address it prints on the phone, adding ?t=<token> once. Details: OPERATIONS.md, \"Command center\".")


def run(host: str | None, port: int = DEFAULT_PORT, show_url: bool = False, invert: bool = False, base_url: str | None = None) -> int:
    from faceless import qr
    tok = token()
    if not tok or len(tok) < MIN_TOKEN:
        print(f"No {TOKEN_NAME} (at least {MIN_TOKEN} characters). Run once: python -m faceless serve --init-token")
        return 2
    host = host or lan_ip()
    if not host:
        print("Could not find a LAN address. On Wi-Fi? Or pass --host 127.0.0.1 and put `tailscale serve` in front.")
        return 2
    if host == "0.0.0.0":   # noqa: S104 - the owner asked for every interface; say what that means
        print("Listening on every interface (0.0.0.0): that includes any VPN or public interface this machine has. The token is the only gate.")
    try:
        httpd = make_server(host, port, tok)
    except OSError as e:
        print(f"Could not listen on {host}:{port}: {e}")
        return 2
    shown = (lan_ip() or host) if host == "0.0.0.0" else host   # noqa: S104
    base = (base_url or f"http://{shown}:{port}").rstrip("/")
    full = f"{base}/?t={tok}"
    print(f"Command center: {base}/   (token required; buttons run allowlisted faceless commands, state/PAUSE stops them)")
    art = None if host.startswith("127.") and not base_url else qr.terminal(full, invert=invert)
    if art:
        print("Scan with the phone's camera (same Wi-Fi, cable unplugged). The code carries the token, so do not screenshot it into a chat:\n")
        print(art)
    elif host.startswith("127."):
        print("Bound to this machine only. Put `tailscale serve` in front, then run again with --base-url https://<machine>.<tailnet>.ts.net for the QR code.")
    if show_url:
        print(f"\nFull address with the token (you asked for it with --show-url): {full}")
    else:
        print("\nThe token is not printed. To type the address by hand, run again with --show-url.")
    print(tailscale_note(port))
    print("Ctrl+C stops it.", flush=True)
    try:
        httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0
