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
.badge{display:inline-block;font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--ink);background:var(--gold);border-radius:999px;padding:1px 9px;margin-left:8px;vertical-align:middle}
.signup{background:var(--ink2);border:1px solid var(--gold);border-radius:16px;padding:16px 18px;margin:12px 0}
.signup label{display:block;font-weight:800;margin-bottom:8px}
.signup input[type=email]{width:100%;background:var(--ink);color:var(--cream);border:1px solid var(--line);border-radius:10px;padding:12px;font-size:17px;box-sizing:border-box}
.signup button{margin-top:10px;border:0;cursor:pointer;font-size:16px}
.fine{color:var(--muted);font-size:14px}
footer{border-top:1px solid var(--line);margin-top:60px;padding:26px 0 40px;color:var(--muted);font-size:14px}
.pref{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:999px;padding:8px 14px;color:var(--cream);font-size:14px}
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
<style>{CSS}</style>{verify}{'<meta name="robots" content="noindex,follow">' if noindex else ""}{ld}{head_snippet()}
</head><body>
<header class="top"><div class="wrap"><a class="brand" href="{root}"><img src="{root}favicon-180.png" alt="">QUIET MONEY</a>
<nav><a href="{root}rules/">Rules</a><a href="{root}tools/">Tools</a><a href="{root}money-reset/">Checklist</a><a href="{root}about/">About</a></nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">
<p><a class="pref" href="https://www.google.com/preferences/source?q={e(domain)}" rel="nofollow">★ Add Quiet Money as a preferred source on Google</a></p>
<p>{e(ch['name'])}: {e(ch['tagline'])} Educational content, not financial advice. Narration and visuals in our videos are AI-assisted; every number is computed and every story is sourced.</p>
<p>{social_links(c["socials"])}</p>
</div></footer>
</body></html>"""


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
                         f'<span>See the listing for what is included. Educational tools, no promised results.</span></a>')
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

    lib = f"""<section class="hero"><h1>The Money Rules <span>Library</span></h1><p class="lead">Every Quiet Money video, written out with the math and the sources.</p></section>
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

    for path, html_text in (("tools", tools_page()), ("about", about_page(rules))):
        (SITE / path).mkdir(exist_ok=True)
        (SITE / path / "index.html").write_text(html_text, encoding="utf-8")
        urls.append(f"{c['base']}/{path}/")

    (SITE / "links").mkdir()
    (SITE / "links" / "index.html").write_text(hub_page(), encoding="utf-8")        # the profile link: no sitemap entry, noindex

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
