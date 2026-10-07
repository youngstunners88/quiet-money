"""The empire gauntlet: every income idea is diverged into a portfolio, attacked, scored, sequenced, and instrumented.

channel/empire/portfolio.jsonl is the data (one line per opportunity, 1-5 judgment scores plus evidence). The loop:
  1. DIVERGE   add opportunities (the weekly scout and the owner's notes feed this file)
  2. ATTACK    hard kills: platform-terms or IP 'block'; soft penalties for saturation, terms 'watch', agent fit
  3. SCORE     (upside x leverage x automation x speed) / (effort x (1 + risk)), then penalties
  4. SEQUENCE  an item is unblocked only when everything it feeds on is at least built
  5. INSTRUMENT every item names its metric and kill rule; stage moves only with evidence
  6. ASK       which owner gates (accounts, money, legal) unlock the most score, ranked
Scores are judgment, not data, until metrics exist; the weekly run re-scores with evidence and logs the ranking.
`python -m faceless empire` rewrites channel/empire/RANKING.md.
"""

from __future__ import annotations

import json
from collections import defaultdict

from faceless.config import STUDIO

DIR = STUDIO / "channel" / "empire"
PORTFOLIO = DIR / "portfolio.jsonl"
RANKING = DIR / "RANKING.md"
STAGES = ["idea", "vetted", "built", "pilot", "scaled"]   # built = the asset exists and is verified; pilot = live at small scale
GATES = {   # owner-only steps: money, accounts, legal, face. Codes keep the ask list consistent.
    "channels": "Create the YouTube, TikTok and Instagram accounts (@quietmoneyrules), connect them, and turn on auto-posting",
    "cloudflare": "Pay for Cloudflare Workers ($5/month) so image generation stops running out",
    "shop": "Open a Gumroad shop (and Etsy for printables); approve prices and listings",
    "email": "Pick an email service, a domain and a postal address, and connect them",
    "domain": "Register a domain with one mailbox (the identity layer)",
    "flow": "Generate the day's 3 Flow clips (about 10 minutes) and drop them in the inbox",
    "fiverr": "List the gig on your Fiverr account and handle client messages",
    "podcast": "Open a free podcast host account",
    "pod": "Open Etsy + Printify accounts",
    "adobe": "Open an Adobe Stock contributor account and confirm the image model's terms allow resale",
    "affiliate": "Sign affiliate programs, after a compliance review of each offer",
}
SAT = {"low": 1.0, "med": 0.9, "high": 0.7}
TOS = {"ok": 1.0, "watch": 0.8}
AGENT = {"yes": 1.0, "partly": 0.8, "no": 0.5}


def load() -> list[dict]:
    if not PORTFOLIO.exists():
        return []
    out = []
    for line in PORTFOLIO.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line) if line.strip() else None
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict) and r.get("id"):
            out.append(r)
    return out


def attack(o: dict) -> dict:
    """Round 2. 'block' on terms or IP kills the idea outright; the rest only discount it."""
    a = o.get("attack", {})
    blocked = [k for k in ("tos", "ip") if a.get(k) == "block"]
    return {"killed": bool(blocked), "why": ", ".join(blocked), "mult": SAT.get(a.get("saturation", "med"), 0.9)
            * TOS.get(a.get("tos", "ok"), 1.0) * AGENT.get(a.get("agent", "yes"), 1.0)}


def score(o: dict) -> float:
    base = o["upside"] * o["leverage"] * o["automation"] * o["speed"] / (o["effort"] * (1 + o["risk"]))
    return round(base * attack(o)["mult"], 2)


def unblocked(o: dict, by_id: dict) -> bool:
    need = STAGES.index("built")
    return all(f not in by_id or STAGES.index(by_id[f]["stage"]) >= need for f in o.get("feeds", []))


def lane(o: dict, by_id: dict) -> str:
    """Who can move this next: dead | agent (build now) | launch (built; the owner's gate opens it) | owner (their act is the work)
    | waiting | validate | running."""
    if attack(o)["killed"]:
        return "dead"
    if o["stage"] == "scaled" or (o["stage"] == "pilot" and not o.get("build_gates")):
        return "running"
    if o.get("build_gates"):
        return "owner"
    if o["stage"] == "built":
        return "launch" if o.get("gates") else "running"
    if not unblocked(o, by_id):
        return "waiting"
    return "validate" if o["stage"] == "idea" else "agent"


def next_action(o: dict, by_id: dict) -> str:
    ln = lane(o, by_id)
    if ln == "dead":
        return "dead: do not build"
    if ln == "owner":
        return "owner: " + "; ".join(GATES[g] for g in o["build_gates"])
    if ln == "launch":
        return "built and verified. Launch needs the owner: " + "; ".join(GATES[g] for g in o["gates"])
    if ln == "waiting":
        return "waits for " + ", ".join(f for f in o["feeds"] if f in by_id and STAGES.index(by_id[f]["stage"]) < STAGES.index("built"))
    if ln == "validate":
        return "validate cheaply (research, one test asset), then vet"
    launch = (" Launch needs the owner: " + "; ".join(GATES[g] for g in o["gates"])) if o["gates"] else ""
    if ln == "agent":
        return "agent builds it now." + launch
    return f"measure; kill if: {o['kill']}." + launch


def rank() -> list[dict]:
    items = load()
    by_id = {o["id"]: o for o in items}
    rows = []
    for o in items:
        at = attack(o)
        rows.append({**o, "score": 0.0 if at["killed"] else score(o), "killed": at["killed"], "why_dead": at["why"],
                     "action": next_action(o, by_id), "unblocked": unblocked(o, by_id), "lane": lane(o, by_id)})
    rows.sort(key=lambda r: (-r["score"], r["id"]))
    return rows


def asks(rows: list[dict]) -> list[tuple[str, float, list[str]]]:
    """Owner gates ranked by the total score they unlock (items not yet scaled and not dead)."""
    g: dict = defaultdict(lambda: [0.0, []])
    for r in rows:
        if r["killed"] or r["stage"] == "scaled":
            continue
        for gate in dict.fromkeys(r["gates"] + r.get("build_gates", [])):   # one item counts once per gate
            g[gate][0] += r["score"]
            g[gate][1].append(r["id"])
    return sorted(((GATES.get(k, k), round(v[0], 1), v[1]) for k, v in g.items()), key=lambda t: -t[1])


def report() -> str:
    rows = rank()
    L = ["# Empire ranking", "",
         "One agent (Claude Code) is the operator; skills are departments, scheduled routines are shifts, deterministic code is the factory,",
         "and the owner is the board for money, accounts, legal and face. Scores are judgment until metrics exist (see `faceless forecast`).", ""]

    def table(title: str, lanes: tuple, note: str = "") -> None:
        sel = [r for r in rows if r["lane"] in lanes]
        if not sel:
            return
        L.extend(["## " + title, note, "| id | opportunity | rail | stage | score | next |", "|---|---|---|---|---|---|"] if note else
                 ["## " + title, "| id | opportunity | rail | stage | score | next |", "|---|---|---|---|---|---|"])
        L.extend(f"| {r['id']} | {r['name']} | {r['rail']} | {r['stage']} | {r['score']} | {r['action']} |" for r in sel)
        L.append("")
    table("The agent builds these now", ("agent",), "Unblocked and buildable without the owner; only the launch needs them.")
    table("Built: waiting for the owner to launch", ("launch",), "Finished and checked; one owner step turns each on.")
    table("Needs the owner first", ("owner",), "The owner's act is the work.")
    table("Running: measure against the kill rule", ("running",))
    table("Waiting on another item", ("waiting",))
    table("Ideas to validate cheaply", ("validate",))
    L += ["## What the owner unlocks, biggest first", ""]
    L += [f"- **{gate}**: {total} points ({', '.join(ids)})" for gate, total, ids in asks(rows)]
    L += ["", "## Killed by the attack round", ""]
    L += [f"- **{r['id']} {r['name']}** (blocked on {r['why_dead']}): {r['note']}" for r in rows if r["killed"]]
    L += ["", "## How a stage moves", "idea -> vetted: evidence the platform allows it and the numbers can work. vetted -> built: the asset exists and its numbers are verified. "
          "built -> pilot: live at small scale. pilot -> scaled: the metric beat its kill rule for 4 weeks. An item that hits its kill rule is killed and the reason is written here."]
    return "\n".join(L) + "\n"


def write() -> list[dict]:
    DIR.mkdir(parents=True, exist_ok=True)
    RANKING.write_text(report(), encoding="utf-8")
    return rank()
