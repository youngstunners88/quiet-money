"""Command line: `python -m faceless <command>` from the repo root."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from faceless import config, ledger
from faceless.config import Paths


def cfg_cards_mode() -> str:
    return config.load()["production"].get("cards", {}).get("mode", "auto")


def cmd_doctor(_args) -> int:
    ok = True
    print("Faceless Studio doctor")
    for tool in ("ffmpeg", "ffprobe"):
        found = shutil.which(tool)
        print(f"  {'OK ' if found else 'ERR'} {tool}: {found or 'missing'}")
        ok &= bool(found)
    for mod in ("PIL", "numpy", "edge_tts", "requests"):
        try:
            __import__(mod)
            print(f"  OK  python:{mod}")
        except ImportError:
            print(f"  ERR python:{mod} (pip install -r requirements.txt)")
            ok = False
    fonts = sorted(p.name for p in Paths.fonts.glob("*.ttf"))
    print(f"  {'OK ' if fonts else 'ERR'} fonts: {', '.join(fonts) or 'none'}")
    from faceless.pipeline import cards
    print(f"  {'OK ' if cards.available() else '..  '}motion cards: HyperFrames {cards.CLI} needs Node 22+ and npx "
          f"({'ready' if cards.available() else 'unavailable: videos use stills only'}); mode {cfg_cards_mode()}")
    keys = {
        "llm": ["GEMINI_API_KEY", "OPENROUTER_API_KEY"],
        "images": ["CLOUDFLARE_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "OPENROUTER_API_KEY"],
        "voice (optional premium)": ["ELEVENLABS_API_KEY"],
        "publish (optional)": ["UPLOAD_POST_API_KEY", "UPLOAD_POST_USER"],
        "decide (optional)": ["TYPESAFE_API_KEY"],
        "connected apps (Composio)": ["COMPOSIO_API_KEY"],
    }
    for group, names in keys.items():
        status = ", ".join(f"{n}={'set' if config.env(n, n.replace('_KEY', '')) else 'missing'}" for n in names)
        print(f"  ..  {group}: {status}")
    cfg = config.load()
    print(f"  ..  channel: {cfg['channel']['name']} | {cfg['production']['videos_per_day']}/day | "
          f"pillars: {', '.join(p.id for p in cfg['pillars'])} | publish mode: {cfg['publish']['mode']}")
    return 0 if ok else 1


def cmd_make(args) -> int:
    from faceless import orchestrator
    from faceless.state import new_job
    Paths.ensure()
    if args.script:
        src = json.loads(open(args.script, encoding="utf-8").read())
        src.setdefault("source", "human")
        job = new_job(args.pillar, args.topic or src.get("title", "untitled"), slot=args.slot)
        (Paths.final / f"{job.id}.json").write_text(json.dumps(src, indent=2, ensure_ascii=False), encoding="utf-8")
        orchestrator.produce(job, judge=not args.no_judge, prefer_voice=args.voice, do_publish=not args.no_publish)
    else:
        job = orchestrator.run_one(args.pillar, args.topic, slot=args.slot, judge=not args.no_judge,
                                   prefer_voice=args.voice, do_publish=not args.no_publish)
    print(json.dumps({"job": job.id, "status": job.status, "scores": job.scores,
                      "video": job.artifacts.get("video")}, indent=2))
    return 0


def cmd_daily(args) -> int:
    from faceless import orchestrator
    jobs = orchestrator.daily(args.count, extra=args.extra, pillar=args.pillar, judge=not args.no_judge,
                              do_publish=not args.no_publish)
    for j in jobs:
        print(f"{j.slot + 1}. [{j.status:9}] {j.scores.get('gauntlet', '-'):>3}  {j.pillar:10} {j.artifacts.get('title', j.topic)}")
    print(json.dumps(ledger.summary(), indent=1))
    if not jobs:
        print("Nothing to do: every requested slot already has a finished video.")
        return 0
    produced = sum(1 for j in jobs if j.status in ("published", "packaged", "held"))
    return 0 if produced else 1


def cmd_status(_args) -> int:
    from faceless.state import all_jobs
    day = ledger.today()
    for j in all_jobs():
        if j.day == day:
            print(f"{j.id:70} {j.status:10} {j.scores}")
    print(json.dumps(ledger.summary(), indent=1))
    return 0


def cmd_ideas(args) -> int:
    from faceless.pipeline import ideate
    reserved: list[str] = []
    for _ in range(args.n):
        item = ideate.next_topic(args.pillar, reserved)
        reserved.append(item["topic"])
        print(json.dumps(item, ensure_ascii=False))
    return 0


def cmd_gauntlet(args) -> int:
    from faceless import gauntlet
    from faceless.pipeline import ideate, package
    from faceless.state import load_job
    job = load_job(args.job)
    scr = json.loads((Paths.final / f"{job.id}.json").read_text(encoding="utf-8"))
    vo = json.loads((job.dir / "voice.json").read_text(encoding="utf-8"))
    imgs = json.loads((job.dir / "images.json").read_text(encoding="utf-8"))
    info = json.loads((job.dir / "render.json").read_text(encoding="utf-8"))
    history = [h for h in ideate.history_texts() if h not in (job.topic, scr.get("title"))]
    gates = gauntlet.check_script(scr, history)
    if not args.no_judge:
        from faceless import research
        gates += gauntlet.judge_script(scr, job.id, brief=research.brief(job.artifacts.get("brief")))[0]
    gates += gauntlet.check_voice(vo) + gauntlet.check_visuals(imgs, len(scr["beats"]))
    gates += gauntlet.check_render(info, vo) + gauntlet.check_package(package.run(job, scr))
    rep = gauntlet.report(job, gates)
    job.scores = {**job.scores, "gauntlet": rep["score"], "passed": rep["passed"]}   # the latest verdict wins
    job.save()
    print((Paths.reports / f"{job.id}.md").read_text(encoding="utf-8"))
    return 0 if rep["passed"] else 2


def cmd_publish(args) -> int:
    from faceless.providers import publish
    from faceless.state import load_job
    job = load_job(args.job)
    if not job.scores.get("passed") and not args.force:
        # Rule 6: held or failing videos ship only after their gates pass (`faceless gauntlet <job>` re-checks)
        print(f"{job.id} has not passed the gauntlet (status {job.status}, score {job.scores.get('gauntlet', '-')}). "
              f"Fix it and re-run `python -m faceless gauntlet {job.id}`, or pass --force after a human review.",
              file=sys.stderr)
        return 2
    meta = json.loads((job.dir / "meta.json").read_text(encoding="utf-8"))
    res = publish.publish(job, meta)
    job.artifacts["publish"] = res
    if job.status != "published":
        job.advance("published", manual=True, forced=bool(args.force and not job.scores.get("passed")))
    print(json.dumps(res, indent=2, default=str))
    return 0


def cmd_scout(args) -> int:
    from faceless import scout
    extra = json.loads(Path(args.import_file).read_text(encoding="utf-8")) if args.import_file else None
    res = scout.run(act=args.act, extra=extra)
    print((scout.REPORT).read_text(encoding="utf-8"))
    return 0


def cmd_empire(_args) -> int:
    from faceless import empire
    empire.write()
    print(empire.RANKING.read_text(encoding="utf-8"))
    return 0


def cmd_kit(args) -> int:
    from faceless import repurpose
    if args.issue:
        out = repurpose.weekly_issue(end=args.target)
        print(out or "no kit items in the last 7 days; run `kit` first")
        return 0 if out else 1
    res = repurpose.build(args.target)
    for r in res:
        print(r["job"], "->", r.get("error") or f"{r['carousel']} slides, audio={'yes' if r['audio'] else 'no'}, {len(r['files'])} files")
    if not res:
        print("no packaged videos matched; pass a post day (YYYY-MM-DD) or a job id")
    return 0 if res and not any("error" in r for r in res) else 1


def cmd_flow(args) -> int:
    from faceless import flow
    if args.action == "status":
        print(json.dumps(flow.status(), indent=2))
        return 0
    path = flow.shotlist(args.day)
    print(path.read_text(encoding="utf-8"))
    return 0


def cmd_products(_args) -> int:
    from faceless import products
    res = products.build_all()
    bad = 0
    for slug, r in res.items():
        print(f"{slug}: {'VERIFIED' if r['verified'] else 'NOT VERIFIED'}, {r['previews']} previews -> {r['file']}")
        for name, got, want, good in r["rows"]:
            print(f"  {'ok ' if good else 'BAD'} {name}: sheet={got} python={want}")
        for e in r["errors"]:
            print("  error:", e)
        bad += 0 if r["verified"] else 1
    return 1 if bad else 0


def cmd_forecast(_args) -> int:
    from faceless import forecast
    print(forecast.report())
    return 0


def cmd_memory(args) -> int:
    from faceless import memory
    if args.rebuild or not memory.DB.exists():
        print(f"indexed {memory.build()} scripts")
    for r in memory.search(" ".join(args.query), pillar=args.pillar, status=args.status, n=args.n):
        print(f"{r['day']} {r['pillar']:10} {r['status']:9} {r['score'] or '-':>4}  {r['title']}\n    {r['match']}")
    return 0


def cmd_keywords(args) -> int:
    from faceless import keywords
    if args.backlog:
        from faceless.pipeline import ideate
        used = {h.lower() for h in ideate.history_texts()}
        items = [i for i in ideate.load_backlog() if i["topic"].lower() not in used][: args.backlog]
        for i in items:
            d = keywords.demand(i["topic"])
            print(f"{d['score']:>2}  {i['pillar']:10} {i['topic']}" + (f"  <- {d['phrases'][0]}" if d["phrases"] else ""))
        return 0
    d = keywords.demand(" ".join(args.text))
    print(f"demand score {d['score']} (autocomplete phrases sharing 2+ words; 0 = no search signal)")
    for p in d["phrases"]:
        print("  -", p)
    return 0


def cmd_composio(args) -> int:
    from faceless.providers import composio_tools as ct
    if args.action == "status":
        conns = ct.connected_toolkits()
        print(f"Composio user: {ct.user_id()}")
        print("Connected:", ", ".join(f"{k} ({v})" for k, v in conns.items()) or "nothing yet")
        return 0
    if args.action == "connect":
        if args.target in ct.connected_toolkits():
            print(f"{args.target} is already connected for {ct.user_id()}.")
            return 0
        req = ct.connect(args.target)
        print(f"Open this link to connect {args.target}:\n{req.redirect_url}")
        if args.wait:
            acct = req.wait_for_connection()
            print(f"Connected: {getattr(acct, 'id', acct)} (status {getattr(acct, 'status', '?')})")
        return 0
    if args.action == "call":
        res = ct.execute(args.target, json.loads(args.args or "{}"))
        print(json.dumps(res, indent=2, default=str)[: args.max_chars])
        return 0
    return 1


def cmd_site(args) -> int:
    from faceless import site
    if args.action == "build":
        print(json.dumps(site.build(), indent=2))
    else:
        print(json.dumps(site.indexnow(), indent=2))
    return 0


def cmd_aeo(args) -> int:
    from faceless import aeo
    rows = aeo.track(engines=args.engines.split(",") if args.engines else None)
    print(json.dumps(aeo.summary(rows), indent=2, ensure_ascii=False))
    return 0


def cmd_brand(_args) -> int:
    from faceless import brand
    bg = brand.generate_background()
    print(json.dumps(brand.build(bg), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    config.load_dotenv()
    p = argparse.ArgumentParser(prog="faceless", description="Faceless Studio engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="check tools, fonts, keys").set_defaults(fn=cmd_doctor)
    m = sub.add_parser("make", help="produce one video")
    m.add_argument("--pillar", required=True, choices=[x.id for x in config.load()["pillars"]])
    m.add_argument("--topic")
    m.add_argument("--script", help="path to a hand-written script JSON (skips the LLM)")
    m.add_argument("--slot", type=int, default=0)
    m.add_argument("--voice", choices=["edge", "elevenlabs", "gemini"])
    m.add_argument("--no-judge", action="store_true")
    m.add_argument("--no-publish", action="store_true")
    m.set_defaults(fn=cmd_make)
    d = sub.add_parser("daily", help="produce the day's batch (resumes: only fills slots without a finished video)")
    d.add_argument("--count", type=int)
    d.add_argument("--extra", type=int, default=0, help="make N more now; they bank into the next free posting slots")
    d.add_argument("--pillar", choices=[x.id for x in config.load()["pillars"]], help="series for every new slot (with --extra)")
    d.add_argument("--no-judge", action="store_true")
    d.add_argument("--no-publish", action="store_true")
    d.set_defaults(fn=cmd_daily)
    sub.add_parser("status", help="today's jobs and spend").set_defaults(fn=cmd_status)
    sc = sub.add_parser("scout", help="rank the next best opportunities; --act tops up topic backlogs")
    sc.add_argument("--act", action="store_true", help="do the safe auto actions (backlog top-up) too")
    sc.add_argument("--import", dest="import_file", help="JSON list of external findings from web research")
    sc.set_defaults(fn=cmd_scout)
    sub.add_parser("empire", help="run the empire gauntlet: rank the income portfolio, kill the bad ideas, list what the owner unlocks").set_defaults(fn=cmd_empire)
    kt = sub.add_parser("kit", help="repurposing kit per packaged video (thread, LinkedIn, carousel, pin, newsletter item, audio)")
    kt.add_argument("target", nargs="?", help="post day YYYY-MM-DD or job id (default: today); with --issue, the last day of the week")
    kt.add_argument("--issue", action="store_true", help="compile the week's newsletter items into one issue")
    kt.set_defaults(fn=cmd_kit)
    fl = sub.add_parser("flow", help="Flow lane: today's 3-prompt shot list for the owner's Google Flow session, or inbox status")
    fl.add_argument("action", nargs="?", choices=["shotlist", "status"], default="shotlist")
    fl.add_argument("--day", help="YYYY-MM-DD (default today)")
    fl.set_defaults(fn=cmd_flow)
    sub.add_parser("products", help="build the spreadsheet products, recalculate them in LibreOffice, check against Python math, write listings").set_defaults(fn=cmd_products)
    sub.add_parser("forecast", help="the math: next batch cost, monthly cost, and assumption-labeled revenue ladder").set_defaults(fn=cmd_forecast)
    me = sub.add_parser("memory", help="search everything we've made (scripts, outcomes, failed gates)")
    me.add_argument("query", nargs="*")
    me.add_argument("--pillar")
    me.add_argument("--status", help="published | held | failed | packaged")
    me.add_argument("-n", type=int, default=5)
    me.add_argument("--rebuild", action="store_true", help="re-index first (automatic if no index yet)")
    me.set_defaults(fn=cmd_memory)
    kw = sub.add_parser("keywords", help="YouTube search demand for a topic or title (free autocomplete)")
    kw.add_argument("text", nargs="*", help="topic or title to check")
    kw.add_argument("--backlog", type=int, default=0, help="score the next N unused backlog topics instead")
    kw.set_defaults(fn=cmd_keywords)
    i = sub.add_parser("ideas", help="pull/generate the next topic for a pillar")
    i.add_argument("--pillar", required=True)
    i.add_argument("--n", type=int, default=1)
    i.set_defaults(fn=cmd_ideas)
    g = sub.add_parser("gauntlet", help="re-run all gates on a finished job")
    g.add_argument("job")
    g.add_argument("--no-judge", action="store_true")
    g.set_defaults(fn=cmd_gauntlet)
    pb = sub.add_parser("publish", help="(re)publish a packaged job")
    pb.add_argument("job")
    pb.add_argument("--force", action="store_true", help="publish even though the gauntlet did not pass (human-reviewed)")
    pb.set_defaults(fn=cmd_publish)
    cp = sub.add_parser("composio", help="connected apps via Composio: status | connect <toolkit> | call <TOOL_SLUG>")
    cp.add_argument("action", choices=["status", "connect", "call"])
    cp.add_argument("target", nargs="?", help="toolkit slug (connect) or tool slug (call)")
    cp.add_argument("--args", help="JSON arguments for call")
    cp.add_argument("--wait", action="store_true", help="block until the connect link is completed")
    cp.add_argument("--max-chars", type=int, default=4000)
    cp.set_defaults(fn=cmd_composio)
    sub.add_parser("brand", help="(re)generate the brand kit in channel/brand-kit").set_defaults(fn=cmd_brand)
    ae = sub.add_parser("aeo", help="probe AI answer engines: are we recommended/cited? (writes analytics/aeo.jsonl)")
    ae.add_argument("--engines", help="comma list from gpt,claude,gemini,perplexity")
    ae.set_defaults(fn=cmd_aeo)
    st = sub.add_parser("site", help="Money Rules Library website: build | indexnow")
    st.add_argument("action", choices=["build", "indexnow"])
    st.set_defaults(fn=cmd_site)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
