# Gauntlet: the QA desk

Every video runs the gauntlet before it can be published. Code lives in `faceless/gauntlet.py`.
Reports land in `reports/<job_id>.md|json`; the day's summary in `reports/daily-<day>.md`.

## How it decides
- **Hard gates** block publishing (the video is *held* for review).
- **Soft gates** cost points. Ship at **score >= 80 and zero hard failures**.
- Failing script gates are fed back as rewrite instructions (max `max_fix_rounds` = 2).
  A duration miss triggers a voice refit, then one script rewrite. Human scripts are never rewritten.
- The final publish/hold call goes through the decision layer (`faceless/decide.py`): code's verdict
  is the fallback; Jev can take over when enabled and confident.

## Gates
| Stage | Gate | Hard? | Why |
|---|---|---|---|
| Script | word_count (175-200) | soft | proxy for duration |
| | beat_count (9-16), visual_prompts | hard | the renderer needs them |
| | hook_length, hook_trigger, hook_text | soft | the first 3 s decide reach |
| | compliance_phrases, no_ticker_picks | hard | finance policy |
| | banned_phrases, readability, loop_ending, callouts, title, hashtags | soft | retention + polish |
| | originality (similarity < 0.55 vs history) | hard | YouTube inauthentic-content policy |
| Judge (LLM) | hook >= 7, retention >= 6, value >= 6 | soft | editor's eye |
| | factual risk <= 4, safe_to_publish | hard | trust + policy |
| Voice | duration 61-72 s, word timings present | hard | TikTok rewards + captions |
| Visuals | one image per beat | hard | |
| | no placeholder art, no low-res fallback | soft | quality |
| Render | 1080x1920, 30 fps, A/V length match, audio, size, visible first frame, caption coverage | hard | platform specs |
| | cut cadence (avg shot <= 3.6 s) | soft | retention |
| Package | disclaimers, affiliate disclosure | hard | legal |

## The ops gauntlet (how the engine itself gets better)
Run a batch → read the reports and look at frames → fix the root cause in code or prompts → re-run
until a clean pass. Log each round below so the next session starts where this one stopped.

### Log
- **R1 (video #1):** 91/100, held. Script 227 words → 74.8 s even at 1.18x. Hook headline showed "DIEDNWITH"
  (escaped `\N`). Captions crossed sentences (TTS drops punctuation). Render 4 min. File 78 MB.
- **R2:** 96/100. Fixed escaping, re-attached punctuation to timed words, sentence-aware chunking,
  callout wrapping, OpenCV warp (9x faster frames), lower grain. Judge: bridge to the $200/month math
  read as if Read invested 40 years → reworded; added "Not a promise. Just math."
- **R3:** 100/100, published. Render 1.9 min, 32 MB, -14.7 LUFS, 66.8 s. Grading moved into parallel shot
  encodes; word_count demoted to soft (duration is the hard truth).
- **R4 (autonomous batch):** Gemini scripts landed ~169 words → slowed voice to 0.94x. Raised base voice rate
  to +14%, word range to 175-200, refit now aims at the nearest window edge.
- **R5:** math 99/100 published. Psychology **held** on judge_compliance (compliance 4, factual 2): the judge
  read hypothetical math with a stated assumption as a return promise, and the gate double-counted factual
  risk. Added explicit 0-10 calibration anchors to the judge, decoupled compliance from factual risk
  (<= 4 passes). Visual review: Gemini spelled numbers out ("two hundred fifty-two months") making weak
  captions → digits required; no contractions → required; FLUX drew gibberish text on cards/screens →
  visual rule steers to writing-free objects; hook_text trailing period stripped. Cloudflare's safety filter
  flagged 2/26 images → retry once with a new seed before the paid fallback. Images moved to 864x1536
  (same 156 neurons per image as 768x1344, less upscaling). Weak-word caption pass now loops (test caught it).
- **R6 (batch results):** math 99 + playbook 91 published, psychology 91 + myth 89 held. Requiring digits made
  Gemini under-write (119-125 words). Found that a duration-driven rewrite **skipped the script gates and
  judge** and the report kept the first draft's gates. Fixed: one gated `script_loop` for every script that
  ships; length rewrites get a concrete word target; word_count turns hard when far out of range; Gemini
  per-model 75 s timeout (one hung call had cost 3 min).
- **R7:** visual review of playbook: clean look, digits read well, no gibberish text, but it promised 3 steps
  and delivered one. Added a `pillar_structure` gate (playbook: three numbered steps; myth: flip the belief
  in the first 3 beats) and spelled the step format out in the pillar config. Held psychology re-run now
  passes the calibrated judge.
