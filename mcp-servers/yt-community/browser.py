"""Drives the owner's own signed-in Chromium profile through the Posts tab, the way a person would. Needs `playwright` and a local browser.

The profile folder is where the owner signed in by hand (the `login` tool). No password, cookie or token is ever read, printed or stored by this code.
Selectors are matched by role and visible text, not by CSS class, and every failure leaves a screenshot and an accessibility dump to fix them from.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

PROFILE = Path(os.environ.get("QM_YT_PROFILE") or Path.home() / ".quiet-money" / "yt-profile")
SHOTS = Path(os.environ.get("QM_YT_SHOTS") or Path.home() / ".quiet-money" / "yt-shots")
TIMEOUT_MS = 30_000


class NotSignedIn(RuntimeError):
    pass


class ComposerNotFound(RuntimeError):
    pass


def _launch(pw, headless: bool):
    PROFILE.mkdir(parents=True, exist_ok=True)
    kw = dict(user_data_dir=str(PROFILE), headless=headless, viewport={"width": 1280, "height": 900}, args=["--disable-blink-features=AutomationControlled"])
    exe = os.environ.get("QM_CHROME")                  # the owner's own Chrome or Chromium, if they prefer it to Playwright's
    if exe:
        kw["executable_path"] = exe
    return pw.chromium.launch_persistent_context(**kw)


def posts_url(channel_id: str, base: str = "https://www.youtube.com") -> str:
    return f"{base}/channel/{channel_id}/posts"


def login(channel_id: str, wait_seconds: int = 600) -> str:
    """Open a visible browser on the owner's machine so they sign in themselves; returns when the Posts composer shows or the time is up."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = _launch(pw, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(posts_url(channel_id), timeout=TIMEOUT_MS)
        end = time.time() + wait_seconds
        while time.time() < end:
            if _composer_visible(page):
                ctx.close()
                return "signed in: the Posts composer is visible; the profile is saved"
            page.wait_for_timeout(2000)
        ctx.close()
        return "timed out before the Posts composer appeared (sign in as the channel owner, then run login again)"


def _composer_visible(page) -> bool:
    try:
        return page.get_by_text(re.compile(r"^\s*(Create (a )?post|Share an update|Add a post)", re.I)).first.is_visible(timeout=1500) or \
            page.get_by_role("button", name=re.compile(r"\bImage\b", re.I)).first.is_visible(timeout=1500)
    except Exception:
        return False


def snapshot(page, tag: str) -> dict:
    SHOTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    png = SHOTS / f"{stamp}-{re.sub(r'[^a-z0-9]+', '-', tag.lower())[:40]}.png"
    page.screenshot(path=str(png), full_page=False)
    txt = png.with_suffix(".aria.txt")
    try:
        txt.write_text(page.locator("body").aria_snapshot(), encoding="utf-8")
    except Exception as e:                              # a page without a snapshot still leaves its screenshot
        txt.write_text(f"no aria snapshot: {e}", encoding="utf-8")
    return {"screenshot": str(png), "aria": str(txt)}


def _open_composer(page):
    for pattern in (r"Create (a )?post", r"Share an update", r"Add a post"):
        loc = page.get_by_text(re.compile(pattern, re.I)).first
        try:
            if loc.is_visible(timeout=2500):
                loc.click(timeout=TIMEOUT_MS)
                break
        except Exception:
            continue


def post_image(channel_id: str, picture: str, text: str, *, publish: bool, headless: bool = False, base: str = "https://www.youtube.com") -> dict:
    """Fill the Posts composer with the picture and text. Without `publish` it stops before the Post button and returns a screenshot."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = _launch(pw, headless=headless)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(TIMEOUT_MS)
            page.goto(posts_url(channel_id, base), timeout=TIMEOUT_MS)
            page.wait_for_load_state("domcontentloaded")
            if "accounts.google.com" in page.url or page.get_by_role("link", name=re.compile(r"^Sign in$", re.I)).count():
                raise NotSignedIn("the profile is signed out: run the login tool on this machine")
            _open_composer(page)
            image_btn = page.get_by_role("button", name=re.compile(r"\bImage\b", re.I)).first
            if not image_btn.is_visible(timeout=5000):
                raise ComposerNotFound("no Image button in the composer: " + str(snapshot(page, "no-composer")))
            with page.expect_file_chooser(timeout=TIMEOUT_MS) as fc:
                image_btn.click()
            fc.value.set_files(picture)
            box = page.get_by_role("textbox").first
            box.click()
            box.fill(text)
            page.wait_for_timeout(1500)                 # let the upload preview settle
            shot = snapshot(page, "filled")
            if not publish:
                return {"published": False, **shot}
            first_line = text.strip().splitlines()[0][:40]
            page.get_by_role("button", name=re.compile(r"^Post$", re.I)).last.click()
            page.get_by_text(first_line, exact=False).first.wait_for(timeout=TIMEOUT_MS)
            return {"published": True, **snapshot(page, "posted")}
        except Exception:
            try:
                snapshot(page, "failed")
            except Exception:
                pass
            raise
        finally:
            ctx.close()
