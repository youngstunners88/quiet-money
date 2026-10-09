"""Regression tests from the repository audit: a killed process must not corrupt state, one damaged file must not stop the others, hostile text in a
script must not become markup on the public site, and no network or encoder call may wait forever."""

import ast
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from faceless import fsutil, preflight, site
from faceless.config import Paths
from faceless.pipeline import render
from faceless.state import Job, all_jobs, scan_jobs

SRC = Path(__file__).resolve().parent.parent / "faceless"


@pytest.fixture
def folders(tmp_path, monkeypatch):
    for name in ("jobs", "final", "output", "state", "reports"):
        monkeypatch.setattr(Paths, name, tmp_path / name)
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    return tmp_path


# ------------------------------------------------------------------ files that survive a kill

def test_an_interrupted_write_leaves_the_old_file_whole_and_no_litter(tmp_path, monkeypatch):
    target = tmp_path / "job.json"
    fsutil.write_atomic(target, '{"v": 1}')

    def boom(src, dst):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(KeyboardInterrupt):
        fsutil.write_atomic(target, '{"v": 2}')
    assert json.loads(target.read_text(encoding="utf-8")) == {"v": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["job.json"]


def test_a_saved_job_is_never_matched_by_the_json_glob_while_it_is_being_written(folders):
    job = Job(id="2026-10-09-s0-story-x", pillar="story", topic="x", day="2026-10-09")
    job.save()
    assert [p.name for p in Paths.jobs.glob("*.json")] == [f"{job.id}.json"]
    assert not list(Paths.jobs.glob(".*.tmp"))


def test_one_damaged_job_file_does_not_stop_the_others(folders):
    good = Job(id="2026-10-09-s0-story-ok", pillar="story", topic="ok", day="2026-10-09")
    good.save()
    (Paths.jobs / "2026-10-09-s1-story-cut.json").write_text('{"id": "2026-10-09-s1-story-cut", "pil', encoding="utf-8")
    (Paths.jobs / "2026-10-09-s2-story-new.json").write_text(json.dumps({"id": "x", "pillar": "p", "topic": "t", "day": "d", "future_field": 1}), encoding="utf-8")
    jobs, bad = scan_jobs()
    assert [j.id for j in jobs] == [good.id]
    assert bad == ["2026-10-09-s1-story-cut.json", "2026-10-09-s2-story-new.json"]
    assert [j.id for j in all_jobs()] == [good.id]


def test_preflight_names_a_damaged_job_file(folders):
    (Paths.jobs / "2026-10-09-s1-story-cut.json").write_text("{", encoding="utf-8")
    check = next(c for c in preflight.checks_state() if c.name == "state:jobs")
    assert check.level == preflight.FAIL and "2026-10-09-s1-story-cut.json" in check.detail
    (Paths.jobs / "2026-10-09-s1-story-cut.json").unlink()
    assert next(c for c in preflight.checks_state() if c.name == "state:jobs").level == preflight.OK


def test_the_site_skips_a_video_whose_script_file_is_cut_off(folders):
    for n, body in (("a", json.dumps({"title": "Rule A", "beats": []})), ("b", '{"title": "Rule B", "be')):
        job = Job(id=f"2026-10-09-s0-story-{n}", pillar="story", topic=n, day="2026-10-09", status="published")
        job.save()
        (Paths.final / f"{job.id}.json").write_text(body, encoding="utf-8")
    assert [r["title"] for r in site.published_rules()] == ["Rule A"]


# ------------------------------------------------------------------ hostile text on the public site

HOSTILE = '</title><script>window.pwned=1</script><img src=x onerror=window.pwned=2>"\'><svg onload=window.pwned=3>'


class Scan(HTMLParser):
    """Collects what could run: script blocks, event-handler attributes, and javascript: URLs."""

    def __init__(self):
        super().__init__()
        self.scripts, self.handlers, self.js_urls, self.tags = [], [], [], []
        self._in = ""

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self._in = (dict(attrs).get("type") or "text/javascript") if tag == "script" else ""
        if tag == "script":
            self.scripts.append(dict(attrs))
        for k, v in attrs:
            if k.startswith("on"):
                self.handlers.append((tag, k))
            if k in ("href", "src", "action") and (v or "").strip().lower().startswith(("javascript:", "data:", "vbscript:")):
                self.js_urls.append((tag, k, v))

    def handle_data(self, data):
        if self._in and self._in != "application/ld+json" and "pwned" in data:   # JSON-LD is data the browser never runs; its brackets are escaped as well
            self.scripts.append({"inline": data})

    def handle_endtag(self, tag):
        if tag == "script":
            self._in = ""


def test_hostile_script_text_cannot_become_markup_on_any_generated_page(folders, monkeypatch):
    out = folders / "site"
    monkeypatch.setattr(site, "SITE", out)
    job = Job(id="2026-10-09-s0-story-hostile", pillar="story", topic=HOSTILE, day="2026-10-09", status="published")
    job.save()
    script = {"title": HOSTILE, "hook_text": HOSTILE, "description": HOSTILE, "hashtags": [HOSTILE],
              "beats": [{"say": HOSTILE, "callout": HOSTILE}], "facts": [{"claim": HOSTILE, "basis": HOSTILE}], "faq": [{"q": HOSTILE, "a": HOSTILE}]}
    (Paths.final / f"{job.id}.json").write_text(json.dumps(script), encoding="utf-8")
    job.dir.mkdir(parents=True, exist_ok=True)
    (job.dir / "meta.json").write_text(json.dumps({"description": HOSTILE}), encoding="utf-8")
    site.build()
    pages = [p for p in out.rglob("*") if p.suffix in (".html", ".xml", ".txt")]
    assert any("hostile" in str(p) for p in pages)
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert "window.pwned=1</script>" not in text and "<img src=x" not in text and "<svg onload" not in text, page
        if page.suffix == ".html":
            scan = Scan()
            scan.feed(text)
            assert not scan.handlers, (page, scan.handlers)
            assert not [u for u in scan.js_urls if u[2] != "javascript:window.print()"], (page, scan.js_urls)
            assert not [s for s in scan.scripts if "inline" in s], page


def test_a_social_link_that_is_not_http_is_dropped_not_printed():
    html = site.social_links({"youtube": "https://youtube.com/@x", "tiktok": "javascript:alert(1)", "x": "data:text/html,hi", "instagram": ""})
    assert "youtube.com/@x" in html and "javascript:" not in html and "data:" not in html and "TikTok" not in html


def test_slugs_cannot_climb_out_of_the_site_folder():
    from faceless.state import slugify
    for evil in ("../../etc/passwd", "..\\..\\x", "a/../../b", "%2e%2e%2f", "\x00../x"):
        slug = slugify(evil, 64)
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug), slug


# ------------------------------------------------------------------ nothing waits forever

def test_every_http_call_has_a_timeout():
    """A request without a timeout can hang a routine until its session limit. Checked on the source, so a new call cannot slip in."""
    bad, seen = [], 0
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("get", "post", "put", "delete", "head", "patch", "request", "urlopen"):
                base = ast.unparse(node.func.value)
                if base == "http()" or base.endswith(".http()") or base in ("requests", "urllib.request"):
                    seen += 1
                    if "timeout" not in {k.arg for k in node.keywords}:
                        bad.append(f"{path.relative_to(SRC.parent)}:{node.lineno}")
    assert seen >= 25 and not bad, bad


def test_every_ffmpeg_and_probe_call_has_a_timeout():
    """Encoders, probes, git and the CI mirror's steps. (The one streaming encoder, render_shot, is guarded by a kill timer instead; see below.)"""
    bad = []
    for path in SRC.rglob("*.py"):
        rel = str(path.relative_to(SRC.parent))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and ast.unparse(node.func.value) == "subprocess" and node.func.attr in ("run", "check_output", "call", "check_call"):
                if "timeout" not in {k.arg for k in node.keywords}:
                    bad.append(f"{rel}:{node.lineno}")
    assert not bad, bad


def test_a_hung_encoder_fails_the_render_instead_of_stalling_it(monkeypatch):
    def hang(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(render.subprocess, "run", hang)
    with pytest.raises(RuntimeError, match="timed out"):
        render._run(["ffmpeg", "-i", "in.mp4", "out.mp4"])


def test_the_raw_video_pipe_is_killed_when_the_encoder_stalls(tmp_path, monkeypatch):
    """A stalled ffmpeg stops reading its stdin, so the next write blocks forever; the guard kills it and the write fails."""
    pytest.importorskip("PIL")
    from PIL import Image
    img = tmp_path / "in.png"
    Image.new("RGB", (64, 64), "gold").save(img)
    monkeypatch.setattr(render, "ENCODE_TIMEOUT", 0.2)
    real_popen = subprocess.Popen

    def stalled(cmd, **kw):                      # a process that never reads its input
        return real_popen([sys.executable, "-c", "import time; time.sleep(30)"], stdin=subprocess.PIPE)

    monkeypatch.setattr(render.subprocess, "Popen", stalled)
    args = (str(img), str(tmp_path / "out.mp4"), 4000, render.HOOK, 1080, 1920, 30, "null")
    with pytest.raises(RuntimeError, match="shot encode failed"):
        render.render_shot(args)


# ------------------------------------------------------------------ the renderer's supply chain

class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeSession:
    def __init__(self, content):
        self.content, self.urls = content, []

    def get(self, url, **kw):
        assert kw.get("timeout")
        self.urls.append(url)
        return FakeResponse(self.content)


def test_a_tampered_gsap_copy_is_refused_and_never_reaches_the_renderer(tmp_path, monkeypatch):
    from faceless import providers
    from faceless.pipeline import cards
    monkeypatch.setattr(Paths, "cache", tmp_path / "cache")
    monkeypatch.setattr(providers, "http", lambda: FakeSession(b"window.steal=1"))
    with pytest.raises(RuntimeError, match="pinned hash"):
        cards.ensure_gsap(tmp_path / "project")
    assert not (tmp_path / "cache" / "gsap-3.14.2.min.js").exists() and not (tmp_path / "project" / cards.LOCAL_GSAP).exists()


def test_a_copy_with_the_pinned_hash_is_cached_and_placed_in_the_project(tmp_path, monkeypatch):
    from faceless.pipeline import cards
    body = b"/* stand-in for gsap */"
    monkeypatch.setattr(cards, "GSAP_SRI", cards.gsap_digest(body))
    monkeypatch.setattr(Paths, "cache", tmp_path / "cache")
    from faceless import providers
    session = FakeSession(body)
    monkeypatch.setattr(providers, "http", lambda: session)
    cards.ensure_gsap(tmp_path / "p1")
    cards.ensure_gsap(tmp_path / "p2")                               # the second project comes from the cache
    assert (tmp_path / "p1" / cards.LOCAL_GSAP).read_bytes() == body == (tmp_path / "p2" / cards.LOCAL_GSAP).read_bytes()
    assert len(session.urls) == 1
    (tmp_path / "cache" / "gsap-3.14.2.min.js").write_bytes(b"corrupted in the cache")   # a damaged cache file is replaced, not trusted
    cards.ensure_gsap(tmp_path / "p3")
    assert (tmp_path / "p3" / cards.LOCAL_GSAP).read_bytes() == body and len(session.urls) == 2


def test_the_project_page_loads_the_verified_local_copy_not_the_cdn():
    from faceless.pipeline import cards
    import inspect
    src = inspect.getsource(cards.build_project)
    assert "{LOCAL_GSAP}" in src and "{GSAP}" not in src


def test_third_party_npm_code_gets_no_key_token_or_secret(monkeypatch):
    from faceless.pipeline import cards
    for name in ("OPENROUTER_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "GITHUB_TOKEN", "UPLOAD_POST_USER_PASSWORD", "CLAUDE_CODE_OAUTH_TOKEN", "SOME_SECRET", "AWS_SESSION_ID"):
        monkeypatch.setenv(name, "leak")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:3128")
    env = cards.renderer_env()
    assert "leak" not in env.values()
    assert env["HTTPS_PROXY"] == "http://proxy.example:3128" and "PATH" in env and env["HYPERFRAMES_NO_TELEMETRY"] == "1"


def test_a_failed_gsap_check_leaves_the_still_images_in_place(tmp_path, monkeypatch):
    """Cards are optional: when the check fails the reel is None and the caller keeps the stills."""
    from faceless.pipeline import cards
    monkeypatch.setattr(cards, "ensure_gsap", lambda root: (_ for _ in ()).throw(RuntimeError("no match")))
    ran = []
    monkeypatch.setattr(cards.subprocess, "run", lambda *a, **k: ran.append(a))
    monkeypatch.setattr(cards, "build_project", lambda *a, **k: 3.0)
    job = Job(id="2026-10-09-s0-math-x", pillar="math", topic="x", day="2026-10-09")
    monkeypatch.setattr(Paths, "output", tmp_path)
    assert cards.render_reel(job, {0: {"kind": "number"}}, {0: (0.0, 3.0)}, "math", "#ffd23f", 30) is None and not ran


# ------------------------------------------------------------------ nothing secret reaches the public journal

def _fake(*parts):
    """A key-shaped test value built from pieces, so no line of this file has the shape of a real key (the repository scan would rightly flag it)."""
    return "".join(parts)


@pytest.mark.parametrize("leak", [
    _fake("s", "k-or-v1-", "0123456789abcdef0123456789abcdef"),
    _fake("AI", "za", "A" * 35),
    _fake("gh", "p_", "a1B2" * 9),
    _fake("github", "_pat_", "x1Y2" * 12),
    _fake("xo", "xb-", "1234567890-abcdefghij"),
    _fake("AK", "IA", "ABCDEFGHIJKLMNOP"),
    _fake("ey", "JhbGciOiJIUzI1NiJ9.", "ey", "JzdWIiOiIxMjM0NTY3ODkwIn0.", "abcdefgh12345"),
    _fake("Bea", "rer ", "abcdefghijklmnopqrstuvwxyz0123456789"),
    _fake("Api", "key ", "0123456789abcdef0123456789abcdef"),
])
def test_a_key_shaped_string_is_scrubbed_even_when_it_is_not_in_the_environment(leak):
    from faceless.config import redact
    line = json.dumps({"error": f"401 from vendor: invalid credential {leak} rejected", "job": "2026-10-09-s0-playbook-ask-your-bank-to-waive-a-fee"})
    out = redact(line)
    assert leak not in out and "[redacted]" in out
    assert "ask-your-bank-to-waive-a-fee" in out                       # a slug that merely contains "sk-" is not a key


def test_a_private_key_block_is_scrubbed_and_the_line_stays_valid_json():
    from faceless.config import redact
    pem = _fake("-----BEGIN ", "PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END ", "PRIVATE KEY-----\n")
    out = redact(json.dumps({"error": pem, "after": "kept"}))
    assert "MIIEvQ" not in out and json.loads(out)["after"] == "kept"


def test_ordinary_journal_lines_pass_through_untouched():
    from faceless.config import redact
    line = json.dumps({"type": "JOB_TRANSITION", "job": "2026-10-09-s3-math-the-15-a-month-trap", "to": "voiced", "cost": 0.0021, "url": "https://example.com/rules/x/?utm_source=hub"})
    assert redact(line) == line


# ------------------------------------------------------------------ addresses and names that come back from a vendor

class _Stream:
    def __init__(self, size, declared=None, status=200):
        self.status_code, self.size = status, size
        self.headers = {"content-type": "image/png", **({"content-length": str(declared)} if declared is not None else {})}
        self.closed = False

    def iter_content(self, n):
        sent = 0
        while sent < self.size:
            step = min(n, self.size - sent)
            sent += step
            yield b"x" * step

    def close(self):
        self.closed = True


class _Session:
    def __init__(self, resp):
        self.resp, self.seen = resp, []

    def get(self, url, **kw):
        self.seen.append((url, kw))
        return self.resp


def test_a_vendor_result_url_must_be_https():
    from faceless.providers import ProviderError, fetch_bytes
    session = _Session(_Stream(10))
    for url in ("http://cdn.example/a.png", "file:///etc/passwd", "ftp://x/y", "//cdn.example/a.png"):
        with pytest.raises(ProviderError, match="non-https"):
            fetch_bytes(url, session=session)
    assert not session.seen                                       # nothing was requested


def test_a_download_over_the_limit_is_refused_by_header_or_by_counting():
    from faceless.providers import ProviderError, fetch_bytes
    with pytest.raises(ProviderError, match="over the 1 MB limit"):
        fetch_bytes("https://cdn.example/a.mp4", session=_Session(_Stream(10, declared=5 * 2**20)), limit=2**20)
    liar = _Stream(5 * 2**20, declared=10)                        # says it is small, is not
    with pytest.raises(ProviderError, match="over the 1 MB limit"):
        fetch_bytes("https://cdn.example/a.mp4", session=_Session(liar), limit=2**20)
    assert liar.closed
    body, ctype = fetch_bytes("https://cdn.example/a.png", session=_Session(_Stream(1000, declared=1000)), limit=2**20)
    assert len(body) == 1000 and ctype == "image/png"


def test_a_failed_status_is_an_error_not_an_empty_file():
    from faceless.providers import ProviderError, fetch_bytes
    with pytest.raises(ProviderError, match="HTTP 404"):
        fetch_bytes("https://cdn.example/a.png", session=_Session(_Stream(0, status=404)))


def test_a_request_id_or_label_cannot_steer_where_a_file_is_written():
    from faceless import muapi
    for evil in ("../../etc/cron.d/x", "..\\..\\x", "a/b/c/d/e/f", "\x00\x01", "%2e%2e%2f"):
        part = muapi._part(evil)
        assert re.fullmatch(r"[A-Za-z0-9_-]+", part), part
    assert muapi._part("") == "x" and muapi._part("abcdef123456") == "abcdef12"


def test_every_vendor_url_download_goes_through_the_bounded_helper():
    """No `.get(url).content` on an address a vendor sent: it would read an unbounded body and accept plain http."""
    offenders = []
    for path in SRC.rglob("*.py"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.get\([^)]*outputs[^)]*\)\.content|\.get\(url[^)]*\)\.content", line):
                offenders.append(f"{path.relative_to(SRC.parent)}:{n}")
    assert not offenders, offenders


def test_tracking_tags_go_before_a_fragment_not_after_it():
    from faceless import offer
    assert offer.tracked("https://shop.example/l/abc#reviews", "quietmoney", "hub", "planner") == "https://shop.example/l/abc?utm_source=quietmoney&utm_medium=hub&utm_campaign=planner#reviews"
    assert offer.tracked("https://shop.example/l/abc?ref=1#x", "a", "b", "c", focus="planner").startswith("https://shop.example/l/abc?ref=1&utm_source=a")
    assert offer.tracked("../tools/", "hub", "link", "tools") == "../tools/?utm_source=hub&utm_medium=link&utm_campaign=tools"
    assert offer.tracked("", "a", "b", "c") == ""


# ------------------------------------------------------------------ logs that are read by everything

def test_a_damaged_line_in_the_spend_ledger_does_not_stop_the_money_checks(tmp_path, monkeypatch):
    from faceless import ledger
    log = tmp_path / "ledger.jsonl"
    day = ledger.today()
    good = json.dumps({"day": day, "provider": "openrouter", "unit": "usd", "amount": 0.5, "usd": 0.5, "job": None})
    log.write_bytes((good + "\n" + '{"day": "2026-10-09", "prov' + "\n" + "42\n" + "[1, 2]\n" + '"text"\n'
                     + json.dumps({"day": day, "provider": "openrouter", "unit": "usd", "amount": "oops", "usd": None}) + "\n"
                     + json.dumps({"day": day}) + "\n").encode() + b"\xff\xfe broken bytes\n" + (good + "\n").encode())
    monkeypatch.setattr(ledger, "LEDGER", log)
    assert ledger.used("openrouter", "usd") == 1.0
    assert ledger.usd_total() == 1.0
    assert ledger.allow("openrouter", "usd", 0.4, 1.5) and not ledger.allow("openrouter", "usd", 0.6, 1.5)
    assert ledger.summary()["openrouter:usd"] == 1.0


def test_the_journal_reader_skips_what_is_not_an_event(tmp_path):
    from faceless import events
    log = tmp_path / "journal.jsonl"
    log.write_bytes(b'{"type": "A"}\n7\nnot json\n[]\n\xc3\n{"type": "B"}\n')
    assert [e["type"] for e in events.read(log)] == ["A", "B"] and [e["type"] for e in events.read(log, kind="B")] == ["B"]


def test_one_bad_sales_line_does_not_stop_recording_new_sales(tmp_path, monkeypatch):
    from faceless import shop
    sales = tmp_path / "sales.jsonl"
    sales.write_text('{"id": "s1"}\nnot json\n[1]\n', encoding="utf-8")
    monkeypatch.setattr(shop, "SALES", sales)
    assert fsutil.read_jsonl(shop.SALES) == [{"id": "s1"}]


# ------------------------------------------------------------------ the model-designed scene gate

HOSTILE_VALUES = [
    '"><script>window.pwned=1</script>', "</text><script>window.pwned=2</script>", "javascript:alert(1)", "url(javascript:alert(1))", "x\" onload=\"window.pwned=3",
    "#fff\" onmouseover=\"window.pwned=4", "M0 0 L1 1\" onclick=\"x", "power2.out\nwindow.pwned=5", "'; window.pwned=6; '", "{{7*7}}", "${window.pwned}",
    " window.pwned=7", "<svg onload=window.pwned=8>", "a" * 5000, -1e9, 1e9, float("nan"), None, [], {}, True, "", "../../x", "__proto__", "constructor",
]


def test_no_hostile_value_in_any_field_gets_through_the_scene_gate_as_markup():
    import copy
    import random
    from faceless.pipeline import sketch
    from tests.test_sketch import ALLOWED, VOCAB, base_scene
    rng = random.Random(20261009)
    pal = sketch.palette("#FFD23F", "#2EE59D", "#ff9a3c")
    passed = refused = 0

    def walk(node, path=()):
        if isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, path + (k,))
            yield path, node
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, path + (i,))
            yield path, node

    for _ in range(2000):
        scene = copy.deepcopy(base_scene())
        for _n in range(rng.randint(1, 2)):
            spots = [p for p, _ in walk(scene) if p]
            if not spots:
                break
            path = rng.choice(spots)
            parent = scene
            for key in path[:-1]:
                parent = parent[key]
            if rng.random() < 0.15 and isinstance(parent, dict):
                parent[rng.choice(["onclick", "href", "style", "extra", "d", "filter"])] = rng.choice(HOSTILE_VALUES)   # a field nobody defined
            else:
                parent[path[-1]] = rng.choice(HOSTILE_VALUES)
        try:
            spec = sketch.validate(scene, dur=5.0, allowed=ALLOWED, vocab=VOCAB)
        except sketch.SpecError:
            refused += 1
            continue
        passed += 1
        svg, js = sketch.emit("s0", 0.0, spec, pal)
        scan = Scan()
        scan.feed(svg)
        assert set(scan.tags) <= {"svg", "rect", "circle", "line", "path", "text", "g"}, scan.tags
        assert not scan.handlers and not scan.js_urls and not scan.scripts, (scan.handlers, scan.js_urls)
        assert "<script" not in svg.lower() and "javascript:" not in svg.lower(), svg[:300]
        for call in js:
            assert re.fullmatch(r'tl\.fromTo\("#s0_[a-z0-9_]+",\{[^\n\u2028\u2029]*\},\{[^\n\u2028\u2029]*\},-?[0-9.]+\);'
                                r'|gsap\.set\("#s0_[a-z0-9_]+",\{transformOrigin:"(?:50% 50%|50% 100%|50% 0%|0% 50%|100% 50%)"\}\);', call), call[:200]
    assert refused > 500 and passed > 20                     # the fuzz is neither trivially refused nor trivially accepted


def test_starting_the_same_topic_in_the_same_slot_keeps_the_cost_record_and_the_reason_it_stopped(folders):
    from faceless.state import new_job
    first = new_job("math", "The $15 a month trap", slot=2, day="2026-10-09")
    first.add_cost("openrouter", 0.0042)
    first.advance("scripted")
    first.advance("voiced")
    again = new_job("math", "The $15 a month trap", slot=2, day="2026-10-09")
    assert again.id == first.id and again.status == "planned" and again.history == []     # the stages run forward again from the start
    assert again.cost == {"openrouter": 0.0042} and again.notes == ["restarted from voiced"]
    again.advance("scripted")                                                                # not a TransitionError: the retry path works
    other = new_job("math", "A different topic", slot=2, day="2026-10-09")
    assert other.id != first.id and other.cost == {} and other.notes == []


def test_a_damaged_job_file_is_replaced_by_a_fresh_job_not_a_crash(folders):
    from faceless.state import new_job
    jid = "2026-10-09-s1-math-the-15-a-month-trap"
    (Paths.jobs / f"{jid}.json").write_text('{"id": "2026-10-09-s1-m', encoding="utf-8")
    job = new_job("math", "The $15 a month trap", slot=1, day="2026-10-09")
    assert job.id == jid and job.status == "planned" and json.loads((Paths.jobs / f"{jid}.json").read_text(encoding="utf-8"))["id"] == jid


def test_dates_come_from_utc_never_from_the_machines_clock_zone():
    """Job days, the ledger and the posting calendar are UTC. A naive `date.today()` or `datetime.now()` names a different day for hours each day on a
    machine outside UTC, which would look for yesterday's packs or put a video in the wrong slot."""
    offenders = []
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner, name = ast.unparse(node.func.value), node.func.attr
                if (owner in ("date", "datetime.date") and name == "today") or (owner == "datetime" and name in ("utcnow", "today")) \
                        or (owner == "datetime" and name == "now" and not node.args and not node.keywords):
                    offenders.append(f"{path.relative_to(SRC.parent)}:{node.lineno}")
    assert not offenders, offenders


def test_today_utc_is_the_utc_date(monkeypatch):
    import datetime as dt
    from faceless import config

    class Fake(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return dt.datetime(2026, 10, 9, 23, 30, tzinfo=dt.timezone.utc).astimezone(tz) if tz else dt.datetime(2026, 10, 10, 1, 30)   # local clock is already tomorrow

    monkeypatch.setattr(config, "datetime", Fake)
    assert config.today_utc() == dt.date(2026, 10, 9)


# ------------------------------------------------------------------ instructions that came from outside

# Skills installed from other people's repositories are text the scheduled routines obey. They are committed, so a changed line shows in a diff, but a
# diff is easy to wave through. Updating one means changing the digest here in the same commit, after reading what changed.
THIRD_PARTY_SKILLS = {
    "agent-browser": "80161e6836b3b40f4e83730a290deb40ac14d877d38c97ad5f6d71be37ce74c3",
    "composio": "48d397d22a12f8ad519a456d1b01c91aefb5c69b0633a40d6f07ff2d8990f7db",
}


def _digest(folder: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    for f in sorted(p for p in folder.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(folder)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def test_skills_from_other_repositories_change_only_on_purpose():
    root = SRC.parent / ".agents" / "skills"
    if not root.exists():
        pytest.skip("no third-party skills in this checkout")
    found = {d.name: _digest(d) for d in root.iterdir() if d.is_dir()}
    assert found == THIRD_PARTY_SKILLS, "a third-party skill changed (or a new one arrived): read the diff, then update THIRD_PARTY_SKILLS in this commit"
    locked = set(json.loads((SRC.parent / "skills-lock.json").read_text(encoding="utf-8")).get("skills", {}))
    assert locked == set(THIRD_PARTY_SKILLS)
