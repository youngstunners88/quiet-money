"""Photopea as the cropper: the owner's own tool (photopea.com), driven headlessly through its official live-messaging API.

Photopea runs in the browser on this machine; its own documentation says files are not uploaded (the page itself and its scripts come from photopea.com). We open the
editor in Chromium inside a tiny local host page, send the picture to it as an ArrayBuffer, run `app.activeDocument.crop([l, t, r, b])`, and ask it to
`saveToOE("jpg:0.95")`, exactly the clicks the owner makes by hand. https://www.photopea.com/api/live describes the protocol.

Every crop is checked against a plain Pillow crop of the same box (same size, near-identical pixels). If Photopea cannot be reached (no Chromium, a blocked host, a
timeout) the same crop is made with Pillow and the report says `engine: pillow`, so a job never stops on a website being slow. Playwright (Apache-2.0, intake USE verdict
2026-10-11) is imported only here and only when a crop runs. Every wait has a timeout.
"""

from __future__ import annotations

import base64
import glob
import http.server
import io
import os
import socketserver
import threading

import numpy as np
from PIL import Image

HOST_PAGE = ('<html><body><iframe id="pp" style="width:1280px;height:760px" src="https://www.photopea.com#%7B%22files%22%3A%5B%5D%7D"></iframe>'
             '<script>window.__s=[];window.__b=[];window.addEventListener("message",function(e){if(typeof e.data==="string"){window.__s.push(e.data);}'
             'else{var u=new Uint8Array(e.data),b="";for(var i=0;i<u.length;i+=32768){b+=String.fromCharCode.apply(null,u.subarray(i,i+32768));}window.__b.push(btoa(b));}});'
             '</script></body></html>')
READY_S, STEP_S = 90, 60


class PhotopeaError(Exception):
    pass


def _chromium() -> str:
    found = sorted(glob.glob(os.path.join(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"), "chromium-*", "chrome-linux", "chrome")))
    if not found:
        raise PhotopeaError("no Chromium found (PLAYWRIGHT_BROWSERS_PATH)")
    return found[-1]


class _Host(http.server.BaseHTTPRequestHandler):
    def do_GET(self):                                                # one fixed page and nothing else: no directory is ever served
        ok = self.path.split("?")[0] == "/host.html"
        body = HOST_PAGE.encode() if ok else b"not found"
        self.send_response(200 if ok else 404)
        self.send_header("Content-Type", "text/html" if ok else "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class Photopea:
    """with Photopea() as pp: jpg_bytes = pp.crop(png_or_jpg_bytes, (left, top, right, bottom))"""

    def __enter__(self) -> "Photopea":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise PhotopeaError("playwright is not installed (pip install playwright)") from e
        self._srv = socketserver.TCPServer(("127.0.0.1", 0), _Host)
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        self._pw = sync_playwright().start()
        try:
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            kw = {"proxy": {"server": proxy, "bypass": "127.0.0.1,localhost"}} if proxy else {}
            self._browser = self._pw.chromium.launch(executable_path=_chromium(), headless=True, args=["--no-sandbox"], **kw)
            self._page = self._browser.new_context(viewport={"width": 1300, "height": 800}).new_page()
            self._page.goto(f"http://127.0.0.1:{self._srv.server_address[1]}/host.html", timeout=30000)
            self._wait_done(READY_S)
        except Exception as e:  # noqa: BLE001 - whatever failed, release the browser and report one clear error
            self.__exit__()
            raise PhotopeaError(f"Photopea did not start: {str(e)[:160]}") from e
        return self

    def __exit__(self, *exc) -> None:
        for step in (lambda: self._browser.close(), lambda: self._pw.stop(), lambda: self._srv.shutdown(), lambda: self._srv.server_close()):
            try:
                step()
            except Exception:  # noqa: BLE001
                pass

    def _wait_done(self, seconds: int) -> None:
        try:
            self._page.wait_for_function("window.__s.indexOf('done')>=0", timeout=seconds * 1000)
        except Exception as e:  # noqa: BLE001
            raise PhotopeaError(f"Photopea did not answer within {seconds} s") from e
        self._page.evaluate("window.__s=[]")

    def _send(self, js_arg: str, payload) -> None:
        self._page.evaluate("window.__s=[];window.__b=[]")                             # empty the inbox
        self._page.evaluate(f"(p)=>{{ {js_arg} }}", payload)

    def crop(self, data: bytes, box: tuple[int, int, int, int], quality: float = 0.95) -> bytes:
        l, t, r, b = (int(v) for v in box)
        self._send("var bin=atob(p),u=new Uint8Array(bin.length);for(var i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);"
                   "document.getElementById('pp').contentWindow.postMessage(u.buffer,'*');", base64.b64encode(data).decode())
        self._wait_done(STEP_S)
        self._send("document.getElementById('pp').contentWindow.postMessage(p,'*');", f"app.activeDocument.crop([{l},{t},{r},{b}]);")
        self._wait_done(STEP_S)
        self._send("document.getElementById('pp').contentWindow.postMessage(p,'*');", f'app.activeDocument.saveToOE("jpg:{quality}");')
        self._wait_done(STEP_S)
        got = self._page.evaluate("window.__b.slice()")
        if not got:
            raise PhotopeaError("Photopea sent no picture back")
        out = base64.b64decode(got[-1])
        self._send("document.getElementById('pp').contentWindow.postMessage(p,'*');", "app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);")
        self._wait_done(STEP_S)
        return out


def pillow_crop(data: bytes, box: tuple[int, int, int, int], quality: int = 95) -> bytes:
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).convert("RGB").crop(box).save(buf, "JPEG", quality=quality, subsampling=0)
    return buf.getvalue()


def agrees(a: bytes, b: bytes, tol: float = 4.0) -> bool:
    """Photopea's crop and Pillow's crop of the same box: same size and nearly the same pixels (both are re-encoded JPEGs)."""
    ia, ib = Image.open(io.BytesIO(a)).convert("RGB"), Image.open(io.BytesIO(b)).convert("RGB")
    return ia.size == ib.size and float(np.abs(np.asarray(ia, dtype=float) - np.asarray(ib, dtype=float)).mean()) < tol
