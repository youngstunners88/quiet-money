"""Opportunity scanner: finds the highest-leverage things to do next and does only the safe ones itself.

Signals it reads (all free, no new keys):
  - our own operation: backlog depth, hold rate and the gates that fail most, image-provider fallbacks and
    quota blocks (ledger/journal), spend, whether any performance metrics exist, publish mode
  - market demand: YouTube autocomplete (what people type), via faceless.keywords
  - external findings added by the `faceless-scout` skill's web research (`scout --import findings.json`)

Output: analytics/opportunities.md (ranked, newest run) + analytics/opportunities.jsonl (append-only log).
Autonomy: `--act` may only top up the topic backlog (reversible, gated by the usual script gauntlet later).
Everything else is a proposal tagged with who must approve it. We have no revenue data yet, so ranking is
by impact on output/reach versus effort, never by guessed profit.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from faceless import config, empire, events, keywords, ledger, policy, variety
from faceless.config import Paths
from faceless.pipeline import ideate
from faceless.state import all_jobs

OPPS = Paths.analytics / "opportunities.jsonl"
REPORT = Paths.analytics / "opportunities.md"
MIN_BACKLOG = 8       # unused topics per pillar below which we top up
TOPUP_BATCH = 6       # topics added per pillar per run
AUTONOMY = {"auto": "scout can do this itself (--act)",
            "operator": "an operator session may do this (code/tests/review); no money or accounts involved",
            "owner": "needs the owner: money, accounts, or credentials"}

SEEDS = {
    "story": ["frugal millionaire", "died with millions", "lottery winners money", "famous money mistakes"],
    "math": ["compound interest", "credit card interest", "index fund fees", "inflation savings"],
    "psychology": ["money habits", "spending psychology", "lifestyle creep", "why am i always broke"],
    "myth": ["money myths", "financial advice wrong", "is renting throwing money away"],
    "playbook": ["save money fast", "cancel subscriptions", "automate savings", "lower bills"],
    "escape": ["passive income", "side hustle", "financial freedom", "how to quit your job", "get out of debt"],
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def health(days: int = 7) -> dict:
    """Facts about the operation, from files the engine already writes."""
    cut = (_now() - timedelta(days=days)).strftime("%Y-%m-%d")
    history = {h.lower() for h in ideate.history_texts()}
    backlog = Counter(i["pillar"] for i in ideate.load_backlog() if i["topic"].lower() not in history)
    jobs = [j for j in all_jobs() if j.day >= cut]
    made = [j for j in jobs if j.status in ("packaged", "published", "held")]
    held = [j for j in made if j.status == "held"]
    failing: Counter = Counter()
    for j in held:
        rp = Paths.reports / f"{j.id}.json"
        if rp.exists():
            try:
                failing.update(g["name"] for g in json.loads(rp.read_text(encoding="utf-8")).get("gates", []) if not g.get("passed"))
            except (json.JSONDecodeError, KeyError):
                pass
    img = Counter(e.get("provider") for e in events.read(kind="PROVIDER_OK")
                  if e.get("capability") == "image" and str(e.get("ts", ""))[:10] >= cut)
    blocked_days = sorted({r["day"] for r in ledger._rows() if r.get("unit") == "blocked" and r.get("day", "") >= cut})
    paid = sum(r.get("usd", 0) for r in ledger._rows() if r.get("day", "") >= cut)
    from faceless import analytics
    return {
        "days": days, "videos": len(made), "held": len(held), "hold_rate": round(len(held) / len(made), 2) if made else 0.0,
        "top_failing_gates": failing.most_common(3), "images": dict(img), "provider_blocked_days": blocked_days,
        "paid_usd": round(paid, 2), "backlog_unused": dict(backlog), "metrics_rows": len(analytics.load()),
        "publish_mode": config.load()["publish"]["mode"],
        "pillars": [p.id for p in config.load()["pillars"]],
    }


def proposals(h: dict) -> list[dict]:
    """Rule-based findings from health(). impact/effort are 1-5; score = impact / effort."""
    out: list[dict] = []

    def add(id_, title, category, impact, effort, autonomy, why):
        out.append({"id": id_, "title": title, "category": category, "impact": impact, "effort": effort,
                    "autonomy": autonomy, "why": why, "score": round(impact / effort, 2)})

    imgs = h["images"]
    total = sum(imgs.values()) or 1
    weak = (imgs.get("pollinations", 0) + imgs.get("procedural", 0)) / total
    if weak > 0.4 or h["provider_blocked_days"]:
        add("images-quota", "Remove the daily image cap: Cloudflare Workers Paid (~$5/month) or top up OpenRouter",
            "ops", 4, 1, "owner",
            f"{round(weak * 100)}% of images this week came from the low-resolution fallback; providers were out of quota "
            f"on {len(h['provider_blocked_days'])} day(s). Paid images look sharper and let all 5 daily videos use real FLUX art.")
    if h["publish_mode"] == "local":
        add("go-live", "Create the YouTube/TikTok/Instagram accounts and turn on auto-posting (Upload-Post)",
            "growth", 5, 2, "owner", "Publish mode is local: videos are made but nobody sees them. Nothing else compounds until posts go out.")
    if h["metrics_rows"] < 10:
        add("metrics", "Start recording post metrics (views, retention, follows) so pillar weights and this scanner can use real data",
            "growth", 4, 2, "owner", f"Only {h['metrics_rows']} metric rows exist; the router stays balanced and profit ranking is impossible until ~10+.")
    for p in h["pillars"]:
        n = h["backlog_unused"].get(p, 0)
        if n < MIN_BACKLOG:
            add(f"topup-{p}", f"Top up the '{p}' topic backlog ({n} left)", "content", 3, 1, "auto",
                "Low backlog means the writer falls back to unconstrained ideation; seeded, demand-checked topics are better.")
    if h["videos"] >= 3 and h["hold_rate"] > 0.25:
        gates = ", ".join(f"{g} x{c}" for g, c in h["top_failing_gates"]) or "see gauntlet reports"
        add("hold-rate", f"Cut the hold rate ({round(h['hold_rate'] * 100)}%): fix the most common failing gate",
            "ops", 4, 2, "operator", f"{h['held']} of {h['videos']} videos held this week. Top failing gates: {gates}.")
    if h["paid_usd"] > 7 * 1.0:
        add("spend", f"Paid spend ${h['paid_usd']} this week: raise free-tier use or lower the paid image cap", "ops", 3, 1, "operator",
            "Paid fallbacks should be rare; check which provider is spending.")
    return out


def _signals(pillar: str) -> list[str]:
    seen: list[str] = []
    for seed in SEEDS.get(pillar, []):
        for s in keywords.suggest(seed):
            if s not in seen and s != seed:
                seen.append(s)
    return seen[:24]


def topup(pillar: str, n: int = TOPUP_BATCH) -> list[dict]:
    """Ask the LLM for topics inspired by what people search; keep fresh ones with search signal; append."""
    from faceless import research
    from faceless.prompts import ideas_prompt
    from faceless.providers import llm
    history = ideate.history_texts() + [i["topic"] for i in ideate.load_backlog()]
    pil = config.pillar(pillar)
    briefs = research.available() if pillar == "escape" else None
    prompt = ideas_prompt(pil, n + 4, history, briefs, signals=_signals(pillar))
    res = llm.complete(prompt, want_json=True, temperature=0.9)
    threshold = config.load()["gauntlet"]["similarity_max"]
    added = []
    raw = res.get("ideas", []) if isinstance(res, dict) else res   # models sometimes return the bare list
    for i in raw if isinstance(raw, list) else []:
        if not isinstance(i, dict):
            continue
        topic = str(i.get("topic", "")).strip()
        if not topic or not ideate.is_fresh(topic, history + [a["topic"] for a in added], threshold):
            continue
        brief = i.get("brief", "") if i.get("brief", "") in (briefs or []) else ""
        d = keywords.demand(topic)
        if d["score"] < 1:      # nobody searches anything like it: skip
            continue
        added.append({"pillar": pillar, "topic": topic, "angle": i.get("angle", ""), "hook": i.get("hook", ""),
                      "brief": brief, "source": "scout", "demand": d["score"]})
        if len(added) >= n:
            break
    ideate.append_backlog(added)
    events.emit("SCOUT_TOPUP", pillar=pillar, added=len(added))
    return added


def run(act: bool = False, extra: list[dict] | None = None) -> dict:
    h = health()
    props = proposals(h) + [dict(x, score=round(x.get("impact", 3) / max(1, x.get("effort", 3)), 2)) for x in (extra or [])]
    props += watch_policies() + watch_variety() + watch_wallet()
    done: list[str] = []
    if act:
        for p in [p for p in props if p["autonomy"] == "auto" and p["id"].startswith("topup-")]:
            try:
                got = topup(p["id"].removeprefix("topup-"))
                done.append(f"{p['id']}: +{len(got)} topics")
            except Exception as e:  # noqa: BLE001 - a flaky LLM must not break the scan
                done.append(f"{p['id']}: failed ({type(e).__name__})")
    props.sort(key=lambda p: (-p["score"], -p["impact"]))
    port = portfolio()
    write_report(h, props, done, port)
    return {"health": h, "proposals": props, "done": done, "portfolio": port}


def watch_policies() -> list[dict]:
    """Re-read the rule pages that govern us. A changed page is an urgent, cheap-to-review proposal; pages this machine cannot read
    become one proposal to fetch them another way (the weekly session has Exa) and `faceless policy --record`. Never blocks the scan."""
    try:
        res = policy.check()
        policy.write_report(res)
    except Exception:  # noqa: BLE001 - network or disk trouble must not break the weekly scan
        return []
    out = [dict(p, score=round(p["impact"] / p["effort"], 2)) for p in policy.proposals(res)]
    blind = [r["id"] for r in res if r["status"] == "unfetchable"]
    if blind:
        out.append({"id": "policy-fetch", "title": f"{len(blind)} rule pages need a session fetch (Exa) and `faceless policy --record`", "category": "compliance",
                    "impact": 3, "effort": 1, "autonomy": "operator", "why": ", ".join(blind), "score": 3.0})
    return out


def watch_wallet(days_floor: int = 21) -> list[dict]:
    """Muapi supplies images once the free Cloudflare budget is spent: warn the owner while there are still weeks of runway."""
    try:
        from faceless import forecast
        from faceless.providers import images
        bal = images.muapi_balance()
        if bal is None:
            return []
        per_day = max(0.01, forecast.monthly_cost()["muapi"] / 30)
        left = bal / per_day
    except Exception:  # noqa: BLE001 - a status check must never break the weekly scan
        return []
    if left >= days_floor:
        return []
    return [{"id": "muapi-topup", "title": f"Top up the Muapi wallet: ${bal:.2f} is about {left:.0f} days of images", "category": "supply",
             "impact": 5, "effort": 1, "autonomy": "owner", "why": f"at about ${per_day:.2f} a day; when it hits zero images fall back to OpenRouter (8x dearer) or placeholder art",
             "score": 5.0}]


def watch_variety() -> list[dict]:
    """Sameness audit of the last videos (YouTube's inauthentic-content risk). Never blocks the scan."""
    try:
        return variety.proposals(variety.write())
    except Exception:  # noqa: BLE001 - embeddings or disk trouble must not break the weekly scan
        return []


def portfolio() -> list[str]:
    """The empire gauntlet's view for the weekly report: what the agent builds next, what is built and waiting, what the owner unlocks.
    Rewrites channel/empire/RANKING.md. Never blocks the scan."""
    try:
        rows = empire.write()
    except Exception as e:  # noqa: BLE001 - a bad portfolio line must not break the scan
        return [f"portfolio unavailable ({type(e).__name__})"]
    pick = lambda lane: [f"{r['id']} {r['name']} ({r['score']})" for r in rows if r["lane"] == lane][:3]  # noqa: E731
    out = []
    for title, lane in (("Agent builds next", "agent"), ("Built, waiting for the owner", "launch")):
        if got := pick(lane):
            out.append(f"{title}: " + "; ".join(got))
    asks = empire.asks(rows)[:3]
    if asks:
        out.append("Owner unlocks the most: " + "; ".join(f"{g} ({t} pts)" for g, t, _ in asks))
    return out


def write_report(h: dict, props: list[dict], done: list[str], port: list[str] | None = None) -> None:
    day = _now().strftime("%Y-%m-%d")
    lines = [f"# Opportunities, {day}", "",
             f"Last {h['days']} days: {h['videos']} videos, {h['held']} held ({round(h['hold_rate'] * 100)}%), "
             f"images {h['images'] or 'n/a'}, paid ${h['paid_usd']}, metrics rows {h['metrics_rows']}, publish mode `{h['publish_mode']}`.",
             "", "No revenue data exists yet: ranking is impact on output/reach divided by effort, not profit.", "",
             "| # | Opportunity | Type | Impact | Effort | Who | Why |", "|---|---|---|---|---|---|---|"]
    for i, p in enumerate(props, 1):
        lines.append(f"| {i} | {p['title']} | {p['category']} | {p['impact']} | {p['effort']} | {p['autonomy']} | {p['why']} |")
    if done:
        lines += ["", "## Done by the scanner this run", *[f"- {d}" for d in done]]
    if port:
        lines += ["", "## Portfolio (full ranking in channel/empire/RANKING.md)", *[f"- {p}" for p in port]]
    lines += ["", "## Who can act", *[f"- **{k}**: {v}" for k, v in AUTONOMY.items()]]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with open(OPPS, "a", encoding="utf-8") as f:
        f.write(json.dumps({"day": day, "health": h, "proposals": props, "done": done}, ensure_ascii=False) + "\n")
