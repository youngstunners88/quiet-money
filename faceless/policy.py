"""Policy watchdog: notice when a platform rule page changes, because one rule change can end a revenue rail.

`channel/compliance/watchlist.json` lists the pages that govern us (monetization, AI labeling, marketplaces, email law, our own
cost drivers). Each run fetches the page, keeps only the sentences that state rules (about AI, eligibility, bans, labels, prices), and
compares them with the saved snapshot. Snapshots store short rule sentences and a hash, never whole pages. A page that cannot be
fetched here (script-rendered, blocked) is reported as `unfetchable` so the weekly session can fetch it another way and hand the text
to `record`. Changed pages become proposals in the weekly scan. Rule facts are verified on the date shown, in platform-rules.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from html.parser import HTMLParser

from faceless import config
from faceless.config import Paths

DIR = Paths.root / "channel" / "compliance"
WATCHLIST = DIR / "watchlist.json"
SNAP = DIR / "snapshots"
REPORT = DIR / "POLICY-WATCH.md"
RULE = re.compile(r"\b(ai|artificial|generat\w*|synthetic|disclos\w*|label\w*|prohibit\w*|not allowed|must|may not|cannot|can't|"
                  r"don't|eligib\w*|monetiz\w*|original|inauthentic|repetit\w*|mass-produced|template\w*|fees?|price|pricing|"
                  r"per million|free of charge|free tier|opt.?out|postal|penalt\w*|suspend\w*|terminat\w*)\b", re.I)


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self.out, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("p", "li", "br", "div", "h1", "h2", "h3", "h4", "tr", "td"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    return re.sub(r"[ \t\r\f\v]+", " ", "".join(p.out))


def headline(s: str) -> bool:
    """A Title Case line with no closing punctuation is a page headline or a news-sidebar item, not a rule ("FTC Secures Fair Pricing Protections by Taking Action ...")."""
    words = s.split()
    return len(words) >= 6 and s[-1] not in ".!?:;" and sum(w[:1].isupper() for w in words) / len(words) >= 0.7


def snippets(text: str, cap: int = 90) -> list[str]:
    """Rule-stating sentences: 25-300 characters, mentioning a rule word, not a headline. Order kept, duplicates dropped."""
    seen, out = set(), []
    for part in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = " ".join(part.split())
        key = s.lower()
        if 25 <= len(s) <= 300 and RULE.search(s) and not headline(s) and key not in seen:
            seen.add(key)
            out.append(s)
        if len(out) >= cap:
            break
    return out


def watchlist() -> list[dict]:
    try:
        return json.loads(WATCHLIST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def fetch(url: str) -> str | None:
    """Plain HTTP fetch; None when the page cannot be read as text here."""
    import requests
    try:
        r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0 (compatible; QuietMoneyPolicyWatch/1.0)"})
    except requests.RequestException:
        return None
    if r.status_code != 200 or "html" not in r.headers.get("content-type", "html"):
        return None
    text = to_text(r.text)
    return text if len(text) > 1500 and len(snippets(text)) >= 3 else None     # a shell page with no rules in it is not a read


def load(pid: str) -> dict | None:
    try:
        return json.loads((SNAP / f"{pid}.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def record_text(pid: str, text: str, today: str | None = None) -> dict:
    """Compare supplied page text with the saved snapshot, then save it. status: new | unchanged | changed."""
    new = snippets(text)
    old = load(pid)
    added = [s for s in new if old and s.lower() not in {x.lower() for x in old["snippets"]}]
    removed = [s for s in (old["snippets"] if old else []) if s.lower() not in {x.lower() for x in new}]
    status = "new" if old is None else "changed" if added or removed else "unchanged"
    SNAP.mkdir(parents=True, exist_ok=True)
    snap = {"id": pid, "fetched": today or date.today().isoformat(), "sha": hashlib.sha256("\n".join(new).encode()).hexdigest()[:16], "snippets": new}
    if status != "unchanged" or old is None:
        snap["changed"] = snap["fetched"]
    elif old:
        snap["changed"] = old.get("changed", old["fetched"])
    (SNAP / f"{pid}.json").write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"id": pid, "status": status, "added": added[:12], "removed": removed[:12], "rules": len(new)}


def check(fetch_fn=fetch, ids: list[str] | None = None) -> list[dict]:
    out = []
    for w in watchlist():
        if ids and w["id"] not in ids:
            continue
        text = fetch_fn(w["url"])
        if text is None:
            snap = load(w["id"])
            out.append({"id": w["id"], "status": "unfetchable", "added": [], "removed": [], "rules": len(snap["snippets"]) if snap else 0,
                        "last": snap["fetched"] if snap else None})
        else:
            out.append(record_text(w["id"], text))
    return out


def stale(days: int = 14, today: str | None = None) -> list[str]:
    """Watched pages whose snapshot is missing or older than `days`."""
    now = date.fromisoformat(today) if today else date.today()
    late = []
    for w in watchlist():
        snap = load(w["id"])
        if not snap or (now - datetime.strptime(snap["fetched"], "%Y-%m-%d").date()).days > days:
            late.append(w["id"])
    return late


def write_report(results: list[dict]) -> None:
    names = {w["id"]: w for w in watchlist()}
    L = [f"# Policy watch, {date.today().isoformat()}", "",
         "Rule sentences saved per page; a change below means a rule moved. Review the diff before the next listing, post run or send.", "",
         "| page | status | rules kept | note |", "|---|---|---|---|"]
    for r in results:
        w = names.get(r["id"], {})
        note = f"re-fetch another way (last read {r.get('last') or 'never'})" if r["status"] == "unfetchable" else ""
        L.append(f"| [{w.get('name', r['id'])}]({w.get('url', '')}) | {r['status']} | {r['rules']} | {note} |")
    for r in results:
        if r["status"] == "changed":
            L += ["", f"## Changed: {names.get(r['id'], {}).get('name', r['id'])}", ""]
            L += [f"- ADDED: {s}" for s in r["added"]] + [f"- REMOVED: {s}" for s in r["removed"]]
    DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def proposals(results: list[dict]) -> list[dict]:
    """Scout proposals: a changed rule page is urgent and cheap to review; an unfetchable one needs a different fetch."""
    out = []
    for r in results:
        if r["status"] == "changed":
            out.append({"id": f"policy-{r['id']}", "title": f"A rule page changed: {r['id']}", "category": "compliance", "impact": 5, "effort": 1,
                        "autonomy": "operator", "why": f"{len(r['added'])} rule sentences added, {len(r['removed'])} removed; see channel/compliance/POLICY-WATCH.md"})
    return out
