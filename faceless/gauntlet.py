"""The gauntlet: every video runs through hard and soft gates before it can be published.

Hard gates block publishing. Soft gates cost points. A video ships at score >= pass_score
with zero hard failures; otherwise the orchestrator feeds the failing gates back into the
stage that can fix them (script rewrite, voice refit, image retry, re-render), up to
max_fix_rounds. Every run writes a report to gauntlet/reports/.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, replace

from faceless import config, decide, events
from faceless.config import Paths
from faceless.pipeline.ideate import similarity
from faceless.pipeline.script import narration, spoken_word_count
from faceless.prompts import BANNED, COMPLIANCE_BANNED, judge_prompt
from faceless.providers import llm


@dataclass
class Gate:
    name: str
    passed: bool
    weight: float
    hard: bool = False
    detail: str = ""
    fix: str = "script"      # stage that can repair it: script | voice | visuals | render | package


def check_script(script: dict, history: list[str]) -> list[Gate]:
    cfg = config.load()
    lo, hi = cfg["production"]["words_range"]
    beats = script["beats"]
    text = narration(script)
    low = text.lower()
    wc = spoken_word_count(script)          # numbers count as spoken ("$1,739" = 6 words)
    g = []
    # soft near the range (duration is the hard truth, measured in check_voice); hard when so far out that the
    # voice refit cannot rescue it, so the cheap script loop rewrites instead of the expensive voice stage
    # words_range is what the writer counts (digits once); spoken numbers run longer, so the spoken window is
    # wider. Calibrated on rendered videos: 61-72 s at the house pace ~ 180-225 spoken words.
    slo, shi = lo + 5, hi + 25
    far = wc < slo - 20 or wc > shi + 20
    g.append(Gate("word_count", slo <= wc <= shi, 8, far,
                  f"{wc} spoken words; need {slo}-{shi}. " + ("Cut" if wc > shi else "Add") + f" about {abs(wc - (slo + shi) // 2)} words."))
    g.append(Gate("beat_count", 9 <= len(beats) <= 16, 6, True, f"{len(beats)} beats; need 10-14."))
    hook = beats[0]["say"] if beats else ""
    hook_words = len(hook.split())
    g.append(Gate("hook_length", hook_words <= 22, 6, False, f"hook is {hook_words} words; keep under 18."))
    hooky = bool(re.search(r"\d|\$|you|your|never|nobody|secret|why|most|richest|died|lost|million|billion", hook.lower()))
    g.append(Gate("hook_trigger", hooky, 6, False, "hook needs a number, a 'you', or a contradiction in the first line."))
    ht = script.get("hook_text", "")
    g.append(Gate("hook_text", 1 <= len(ht.split()) <= 8, 4, False, f"on-screen hook '{ht}' should be 2-7 words."))
    long_beats = [i + 1 for i, b in enumerate(beats) if len(b["say"].split()) > 26]
    g.append(Gate("beat_length", not long_beats, 4, False, f"beats too long for the ear: {long_beats}"))
    missing_vis = [i + 1 for i, b in enumerate(beats) if len(b.get("visual", "").split()) < 5]
    g.append(Gate("visual_prompts", not missing_vis, 8, True, f"beats missing a concrete visual prompt: {missing_vis}"))
    callouts = sum(1 for b in beats if b.get("callout"))
    g.append(Gate("callouts", 3 <= callouts <= 8, 3, False, f"{callouts} callouts; use 4-7 on-screen numbers/phrases."))
    banned = [p for p in BANNED if p in low]
    g.append(Gate("banned_phrases", not banned, 5, False, f"remove filler phrases: {banned}"))
    comp = [p for p in COMPLIANCE_BANNED if p in low]
    g.append(Gate("compliance_phrases", not comp, 10, True, f"remove advice/promise language: {comp}"))
    tickers = re.findall(r"\$[A-Z]{2,5}\b", " ".join(b["say"] for b in beats))
    g.append(Gate("no_ticker_picks", not tickers, 8, True, f"no ticker callouts: {tickers}"))
    last = beats[-1]["say"].strip() if beats else ""
    g.append(Gate("loop_ending", not last.endswith((".", "!")) or bool(re.search(r"\b(that's|this is|how|why)\b", last.lower())),
                  4, False, "end the last line mid-thought so it loops back into the hook."))
    title = script.get("title", "")
    g.append(Gate("title", 10 <= len(title) <= 60, 3, False, f"title is {len(title)} chars; 25-60 works best.", "script"))
    tags = script.get("hashtags", [])
    g.append(Gate("hashtags", 3 <= len(tags) <= 6, 2, False, f"{len(tags)} hashtags; use 4-5.", "script"))
    sims = [similarity(title + " " + hook, h) for h in history]
    top = max(sims) if sims else 0.0
    g.append(Gate("originality", top < cfg["gauntlet"]["similarity_max"], 8, True,
                  f"too close to an earlier video (similarity {top:.2f}); change the angle and hook."))
    g += check_structure(script, low)
    from faceless import quality
    label, margin, _ = quality.classify(text)
    g.append(Gate("voice_quality", label != "slop", 5, False,
                  "reads like generic AI copy (compression classifier): swap filler for concrete numbers, names, "
                  "and short spoken sentences; cut phrases like 'financial journey' and 'unlock'"))
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    avg = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
    g.append(Gate("readability", avg <= 16, 3, False, f"average sentence is {avg:.1f} words; aim for 8-14."))
    return g


STEP_MARKERS = [r"\bstep (one|1)\b|\bfirst\b|^one\b", r"\bstep (two|2)\b|\bsecond\b|^two\b",
                r"\bstep (three|3)\b|\bthird\b|^three\b"]


def check_structure(script: dict, low: str) -> list[Gate]:
    """Pillar formats are promises to the viewer; check the script keeps them."""
    pillar = script.get("pillar", "")
    if pillar == "playbook":
        says = [b["say"].lower() for b in script["beats"]]
        found = [any(re.search(m, x) for x in says) for m in STEP_MARKERS]
        return [Gate("pillar_structure", all(found), 6, False,
                     "a 'Do This Today' video must deliver three numbered steps: start beats with "
                     "'Step one.', 'Step two.', 'Step three.' and keep each step concrete.")]
    if pillar == "myth":
        opening = " ".join(b["say"].lower() for b in script["beats"][:3])
        ok = bool(re.search(r"myth|wrong|isn't|is not|lie|actually|truth", opening))
        return [Gate("pillar_structure", ok, 4, False,
                     "a 'Money Myths' video must name the belief and flip it within the first 3 beats.")]
    if pillar == "escape":
        says = [b["say"].lower() for b in script["beats"]]
        catch = any(re.search(CATCH, x) for x in says)
        move = any(re.search(MOVE, x) for x in says[-5:])
        return [Gate("pillar_structure", catch and move, 6, False,
                     "an 'Escape the Rat Race' video must state the honest catch (effort, risk, or debt) and end with one "
                     "concrete move for this week ('This week, ...').")]
    return []


CATCH = (r"\b(catch|risks?|risky|downside|no guarantees?|not guaranteed|warning|isn't easy|is not easy|"
         r"the hard part|bankrupt\w*|debt)\b")
MOVE = (r"\b(this week|today|tonight|tomorrow|right now|start with|step one|your first|write down|"
        r"make a list|list (?:every|all|your))\b")


def judge_number(value, default: float = 5.0) -> float:
    """A 0-10 judge score. 0 is a real answer (no risk), not a missing one; "7/10" or "7" parse as 7."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    m = re.match(r"\s*(\d+(?:\.\d+)?)", str(value or ""))
    return float(m.group(1)) if m else default


def _strings(value) -> list[str]:
    return [str(x) for x in value] if isinstance(value, list) else ([str(value)] if value else [])


def judge_script(script: dict, job_id: str | None = None, brief: str = "") -> tuple[list[Gate], dict]:
    try:
        j = llm.complete(judge_prompt(script, brief), want_json=True, temperature=0.2, job=job_id)
    except Exception as e:  # noqa: BLE001 - judging is advisory when every LLM is down
        events.emit("JUDGE_UNAVAILABLE", job=job_id, error=str(e)[:200])
        return [], {}
    if not isinstance(j, dict):
        events.emit("JUDGE_UNAVAILABLE", job=job_id, error=f"judge returned {type(j).__name__}, not an object")
        return [], {}
    num = lambda k: judge_number(j.get(k))  # noqa: E731
    fixes = "; ".join(_strings(j.get("fixes"))[:3])
    suspects = "; ".join(_strings(j.get("suspect_claims"))[:3])
    # Jev (when enabled) gets the final say on the publish-safety question, code keeps the fallback.
    safe = decide.ask({"safe_to_publish": decide.Q(
        "noul", "Is this short video script safe to publish as general money education: no personalized "
        "financial advice, no promised returns, no claims likely to be false?",
        fallback=1.0 if num("compliance_risk") <= 4 else 0.0)},
        state={"title": script.get("title"), "script": narration(script)[:3000], "judge": j}, job=job_id)
    g = [
        Gate("judge_hook", num("hook") >= 7, 8, False, f"hook scored {num('hook'):.0f}/10. {fixes}"),
        Gate("judge_retention", num("retention") >= 6, 6, False, f"retention scored {num('retention'):.0f}/10. {fixes}"),
        Gate("judge_value", num("value") >= 6, 5, False, f"value scored {num('value'):.0f}/10. {fixes}"),
        Gate("judge_facts", num("factual_risk") <= 4, 10, True, f"factual risk {num('factual_risk'):.0f}/10: {suspects}"),
        Gate("judge_compliance", float(safe["safe_to_publish"].value) >= 0.5, 10, True,
             f"compliance risk {num('compliance_risk'):.0f}/10"),
    ]
    return g, j


def check_voice(voice: dict) -> list[Gate]:
    lo, hi = config.load()["production"]["target_seconds"]
    d = voice["duration"]
    return [
        Gate("duration", lo <= d <= hi + 1.5, 10, True, f"{d:.1f}s; need {lo:.0f}-{hi:.0f}s (TikTok rewards need >60s).", "script"),
        Gate("word_timings", len(voice["words"]) > 50, 8, True, "missing word timings for captions", "voice"),
        Gate("voice_provider", voice["provider"] in ("edge", "elevenlabs"), 2, False,
             f"voice came from fallback {voice['provider']} (estimated caption timing)", "voice"),
    ]


def check_visuals(imgs: list[dict], beats: int) -> list[Gate]:
    fallback = [i["beat"] + 1 for i in imgs if i["provider"] in ("procedural",)]
    lowres = [i["beat"] + 1 for i in imgs if i["provider"] == "pollinations"]
    return [
        Gate("image_count", len(imgs) == beats, 10, True, f"{len(imgs)} images for {beats} beats", "visuals"),
        # a few abstract fallbacks are a style note; a video that is mostly gradients is not a video (hold it)
        Gate("no_placeholder_art", not fallback, 6, len(fallback) * 2 > max(1, beats),
             f"beats using abstract fallback art: {fallback}", "visuals"),
        Gate("image_quality", not lowres, 3, False, f"beats using low-res fallback images: {lowres}", "visuals"),
    ]


def probe(path: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,width,height,r_frame_rate:format=duration,size", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def frame_luma(path: str, at: float) -> bytes:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{at:.2f}", "-i", path, "-frames:v", "1", "-vf",
                        "scale=64:114,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    return p.stdout


def mean_brightness(path: str, at: float) -> float:
    data = frame_luma(path, at)
    return sum(data) / max(1, len(data))


def frame_visible(data: bytes) -> bool:
    """A frame reads as black only when it is dark everywhere. Low-key cinematic shots (the myth and math
    looks) average under 18 but keep lit detail: their 90th-percentile pixel is well above 40."""
    if not data:
        return False
    s = sorted(data)
    return sum(s) / len(s) > 18 or s[int(len(s) * 0.9)] > 40


def check_render(info: dict, voice: dict) -> list[Gate]:
    cfg = config.load()["production"]
    pr = probe(info["video"])
    v = next((s for s in pr["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    dur = float(pr["format"]["duration"])
    size_mb = int(pr["format"]["size"]) / 1e6
    num, _, den = v.get("r_frame_rate", "0/1").partition("/")
    fps = float(num) / float(den or 1)
    words = len(voice["words"])
    return [
        Gate("resolution", (v.get("width"), v.get("height")) == (cfg["width"], cfg["height"]), 10, True,
             f"{v.get('width')}x{v.get('height')}", "render"),
        Gate("fps", abs(fps - cfg["fps"]) < 0.5, 4, True, f"{fps} fps", "render"),
        Gate("av_sync_length", abs(dur - voice["duration"]) < 0.35, 8, True,
             f"video {dur:.2f}s vs voice {voice['duration']:.2f}s", "render"),
        Gate("audio_present", a is not None, 10, True, "no audio stream", "render"),
        Gate("file_size", size_mb < 250, 4, True, f"{size_mb:.1f} MB", "render"),
        Gate("first_frame_visible", frame_visible(frame_luma(info["video"], 0.05)), 6, True,
             "first frame is nearly black (kills the hook)", "visuals"),
        Gate("cut_cadence", info["avg_shot"] <= 3.6, 5, False, f"avg shot {info['avg_shot']}s; target <= 3.2s", "render"),
        Gate("caption_coverage", info["captioned_words"] >= words * 0.98, 8, True,
             f"{info['captioned_words']}/{words} words captioned", "render"),
    ]


def check_package(meta: dict) -> list[Gate]:
    d = meta["description"].lower()
    return [
        Gate("disclosure", "not financial advice" in d and "ai-assisted" in d, 10, True, "missing disclaimers", "package"),
        Gate("affiliate_disclosure", not config.load()["channel"].get("has_affiliate_links") or "affiliate" in d, 8, True,
             "affiliate links are on but the description has no affiliate disclosure", "package"),
        Gate("caption_tags", "#" in meta["caption"], 2, False, "caption has no hashtags", "package"),
    ]


def score(gates: list[Gate]) -> tuple[int, list[Gate]]:
    total = sum(g.weight for g in gates) or 1
    got = sum(g.weight for g in gates if g.passed)
    hard = [g for g in gates if g.hard and not g.passed]
    return round(100 * got / total), hard


def failing(gates: list[Gate]) -> list[Gate]:
    return [g for g in gates if not g.passed]


def reconcile(gates: list[Gate]) -> list[Gate]:
    """Once the voice is measured, duration is the truth: a word-count miss on a script whose audio runs
    61-72 s is a style note, not a reason to hold the video (a slow, well-paced playbook can run 150 words)."""
    if any(g.name == "duration" and g.passed for g in gates):
        return [replace(g, hard=False) if g.name == "word_count" else g for g in gates]
    return gates


def report(job, gates: list[Gate], extra: dict | None = None) -> dict:
    gates = reconcile(gates)
    s, hard = score(gates)
    passed = s >= config.load()["gauntlet"]["pass_score"] and not hard
    data = {"job": job.id, "score": s, "passed": passed, "hard_failures": [g.name for g in hard],
            "gates": [asdict(g) for g in gates], **(extra or {})}
    Paths.reports.mkdir(parents=True, exist_ok=True)
    (Paths.reports / f"{job.id}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# Gauntlet: {job.id}", f"Score **{s}/100**, {'PASS' if passed else 'FAIL'}", "",
          "| gate | result | weight | detail |", "|---|---|---|---|"]
    for g in gates:
        md.append(f"| {g.name}{' (hard)' if g.hard else ''} | {'pass' if g.passed else 'FAIL'} | {g.weight:g} | "
                  f"{'' if g.passed else g.detail.replace('|', '/')} |")
    (Paths.reports / f"{job.id}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    events.emit("GAUNTLET", job=job.id, score=s, passed=passed, hard=[g.name for g in hard])
    return data
