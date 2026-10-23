"""Static website: the Money Rules Library (SEO + answer-engine optimization).

Why a site at all (from the AEO research in channel/seo-playbook.md):
- AI assistants answer from search indexes (ChatGPT ~ Bing, Gemini ~ Google, Claude ~ Brave), so a crawlable,
  topically focused site is how the channel gets recommended, cited, and linked.
- Documentation-style pages are what answer engines cite most; every video becomes one structured page
  (rule, full script, key numbers, sources, FAQ) with schema.org markup.
Outputs to site/ (deployed to GitHub Pages by .github/workflows/faceless-site.yml).
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime

from faceless import config
from faceless.config import Paths
from faceless.state import all_jobs, slugify
from faceless.fsutil import write_atomic

SITE = Paths.root / "site"
KIT = Paths.root / "channel" / "brand-kit"
CHECKLIST = Paths.root / "channel" / "offers" / "money-reset-checklist.md"


def cfg() -> dict:
    c = config.load()
    s = c.get("site", {})
    return {
        "base": s.get("base_url", "https://example.github.io/quiet-money").rstrip("/"),
        "indexnow_key": s.get("indexnow_key", ""),
        "google_verification": s.get("google_verification", ""),
        "bing_verification": s.get("bing_verification", ""),
        "socials": s.get("socials", {}),
        "head_snippet": s.get("head_snippet", ""),
        "channel": c["channel"],
        "pillars": {p.id: p for p in c["pillars"]},
    }


def e(text) -> str:
    return html.escape(str(text or ""), quote=True)


SOCIAL_NAMES = {"youtube": "YouTube", "tiktok": "TikTok", "instagram": "Instagram", "x": "X", "linkedin": "LinkedIn", "pinterest": "Pinterest"}


def plain(text, limit: int = 300) -> str:
    """One line of plain text for a Markdown file crawlers and answer engines read: no line breaks (a title could start a heading or an instruction on its
    own line), no brackets or angle brackets (they would end the link or open a tag)."""
    return re.sub(r"[\[\]<>]", "", " ".join(str(text or "").split()))[:limit]


def safe_url(url) -> str:
    """The address if it is plain http(s), else nothing. Escaping stops a quote from breaking out of an attribute; it does not stop `javascript:`,
    which runs when clicked. Every address that comes from configuration or a model goes through here before it becomes a link."""
    u = str(url or "").strip()
    return u if re.match(r"https?://[^\s<>\"']+$", u, re.I) else ""


def social_links(socials: dict) -> str:
    return " · ".join(f'<a href="{e(safe_url(u))}" rel="me">{e(SOCIAL_NAMES.get(k, k.title()))}</a>' for k, u in socials.items() if safe_url(u))


def ld_json(data) -> str:
    """JSON for a <script> block. Scripts and titles are LLM-written: a literal "</script>" in one would end
    the block and run as HTML on the public site, so the characters that can break out are escaped."""
    return (json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _items(value, keys: tuple[str, str]) -> list[dict]:
    """facts/faq entries as dicts; LLM output sometimes gives bare strings or other shapes."""
    out = []
    for x in value if isinstance(value, list) else []:
        if isinstance(x, dict):
            out.append(x)
        elif str(x or "").strip():
            out.append({keys[0]: str(x).strip(), keys[1]: ""})
    return out


def sentence_case(text: str) -> str:
    """ALL-CAPS hooks read as a sentence; mixed-case ones keep their acronyms (IRA, 401(k), FIRE)."""
    text = text.lower() if text.isupper() else text
    return text[:1].upper() + text[1:]


def rfc822(day: str) -> str:
    try:
        return format_datetime(datetime.fromisoformat(day).replace(tzinfo=timezone.utc))
    except ValueError:
        return ""


# ------------------------------------------------------------------ data

def published_rules() -> list[dict]:
    rules = []
    for job in all_jobs():
        if job.status != "published":
            continue
        fp = Paths.final / f"{job.id}.json"
        if not fp.exists():
            continue
        meta_p = job.dir / "meta.json"
        try:   # one unreadable file costs that video its page, never the whole site
            s = json.loads(fp.read_text(encoding="utf-8"))
            meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        except (OSError, ValueError):
            continue
        if not isinstance(s, dict) or not isinstance(meta, dict):
            continue
        yt = (job.artifacts.get("publish") or {}).get("youtube_id") or job.artifacts.get("youtube_id")
        rules.append({
            "slug": slugify(s.get("title", job.topic), 64),
            "job": job.id, "day": job.day, "pillar": job.pillar,
            "title": s.get("title", job.topic), "hook": s.get("hook_text", ""),
            "description": s.get("description", "") or meta.get("description", "").split("\n")[0],
            "beats": [b for b in s.get("beats", []) if isinstance(b, dict) and b.get("say")],
            "facts": _items(s.get("facts"), ("claim", "basis")), "faq": _items(s.get("faq"), ("q", "a")),
            "hashtags": s.get("hashtags", []), "youtube_id": yt,
        })
    rules.sort(key=lambda r: (r["day"], r["job"]))
    seen: set[str] = set()
    for r in rules:   # two videos with the same title must not overwrite each other's page; oldest keeps the URL
        base, n = r["slug"], 2
        while r["slug"] in seen:
            r["slug"], n = f"{base}-{n}", n + 1
        seen.add(r["slug"])
    rules.reverse()
    return rules


# ------------------------------------------------------------------ layout

CSS = """
:root{--ink:#0e0e10;--ink2:#17171b;--line:#2a2a30;--gold:#ffd23f;--gold2:#c9a227;--cream:#f5f1e6;--muted:#a19d93}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;overflow-wrap:anywhere;background:var(--ink);color:var(--cream);font:17px/1.65 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--gold);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:860px;margin:0 auto;padding:0 18px}
header.top{border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(14,14,16,.92);backdrop-filter:blur(8px);z-index:5}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;height:60px}
.brand{display:flex;align-items:center;gap:10px;font:900 18px Montserrat,sans-serif;letter-spacing:.06em;color:var(--gold)}
.brand img{width:30px;height:30px;border-radius:50%}
nav a{color:var(--cream);margin-left:18px;font-size:15px;white-space:nowrap}
@media(max-width:520px){nav a{margin-left:12px;font-size:14px}.brand{font-size:15px;gap:8px}.brand img{width:26px;height:26px}}
.hero{padding:56px 0 30px}
.hero h1{font:900 clamp(34px,7vw,58px)/1.05 Montserrat,sans-serif;margin:0 0 14px;letter-spacing:-.01em}
.hero h1 span{color:var(--gold)}
.lead{font-size:clamp(18px,2.6vw,21px);color:var(--muted);max-width:640px}
.btn{display:inline-block;background:var(--gold);color:var(--ink);font-weight:800;padding:12px 20px;border-radius:999px;margin:8px 10px 0 0}
.btn.ghost{background:transparent;color:var(--cream);border:1px solid var(--line)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;margin:18px 0 40px}
.card{background:var(--ink2);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
.card .thumb{aspect-ratio:16/9;background:linear-gradient(135deg,#2a2208,#0e0e10);display:flex;align-items:center;justify-content:center;padding:18px;text-align:center;font:900 20px/1.15 Montserrat,sans-serif;color:var(--gold);text-transform:uppercase}
.card .thumb img{width:100%;height:100%;object-fit:cover}
.card .body{padding:14px 16px 18px}.card h3{font-size:18px;line-height:1.3;margin:6px 0 6px}.card h3 a{color:var(--cream)}
.tag{display:inline-block;font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--gold)}
h2{font:900 26px Montserrat,sans-serif;margin:42px 0 6px}
article h1{font:900 clamp(30px,6vw,46px)/1.1 Montserrat,sans-serif;margin:30px 0 10px}
article .summary{font-size:20px;color:var(--muted)}
.rule{border-left:4px solid var(--gold);background:var(--ink2);padding:14px 18px;border-radius:0 12px 12px 0;font-size:19px;margin:22px 0}
.nums{display:flex;flex-wrap:wrap;gap:10px;margin:10px 0 0;padding:0;list-style:none}
.nums li{background:var(--ink2);border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-weight:800;color:var(--gold)}
.video{aspect-ratio:9/16;max-width:360px;border-radius:16px;overflow:hidden;border:1px solid var(--line);margin:18px 0}
.video iframe{width:100%;height:100%;border:0}
.sources li{color:var(--muted);font-size:15px}
.faq dt{font-weight:800;margin-top:14px}.faq dd{margin:4px 0 0;color:var(--muted)}
.crumbs{font-size:14px;color:var(--muted);margin-top:22px}
.calc{background:var(--ink2);border:1px solid var(--line);border-radius:16px;padding:18px;margin:16px 0}
.calc label{display:block;font-size:14px;color:var(--muted);margin-top:10px}
.calc input{width:100%;background:var(--ink);color:var(--cream);border:1px solid var(--line);border-radius:10px;padding:10px;font-size:17px}
.calc output{display:block;font:900 26px Montserrat,sans-serif;color:var(--gold);margin-top:14px}
.check li{list-style:none;margin:6px 0}.check li:before{content:"☐ ";color:var(--gold)}
.hubcards{display:grid;gap:12px;margin:18px 0 8px}
.hubcard{display:block;background:var(--ink2);border:1px solid var(--line);border-radius:16px;padding:16px 18px;color:var(--cream)}
.hubcard:hover{text-decoration:none;border-color:var(--gold)}
.hubcard b{display:block;font:900 19px/1.25 Montserrat,sans-serif}
.hubcard span{display:block;color:var(--muted);font-size:15px;margin-top:2px}
.hubcard.primary,.hubcard.feat{border-color:var(--gold)}
.hubcard .tier{display:block;font-size:13px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--gold);margin-top:4px}
.badge{display:inline-block;font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--ink);background:var(--gold);border-radius:999px;padding:1px 9px;margin-left:8px;vertical-align:middle}
.signup{background:var(--ink2);border:1px solid var(--gold);border-radius:16px;padding:16px 18px;margin:12px 0}
.signup label{display:block;font-weight:800;margin-bottom:8px}
.signup input[type=email]{width:100%;background:var(--ink);color:var(--cream);border:1px solid var(--line);border-radius:10px;padding:12px;font-size:17px;box-sizing:border-box}
.signup button{margin-top:10px;border:0;cursor:pointer;font-size:16px}
.fine{color:var(--muted);font-size:14px}
footer{border-top:1px solid var(--line);margin-top:60px;padding:26px 0 40px;color:var(--muted);font-size:14px}
.pref{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:999px;padding:8px 14px;color:var(--cream);font-size:14px}
.shots{display:grid;gap:18px;margin:18px 0 8px}.shots figure{margin:0;background:var(--ink2);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.shots img{display:block;width:100%;height:auto}.shots figcaption{padding:10px 16px 14px;color:var(--muted);font-size:15px}
.inside{padding-left:20px}.inside li{margin:8px 0}
.buy{background:var(--ink2);border:1px solid var(--gold);border-radius:16px;padding:16px 18px;margin:28px 0}
.buy .price{font:900 34px Montserrat,sans-serif;color:var(--gold);margin-right:12px;vertical-align:middle}
@media print{header.top,footer,.btn{display:none}body{background:#fff;color:#000}}
"""


def head_snippet() -> str:
    """The owner's analytics tag, if one is configured: `[site] head_snippet` names a file of HTML (any provider; a cookieless one needs no banner).
    It is inserted as written, so it is the owner's to review; nothing here knows or loads a particular provider."""
    name = cfg()["head_snippet"]
    path = (Paths.root / name) if name else None
    try:
        return path.read_text(encoding="utf-8").strip() if path and path.is_file() else ""
    except OSError:
        return ""


POSTHOG_HOST = "https://us.i.posthog.com"
POSTHOG_TOKEN_SHAPE = re.compile(r"^phc_[A-Za-z0-9]{20,64}$")
VISITS_ANALYTICS = ("We count visits with PostHog in a cookieless mode: nothing is stored on your device, no advertising profile is built, "
                    "and session recording is off. We record which pages are viewed, whether a calculator was used, and clicks to our shop, "
                    "so we know which pages help people.")


def posthog_token() -> str:
    """The PostHog project token from the environment at build time (never from a file, rule 11). Project tokens are sent by every
    visitor's browser by design; the personal API key is a secret and never reaches a page. Anything not shaped like a token is ignored."""
    t = config.env("POSTHOG_TOKEN") or ""
    return t if POSTHOG_TOKEN_SHAPE.match(t) else ""


def analytics_snippet() -> str:
    """Cookieless page analytics (O15): pageviews, the first calculator input on a page, and clicks to the shop. Empty without a token."""
    token = posthog_token()
    if not token:
        return ""
    init = json.dumps({"api_host": POSTHOG_HOST, "persistence": "memory", "autocapture": False, "capture_pageview": True,
                       "disable_session_recording": True, "disable_surveys": True,
                       "capture_dead_clicks": False, "capture_heatmaps": False, "capture_performance": False, "advanced_disable_flags": True})
    return ("<script>!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split('.');"
            "2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}"
            "(p=t.createElement('script')).type='text/javascript',p.crossOrigin='anonymous',p.async=!0,p.src=s.api_host.replace('.i.posthog.com',"
            "'-assets.i.posthog.com')+'/static/array.js',(r=t.getElementsByTagName('script')[0]).parentNode.insertBefore(p,r);var u=e;"
            "for(void 0!==a?u=e[a]=[]:a='posthog',u.people=u.people||[],n='capture register reset opt_out_capturing'.split(' '),o=0;o<n.length;o++)"
            "g(u,n[o]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);"
            f"posthog.init({json.dumps(token)},{init});"
            "(function(){var used=false;document.addEventListener('input',function(){if(!used){used=true;"
            "posthog.capture('calculator_used',{page:location.pathname})}},true);"
            "document.addEventListener('click',function(ev){var a=ev.target.closest&&ev.target.closest('a');"
            "if(a&&/gumroad\\.com|etsy\\.com/.test(a.href)){posthog.capture('shop_click',{href:a.href,page:location.pathname})}},true)})();"
            "</script>")


def page(path: str, title: str, description: str, body: str, *, jsonld: list | None = None,
         og_type: str = "website", image: str | None = None, noindex: bool = False) -> str:
    c = cfg()
    depth = path.strip("/").count("/") + (1 if path.strip("/") else 0)
    root = "../" * depth if depth else "./"
    url = f"{c['base']}/{path.strip('/')}/" if path.strip("/") else f"{c['base']}/"
    img = image or f"{c['base']}/og-image.png"
    ch = c["channel"]
    verify = ""
    if c["google_verification"]:
        verify += f'<meta name="google-site-verification" content="{e(c["google_verification"])}">'
    if c["bing_verification"]:
        verify += f'<meta name="msvalidate.01" content="{e(c["bing_verification"])}">'
    ld = "".join(f'<script type="application/ld+json">{ld_json(x)}</script>' for x in (jsonld or []))
    domain = c["base"].split("//", 1)[-1].split("/", 1)[0]
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{e(ch['name'])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(url)}"><meta property="og:image" content="{e(img)}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#0e0e10">
<link rel="icon" href="{root}favicon-32.png"><link rel="apple-touch-icon" href="{root}favicon-180.png">
<link rel="alternate" type="application/rss+xml" title="{e(ch['name'])}" href="{root}feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Montserrat:wght@900&display=swap" rel="stylesheet">
<style>{CSS}</style>{verify}{'<meta name="robots" content="noindex,follow">' if noindex else ""}{ld}{head_snippet()}{analytics_snippet()}
</head><body>
<header class="top"><div class="wrap"><a class="brand" href="{root}"><img src="{root}favicon-180.png" alt="">QUIET MONEY</a>
<nav><a href="{root}rules/">Rules</a><a href="{root}tools/">Tools</a><a href="{root}money-reset/">Checklist</a><a href="{root}about/">About</a></nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">
<p><a class="pref" href="https://www.google.com/preferences/source?q={e(domain)}" rel="nofollow">★ Add Quiet Money as a preferred source on Google</a></p>
<p>{e(ch['name'])}: {e(ch['tagline'])} Educational content, not financial advice. Narration and visuals in our videos are AI-assisted; every number is computed and every story is sourced.</p>
<p>{social_links(c["socials"])}</p>
<p class="legal"><a href="{root}terms/">Terms</a> · <a href="{root}privacy/">Privacy</a> · <a href="{root}about/">About</a></p>
</div></footer>
</body></html>"""


TIKTOK_VERIFY_NAME = "tiktokU0fxJODyiu9rM34RSekGr3RvbXUSuyKd.txt"
TIKTOK_VERIFY_BODY = "tiktok-developers-site-verification=U0fxJODyiu9rM34RSekGr3RvbXUSuyKd"

LEGAL_UPDATED = "2026-10-23"
CONTACT_URL = "https://github.com/youngstunners88/quiet-money/issues"   # the public contact route; no personal email on a public page


def terms_page() -> str:
    c = cfg()
    ch = c["channel"]
    body = f"""<article><h1>Terms of Service</h1>
<p class="summary">Last updated {LEGAL_UPDATED}. These terms cover this website and the short videos, written explainers and free tools published by {e(ch['name'])}.</p>
<h2>What this is</h2><p>{e(ch['name'])} publishes educational content about money psychology and personal finance: short videos, written explainers, free checklists and calculators. It is educational content, not financial advice. Nothing here is a recommendation to buy, sell or hold any product or asset, and nothing here is tailored to your situation.</p>
<h2>Using the site</h2><p>You may read, share and link to our pages. Please do not copy our videos, scripts or checklists for resale, do not scrape the site at a rate that slows it down, and do not use it to mislead anyone. We may change or remove content at any time.</p>
<h2>Accuracy</h2><p>Every number on this site is computed and every story is sourced where possible. Still, financial rules change and examples are simplified. Check important decisions with a qualified professional.</p>
<h2>AI-assisted content</h2><p>Narration and visuals in our videos are AI-assisted and the host is a virtual presenter. We label this on the videos and in their descriptions.</p>
<h2>Products and links</h2><p>Some pages link to paid digital products sold through third-party platforms, and some links may be affiliate links. Purchases are governed by the seller's own terms. We may earn a commission on an affiliate purchase at no cost to you.</p>
<h2>Liability</h2><p>The content is provided as is, without warranty. To the extent the law allows, {e(ch['name'])} is not liable for losses that come from relying on it.</p>
<h2>Privacy</h2><p>How we handle personal information is described in our <a href="../privacy/">Privacy Policy</a>.</p>
<h2>Contact</h2><p>Questions about these terms: <a href="{CONTACT_URL}" rel="noopener">open an issue on our public repository</a>.</p></article>"""
    return page("terms", f"Terms of Service | {ch['name']}", f"The terms for using {ch['name']}'s website, videos and free tools.", body)


def privacy_page() -> str:
    c = cfg()
    ch = c["channel"]
    body = f"""<article><h1>Privacy Policy</h1>
<p class="summary">Last updated {LEGAL_UPDATED}. This explains what information {e(ch['name'])} collects through this website, and what it does not.</p>
<h2>What we collect</h2>
<ul><li><strong>Website visits.</strong> Our site is hosted on GitHub Pages, which keeps standard server logs (such as IP address, browser type and the pages requested) under its own privacy policy. {VISITS_ANALYTICS if posthog_token() else "We do not run an analytics tag or advertising tracker on this site."}</li>
<li><strong>Fonts.</strong> Pages load fonts from Google Fonts, which means your browser contacts Google when you open a page.</li>
<li><strong>Videos.</strong> Embedded videos come from YouTube's privacy-enhanced embed, which does not set cookies until you press play.</li>
<li><strong>Email (when offered).</strong> If we open an email list, you will give your email address on a sign-up form. We will use it only to send the newsletter you asked for and you can unsubscribe at any time. This form is not active on the site yet.</li>
<li><strong>Purchases.</strong> Paid products are sold through third-party platforms. Those platforms collect the payment and purchase details under their own privacy policies. We do not receive or store your card details.</li></ul>
<h2>What we do not do</h2><p>We do not sell personal information, do not have user accounts on this site, and do not ask for passwords or payment details here.</p>
<h2>Social platforms</h2><p>When you follow or comment on our videos on TikTok, YouTube or Instagram, that platform handles your data under its own policy. We see only the public comments and counts those platforms show us.</p>
<h2>Children</h2><p>This site is for adults. We do not knowingly collect information from anyone under 16.</p>
<h2>Your choices</h2><p>You can block cookies and third-party requests in your browser, unsubscribe from any future email, and ask us to delete any personal information we hold about you.</p>
<h2>Contact</h2><p>To ask about your data or this policy, <a href="{CONTACT_URL}" rel="noopener">open an issue on our public repository</a>.</p></article>"""
    return page("privacy", f"Privacy Policy | {ch['name']}", f"What {ch['name']} collects through its website, and what it does not.", body)


def card(r: dict, root: str) -> str:
    c = cfg()
    pillar = c["pillars"].get(r["pillar"])
    thumb = (f'<img src="https://i.ytimg.com/vi/{e(r["youtube_id"])}/hqdefault.jpg" alt="" loading="lazy">'
             if r["youtube_id"] else e(r["hook"] or r["title"]))
    return (f'<div class="card"><div class="thumb">{thumb}</div><div class="body">'
            f'<span class="tag">{e(pillar.name if pillar else r["pillar"])}</span>'
            f'<h3><a href="{root}rules/{r["slug"]}/">{e(r["title"])}</a></h3>'
            f'<div style="color:var(--muted);font-size:15px">{e(r["description"][:140])}</div></div></div>')


def org_ld() -> dict:
    c = cfg()
    return {"@context": "https://schema.org", "@type": "Organization", "name": c["channel"]["name"],
            "url": c["base"] + "/", "logo": c["base"] + "/favicon-512.png",
            "description": f"{c['channel']['tagline']} Short videos on {c['channel']['niche']}.",
            "sameAs": [u for u in c["socials"].values() if u]}


def rule_page(r: dict, related: list[dict]) -> str:
    c = cfg()
    pillar = c["pillars"].get(r["pillar"])
    paras, cur = [], []
    for b in r["beats"]:
        cur.append(b["say"])
        if len(cur) >= 4:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    nums = [b["callout"] for b in r["beats"] if b.get("callout")]
    url = f"{c['base']}/rules/{r['slug']}/"
    video = (f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{e(r["youtube_id"])}" '
             f'title="{e(r["title"])}" allowfullscreen loading="lazy"></iframe></div>') if r["youtube_id"] else ""
    facts = "".join(f"<li>{e(f.get('claim'))} <em>({e(f.get('basis'))})</em></li>" for f in r["facts"])
    faq = r["faq"] or [{"q": f"What is the main lesson of \"{r['title']}\"?", "a": r["description"]}]
    faq_html = "".join(f"<dt>{e(x.get('q'))}</dt><dd>{e(x.get('a'))}</dd>" for x in faq)
    article_ld = {"@context": "https://schema.org", "@type": "Article", "headline": r["title"],
                  "description": r["description"], "datePublished": r["day"], "mainEntityOfPage": url,
                  "author": {"@type": "Organization", "name": c["channel"]["name"]},
                  "publisher": org_ld(), "articleSection": pillar.name if pillar else r["pillar"],
                  "keywords": ", ".join(t.lstrip("#") for t in r["hashtags"])}
    lds = [article_ld,
           {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
               {"@type": "Question", "name": x.get("q"), "acceptedAnswer": {"@type": "Answer", "text": x.get("a")}}
               for x in faq]},
           {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
               {"@type": "ListItem", "position": 1, "name": "Rules", "item": c["base"] + "/rules/"},
               {"@type": "ListItem", "position": 2, "name": r["title"], "item": url}]}]
    if r["youtube_id"]:
        lds.append({"@context": "https://schema.org", "@type": "VideoObject", "name": r["title"],
                    "description": r["description"], "uploadDate": r["day"],
                    "thumbnailUrl": f"https://i.ytimg.com/vi/{r['youtube_id']}/hqdefault.jpg",
                    "embedUrl": f"https://www.youtube.com/embed/{r['youtube_id']}"})
    rel = "".join(card(x, "../../") for x in related[:3])
    body = f"""<p class="crumbs"><a href="../../rules/">Rules</a> › {e(pillar.name if pillar else '')}</p>
<article><span class="tag">{e(pillar.name if pillar else r['pillar'])}</span>
<h1>{e(r['title'])}</h1><p class="summary">{e(r['description'])}</p>
<div class="rule"><strong>The rule:</strong> {e(sentence_case(r['hook']) or r['title'])}.</div>
{video}
{'<h2>Key numbers</h2><ul class="nums">' + ''.join(f'<li>{e(n)}</li>' for n in nums) + '</ul>' if nums else ''}
<h2>The full story</h2>{''.join(f'<p>{e(p)}</p>' for p in paras)}
{'<h2>Sources and math</h2><ul class="sources">' + facts + '</ul>' if facts else ''}
<h2>Questions</h2><dl class="faq">{faq_html}</dl>
<p><a class="btn" href="../../money-reset/">Get the free 7-day Money Reset</a><a class="btn ghost" href="../../tools/">Run the numbers</a></p>
</article>{'<h2>More money rules</h2><div class="grid">' + rel + '</div>' if rel else ''}"""
    return page(f"rules/{r['slug']}", f"{r['title']} | Quiet Money", r["description"], body,
                jsonld=lds, og_type="article")


TOOLS_JS = """
function money(x){return '$'+Math.round(x).toLocaleString('en-US')}
function fv(){const m=+q('m').value,r=+q('r').value/100/12,y=+q('y').value,n=y*12;
 const v=r?m*((1+r)**n-1)/r:m*n;q('fvo').textContent=money(v)+'  (you put in '+money(m*n)+')'}
function card(){let b=+q('b').value;const apr=+q('a').value/100,p=+q('p').value;let mo=0,i=0;
 while(b>0.005&&mo<1200){const t=b*apr/12;if(p<=t){q('co').textContent='Payment never covers the interest';return}
 i+=t;b=b+t-p;mo++}q('co').textContent=mo+' months, '+money(i)+' interest'}
function infl(){const a=+q('ia').value,r=+q('ir').value/100,y=+q('iy').value;q('io').textContent=money(a/((1+r)**y))+' of buying power'}
function q(id){return document.getElementById(id)}
document.querySelectorAll('input').forEach(x=>x.addEventListener('input',()=>{fv();card();infl()}));fv();card();infl();
"""


def tools_page() -> str:
    body = """<section class="hero"><h1>Money <span>calculators</span></h1>
<p class="lead">The exact math behind our videos. Change the numbers; the results update instantly. Projections use the
assumption you enter; real returns vary.</p></section>
<div class="calc"><h2 style="margin-top:0">Monthly investing growth</h2>
<label>Monthly amount ($)<input id="m" type="number" value="200"></label>
<label>Yearly return (%)<input id="r" type="number" value="8" step="0.5"></label>
<label>Years<input id="y" type="number" value="40"></label><output id="fvo"></output></div>
<div class="calc"><h2 style="margin-top:0">Credit card payoff</h2>
<label>Balance ($)<input id="b" type="number" value="6000"></label>
<label>APR (%)<input id="a" type="number" value="24"></label>
<label>Monthly payment ($)<input id="p" type="number" value="300"></label><output id="co"></output></div>
<div class="calc"><h2 style="margin-top:0">Inflation: what your cash will buy</h2>
<label>Amount today ($)<input id="ia" type="number" value="100"></label>
<label>Inflation (%)<input id="ir" type="number" value="3" step="0.5"></label>
<label>Years<input id="iy" type="number" value="20"></label><output id="io"></output></div>
<script>""" + TOOLS_JS + "</script>"
    ld = [{"@context": "https://schema.org", "@type": "WebApplication", "name": "Quiet Money calculators",
           "applicationCategory": "FinanceApplication", "operatingSystem": "Any",
           "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}]
    return page("tools", "Money calculators: compound growth, card payoff, inflation | Quiet Money",
                "Free calculators for compound growth, credit card payoff, and inflation, the exact math behind Quiet Money videos.",
                body, jsonld=ld)


def about_page(rules: list[dict]) -> str:
    c = cfg()
    ch = c["channel"]
    series = "".join(f"<li><strong>{e(p.name)}</strong>: {e(p.format)}</li>" for p in c["pillars"].values())
    body = f"""<article><h1>About Quiet Money</h1>
<p class="summary">Quiet Money is a short-video channel that explains money psychology and personal finance in about 60 seconds per video, with real numbers.</p>
<h2>What it is</h2><p>Quiet Money publishes new short videos every day on YouTube Shorts, TikTok, and Instagram Reels, and keeps a written version of every video here in the Money Rules Library. Each video teaches one money rule that most people were never taught: how compound interest works, why minimum credit card payments take decades, how raises disappear into lifestyle creep, and what ordinary people did to build wealth quietly.</p>
<h2>Who it is for</h2><p>{e(ch['audience'].capitalize())}.</p>
<h2>The series</h2><ul>{series}</ul>
<h2>How we make videos</h2><p>Every calculation is computed by code with the assumption stated on screen (for example "at 8% a year"). Every true story is checked against at least two reputable sources, listed on its page. Narration and visuals are AI-assisted and labeled as such on every platform. Real people are never shown by face.</p>
<h2>What we do not do</h2><p>We do not give personalized financial advice, recommend specific stocks or coins, or promise returns. This is education.</p>
<h2>Library</h2><p>{len(rules)} money rules published so far. Start with the <a href="../rules/">full library</a> or the <a href="../tools/">calculators</a>.</p>
</article>"""
    return page("about", "About Quiet Money: money rules in 60 seconds", "What Quiet Money is, who it is for, and how every number and story is checked.",
                body, jsonld=[org_ld()])


def signup_form(heading: str = "Get the 7-day Money Reset by email") -> str:
    """The email signup. It exists only once the owner has put their email service's public form address in `[newsletter] form_action`;
    until then nothing is rendered, so no page ever shows a form that goes nowhere."""
    nl = config.load().get("newsletter", {})
    action = str(nl.get("form_action", "")).strip()
    if not action.startswith("https://"):
        return ""
    field = re.sub(r"[^A-Za-z0-9_\-\[\]]", "", str(nl.get("form_email_field", "email"))) or "email"
    return (f'<form class="signup" action="{e(action)}" method="post"><label for="signup-email">{e(heading)}</label>'
            f'<input id="signup-email" type="email" name="{e(field)}" placeholder="you@example.com" required autocomplete="email">'
            f'<button class="btn" type="submit">Send it</button>'
            f'<p class="fine">Free. One short email a day for seven days, then a weekly note. Unsubscribe any time.</p></form>')


HUB_JS = ("(function(){try{var o=new URLSearchParams(location.search).get('o');if(!o)return;o=o.replace(/[^a-z0-9._-]/g,'');"
          "var c=document.querySelector('.hubcards');var el=c&&c.querySelector('[data-o=\"'+o+'\"]');"
          "if(el&&el!==c.firstElementChild){el.classList.add('feat');c.insertBefore(el,c.firstElementChild);}}catch(e){}})();")


def hub_page() -> str:
    """The page every profile links to: the free checklist first, then any paid product that has a live listing, then the tools. Not in the
    sitemap and marked noindex (it is a destination for people who watched a video, not a page for search). `?o=<slug>` moves that card to the
    top, which is how a video about the planner lands on the planner."""
    from faceless import offer
    c = cfg()
    ch = c["channel"]
    cards = []
    for d in offer.destinations():
        if d["kind"] == "free":
            href = offer.tracked("../money-reset/", "hub", "link", d["slug"])
            cards.append(f'<a class="hubcard primary" data-o="{e(d["slug"])}" href="{e(href)}"><b>Free 7-day Money Reset</b>'
                         f'<span>Seven 10-minute steps, one a day. Find the leaks, automate savings, split every paycheck. Printable.</span></a>')
        else:
            href = offer.tracked(d["url"], "quietmoney", "hub", d["slug"])
            cards.append(f'<a class="hubcard" data-o="{e(d["slug"])}" href="{e(href)}" rel="noopener"><b>{e(d["name"])}<span class="badge">Paid</span></b>'
                         + (f'<span class="tier">{e(d["tier"])}</span>' if d.get("tier") else "")
                         + '<span>See the listing for what is included. Educational tools, no promised results.</span></a>')
    cards.append(f'<a class="hubcard" data-o="tools" href="{e(offer.tracked("../tools/", "hub", "link", "tools"))}"><b>Calculators</b>'
                 f'<span>Compound growth, credit card payoff, inflation: put your own numbers in.</span></a>')
    cards.append(f'<a class="hubcard" data-o="rules" href="{e(offer.tracked("../rules/", "hub", "link", "rules"))}"><b>Every money rule, written out</b>'
                 f'<span>The math and the sources behind each video.</span></a>')
    socials = social_links(c["socials"])
    affiliate = "<p class=\"fine\">Some links may be affiliate links; if you buy through one we may earn a commission at no cost to you.</p>" if ch.get("has_affiliate_links") else ""
    body = (f'<section class="hero"><h1>Start <span>here</span></h1><p class="lead">The money rules nobody taught you, with the real numbers.</p></section>'
            f'{signup_form()}<div class="hubcards">{"".join(cards)}</div>'
            f'<p class="fine">Follow: {socials}</p>{affiliate}'
            f'<p class="fine">Educational content, not financial advice. Examples use assumed numbers; nothing here promises a result.</p>'
            f'<script>{HUB_JS}</script>')
    return page("links", f"Start here | {ch['name']}", f"The free 7-day Money Reset, calculators and every money rule from {ch['name']}.", body, noindex=True)


# ---------------------------------------------------------------- the Daily Planner's product page (only while its listing is live, rule 13)

PLANNER_SLUG = "daily-quiet-money-planner"
PLANNER_FACTS = {"pages": 427, "days": 365, "weeks": 52, "wellness": 52}      # kept as numbers so the site build needs no PDF tools; a test ties them to the book
PLANNER_WEB = Paths.root / "channel" / "shop" / PLANNER_SLUG / "web"
PLANNER_SAMPLE = Paths.root / "channel" / "offers" / "lead-magnets" / "first-quiet-week" / "The-First-Quiet-Week.pdf"   # the free sample week (faceless/lead_magnet_sample.py)
PLANNER_SHOTS = [
    ("02-inside", "The planner's cover, welcome page, net worth snapshot, debt map, year map and a daily page laid out side by side",
     "The front of the book: cover, welcome, net worth snapshot, debt map, year at a glance, and a daily page."),
    ("03-feature-1", "A daily page with a picture, a short lesson, a Try this action and a small tracker", "A daily page: one picture, one short lesson, one small action."),
    ("04-feature-2", "A By the numbers daily page with a gold coin picture and a worked example",
     "By the numbers days: every figure is a worked example computed with tested math, its assumptions stated."),
    ("07-feature-5", "The Year at a Glance page listing all 52 weekly themes in four quarters with tick boxes",
     "The year at a glance: 52 weekly themes in four quarters. Tick each week off as you finish it."),
    ("05-feature-3", "The Net Worth Snapshot page with columns for Days 1, 91, 182, 273 and 365",
     "The net worth snapshot: fill in a column on Days 1, 91, 182, 273 and 365."),
    ("06-feature-4", "A Weekly Check-in page with boxes for money in, spent, saved and debt paid",
     "The weekly check-in: money in, spent, saved, debt paid, three wins and one thing to fix."),
]
PLANNER_FAQ = [
    ("What exactly do I get?", f"Two PDF files, US Letter and A4, {PLANNER_FACTS['pages']} pages each: the same book in two paper sizes. They download the moment you pay. Nothing is shipped."),
    ("Is it dated?", "No. The planner is undated. Open Day 1 whenever you begin, and if you miss days, skip ahead to today's page."),
    ("Do I have to print it?", "It is made for printing: the whole book or a week at a time, one side or two, in colour or black and white. It is not a fillable form, "
     "but you can write on it in any PDF app that lets you annotate."),
    ("Does it tell me what to buy or invest in?", "No. It is an educational tool, not financial advice. It never tells you to buy a particular stock, coin or product. "
     "Every number in it is a worked example with its assumptions stated, and nothing in it promises a result."),
    ("Which country is it for?", "The examples use US-style dollar figures. Where a lesson depends on your country, such as credit scores, retirement accounts or tax, it says so."),
    ("Was AI used to make it?", "Yes, and we say so. It was designed by Quiet Money with AI assistance. Every computed figure comes from one shared set of math functions. "
     "The pictures are drawn in code or made with AI tools. Thirty-two of the wellness posters are the owner's own artwork; the other twenty were made in the same "
     "style with AI tools. The man on the cover is Quinton, the Quiet Money host, an AI-generated character."),
    ("What if it is not for me?", "Ask for a refund through your Gumroad receipt within 30 days of buying."),
    ("Can I share it?", "One purchase covers as many printed copies as you and your household need. Please do not resell or share the files."),
    ("I found a mistake. What now?", "Reply to the message where you bought it. The mistake gets fixed and you get the updated file."),
]
# Carries the visitor's own source tag (?utm_source=youtube) into the buy link as utm_content, cleaned like HUB_JS.
PLANNER_JS = ("(function(){try{var s=new URLSearchParams(location.search).get('utm_source');if(!s)return;"
              "s=s.toLowerCase().replace(/[^a-z0-9._-]/g,'').slice(0,40);if(!s)return;"
              "document.querySelectorAll('a[data-buy]').forEach(function(a){var u=new URL(a.href);"
              "if(u.protocol!=='https:')return;u.searchParams.set('utm_content','from-'+s);a.href=u.toString();});}catch(e){}})();")


def planner_listing() -> str:
    """The planner's live listing URL, or "" while it is not live (then no page and no links are made)."""
    from faceless import offer
    live = {d["slug"]: d["url"] for d in offer.destinations() if d["kind"] == "paid"}
    return safe_url(live.get(PLANNER_SLUG, ""))


def planner_line(root: str) -> str:
    if not planner_listing():
        return ""
    return (f'<p class="fine">Want one lesson a day, in order, on paper? <a href="{root}planner/">The Quiet Money Daily Planner</a> '
            f'is a {PLANNER_FACTS["days"]}-day printable.</p>')


def _figure(stem: str, alt: str, caption: str, eager: bool = False) -> str:
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    cap = f"<figcaption>{e(caption)}</figcaption>" if caption else ""
    return (f'<figure><img src="img/{stem}-1400.jpg" srcset="img/{stem}-800.jpg 800w, img/{stem}-1400.jpg 1400w" '
            f'sizes="(max-width: 860px) 100vw, 824px" width="1400" height="1050" alt="{e(alt)}" {load}>{cap}</figure>')


def planner_page() -> str:
    """A product page on our own site for search and AI answers: what is inside, real pages, honest notes, an FAQ, a buy button to the live listing.
    No ratings or reviews in the markup until real ones exist and show on the page."""
    from faceless import offer
    listing_url = planner_listing()
    if not listing_url:
        return ""
    sample_line = ('<p><a class="btn ghost" href="' + PLANNER_SAMPLE.name + '" download>Try week 1 free (PDF, 9 pages)</a></p>'
                   if PLANNER_SAMPLE.exists() else "")
    c, F = cfg(), PLANNER_FACTS
    price = offer.catalog().get(PLANNER_SLUG, {}).get("price") or 17
    p = f"${price:g}"
    buy = e(offer.tracked(listing_url, "site", "planner_page", PLANNER_SLUG))
    have = {f.name for f in PLANNER_WEB.glob("*.jpg")} if PLANNER_WEB.exists() else set()
    hero = _figure("01-hero", "The Quiet Money Daily Planner: the printed cover in front of two open daily pages", "", eager=True) if "01-hero-1400.jpg" in have else ""
    shots = "".join(_figure(*s) for s in PLANNER_SHOTS if f"{s[0]}-1400.jpg" in have)
    body = f"""<p class="crumbs"><a href="../">Home</a> › Daily Planner</p>
<section class="hero"><span class="tag">Printable money planner · {p}</span>
<h1>One money lesson a day, <span>for a whole year.</span></h1>
<p class="lead">The Quiet Money Daily Planner is a {F['days']}-day printable that teaches basic personal finance one page at a time. Every day is one picture, one short lesson and one small action.</p>
<a class="btn" data-buy href="{buy}" rel="noopener">Get the planner for {p}</a><a class="btn ghost" href="#inside">See what is inside</a>
<p class="fine">Instant PDF download through Gumroad. US Letter and A4 included. 30-day refund. Educational tool, not financial advice.</p></section>
{f'<div class="shots">{hero}</div>' if hero else ''}
<h2>Who it is for</h2>
<p>Anyone who earns a paycheck, feels behind with money and wants the basics without jargon. You do not need to know anything to start. The daily actions are small: write down your net worth, find a forgotten account, pick one weekly time for money.</p>
<h2 id="inside">What is inside</h2>
<ul class="nums"><li>{F['pages']} pages</li><li>{F['days']} daily pages</li><li>{F['weeks']} weekly themes</li><li>Letter + A4</li><li>Undated</li></ul>
<ul class="inside">
<li><strong>Two PDFs</strong>, US Letter and A4, {F['pages']} pages each.</li>
<li><strong>{F['days']} daily pages.</strong> Each has a black-and-gold picture, a short plain-English lesson, a Try this action, space for notes and a small tracker: spent today, saved or paid down, and how you feel about money from 1 to 5.</li>
<li><strong>A weekly rhythm:</strong> Learn, By the numbers, Do it, Mindset, Action, a weekly check-in, then a reflect-and-reset page.</li>
<li><strong>Front pages:</strong> a welcome page, a net worth snapshot you fill in on Days 1, 91, 182, 273 and 365, a debt map, and the year at a glance.</li>
<li><strong>{F['wellness']} wellness break pages</strong>, one after each week, each tying a simple everyday habit to a money habit. General information, not medical advice.</li>
<li><strong>At the back:</strong> a summary and goals page, a plain-English money words glossary, two notes pages and an about page.</li>
</ul>
<h2>A real page: Day 1</h2>
<div class="rule"><span class="tag">Learn</span><br><strong>Start with the truth.</strong> Net worth is what you own minus what you owe. It can be negative, and that is a starting line, not a verdict. Writing it down once already puts you ahead of yesterday.<br><br><strong>Try this:</strong> Fill in the Net Worth Snapshot at the front of this book. Round every number to the nearest $10 and do not judge any of it.</div>
<h2>How the year is laid out</h2>
<ul class="inside">
<li><strong>Quarter 1, foundations (weeks 1 to 13):</strong> where you stand, where it goes, the paycheck split, spending leaks, pay yourself first, the first $1,000, sinking funds, lifestyle creep.</li>
<li><strong>Quarter 2, debt, credit and compounding (weeks 14 to 26):</strong> the debt map, interest math, snowball or avalanche, credit cards, credit scores, compound interest, the rule of 72, inflation.</li>
<li><strong>Quarter 3, investing and income (weeks 27 to 39):</strong> investing basics, funds and costs, retirement accounts, risk, raises and negotiation, side income, assets and liabilities, taxes in brief.</li>
<li><strong>Quarter 4, life, protection and freedom (weeks 40 to 52):</strong> housing, insurance, planning big purchases, money and other people, scams and fraud, goals and your freedom number, money myths, quiet wealth.</li>
</ul>
{f'<h2>Look inside</h2><div class="shots">{shots}</div>' if shots else ''}
<h2>How it works</h2>
<ol class="inside"><li><strong>Buy and download.</strong> Two PDFs arrive the moment you pay: US Letter and A4.</li>
<li><strong>Print it your way.</strong> The whole book or a week at a time, one side or two.</li>
<li><strong>Start on any day.</strong> Fill in the net worth snapshot and the debt map, then open Day 1.</li></ol>
<h2>Honest notes</h2>
<ul class="inside"><li>Education, not financial advice. It never tells you to buy a particular stock, coin or product.</li>
<li>Every number is a worked example with its assumptions stated. Your own numbers are the ones that matter.</li>
<li>Designed by Quiet Money with AI assistance. The man on the cover is Quinton, the Quiet Money host, an AI-generated character.</li>
<li>The planner is new, so there are no customer reviews yet. The pictures on this page are made from the real pages.</li></ul>
<div class="buy"><span class="price">{p}</span><span class="fine">One payment. Instant PDF download. Letter + A4. 30-day refund.</span><br>
<a class="btn" data-buy href="{buy}" rel="noopener">Get the planner on Gumroad</a></div>
<h2>Questions</h2>
<dl class="faq">{"".join(f"<dt>{e(q)}</dt><dd>{e(a)}</dd>" for q, a in PLANNER_FAQ)}</dl>
{sample_line}<p class="fine">Not ready to buy? Start with the free <a href="../money-reset/">7-day Money Reset</a>, try the <a href="../tools/">calculators</a>, or read the <a href="../rules/">Money Rules Library</a>.</p>
<script>{PLANNER_JS}</script>"""
    base, url = c["base"], f"{c['base']}/planner/"
    imgs = [f"{base}/planner/img/{n}" for n in ("01-hero-1400.jpg", "02-inside-1400.jpg") if n in have]
    product = {"@context": "https://schema.org", "@type": "Product", "name": "The Quiet Money Daily Planner",
               "description": f"A {F['days']}-day printable money planner: one picture, one short lesson and one small action for every day of the year. "
                              f"Two undated PDFs, US Letter and A4, {F['pages']} pages each. Educational, not financial advice.",
               "url": url, "sku": PLANNER_SLUG, "brand": {"@type": "Brand", "name": c["channel"]["name"]},
               "offers": {"@type": "Offer", "price": f"{price:.2f}", "priceCurrency": "USD", "availability": "https://schema.org/InStock", "url": listing_url}}
    if imgs:
        product["image"] = imgs
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "The Quiet Money Daily Planner", "item": url}]}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in PLANNER_FAQ]}
    image = f"{base}/planner/img/cover-1200.jpg" if "cover-1200.jpg" in have else None
    return page("planner", "Daily Money Planner: 365 printable lessons | Quiet Money",
                f"A {F['days']}-day printable money planner: one picture, one short lesson and one small action a day. Undated PDF, US Letter and A4, "
                f"{F['pages']} pages. {p}, 30-day refund.", body, jsonld=[product, crumbs, faq], og_type="product", image=image)


def md_checklist(md: str) -> str:
    out = []
    for line in md.splitlines():
        s = line.strip()
        if not s or s == "---":
            continue
        if s.startswith("# "):
            out.append(f"<h1>{e(s[2:])}</h1>")
        elif s.startswith("## "):
            out.append(f"<h2>{e(s[3:])}</h2>")
        elif s.startswith("- [ ] "):
            out.append(f'<ul class="check"><li>{e(s[6:])}</li></ul>')
        else:
            out.append(f"<p>{re.sub(r'[*_]', '', e(s))}</p>")
    return "\n".join(out)


def build() -> dict:
    c = cfg()
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    for name in ("og-image.png", "favicon-32.png", "favicon-180.png", "favicon-512.png", "avatar.png"):
        if (KIT / name).exists():
            shutil.copy2(KIT / name, SITE / name)
    rules = published_rules()
    urls = [c["base"] + "/"]
    ch = c["channel"]

    hero = f"""<section class="hero"><h1>The money rules <span>nobody taught you.</span></h1>
<p class="lead">{e(ch['name'])} turns money psychology and personal finance into 60-second lessons with real numbers. Every video has a written page here with the full story, the math, and the sources.</p>
<a class="btn" href="money-reset/">Free 7-day Money Reset</a><a class="btn ghost" href="rules/">Browse the library</a></section>
<h2>Latest money rules</h2><div class="grid">{''.join(card(r, './') for r in rules[:9])}</div>
<h2>The series</h2><div class="grid">{''.join(f'<div class="card"><div class="body"><span class="tag">Series</span><h3><a href="series/{p.id}/">{e(p.name)}</a></h3><div style="color:var(--muted);font-size:15px">{e(p.format[:120])}</div></div></div>' for p in c['pillars'].values())}</div>"""
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": ch["name"], "url": c["base"] + "/",
               "description": ch["tagline"]}
    (SITE / "index.html").write_text(page("", f"{ch['name']}: {ch['tagline']}", f"{ch['tagline']} Money psychology and personal finance in 60 seconds, with real numbers and sources.",
                                          hero, jsonld=[org_ld(), site_ld]), encoding="utf-8")

    lib = f"""<section class="hero"><h1>The Money Rules <span>Library</span></h1><p class="lead">Every Quiet Money video, written out with the math and the sources.</p>{planner_line('../')}</section>
<div class="grid">{''.join(card(r, '../') for r in rules)}</div>"""
    (SITE / "rules").mkdir()
    (SITE / "rules" / "index.html").write_text(page("rules", "Money Rules Library | Quiet Money", "Every Quiet Money video written out: the rule, the story, the math, and the sources.", lib), encoding="utf-8")
    urls.append(c["base"] + "/rules/")

    for r in rules:
        d = SITE / "rules" / r["slug"]
        d.mkdir(parents=True, exist_ok=True)
        related = [x for x in rules if x["pillar"] == r["pillar"] and x["slug"] != r["slug"]] or [x for x in rules if x["slug"] != r["slug"]]
        (d / "index.html").write_text(rule_page(r, related), encoding="utf-8")
        urls.append(f"{c['base']}/rules/{r['slug']}/")

    for pid, p in c["pillars"].items():
        d = SITE / "series" / pid
        d.mkdir(parents=True, exist_ok=True)
        items = [r for r in rules if r["pillar"] == pid]
        body = f"""<section class="hero"><span class="tag">Series</span><h1>{e(p.name)}</h1><p class="lead">{e(p.format)}</p></section>
<div class="grid">{''.join(card(r, '../../') for r in items) or '<p>New videos in this series are on the way.</p>'}</div>"""
        (d / "index.html").write_text(page(f"series/{pid}", f"{p.name} | Quiet Money", p.format[:155], body), encoding="utf-8")
        urls.append(f"{c['base']}/series/{pid}/")

    for path, html_text in (("tools", tools_page()), ("about", about_page(rules)), ("terms", terms_page()), ("privacy", privacy_page())):
        (SITE / path).mkdir(exist_ok=True)
        (SITE / path / "index.html").write_text(html_text, encoding="utf-8")
        urls.append(f"{c['base']}/{path}/")

    (SITE / "links").mkdir()
    (SITE / "links" / "index.html").write_text(hub_page(), encoding="utf-8")        # the profile link: no sitemap entry, noindex

    planner_html = planner_page()
    if planner_html:
        (SITE / "planner" / "img").mkdir(parents=True)
        for f in sorted(PLANNER_WEB.glob("*.jpg")) if PLANNER_WEB.exists() else []:
            shutil.copy2(f, SITE / "planner" / "img" / f.name)
        if PLANNER_SAMPLE.exists():
            shutil.copy2(PLANNER_SAMPLE, SITE / "planner" / PLANNER_SAMPLE.name)
        (SITE / "planner" / "index.html").write_text(planner_html, encoding="utf-8")
        urls.append(c["base"] + "/planner/")

    (SITE / "money-reset").mkdir()
    body = signup_form() + md_checklist(CHECKLIST.read_text(encoding="utf-8")) + '<p><a class="btn" href="javascript:window.print()">Print it</a></p>'
    (SITE / "money-reset" / "index.html").write_text(page("money-reset", "The free 7-day Money Reset checklist | Quiet Money",
                                                          "Seven 10-minute steps that put your money on rules instead of willpower: find leaks, automate savings, kill expensive debt.",
                                                          body), encoding="utf-8")
    urls.append(c["base"] + "/money-reset/")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{e(u)}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
                                      + "</urlset>\n", encoding="utf-8")
    # explicit allow for the crawlers behind AI answers (Bing->ChatGPT, Brave->Claude, Google->Gemini)
    bots = ["Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot",
            "PerplexityBot", "Google-Extended", "Applebot", "DuckDuckBot"]
    (SITE / "robots.txt").write_text("".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots)
                                     + f"User-agent: *\nAllow: /\n\nSitemap: {c['base']}/sitemap.xml\n", encoding="utf-8")
    llms = [f"# {ch['name']}", "", f"> {ch['tagline']} Short videos on {ch['niche']}, each written out with its math and sources.", "",
            "Educational content, not financial advice. Every number is computed; every story is sourced.", "",
            "## Pages", f"- [Money Rules Library]({c['base']}/rules/): every video as a written page",
            f"- [Calculators]({c['base']}/tools/): compound growth, credit card payoff, inflation",
            f"- [Free 7-day Money Reset]({c['base']}/money-reset/): printable checklist",
            *([f"- [The Quiet Money Daily Planner]({c['base']}/planner/): a 365-day printable money planner (paid): what is inside and honest notes"] if planner_html else []),
            f"- [About]({c['base']}/about/): what Quiet Money is and how videos are made", "", "## Money rules"]
    llms += [f"- [{plain(r['title'])}]({c['base']}/rules/{r['slug']}/): {plain(r['description'])}" for r in rules]
    (SITE / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")
    items = "".join(f"<item><title>{e(r['title'])}</title><link>{c['base']}/rules/{r['slug']}/</link>"
                    f"<guid>{c['base']}/rules/{r['slug']}/</guid><pubDate>{rfc822(r['day'])}</pubDate>"
                    f"<description>{e(r['description'])}</description></item>" for r in rules[:30])
    (SITE / "feed.xml").write_text(f'<?xml version="1.0"?><rss version="2.0"><channel><title>{e(ch["name"])}</title>'
                                   f'<link>{c["base"]}/</link><description>{e(ch["tagline"])}</description>{items}</channel></rss>',
                                   encoding="utf-8")
    if c["indexnow_key"]:
        (SITE / f"{c['indexnow_key']}.txt").write_text(c["indexnow_key"], encoding="utf-8")
    # TikTok's URL-prefix verification file (public token, served at the site root so TikTok can check the prefix)
    (SITE / TIKTOK_VERIFY_NAME).write_text(TIKTOK_VERIFY_BODY, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    write_atomic(SITE / "urls.json", json.dumps(urls, indent=1))
    return {"pages": len(urls), "rules": len(rules), "dir": str(SITE)}


def indexnow(urls: list[str] | None = None) -> dict:
    """Tell Bing/Yandex/Seznam (IndexNow) about new or changed URLs; Bing feeds ChatGPT's search."""
    from faceless.providers import http
    c = cfg()
    if not c["indexnow_key"]:
        return {"skipped": "no indexnow_key"}
    urls = urls or json.loads((SITE / "urls.json").read_text(encoding="utf-8"))
    host = c["base"].split("//", 1)[-1].split("/", 1)[0]
    body = {"host": host, "key": c["indexnow_key"], "keyLocation": f"{c['base']}/{c['indexnow_key']}.txt", "urlList": urls[:10000]}
    r = http().post("https://api.indexnow.org/indexnow", json=body, timeout=30)
    return {"status": r.status_code, "submitted": len(body["urlList"])}


def new_indexnow_key() -> str:
    return hashlib.sha256(f"quiet-money-{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:32]
