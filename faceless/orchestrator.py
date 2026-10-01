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
from datetime import datetime, timezone

from faceless import analytics, config, decide, events, gauntlet
from faceless.config import Paths
from faceless.pipeline import ideate, package, render, script as script_stage, visuals, voice as voice_stage
from faceless.providers import publish as publisher
from faceless.state import Job, new_job


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
            jg, judged = gauntlet.judge_script(scr, job.id)
            gates += jg
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
    job.advance("packaged")
    if rep["score"] >= 95:   # teach the voice classifier what our best writing looks like
        from faceless import quality
        quality.remember("quality", job.id, script_stage.narration(scr))
    if do_publish and verdict["next_step"].value == "publish":
        res = publisher.publish(job, meta)
        job.artifacts["publish"] = res
        job.advance("published", **{k: v.get("post_at") for k, v in res.items() if isinstance(v, dict)})
    elif verdict["next_step"].value == "hold":
        job.notes.append("held for review: " + ", ".join(rep["hard_failures"] or ["low score"]))
        job.advance("held")
    job.save()
    return rep


def run_one(pillar: str, topic: str | None = None, slot: int = 0, **kw) -> Job:
    Paths.ensure()
    item = {"topic": topic} if topic else ideate.next_topic(pillar)
    job = new_job(pillar, item["topic"], slot=slot)
    try:
        produce(job, **kw)
    except Exception as e:  # noqa: BLE001
        job.notes.append(f"{type(e).__name__}: {e}")
        job.advance("failed", error=str(e)[:300])
        events.emit("JOB_FAILED", job=job.id, trace=traceback.format_exc()[-1500:])
        raise
    return job


def daily(count: int | None = None, **kw) -> list[Job]:
    Paths.ensure()
    cfg = config.load()
    count = count or cfg["production"]["videos_per_day"]
    day_index = datetime.now(timezone.utc).toordinal()
    weights = analytics.pillar_weights()
    plan = analytics.allocate(count, weights, day_index)
    events.emit("DAILY_PLAN", plan=plan, weights={k: round(v, 3) for k, v in weights.items()})
    jobs, reserved = [], []
    for slot, pillar in enumerate(plan):
        try:
            item = ideate.next_topic(pillar, reserved)
            reserved.append(item["topic"])
            job = new_job(pillar, item["topic"], slot=slot)
            jobs.append(job)
            produce(job, **kw)
        except Exception as e:  # noqa: BLE001 - one bad job must not sink the day
            events.emit("JOB_FAILED", pillar=pillar, slot=slot, error=str(e)[:300], trace=traceback.format_exc()[-1500:])
            if jobs and jobs[-1].status not in ("failed", "published", "held"):
                jobs[-1].notes.append(str(e)[:300])
                jobs[-1].advance("failed", error=str(e)[:200])
    write_daily_report(jobs)
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
