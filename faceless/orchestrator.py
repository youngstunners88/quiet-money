"""Orchestrator: routes slots to pillars, drives each job through the stages and the gauntlet.

Separation of concerns:
  orchestrator  - sequencing, retries, routing          (this file)
  pipeline/*    - one stage each, pure "inputs -> artifacts"
  providers/*   - vendor I/O behind capability interfaces
  gauntlet      - judgement (gates + scores), never side effects
  decide        - typed decisions (Jev or heuristic), recorded
  state/events  - persistence and audit trail
"""

from __future__ import annotations

import json
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from faceless import analytics, config, decide, events, gauntlet, qa, research, safety
from faceless.config import Paths
from faceless.pipeline import ideate, package, render, script as script_stage, visuals, voice as voice_stage
from faceless.providers import publish as publisher
from faceless.state import Job, all_jobs, new_job


def _load(job: Job, name: str):
    p = job.dir / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def script_loop(job: Job, history: list[str], judge: bool, feedback: list[str] | None = None):
    """Draft -> gate -> judge -> rewrite until it passes. Every script that ships goes through here."""
    cfg = config.load()
    rounds = cfg["gauntlet"]["max_fix_rounds"]
    judged: dict = {}
    for rnd in range(rounds + 1):
        scr = script_stage.write(job, feedback=feedback)
        gates = gauntlet.check_script(scr, history)
        if judge:
            jg, judged = gauntlet.judge_script(scr, job.id, brief=research.brief(job.artifacts.get("brief")))
            gates += jg
        gates += qa.script_gates(scr, job.id) + qa.duplicate_gates(scr, job.id)   # decision-model + semantic checks; no opinion when unavailable
        s, hard = gauntlet.score(gates)
        bad = gauntlet.failing(gates)
        events.emit("SCRIPT_GATES", job=job.id, round=rnd, score=s, failing=[g.name for g in bad])
        if s >= cfg["gauntlet"]["pass_score"] and not hard:
            break
        if scr.get("source") == "human" or rnd == rounds:
            break  # never overwrite a human-written script; its failures go to the report instead
        feedback = (feedback or [])[:1] + [g.detail for g in bad]  # keep the original brief (e.g. length)
    script_stage.finalize(job, scr)
    job.artifacts["title"] = scr["title"]
    return scr, gates, judged


def length_brief(seconds: float, words: int) -> str:
    prod = config.load()["production"]
    lo, hi = prod["target_seconds"]
    # the configured word range is calibrated to the base voice pace; the measured pace may already be refit
    target_w = sum(prod["words_range"]) // 2
    verb = "too short" if seconds < lo else "too long"
    return (f"The narration ran {seconds:.1f}s, {verb}; it must run {lo:.0f}-{hi:.0f}s. Rewrite to about "
            f"{target_w} words in total across all 'say' fields (currently {words}). Count them before answering.")


def produce(job: Job, *, judge: bool = True, prefer_voice: str | None = None, do_publish: bool = True) -> dict:
    history = [h for h in ideate.history_texts() if h != job.topic]
    all_gates: list[gauntlet.Gate] = []

    # 1. script (+ judge) with rewrite loop
    scr, gates, judged = script_loop(job, history, judge)
    job.advance("scripted", words=script_stage.word_count(scr))

    # 2. voice. A duration miss sends the script back through the full gated loop with a word target.
    vo = voice_stage.run(job, scr, prefer=prefer_voice)
    vg = gauntlet.check_voice(vo)
    if not vg[0].passed and scr.get("source") != "human":
        brief = length_brief(vo["duration"], script_stage.word_count(scr))
        events.emit("LENGTH_REWRITE", job=job.id, brief=brief)
        scr, gates, judged = script_loop(job, history, judge, feedback=[brief])
        vo = voice_stage.run(job, scr, prefer=prefer_voice)
        vg = gauntlet.check_voice(vo)
    all_gates += gates + vg          # gates of the script that actually ships
    job.advance("voiced", seconds=vo["duration"], provider=vo["provider"])

    # 3. visuals
    imgs = visuals.run(job, scr)
    all_gates += gauntlet.check_visuals(imgs, len(scr["beats"]))
    job.advance("visualized")

    # 4. render
    info = render.run(job, scr, vo, imgs)
    job.artifacts.update(video=info["video"], cover=info["cover"])
    all_gates += gauntlet.check_render(info, vo)
    job.advance("rendered")

    # 5. package + final verdict
    meta = package.run(job, scr)
    all_gates += gauntlet.check_package(meta)
    rep = gauntlet.report(job, all_gates, {"judge": judged})
    job.scores = {"gauntlet": rep["score"], "passed": rep["passed"]}
    job.advance("gated", score=rep["score"])

    verdict = decide.ask({"next_step": decide.Q(
        "choice", "Should this finished video be published on schedule, or held for human review?",
        fallback="publish" if rep["passed"] else "hold",
        options={"publish": "All quality gates passed; safe, on-brand, ready to post.",
                 "hold": "A hard gate failed, the score is low, or a claim needs a human check."})},
        state={"score": rep["score"], "hard_failures": rep["hard_failures"], "title": meta["title"]}, job=job.id)
    # the decider may hold a passing video, never ship a failing one (Rule 6: score >= pass_score, no hard fails)
    next_step = verdict["next_step"].value if rep["passed"] else "hold"
    job.advance("packaged")
    if rep["score"] >= 95:   # teach the voice classifier what our best writing looks like
        from faceless import quality
        quality.remember("quality", job.id, script_stage.narration(scr))
    if do_publish and next_step == "publish":
        res = publisher.publish(job, meta)
        job.artifacts["publish"] = res
        job.advance("published", **{k: v.get("post_at") for k, v in res.items() if isinstance(v, dict)})
        _kit(job)
    elif next_step != "publish":
        job.notes.append("held for review: " + ", ".join(rep["hard_failures"] or ["low score"]))
        job.advance("held")
    job.save()
    return rep


def _kit(job: Job) -> None:
    """Repurposing kit next to the posting pack. A failure here never costs a video its slot."""
    if not config.load().get("repurpose", {}).get("enabled", False):
        return
    local = (job.artifacts.get("publish") or {}).get("local") or {}
    if not local.get("folder"):
        return
    try:
        from faceless import repurpose
        made = repurpose.build_pack(job, Path(local["folder"]))
        events.emit("KIT_BUILT", job=job.id, files=len(made["files"]), audio=made["audio"])
    except Exception as e:   # noqa: BLE001 - best-effort side product
        job.notes.append(f"kit skipped: {type(e).__name__}")


def start_job(pillar: str, item: dict, slot: int) -> Job:
    """New job from a backlog item; its angle and research brief travel with it to the writer and judge."""
    job = new_job(pillar, item["topic"], slot=slot)
    job.artifacts.update({k: item[k] for k in ("angle", "brief") if item.get(k)})
    job.save()
    return job


def run_one(pillar: str, topic: str | None = None, slot: int = 0, **kw) -> Job:
    Paths.ensure()
    why = safety.paused()
    if why:
        raise RuntimeError(f"studio is paused ({why}); `python -m faceless pause --resume` to continue")
    item = (ideate.find_topic(topic) or {"topic": topic}) if topic else ideate.next_topic(pillar)
    job = start_job(pillar, item, slot)
    try:
        produce(job, **kw)
    except Exception as e:  # noqa: BLE001
        job.notes.append(f"{type(e).__name__}: {e}")
        job.advance("failed", error=str(e)[:300])
        events.emit("JOB_FAILED", job=job.id, trace=traceback.format_exc()[-1500:])
        raise
    return job


SHIPPABLE = ("packaged", "published")   # held and failed jobs leave their slot open for a retry


def open_slots(count: int, extra: int = 0, now: datetime | None = None) -> list[tuple[str, int]]:
    """(post date, slot of day) pairs to fill. Default: today's slots that have no shippable video yet
    (so a re-run resumes instead of duplicating). extra=N: the next N free slots from now on.
    Slots whose posting time has passed are skipped: a video for them would post a day late and
    collide with tomorrow's video in the same slot."""
    now = now or datetime.now(timezone.utc)
    taken = {publisher.nominal_slot(j.day, j.slot) for j in all_jobs() if j.status in SHIPPABLE}
    day, out = now.date(), []
    for _ in range(366 if extra else 1):
        for k in range(count):
            key = (day.isoformat(), k)
            if key not in taken and publisher.nominal_time(*key) > now + publisher.LEAD:
                out.append(key)
        if extra and len(out) >= extra:
            return out[:extra]
        day += timedelta(days=1)
    return out


def daily(count: int | None = None, extra: int = 0, pillar: str | None = None, **kw) -> list[Job]:
    Paths.ensure()
    why = safety.paused()
    if why:
        events.emit("DAILY_HALTED", reason=why)
        return []
    cfg = config.load()
    per_day = len(cfg["publish"]["slots"])
    count = count or cfg["production"]["videos_per_day"]
    if count > per_day:   # more than a day of slots: make them all now, banking the rest into the next free slots
        extra, count = max(extra, count), per_day
    today = datetime.now(timezone.utc).date()
    weights = analytics.pillar_weights()
    plans: dict[str, list[str]] = {}
    slots = open_slots(count, extra)
    events.emit("DAILY_PLAN", slots=[f"{d}#{k + 1}" for d, k in slots], extra=extra,
                weights={k: round(v, 3) for k, v in weights.items()})
    jobs, reserved = [], [j.topic for j in all_jobs() if j.day == today.isoformat()]
    forced = pillar
    for post_day, k in slots:
        plan = plans.setdefault(post_day, analytics.allocate(per_day, weights, date.fromisoformat(post_day).toordinal()))
        pillar = forced or plan[k]
        slot = (date.fromisoformat(post_day) - today).days * per_day + k
        job = None
        try:
            item = ideate.next_topic(pillar, reserved)
            reserved.append(item["topic"])
            job = start_job(pillar, item, slot)
            jobs.append(job)
            produce(job, **kw)
        except Exception as e:  # noqa: BLE001 - one bad job must not sink the day
            events.emit("JOB_FAILED", job=job.id if job else None, pillar=pillar, slot=slot, error=str(e)[:300],
                        trace=traceback.format_exc()[-1500:])
            # only this slot's job fails; a topic error before it exists must not touch the previous slot's video.
            # A packaged video whose upload failed stays packaged (its local pack is ready; `publish` retries it).
            if job:
                job.notes.append(str(e)[:300])
                if job.status not in (*SHIPPABLE, "failed", "held"):
                    job.advance("failed", error=str(e)[:200])
                else:
                    job.save()
    write_daily_report([j for j in all_jobs() if j.day == today.isoformat()])
    return jobs


def write_daily_report(jobs: list[Job]) -> None:
    from faceless import ledger
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Daily run {day}", "", "| slot | pillar | title | status | score | seconds |", "|---|---|---|---|---|---|"]
    for j in jobs:
        vo = _load(j, "voice.json") or {}
        lines.append(f"| {j.slot + 1} | {j.pillar} | {j.artifacts.get('title', j.topic)} | {j.status} | "
                     f"{j.scores.get('gauntlet', '-')} | {vo.get('duration', '-')} |")
    lines += ["", "## Spend", "```", json.dumps(ledger.summary(day), indent=1), "```"]
    (Paths.reports / f"daily-{day}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
