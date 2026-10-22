"""Command line: `python -m faceless <command>` from the repo root."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from faceless import config, ledger
from faceless.config import Paths
from faceless.fsutil import write_atomic


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
    from faceless import musiclib, qa
    n_tracks = len(musiclib.tracks())
    print(f"  {'OK ' if n_tracks else '..  '}music library: {n_tracks} tracks ({'real instrumental beds' if n_tracks else 'procedural bed only; `music --build`'}); "
          f"production.music = {config.load()['production'].get('music')}")
    from faceless.providers import images as _img
    bal = _img.muapi_balance()
    print(f"  {'OK ' if bal else '..  '}Muapi image fallback: " + (f"wallet ${bal:.2f}" if bal is not None else "no key or unreachable (falls back to OpenRouter)"))
    print(f"  {'OK ' if qa.enabled() else '..  '}semantic QA (Clef, else the Muapi judge): {'on' if qa.enabled() else 'off (needs the Cloudflare keys or a Muapi key, and [qa] enabled)'}")
    keys = {
        "llm": ["GEMINI_API_KEY", "LONGCAT_API_KEY", "OPENROUTER_API_KEY"],
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
    if _blocked_by_preflight(args):
        return 4
    from faceless import orchestrator
    from faceless.state import new_job
    Paths.ensure()
    if args.script:
        src = json.loads(open(args.script, encoding="utf-8").read())
        src.setdefault("source", "human")
        job = new_job(args.pillar, args.topic or src.get("title", "untitled"), slot=args.slot)
        write_atomic(Paths.final / f"{job.id}.json", json.dumps(src, indent=2, ensure_ascii=False))
        orchestrator.produce(job, judge=not args.no_judge, prefer_voice=args.voice, do_publish=not args.no_publish)
    else:
        job = orchestrator.run_one(args.pillar, args.topic, slot=args.slot, judge=not args.no_judge,
                                   prefer_voice=args.voice, do_publish=not args.no_publish)
    print(json.dumps({"job": job.id, "status": job.status, "scores": job.scores,
                      "video": job.artifacts.get("video")}, indent=2))
    return 0


def _blocked_by_preflight(args) -> bool:
    """Refuse to start a run on a machine that cannot finish it: nothing is spent on scripts that can never be rendered."""
    if getattr(args, "skip_preflight", False):
        return False
    from faceless import events, preflight
    blockers = preflight.gate()
    if not blockers:
        return False
    print("BLOCKED: this machine cannot finish a video, so nothing was started (and nothing was spent):")
    for b in blockers:
        print(f"  FAIL {b.name}: {b.detail}" + (f"\n       fix: {b.fix}" if b.fix else ""))
    print("Fix the above and run again (or --skip-preflight if you know better).")
    events.emit("PREFLIGHT_BLOCKED", checks=[b.name for b in blockers])
    return True


def cmd_daily(args) -> int:
    if _blocked_by_preflight(args):
        return 4
    from faceless import orchestrator
    jobs = orchestrator.daily(args.count, extra=args.extra, pillar=args.pillar, judge=not args.no_judge,
                              do_publish=not args.no_publish)
    for j in jobs:
        print(f"{j.slot + 1}. [{j.status:9}] {j.scores.get('gauntlet', '-'):>3}  {j.pillar:10} {j.artifacts.get('title', j.topic)}")
    print(json.dumps(ledger.summary(), indent=1))
    if not jobs:
        from faceless import safety
        if safety.paused():
            print(f"HALTED: the studio is paused ({safety.paused()}). `python -m faceless pause --resume` to continue.")
            return 3
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


def cmd_caption_check(args) -> int:
    from faceless import capcheck
    res = capcheck.check(Path(args.media), Path(args.ass), args.max)
    print(json.dumps(res, indent=1))
    return 0 if res["ok"] else 1


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
    job.save()   # a job that was already published still keeps what this run added (the YouTube upload)
    print(json.dumps(res, indent=2, default=str))
    return 0


def cmd_host(args) -> int:
    """The recurring host: status | voice | character | line | clip [--apply] | anchor VIDEO."""
    from faceless import host
    a = args.action
    if a == "status":
        print(json.dumps(host.status(), indent=1))
    elif a == "voice":
        print("voice profile:", host.design_voice(force=args.force))
    elif a == "character":
        print("character:", host.create_character())
    elif a == "line":
        key, text, backend = host.choose_line()
        print(f"chosen by {backend}: [{key}] {text}")
    elif a == "clip":
        line = args.text or host.choose_line()[1]
        res = host.make_clip(line, apply=args.apply, max_usd=args.max_usd)
        print(json.dumps(res, indent=1, default=str))
        if not args.apply:
            print("priced only; add --apply to generate (spends the price above)")
    elif a == "anchor":
        print("voice anchor:", host.keep_voice_anchor(args.text))
    return 0


def cmd_post_backlog(args) -> int:
    """Put made, quality-passed videos that never reached YouTube on today's remaining slots (strongest series first)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from faceless import backlog, safety
    from faceless.providers import ProviderError, ProviderUnavailable, publish
    from faceless.state import all_jobs
    jobs = all_jobs()
    todo = backlog.plan(jobs, args.n)
    for job, when in todo:
        print(f"{when:%a %H:%M %Z}  {job.pillar:<10} score {job.scores.get('gauntlet')}  {job.artifacts.get('title') or job.id}")
    if not todo or not args.apply:
        print("nothing to post" if not todo else "dry run; add --apply to schedule these")
        return 0
    failed = 0
    for job, when in todo:
        job.artifacts["youtube_plan"] = {"post_at": when.isoformat()}
        meta = backlog.meta(job)
        try:
            safety.guard("publish via youtube")
            res = publish.youtube(job, meta)
            print(f"scheduled {job.id}: {res.get('video_id')} at {when:%H:%M %Z}")
        except (ProviderError, ProviderUnavailable) as e:
            failed += 1
            print(f"NOT scheduled {job.id}: {e}", file=sys.stderr)
        job.save()
        if failed and isinstance(sys.exc_info()[1], ProviderUnavailable):
            break
    return 1 if failed else 0


def cmd_yt_channel(args) -> int:
    """Show what differs between studio.toml [youtube] and the live channel; --apply makes the channel match."""
    from faceless import ytchannel
    want = ytchannel.desired()
    now = ytchannel.live(want["channel_id"])
    todo = ytchannel.plan(want, now)
    print("the live channel already matches studio.toml" if not todo else "to change: " + ", ".join(todo))
    if todo and args.apply:
        print("done: " + ", ".join(ytchannel.apply(want, now, todo)))
    elif todo:
        print("run again with --apply to make these changes")
    print("by hand in Studio (the API cannot): profile picture channel/brand-kit/avatar.png, channel links, pinning a comment")
    return 0


def cmd_yt_verify(args) -> int:
    """Read back every video scheduled in the last 14 days: still there, processed, public on time. Exit 2 if any is not."""
    from datetime import timedelta
    from faceless import ytchannel
    from faceless.providers import ProviderUnavailable
    from faceless.state import all_jobs
    since = datetime.now(timezone.utc) - timedelta(days=14)
    videos = {y["video_id"]: {"job": j.id, "post_at": y.get("post_at")} for j in all_jobs()
              if (y := j.artifacts.get("youtube")) and y.get("video_id") and (not y.get("post_at") or datetime.fromisoformat(y["post_at"]) > since)}
    try:
        problems, rows = ytchannel.verify(videos)
    except ProviderUnavailable as e:    # a spent quota is a wait, not a defect: say so plainly instead of a traceback
        print(f"yt-verify could not run: {e}. Nothing is wrong with the videos; run it again after 07:00 UTC.")
        return 1
    for r in rows:
        print(f"{r['video']}  {str(r['privacy']):8} {str(r['processing']):10} views {r['views']:>6}  likes {r['likes']:>4}  comments {r['comments']:>3}  {r['job']}")
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(rows)} video(s) checked, {len(problems)} problem(s)")
    return 2 if problems else 0


def cmd_yt_comments(args) -> int:
    """Post the first comment on every scheduled YouTube video that has gone public."""
    from faceless.providers import publish
    done = publish.post_due_comments()
    print(f"first comment posted on {len(done)} video(s)" + (": " + ", ".join(done) if done else ""))
    return 0


def cmd_scout(args) -> int:
    from faceless import scout
    extra = json.loads(Path(args.import_file).read_text(encoding="utf-8")) if args.import_file else None
    scout.run(act=args.act, extra=extra)
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


def cmd_planner(args) -> int:
    from faceless import planner_art, planner_clean, product_planner as pp
    if args.action == "build":
        sizes = ("Letter", "A4") if args.size == "both" else (args.size,)
        res = pp.build(sizes, limit=args.days)
        for size, f in res["files"].items():
            print(f"{size}: {f['path']} ({f['mb']} MB)")
        print(f"{res['days']} days in {res['seconds']} s. Next: python -m faceless planner check")
        return 0
    if args.action == "check":
        bad = 0
        for name, ok, detail, hard in pp.check():
            print(f"{'ok  ' if ok else ('FAIL' if hard else 'warn')} {name}: {detail}")
            bad += 0 if ok or not hard else 1
        return 1 if bad else 0
    if args.action == "ingest":
        if not args.folder:
            raise SystemExit("usage: planner ingest <folder> [--start N]")
        done = planner_clean.ingest(Path(args.folder), args.start)
        print(f"{len(done)} pictures copied to assets/planner/source (days {done[0][0]} to {done[-1][0]})" if done else "no pictures found")
        return 0
    if args.action == "clean":
        box = tuple(float(v) for v in args.box.split(",")) if args.box else None
        rep = planner_clean.run_clean(box)
        hit = {k: v for k, v in rep.items() if v["removed"]}
        print(f"{len(rep)} pictures checked, {len(hit)} had a handle removed (report: assets/planner/clean-report.json). Look at assets/planner/clean-before-after.jpg before you trust it.")
        return 0
    if args.action == "inventory":
        print(json.dumps(planner_clean.inventory(), indent=2))
        return 0
    if args.action == "posters-make":
        from faceless import planner_poster_make
        print(f"typeset wellness posters {planner_poster_make.make()}")
        return 0
    from faceless import planner_cover
    folder = Path(config.STUDIO) / "channel" / "products" / pp.PRODUCT
    planner_cover.cover(1700, 2200).save(folder / "cover.png")
    print(folder / "cover.png")
    for name, style in (("cover-desk.png", "desk"), ("cover-coin.png", None)):                       # the alternates for A/B (skill faceless-cover)
        (planner_cover.cover(1700, 2200, style=style) if style else planner_cover.cover_coin(1700, 2200)).save(folder / name)
        print(folder / name)
    return 0


def cmd_panel(args) -> int:
    from faceless import panel
    brief = Path(args.brief).read_text(encoding="utf-8")
    res = panel.run(brief, [m.strip() for m in args.models.split(",") if m.strip()], args.runs, label=args.label or Path(args.brief).stem)
    for m, r in res["models"].items():
        print(f"{m}: votes {r['votes'] or 'none'}, failed {r['failed']}, mean confidence {r['mean_confidence']}, ${r['usd']}")
    print("tally:", res["tally"], "| saved:", panel.save(res))
    return 0


def cmd_autoresponder(_args) -> int:
    from faceless import autoresponder
    for path in autoresponder.write():
        print(path.relative_to(config.STUDIO) if hasattr(config, "STUDIO") else path)
    return 0


def cmd_brandkit(args) -> int:
    from faceless import brandkit
    if args.samples:
        for r in brandkit.samples():
            print(r["dir"])
        print(brandkit.write_gig())
        return 0
    if not args.name:
        print("give a channel name, or --samples")
        return 2
    try:
        r = brandkit.build(args.name, args.tagline, args.palette, args.niche, [x.strip() for x in args.pills.split(",") if x.strip()], args.out)
    except ValueError as e:
        print(e)
        return 2
    print(r["dir"], "->", r["zip"])
    return 0


def cmd_qa(args) -> int:
    from faceless import qa
    res = qa.calibrate(args.images, args.scripts)
    for kind in ("images", "scripts"):
        rows = res[kind]
        print(f"{kind}: {len(rows)} scored")
        keys = [k for k in (rows[0] if rows else {}) if k not in ("file", "flags")]
        for k in keys:
            vals = sorted(r[k] for r in rows)
            print(f"  {k}: median {vals[len(vals) // 2]:.2f}  p90 {vals[int(len(vals) * .9)]:.2f}  max {vals[-1]:.2f}  over-threshold {sum(1 for r in rows if k in r['flags'])}")
        for r in rows:
            if r["flags"]:
                print("   flagged", r["file"], {k: r[k] for k in keys}, r["flags"])
    return 0


def cmd_music(args) -> int:
    from faceless import musiclib
    if args.build:
        for r in musiclib.build(args.limit):
            print(json.dumps({k: r[k] for k in r if k in ("file", "seconds", "bpm", "failed", "skipped")}))
        return 0
    rows = musiclib.tracks()
    for t in rows:
        print(f"{t['file']:14} {t['seconds']:>5}s  {t['bpm']} bpm  {t['mood'][:70]}")
    print(f"{len(rows)} tracks; {len(musiclib.plan())} still to build (`music --build`)")
    return 0


def cmd_policy(args) -> int:
    from pathlib import Path

    from faceless import policy
    if args.record:
        pid, file = args.record
        res = [policy.record_text(pid, Path(file).read_text(encoding="utf-8", errors="replace"))]
    else:
        res = policy.check()
    policy.write_report(res)
    for r in res:
        print(f"{r['id']:34} {r['status']:12} {r['rules']:>3} rules" + (f"  +{len(r['added'])} -{len(r['removed'])}" if r["status"] == "changed" else ""))
    late = policy.stale()
    if late:
        print("never read or older than 14 days:", ", ".join(late))
    return 0


def cmd_variety(args) -> int:
    from faceless import variety
    variety.write(args.n)
    print(variety.REPORT.read_text(encoding="utf-8"))
    return 0


def _muapi_payload(args, upload: bool) -> dict:
    """--json FILE and --set key=value (values parse as JSON when they can; @file reads text). A local media file for an input
    becomes a hosted URL when `upload` is true (free); for an estimate it becomes a placeholder so nothing is uploaded."""
    from faceless import muapi
    payload = {}
    if args.json:
        payload.update(json.loads(Path(args.json).read_text(encoding="utf-8")))
    for item in args.set or []:
        k, eq, v = item.partition("=")
        if not eq:
            raise SystemExit(f"--set expects key=value, got {item!r}")
        if v.startswith("@") and Path(v[1:]).is_file() and Path(v[1:]).suffix.lower() in (".txt", ".md", ".json", ""):
            v = Path(v[1:]).read_text(encoding="utf-8").strip()
        else:
            try:
                v = json.loads(v)
            except ValueError:
                pass
        payload[k] = v
    media = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".webm", ".mp3", ".wav")

    def lift(v):
        if isinstance(v, str) and v.lower().endswith(media) and Path(v).is_file():
            return muapi.upload(v) if upload else "https://example.com/" + Path(v).name
        if isinstance(v, list):
            return [lift(x) for x in v]
        return v
    return {k: lift(v) for k, v in payload.items()}


def cmd_muapi(args) -> int:
    """The Muapi desk: find, inspect, price and run any model under the studio's spend limits."""
    from faceless import muapi, safety
    act, rest = args.action, args.rest
    if act == "catalog":
        rows = muapi.catalog(refresh=args.refresh)
        if args.category:
            rows = [m for m in rows if (m["category"] or "").lower() == args.category.lower()]
            for m in sorted(rows, key=lambda m: (m["cost"] if m["cost"] is not None else 9e9))[:args.limit]:
                print(f"{'~' if m['dynamic'] else ' '}${(m['cost'] if m['cost'] is not None else -1):8.4f}  {m['name']:46} {m['desc'][:70]}")
        else:
            from collections import Counter
            print(f"{len(rows)} enabled models")
            for cat, n in Counter(m["category"] for m in rows).most_common():
                print(f"  {n:4}  {cat}")
        return 0
    if act == "find":
        for m in muapi.find(" ".join(rest), category=args.category, family=args.family, max_usd=args.max_usd, limit=args.limit):
            print(f"{'~' if m['dynamic'] else ' '}${(m['cost'] if m['cost'] is not None else -1):8.4f}  {m['name']:44} [{m['category']}] needs {', '.join(m['required'][:4])}\n            {m['desc'][:100]}")
        return 0
    if act == "inspect" and rest:
        m = muapi.get(rest[0])
        if not m:
            print(f"unknown model {rest[0]!r}")
            return 1
        print(f"{m['name']}  [{m['category']}]  ${m['cost']} {'(varies with the request)' if m['dynamic'] else ''}\n{m['desc']}\n")
        for f in muapi.params(m["name"]):
            print(f"  {'*' if f['required'] else ' '} {f['name']:22} {str(f['type']):9} default={f['default']!r:12} {('options ' + str(f['enum'])[:60]) if f['enum'] else ''} {f['description'][:60]}")
        print("\n  * = required")
        return 0
    if act == "estimate" and rest:
        e = muapi.estimate(rest[0], _muapi_payload(args, upload=False))
        print("no price available" if e is None else f"${e:.4f}")
        return 0 if e is not None else 1
    if act == "run" and rest:
        name = rest[0]
        payload = _muapi_payload(args, upload=bool(args.yes))
        est = muapi.estimate(name, payload)
        print(f"{name}: estimated {'unknown' if est is None else f'${est:.4f}'}; spent today ${ledger.usd_total():.2f} of the ${safety.ceiling():.2f} ceiling")
        if not args.yes:
            print("dry run: nothing was spent. Add --yes to run it.")
            return 0
        out = muapi.run(name, payload, args.out, max_usd=args.max_usd, label=args.label)
        print(f"done: ${out['usd']:.4f}, wallet {out['balance']}, {out['seconds']} s")
        for f in out["files"]:
            print("  file:", f)
        for t in out["text"]:
            print("  text:", t[:2000])
        for d in out["data"]:
            print("  data:", json.dumps(d)[:800])
        return 0
    if act == "result" and rest:
        out = muapi.result(rest[0], args.out)
        print(json.dumps({k: v for k, v in out.items() if v}, indent=1)[:3000])
        return 0
    if act == "balance":
        bal = muapi.balance()
        print("no key or unreachable" if bal is None else f"wallet ${bal:.2f}")
        print(f"spent today ${ledger.usd_total():.2f} of the ${safety.ceiling():.2f} daily ceiling; desk used ${ledger.used('muapi', muapi.UNIT):.2f} of ${float(muapi.cfg()['daily_usd']):.2f}")
        return 0
    if act == "snapshot":
        rows = muapi.catalog(refresh=True)
        n = muapi.write_snapshot(rows)
        ref = Path(config.STUDIO) / ".claude" / "skills" / "muapi" / "references" / "catalog.md"
        ref.parent.mkdir(parents=True, exist_ok=True)
        ref.write_text(muapi.digest(rows), encoding="utf-8")
        print(f"snapshot: {n} models -> {muapi.SNAPSHOT.relative_to(config.STUDIO)} and {ref.relative_to(config.STUDIO)}")
        return 0
    if act == "doctor":
        bal = muapi.balance()
        rows = muapi.catalog()
        print(f"  {'OK ' if muapi.available() else 'ERR'} MUAPI_API_KEY {'set' if muapi.available() else 'missing'}")
        print(f"  {'OK ' if bal is not None else '..  '} wallet {'$%.2f' % bal if bal is not None else 'unknown'}")
        print(f"  {'OK ' if rows else 'ERR'} catalog {len(rows)} models; snapshot {'present' if muapi.SNAPSHOT.exists() else 'MISSING (run `muapi snapshot`)'}")
        print(f"  {'OK ' if not safety.paused() else 'ERR'} {'running' if not safety.paused() else 'PAUSED: ' + str(safety.paused())}")
        print(f"  ..  limits: desk ${float(muapi.cfg()['daily_usd']):.2f}/day, ${float(muapi.cfg()['per_call_usd']):.2f}/call; studio ceiling ${safety.ceiling():.2f}/day")
        return 0 if muapi.available() and rows else 1
    print("usage: muapi catalog|find <words>|inspect <model>|estimate <model>|run <model>|result <id>|balance|snapshot|doctor")
    return 2


def cmd_pause(args) -> int:
    from faceless import safety
    if args.resume:
        print("resumed" if safety.resume() else "was not paused")
    elif args.reason:
        safety.pause(" ".join(args.reason))
        print("PAUSED: no paid calls, no publishing, `daily`/`make` refuse. `python -m faceless pause --resume` to continue.")
    else:
        print(f"paused: {safety.paused()}" if safety.paused() else f"running; spent ${ledger.usd_total():.2f} of the ${safety.ceiling():.2f} daily ceiling")
    return 0


def cmd_skills(args) -> int:
    """Lint every skill: the skills are the scheduled routines' instructions, so a stale one is a production bug."""
    from faceless import skilllint
    res = skilllint.lint_all()
    print(skilllint.report(res))
    bad = skilllint.failures(res)
    print(f"\n{len(res)} skills, {bad} failure(s)")
    return 1 if bad else 0


def cmd_context(args) -> int:
    """Is the Markdown map (CLAUDE.md routing, workspace CONTEXT.md files, skills) still true? Reads only; never edits."""
    from faceless import contextlint
    res = contextlint.check()
    print(contextlint.report(res))
    return 1 if any(l == "fail" for l, _ in res) else 0


def cmd_monid(args) -> int:
    """The Monid desk: discover, inspect, price and run pay-per-use data endpoints under the studio's spend limits (dry run unless --yes)."""
    from faceless import monid, safety
    act, rest = args.action, args.rest
    if act == "find" and rest:
        for r in monid.discover(" ".join(rest), args.limit):
            p = r.get("price") or {}
            print(f"{r['provider']}{r['endpoint']}  {p.get('type')} ${monid._num(p.get('amount', p.get('value')))}\n    {str(r.get('description'))[:110]}")
        return 0
    if act == "inspect" and len(rest) == 2:
        i = monid.inspect(rest[0], rest[1])
        print(json.dumps({k: i.get(k) for k in ("id", "description", "price", "inputSchema", "notes")}, indent=1)[:4000])
        return 0
    if act == "run" and len(rest) == 2:
        payload = json.loads(args.input or "{}")
        est = monid.estimate(monid.inspect(rest[0], rest[1]), args.results)
        print(f"{rest[0]}{rest[1]}: worst case {'unknown (pass --results N)' if est is None else f'${est:.4f}'}; spent today ${ledger.usd_total():.2f} of the ${safety.ceiling():.2f} ceiling")
        if not args.yes:
            print("dry run: nothing was spent. Add --yes to run it.")
            return 0
        out = monid.run(rest[0], rest[1], payload, results=args.results, max_usd=args.max_usd, label=args.label)
        print(f"done: ${out['usd']:.4f}, wallet {out['balance']}\n  file: {out['file']}\n  output: {json.dumps(out['output'])[:1200]}")
        return 0
    if act == "result" and rest:
        print(json.dumps(monid.result(rest[0]), indent=1, default=str)[:3000])
        return 0
    if act == "balance":
        bal = monid.balance()
        print("no key or unreachable" if bal is None else f"wallet ${bal:.2f}")
        print(f"desk used ${ledger.used('monid', monid.UNIT):.2f} of ${float(monid.cfg()['daily_usd']):.2f} today")
        return 0
    print("usage: monid find <words> | inspect <provider> <endpoint> | run <provider> <endpoint> --input '{...}' [--results N] [--yes] | result <id> | balance")
    return 1


def cmd_brain(args) -> int:
    """The Brain: transcripts in, notes out (skill faceless-brain)."""
    from faceless import brain
    a, rest = args.action, args.rest
    if a == "ingest" and rest and args.file:
        print(brain.ingest(rest[0], Path(args.file).read_text(encoding="utf-8"), args.method, args.speaker or "", args.title or ""))
        return 0
    if a == "check":
        bad = brain.check()
        for k, v in bad.items():
            print(k, "->", "; ".join(v))
        print(f"{len(brain.notes())} note(s), {len(bad)} with problems")
        return 1 if bad else 0
    if a == "index":
        print(f"{brain.index()} note(s) indexed in brain/INDEX.md")
        return 0
    if a == "search" and rest:
        for h in brain.search(" ".join(rest)):
            print(f"{h['score']:>3}  {h['note']}  {h['line'][:100]}")
        return 0
    if a == "watch":
        for v in brain.watch():
            print(v["url"], v["channel"], v["title"][:80])
        return 0
    if a == "fetch" and rest and args.paid:
        text = brain.fetch_paid(rest[0])
        out = Path(config.STUDIO) / "state" / "brain" / "raw" / f"{rest[0]}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(out)
        return 0
    if a == "status":
        print(json.dumps(brain.status(), indent=1))
        return 0
    print("usage: brain ingest URL --file PATH --method exa|owner|tokconnect|transcriptx|muapi | check | index | search WORDS | watch | fetch VIDEO_ID --paid | status")
    return 1


def cmd_marketing(args) -> int:
    """The weekly marketing brief (reads only), or move an experiment / close an owner-queue item."""
    from faceless import marketing
    a, rest = args.action, args.rest
    if a == "done" and rest:
        print("closed:", marketing.mark_done(rest[0])["ask"][:120])
    elif a == "start" and rest:
        print("running:", marketing.set_experiment(rest[0], "running")["id"])
    elif a == "result" and len(rest) >= 2:
        print(marketing.set_experiment(rest[0], rest[1], " ".join(rest[2:]))["id"], rest[1])
    else:
        print(marketing.write_brief())
    return 0


def cmd_metrics(args) -> int:
    """Read back what the last 14 days of videos earned (48-hour and 7-day snapshots) and record it for the scorer and the weekly brief."""
    from faceless import metrics
    if args.csv:
        print(metrics.to_csv(), end="")
        return 0
    if not args.pull:
        print(json.dumps(metrics.summary(), indent=1))
        return 0
    res = metrics.pull()
    print(f"{res['checked']} video(s) read, {res['snapshots']} snapshot(s) recorded, {res['rows']} scorer row(s) written")
    for p in res["problems"]:
        print("PROBLEM:", p)
    return 2 if res["problems"] else 0


def cmd_listing(args) -> int:
    """Etsy and Gumroad listing packs: build (images, video, copy, checklist) or check (the gauntlet only)."""
    from faceless import listing
    if args.action == "build":
        res = listing.build(args.product, video=not args.no_video)
        print(listing.report(res))
        return 0 if all(r["passed"] for r in res.values()) else 1
    if args.action == "check":
        bad = 0
        for pid, gates in listing.check(args.product).items():
            ok = listing.passed(gates)
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {pid}: {sum(g.ok for g in gates)}/{len(gates)} gates")
            for g in gates:
                if not g.ok:
                    print(f"        {'hard' if g.hard else 'soft'}: {g.name}: {g.detail}")
        return 1 if bad else 0
    print("usage: listing build|check [product|all] [--no-video]")
    return 2


def cmd_shop(args) -> int:
    """Storefront connections and Gumroad drafts: status | plan | push [--yes] | sales."""
    from faceless import shop
    if args.action == "status":
        for r in shop.status():
            print(f"{r['state']:12} {r['rail']}: {r['detail']}" + (f"\n{'':13}next: {r['next']}" if r["next"] else ""))
        return 0
    if args.action in ("plan", "push"):
        res = shop.push(args.product if args.product != "all" else None, run=bool(args.yes) and args.action == "push")
        for r in res:
            print(f"{r['product']:28} {r['action']}  ({r['name']})")
        if args.action == "push" and not args.yes:
            print("dry run: nothing was created. Add --yes to create DRAFT products (they are never published).")
        return 0
    if args.action in ("draft", "publish"):
        pid = args.product if args.product != "all" else "daily-quiet-money-planner"
        if args.action == "draft":
            if not args.yes:
                print("dry run. Add --yes to create DRAFT listings on every rail that is ready (nothing goes live).")
                return 0
            for r in shop.draft_all(pid):
                print(f"{r.get('rail', ''):8} {r.get('product', pid)}  {r['action']}  {r.get('why', '')}")
            return 0
        rail = args.rail
        if not rail:
            raise SystemExit("usage: shop publish <product> --rail gumroad|etsy --yes")
        ok, why = shop.approval(pid, rail)
        if not ok or not args.yes:
            print(("refused: " + why) if not ok else "approved. Add --yes to set it live.")
            return 1 if not ok else 0
        print(shop.publish(pid, rail))
        return 0
    if args.action == "sales":
        fresh = shop.sales(args.days)
        print(f"{len(fresh)} new sale(s) recorded in analytics/sales.jsonl")
        return 0
    print("usage: shop status|plan|push|draft|publish|sales [product] [--rail gumroad|etsy] [--yes] [--days N]")
    return 2


def cmd_etsy(args) -> int:
    """Etsy rail: status | auth [--code CODE] | plan PRODUCT | draft PRODUCT --yes."""
    from faceless import etsy
    pid = args.product or "daily-quiet-money-planner"
    if args.action == "status":
        print(json.dumps(etsy.status(), indent=1))
    elif args.action == "auth":
        if args.code:
            print(json.dumps(etsy.finish_auth(args.code, args.state), indent=1))
        else:
            print("Open this link signed in to the Etsy shop, approve, then copy the `code` from the address bar and run `python -m faceless etsy auth --code <code>`:\n" + etsy.auth_url())
    elif args.action == "plan":
        print(json.dumps(etsy.plan(pid), indent=1))
    else:
        if not args.yes:
            print("dry run. Add --yes to create an inactive DRAFT listing (nothing goes live).")
            return 0
        print(json.dumps(etsy.create_draft(pid), indent=1, default=str))
    return 0


def cmd_keys(args) -> int:
    from faceless import keys
    rows = keys.check(only=args.service)
    print(json.dumps(rows, indent=1) if args.json else keys.render(rows))
    return 0


def cmd_songs(args) -> int:
    """Song desk: `songs` writes today's packs (idempotent; --force rewrites) | `songs status`."""
    from faceless import songs
    if args.action == "status":
        st = songs.status(args.day)
        print(f"{st['day']}: {st['packs']}/{st['wanted']} song packs ready: " + (", ".join(st["titles"]) or "none"))
        return 0 if st["packs"] >= st["wanted"] else 1
    try:
        res = songs.build_day(args.day, force=args.force)
    except Exception as e:  # noqa: BLE001 - provider and pause errors are reported, not raised
        print("songs refused:", e)
        return 1
    print(f"{res['day']}: {res['made']}/{res['wanted']} song packs in music/packs/{res['day']}/")
    for s in res["songs"]:
        print(f"  {s['slot']}. {s['title']} ({s['lane']}) - {s['hook_line']}")
    for p in res["problems"]:
        print("  problem:", p)
    return 0 if res["made"] >= res["wanted"] else 1


def cmd_comics(args) -> int:
    """Comics: `comics [--day D] [--n 5] [--reference IMG] [--theme TEXT]` draws the day's picture posts into distribution/comics/<day>/."""
    from faceless import comics
    try:
        print(comics.build(args.day, args.n, Path(args.reference) if args.reference else None, args.theme or ""))
    except Exception as e:
        print("comics refused:", e)
        return 1
    return 0


def cmd_songvideo(args) -> int:
    """Song video: `songvideo IMAGE AUDIO "Title" OUT.mp4 [--draft] [--grade dusk|warm|deep]` | `songvideo --poster IMAGE "Title" OUT.jpg`."""
    from pathlib import Path

    from faceless import songvideo
    if args.poster:
        image, title, out = args.args[:3]
        print(songvideo.poster(Path(image), title, Path(out), grade=args.grade, portrait=args.portrait, focus=args.focus))
        return 0
    image, audio, title, out = args.args[:4]
    info = songvideo.make(Path(image), Path(audio), title, Path(out), grade=args.grade, draft=args.draft, portrait=args.portrait, pan=(args.pan_from, args.pan_to))
    print(f"{info['video']}: {info['seconds']}s {info['size']}{' (draft)' if info['draft'] else ''}")
    return 0


def cmd_songpost(args) -> int:
    """Song post: `songpost --day D` writes POST.md for every song of a day | `songpost PACK_DIR VIDEO [--at ISO] [--apply]` (dry run unless --apply)."""
    from pathlib import Path

    from faceless import config, songpost
    if not args.args:
        day = args.day or config.today_utc().isoformat()
        bad = 0
        for pj in songpost.pack_dir_posts(day):
            copy = songpost.write_pack(pj)
            print(f"{pj.parent.name}: {copy['title']}" + (f"  PROBLEMS: {'; '.join(copy['problems'])}" if copy["problems"] else ""))
            bad += bool(copy["problems"])
        return 1 if bad else 0
    pj = Path(args.args[0]) / "pack.json"
    video = Path(args.args[1]) if len(args.args) > 1 else Path("")
    try:
        res = songpost.publish(pj, video, apply=args.apply, publish_at=args.at)
    except Exception as e:  # noqa: BLE001 - quota, pause and channel refusals are reported, not raised
        print("songpost refused:", e)
        return 1
    print(json.dumps(res, indent=1))
    return 0 if not res["problems"] else 1


def cmd_offer(args) -> int:
    """Offers: coverage and profile links | --batch [DAY] (make sure every passed video has its pack and row) | check TEXT | mark VIDEO pinned."""
    from faceless import offer
    if args.batch is not None:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d") if args.batch in ("today", "") else args.batch
        res = offer.batch(day)
        print(f"{res['day']}: {res['videos']} passed video(s), {res['with_offer']} with an offer, {res['written']} written now")
        for p in res["problems"]:
            print("  problem:", p)
        return 0 if not res["problems"] and res["with_offer"] == res["videos"] else 1
    if args.action == "check":
        text = " ".join(args.args)
        try:                                                          # a whole draft file: offer check path/to/draft.md
            is_file = len(args.args) == 1 and Path(args.args[0]).is_file()
        except OSError:                                               # long text is not a path
            is_file = False
        if is_file:
            text = Path(args.args[0]).read_text(encoding="utf-8")
        bad = offer.violations(text)
        print("clean" if not bad else "refused:\n  " + "\n  ".join(bad))
        return 0 if not bad else 1
    if args.action == "mark":
        if len(args.args) != 2:
            print("usage: offer mark VIDEO_ID draft|pinned")
            return 2
        try:
            row = offer.mark(args.args[0], args.args[1])
        except (KeyError, ValueError) as e:
            print(e)
            return 1
        print(f"{row['video_id']}: {row['status']}")
        return 0
    st = offer.status()
    print(f"offers on {st['videos']} video(s): {st['draft']} waiting to be pinned, {st['pinned']} pinned, {st['link_missing']} without a link")
    print("mix:", ", ".join(f"{k} x{v}" for k, v in sorted(st["by_slug"].items())) or "none yet")
    print("paid offers live:", ", ".join(st["paid_live"]) or "none (the free checklist leads every video until [offer] shop_urls has a live listing)")
    print("hub page:", st["hub"] or "NOT SET ([site] base_url)")
    print("put these in each profile's link field:")
    for p, u in st["profile_links"].items():
        print(f"  {p:10} {u}")
    return 0


def cmd_distribute(args) -> int:
    """Where a finished video can go from here: every rail with its state and the owner's next step (nothing is posted or paid for)."""
    from faceless import distribute
    rows = distribute.status(live=args.live)
    print(distribute.as_json(rows) if args.json else distribute.render(rows))
    return 0


def cmd_preflight(args) -> int:
    """Can today's run succeed? One traffic light per check; exit 1 on any fail (2 on warn with --strict)."""
    from faceless import preflight
    checks = preflight.run(wallet=not args.offline)
    if args.json:
        print(json.dumps([c.__dict__ for c in checks], indent=1))
    else:
        print(preflight.report(checks))
    return preflight.exit_code(checks, args.strict)


def cmd_intake(args) -> int:
    """Look at outside tools without installing or running them: allowlisted metadata, a red-flag scan, one dossier each."""
    from faceless import intake
    if args.apply:
        folder = Path(args.apply)
        counts = intake.apply_verdicts(folder)
        (folder / "decisions.md").write_text(intake.verdict_table(intake.load_verdicts(folder)), encoding="utf-8")
        intake.refresh_registers(folder)
        print(f"ticked and explained {counts['dossiers']} dossiers ({counts['ids_without_dossier']} ids without one); wrote {folder / 'decisions.md'} and refreshed "
              f"channel/empire/RESOURCES.md and repo-farm/registry.md")
        return 0
    if not args.items:
        print("give at least one link or install line, or --apply FOLDER to record verdicts.json into the dossiers")
        return 2
    rows = intake.run(args.items, out_dir=args.out)
    for r in rows:
        high = [c for sev, c, _ in r["flags"] if sev == "high"]
        stars = (r.get("facts") or {}).get("stars")
        print(f"{r['kind']:7} {r['name'][:46]:46} " + (f"{stars:>6} stars  " if stars is not None else " " * 14) + (f"HIGH: {', '.join(high)}" if high else r.get("note", "no high flags") if r["kind"] == "web" else "no high flags"))
    first = next((r["file"] for r in rows if r.get("file")), None)
    if first:
        print(f"\ndossiers in {Path(first).parent} (index.md lists them); each ends with a verdict box for the reviewer")
    return 0


def cmd_ci(args) -> int:
    """CI as GitHub sees it: a clean export of what a commit would contain, a scrubbed environment, the same steps as ci.yml."""
    from faceless import cilocal
    return cilocal.run(only=args.only, keep=args.keep)


def cmd_watchdog(args) -> int:
    """The dead-man's switch: reads only the repo. Prints the findings; --out writes them as Markdown for the workflow's issue step."""
    from faceless import watchdog
    findings = watchdog.evaluate()
    body = watchdog.render_md(findings)
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
    if args.json:
        print(json.dumps(findings, indent=1))
    else:
        print(f"{watchdog.summary(findings)}\n\n{body}")
    return 1 if watchdog.failing(findings, args.fail_on) else 0


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
    m.add_argument("--skip-preflight", action="store_true", help="start even if the machine cannot finish a video (not recommended)")
    m.set_defaults(fn=cmd_make)
    d = sub.add_parser("daily", help="produce the day's batch (resumes: only fills slots without a finished video)")
    d.add_argument("--count", type=int)
    d.add_argument("--extra", type=int, default=0, help="make N more now; they bank into the next free posting slots")
    d.add_argument("--pillar", choices=[x.id for x in config.load()["pillars"]], help="series for every new slot (with --extra)")
    d.add_argument("--no-judge", action="store_true")
    d.add_argument("--no-publish", action="store_true")
    d.add_argument("--skip-preflight", action="store_true", help="start even if the machine cannot finish a video (not recommended)")
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
    pl = sub.add_parser("planner", help="the Daily Planner product: `build` the PDFs, `check` the gauntlet, `ingest <folder>` the owner's pictures, `clean` the handle off them, `inventory`, `cover`, `posters-make` (typeset the studio's twelve wellness posters)")
    pl.add_argument("action", choices=["build", "check", "ingest", "clean", "inventory", "cover", "posters-make"])
    pl.add_argument("folder", nargs="?", help="ingest: the folder with the owner's pictures")
    pl.add_argument("--size", choices=["Letter", "A4", "both"], default="both")
    pl.add_argument("--days", type=int, help="build only the first N days (a quick test)")
    pl.add_argument("--start", type=int, default=1, help="ingest: the day number of the first picture")
    pl.add_argument("--box", help="clean: x0,y0,x1,y1 as fractions of the picture, when the handle is somewhere unusual")
    pl.set_defaults(fn=cmd_planner)
    pn = sub.add_parser("panel", help="put one decision brief to several models through OpenRouter, several runs each, and tally their answers (a person adjudicates)")
    pn.add_argument("brief", help="a text file that tells the models to answer in JSON with a choice")
    pn.add_argument("--models", required=True, help="comma-separated OpenRouter model ids")
    pn.add_argument("--runs", type=int, default=3)
    pn.add_argument("--label")
    pn.set_defaults(fn=cmd_panel)
    sub.add_parser("autoresponder", help="write the 7-day Money Reset email sequence (numbers computed, ready to import)").set_defaults(fn=cmd_autoresponder)
    bk = sub.add_parser("brandkit", help="build a client brand kit (avatar, banner, watermark, share image, favicons, logo, BRAND.md) for the Fiverr service")
    bk.add_argument("name", nargs="?", help="channel name (1-24 characters)")
    bk.add_argument("--tagline", default="")
    bk.add_argument("--palette", default="gold", help="gold | mint | coral | sky | violet | lime")
    bk.add_argument("--niche", default="")
    bk.add_argument("--pills", default="", help="comma list of up to 4 topic words for the banner")
    bk.add_argument("--out", help="output folder")
    bk.add_argument("--samples", action="store_true", help="(re)build the four gallery samples and GIG.md")
    bk.set_defaults(fn=cmd_brandkit)
    qq = sub.add_parser("qa", help="calibrate the semantic QA gates (Clef) on cached images and finished scripts; spends free neurons")
    qq.add_argument("--images", type=int, default=40)
    qq.add_argument("--scripts", type=int, default=30)
    qq.set_defaults(fn=cmd_qa)
    mu = sub.add_parser("music", help="the music library: list tracks, or --build the missing ones (Lyria RealTime, free tier, about 90 s each)")
    mu.add_argument("--build", action="store_true")
    mu.add_argument("--limit", type=int, help="build at most N tracks")
    mu.set_defaults(fn=cmd_music)
    po = sub.add_parser("policy", help="policy watchdog: fetch the watched rule pages and report changes; --record ID FILE saves text fetched another way")
    po.add_argument("--record", nargs=2, metavar=("ID", "FILE"))
    po.set_defaults(fn=cmd_policy)
    va = sub.add_parser("variety", help="sameness audit of the last N videos (YouTube's inauthentic-content risk); writes analytics/variety.md")
    va.add_argument("-n", type=int, default=20)
    va.set_defaults(fn=cmd_variety)
    br = sub.add_parser("brain", help="the Brain: ingest URL --file PATH --method M | check | index | search WORDS | watch | fetch VIDEO_ID --paid | status")
    br.add_argument("action", choices=["ingest", "check", "index", "search", "watch", "fetch", "status"])
    br.add_argument("rest", nargs="*")
    br.add_argument("--file")
    br.add_argument("--method", default="owner", choices=["exa", "owner", "tokconnect", "transcriptx", "muapi"])
    br.add_argument("--speaker")
    br.add_argument("--title")
    br.add_argument("--paid", action="store_true")
    br.set_defaults(fn=cmd_brain)
    mk = sub.add_parser("marketing", help="the weekly marketing brief (reads only; writes analytics/brief-<day>.md) | done <U01> | start <X1> | result <X1> won|killed [note]")
    mk.add_argument("action", nargs="?", default="brief", choices=["brief", "done", "start", "result"])
    mk.add_argument("rest", nargs="*")
    mk.set_defaults(fn=cmd_marketing)
    me = sub.add_parser("metrics", help="--pull reads back what the last 14 days of videos earned (48-hour and 7-day snapshots, read-only); --csv exports the snapshots; bare shows median 48-hour views by pillar")
    me.add_argument("--pull", action="store_true")
    me.add_argument("--csv", action="store_true")
    me.set_defaults(fn=cmd_metrics)
    mo = sub.add_parser("monid", help="Monid desk (pay-per-use data endpoints): find <words> | inspect <provider> <endpoint> | run <provider> <endpoint> --input JSON [--yes] | result <id> | balance")
    mo.add_argument("action", choices=["find", "inspect", "run", "result", "balance"])
    mo.add_argument("rest", nargs="*")
    mo.add_argument("--input", help="JSON body for run")
    mo.add_argument("--results", type=int, help="how many results a per-result endpoint may return (sets the worst-case price)")
    mo.add_argument("--max-usd", type=float, dest="max_usd", help="raise the per-call limit for this call")
    mo.add_argument("--limit", type=int, default=8)
    mo.add_argument("--label", help="name for the saved result")
    mo.add_argument("--yes", action="store_true", help="actually run and spend")
    mo.set_defaults(fn=cmd_monid)
    mp = sub.add_parser("muapi", help="Muapi desk: catalog | find <words> | inspect <model> | estimate <model> | run <model> [--yes] | result <id> | balance | snapshot | doctor")
    mp.add_argument("action")
    mp.add_argument("rest", nargs="*")
    mp.add_argument("--set", action="append", metavar="KEY=VALUE", help="a request field; a local image or video path is uploaded for you")
    mp.add_argument("--json", help="a JSON file with the request fields")
    mp.add_argument("--out", help="folder for downloaded results (default production/cache/muapi)")
    mp.add_argument("--yes", action="store_true", help="actually spend (run is a dry run without it)")
    mp.add_argument("--max-usd", type=float, help="raise the per-call limit for this one call")
    mp.add_argument("--category")
    mp.add_argument("--family")
    mp.add_argument("--label")
    mp.add_argument("--limit", type=int, default=15)
    mp.add_argument("--refresh", action="store_true")
    mp.set_defaults(fn=cmd_muapi)
    pz = sub.add_parser("pause", help="kill switch: `pause <reason>` stops paid calls and publishing, `pause --resume` continues, bare `pause` shows the state")
    pz.add_argument("reason", nargs="*")
    pz.add_argument("--resume", action="store_true")
    pz.set_defaults(fn=cmd_pause)
    sub.add_parser("context", help="check CLAUDE.md routing, the workspace CONTEXT.md files and the skills still agree (reads only)").set_defaults(fn=cmd_context)
    sub.add_parser("skills", help="lint every skill (format rules from Anthropic's skill guide, plus: every command and file a skill names must exist)").set_defaults(fn=cmd_skills)
    ls = sub.add_parser("listing", help="Etsy and Gumroad listing packs: `listing build [product|all]` makes images, video, copy and a checklist; `listing check` runs the listing gauntlet")
    ls.add_argument("action", choices=["build", "check"])
    ls.add_argument("product", nargs="?", default="all")
    ls.add_argument("--no-video", action="store_true")
    ls.set_defaults(fn=cmd_listing)
    et = sub.add_parser("etsy", help="the Etsy rail: `etsy status`, `etsy auth` (one-time login), `etsy plan`, `etsy draft --yes` (inactive draft, never live)")
    et.add_argument("action", choices=["status", "auth", "plan", "draft"])
    et.add_argument("product", nargs="?")
    et.add_argument("--code")
    et.add_argument("--state")
    et.add_argument("--yes", action="store_true")
    et.set_defaults(fn=cmd_etsy)
    sh = sub.add_parser("shop", help="storefronts: `shop status` (what is connected, the owner's next step), `shop plan`, `shop push --yes` (DRAFT products on Gumroad, never published), `shop sales`")
    sh.add_argument("action", choices=["status", "plan", "push", "draft", "publish", "sales"])
    sh.add_argument("--rail", choices=["gumroad", "etsy"])
    sh.add_argument("product", nargs="?", default="all")
    sh.add_argument("--yes", action="store_true")
    sh.add_argument("--days", type=int, default=30)
    sh.set_defaults(fn=cmd_shop)
    ych = sub.add_parser("yt-channel", help="the YouTube channel page as code: description, keywords, banner, series playlists (`--apply` makes the live channel match studio.toml)")
    ych.add_argument("--apply", action="store_true")
    ych.set_defaults(fn=cmd_yt_channel)
    yv = sub.add_parser("yt-verify", help="read back every video scheduled on YouTube in the last 14 days: still there, processed, public on time (exit 2 on any problem); prints views and likes")
    yv.set_defaults(fn=cmd_yt_verify)
    yc = sub.add_parser("yt-comments", help="post the first comment on YouTube videos that have gone public (YouTube takes none while a video is scheduled)")
    yc.set_defaults(fn=cmd_yt_comments)
    ky = sub.add_parser("keys", help="which key of each service works and what is left on it (free, read-only; values are never printed)")
    ky.add_argument("service", nargs="?", default=None)
    ky.add_argument("--json", action="store_true")
    ky.set_defaults(fn=cmd_keys)
    sg = sub.add_parser("songs", help="the song desk: 3 original songs a day as Suno style prompts, lyrics and cover-image prompts (`songs status`, `--day D`, `--force`)")
    sg.add_argument("action", nargs="?", default="make", choices=["make", "status"])
    sg.add_argument("--day", default=None)
    sg.add_argument("--force", action="store_true")
    sg.set_defaults(fn=cmd_songs)
    sv = sub.add_parser("songvideo", help="a song and a picture become a 16:9 music video (1920x1080; --portrait for 1080x1920) (grade, bloom, pan, particles, grain, waveform, wordmark): `songvideo IMAGE AUDIO TITLE OUT.mp4 [--draft]`, `--poster IMAGE TITLE OUT.jpg`")
    sv.add_argument("args", nargs="+")
    sv.add_argument("--poster", action="store_true")
    sv.add_argument("--draft", action="store_true")
    sv.add_argument("--portrait", action="store_true", help="1080x1920 for Shorts and Reels (default is 16:9, 1920x1080)")
    sv.add_argument("--grade", default="deep", choices=["dusk", "warm", "deep"])
    sv.add_argument("--focus", type=float, default=0.5)
    sv.add_argument("--pan-from", type=float, default=0.0)
    sv.add_argument("--pan-to", type=float, default=1.0)
    sv.set_defaults(fn=cmd_songvideo)
    cm = sub.add_parser("comics", help="the funny picture-post series (five a day, for the channel's Posts tab): `comics [--day D] [--n 5] [--reference IMG] [--theme T]`")
    cm.add_argument("--day"); cm.add_argument("--n", type=int, default=5); cm.add_argument("--reference"); cm.add_argument("--theme")
    cm.set_defaults(fn=cmd_comics)
    sp = sub.add_parser("songpost", help="YouTube copy for a song (SEO, AEO, GEO, one tracked link, AI disclosure): `songpost --day D` writes POST.md for each pack, `songpost PACK_DIR VIDEO [--at ISO] [--apply]` uploads only with --apply")
    sp.add_argument("args", nargs="*")
    sp.add_argument("--day", default=None)
    sp.add_argument("--at", default=None, help="UTC time to go public, e.g. 2026-10-13T15:30:00Z")
    sp.add_argument("--apply", action="store_true")
    sp.set_defaults(fn=cmd_songpost)
    of = sub.add_parser("offer", help="the call to action on every video: coverage and profile links, `--batch [today|DAY]` writes missing packs and ledger rows, `check TEXT` runs the claim check, `mark VIDEO pinned`")
    of.add_argument("action", nargs="?", default="status", choices=["status", "check", "mark"])
    of.add_argument("args", nargs="*")
    of.add_argument("--batch", nargs="?", const="today", default=None, metavar="DAY")
    of.set_defaults(fn=cmd_offer)
    ds = sub.add_parser("distribute", help="distribution rails: posting, profile links, offers, email list, products, measurement, with each one's state and the owner's next step; `--live` also checks the hub page is published")
    ds.add_argument("--live", action="store_true")
    ds.add_argument("--json", action="store_true")
    ds.set_defaults(fn=cmd_distribute)
    pf = sub.add_parser("preflight", help="can today's run succeed? traffic lights for tools, keys, spend, kill switch, disk, state, freshness, skills, leaked secrets")
    pf.add_argument("--strict", action="store_true", help="exit 2 when something only warns")
    pf.add_argument("--offline", action="store_true", help="skip the wallet call")
    pf.add_argument("--json", action="store_true")
    pf.set_defaults(fn=cmd_preflight)
    it = sub.add_parser("intake", help="look at outside tools safely (repos, npm/PyPI packages, install lines): metadata + red flags + a verdict box; nothing is cloned, installed or run")
    it.add_argument("items", nargs="*", help="GitHub URLs, install lines such as 'npx tool', 'pip install tool', or other links (listed, not fetched)")
    it.add_argument("--out", help="folder for the dossiers (default repo-farm/intake/<day>)")
    it.add_argument("--apply", metavar="FOLDER", help="record FOLDER/verdicts.json into its dossiers (ticks the box, adds the decision) and write decisions.md")
    it.set_defaults(fn=cmd_intake)
    ci = sub.add_parser("ci", help="run CI as GitHub sees it (clean export, no keys, runner tools only) before you push")
    ci.add_argument("--only", choices=["tests", "skills", "imports", "site"], help="run one step")
    ci.add_argument("--keep", action="store_true", help="keep the exported folder even when everything passes")
    ci.set_defaults(fn=cmd_ci)
    wd = sub.add_parser("watchdog", help="dead-man's switch: is the operation alive? reads only the repo (the scheduled workflow opens an issue when it is not)")
    wd.add_argument("--out", help="write the findings as Markdown to this file")
    wd.add_argument("--json", action="store_true")
    wd.add_argument("--fail-on", choices=["critical", "warn"])
    wd.set_defaults(fn=cmd_watchdog)
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
    cc = sub.add_parser("caption-check", help="measure caption drift against the speech in a finished video (hand-built ones too)")
    cc.add_argument("media")
    cc.add_argument("ass")
    cc.add_argument("--max", type=float, default=0.35)
    cc.set_defaults(fn=cmd_caption_check)
    g = sub.add_parser("gauntlet", help="re-run all gates on a finished job")
    g.add_argument("job")
    g.add_argument("--no-judge", action="store_true")
    g.set_defaults(fn=cmd_gauntlet)
    ho = sub.add_parser("host", help="the recurring host (one face, one voice, once a week): status | voice | character | line | clip | anchor")
    ho.add_argument("action", choices=["status", "voice", "character", "line", "clip", "anchor"])
    ho.add_argument("text", nargs="?", help="clip: the spoken line (default: the decision layer's pick); anchor: the video to take the voice from")
    ho.add_argument("--apply", action="store_true", help="clip: actually generate (spends money)")
    ho.add_argument("--force", action="store_true", help="voice: make a new profile even if one exists")
    ho.add_argument("--max-usd", type=float, default=2.5)
    ho.set_defaults(fn=cmd_host)
    pbl = sub.add_parser("post-backlog", help="schedule made, passed videos that never reached YouTube on today's remaining slots (dry run unless --apply)")
    pbl.add_argument("--n", type=int, default=5)
    pbl.add_argument("--apply", action="store_true")
    pbl.set_defaults(fn=cmd_post_backlog)
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
