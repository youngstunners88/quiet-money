"""Command line: `python -m faceless <command>` from the repo root."""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from faceless import config, ledger
from faceless.config import Paths


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
    print((Paths.reports / f"{job.id}.md").read_text(encoding="utf-8"))
    return 0 if rep["passed"] else 2


def cmd_publish(args) -> int:
    from faceless.providers import publish
    from faceless.state import load_job
    job = load_job(args.job)
    meta = json.loads((job.dir / "meta.json").read_text(encoding="utf-8"))
    res = publish.publish(job, meta)
    job.artifacts["publish"] = res
    if job.status != "published":
        job.advance("published", manual=True)
    print(json.dumps(res, indent=2, default=str))
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
