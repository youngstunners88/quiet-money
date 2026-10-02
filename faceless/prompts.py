"""Prompt templates in the five-part structure (Identity, Task, Context, Constraints, Output format).

The folder files carry the persistent identity; these prompts carry the per-task direction.
"""

from __future__ import annotations

from faceless import config, moneymath

BANNED = ["in today's world", "let's dive in", "delve", "game-changer", "game changer", "unlock",
          "buckle up", "smash that", "hey guys", "welcome back", "did you know", "in this video",
          "testament", "tapestry", "navigate the", "realm"]

COMPLIANCE_BANNED = ["guaranteed return", "guaranteed returns", "risk-free", "risk free", "get rich quick",
                     "you should buy", "buy this stock", "100% safe", "can't lose", "cannot lose"]


def identity() -> str:
    ch = config.load()["channel"]
    return (f"You are the head writer of \"{ch['name']}\", a faceless short-form channel about "
            f"{ch['niche']}. Tagline: \"{ch['tagline']}\". You write like a calm, sharp documentary "
            f"narrator: short punchy sentences, concrete numbers, zero fluff, quietly confident. "
            f"Audience: {ch['audience']}.")


def script_prompt(pillar, topic: str, angle: str = "", feedback: list[str] | None = None,
                  recent_titles: list[str] | None = None, brief: str = "") -> str:
    cfg = config.load()
    lo, hi = cfg["production"]["words_range"]
    ch = cfg["channel"]
    parts = [
        "# TASK",
        f"Write one vertical short-form video script (TikTok / YouTube Shorts / Reels) for the pillar "
        f"\"{pillar.name}\" on this topic: {topic}." + (f" Angle: {angle}." if angle else ""),
        "",
        "# CONTEXT",
        f"Pillar format: {pillar.format}",
        "The video is narrated by a voiceover over cinematic still images that slowly move, with bold "
        "word-by-word captions. Each beat = one image on screen for ~4-6 seconds.",
        "Retention mechanics that must be present:",
        "1. HOOK (beat 1, under 15 words): open on the single most surprising fact, number, or contradiction. "
        "No greeting, no setup, no question that can be answered with 'no'.",
        "2. Open loop: by beat 2 promise a payoff the viewer only gets by staying.",
        "3. Pattern interrupt around the middle (e.g. 'But here's the part nobody mentions.').",
        "4. Specific numbers, names, and years beat vague claims.",
        "5. LOOP ENDING: the final beat ends mid-thought so it flows back into the first line when the video "
        "replays (e.g. last line '...and that's exactly how' -> first line 'A janitor died with $8 million').",
        f"6. One follow CTA woven into the last 2 beats, in this spirit: \"{ch['cta_follow']}\"",
        "",
        moneymath.fact_sheet() if pillar.id in ("math", "playbook", "myth", "psychology", "escape") else "",
        *(["", "# RESEARCH BRIEF (verified background. Teach the frameworks in your own words and use one item from "
            "'The honest catch'. Do NOT quote anyone and do not make the video about a person; if you name someone at "
            "all, state only facts from this brief, with 'he says' on self-reported numbers)",
            brief] if brief else []),
        "",
        "# CONSTRAINTS",
        f"- LENGTH IS CRITICAL: {lo}-{hi} words in total across all 'say' fields (aim for {(lo + hi) // 2}); the "
        "video must run 61-72 seconds and shorter scripts are rejected. Count the words before answering and "
        "report the count in 'word_count'.",
        "- 11 to 14 beats. Each 'say' is 1-2 sentences, max 20 words. Write for the ear: ALWAYS use contractions "
        "(it's, here's, you're, don't, that's), plain words, 8th-grade reading level.",
        "- Write money and percentages as digits: $226,000, $5, 8%, 30 years (the voice reads them correctly and "
        "the captions look sharper). Years as digits too (2014).",
        "- Every number must be true. For calculations, quote ONLY numbers from the fact sheet above, with its "
        "assumption (e.g. 'at 8% a year'). For stories, only well-documented facts; if unsure, leave it out.",
        "- Educational only: never tell the viewer to buy a specific stock, coin, or product. No promises of returns.",
        f"- Never use these phrases: {', '.join(BANNED + COMPLIANCE_BANNED)}.",
        "- 'callout' is optional on-screen text (max 4 words, often a number like '$698,000'); use it on 4-7 beats, "
        "never on beat 1.",
        "- 'visual' is an image-generation prompt for that beat: a concrete cinematic scene (subject, setting, "
        "lighting, camera angle). Real people must NOT be depicted by face: use hands, silhouettes, backs, objects, "
        "places. No text, numbers, logos, or screens with writing in the image: prefer objects without writing; if a "
        "card, phone, receipt, or document is essential, show it from behind, at a steep angle, or blurred.",
        "- 'hook_text' is the on-screen headline for the first 3 seconds: max 7 words, ALL CAPS energy.",
        "- 'title': max 60 characters, curiosity + specificity, no clickbait lies.",
        "- 'caption': 1-2 punchy lines + 4-5 hashtags (mix broad #money #personalfinance with niche tags).",
        "- 'description': 2-3 sentences summarizing the lesson.",
        "- 'first_comment': a question that invites replies (comments boost reach).",
    ]
    if recent_titles:
        parts += ["", "Recent videos (do NOT repeat their angle or hook):", *[f"- {t}" for t in recent_titles[-25:]]]
    if feedback:
        parts += ["", "# FIX THESE PROBLEMS FROM THE LAST DRAFT", *[f"- {f}" for f in feedback]]
    parts += [
        "",
        "# OUTPUT FORMAT",
        "Return ONLY valid JSON with this exact shape:",
        '{"title": str, "hook_text": str, "word_count": int, "beats": [{"say": str, "callout": str, "visual": str}], '
        '"caption": str, "description": str, "hashtags": [str], "first_comment": str, '
        '"facts": [{"claim": str, "basis": str}]}',
    ]
    return "\n".join(p for p in parts if p is not None)


def ideas_prompt(pillar, n: int, avoid: list[str], briefs: list[str] | None = None,
                 signals: list[str] | None = None) -> str:
    people = ([f"- Topics about a real person are allowed ONLY for people with a research brief: {', '.join(briefs)}. "
               "Set 'brief' to that id (e.g. \"hormozi\"); for topics about no specific person set 'brief' to \"\"."]
              if briefs else [])
    return "\n".join([
        "# TASK",
        f"Propose {n} video topics for the pillar \"{pillar.name}\".",
        "# CONTEXT",
        f"Pillar format: {pillar.format}",
        "Topics that go viral in this niche: surprising true money stories, hidden costs, habits of people who "
        "quietly got rich, psychological traps, myths everyone repeats, simple actions with big payoffs.",
        "# CONSTRAINTS",
        "- Evergreen, globally understandable, factually checkable. No specific stock/crypto picks.",
        "- Each must support a 61-72 second script with a strong number or story.",
        *people,
        *([f"- People are searching for (use as inspiration, do not copy): {'; '.join(signals)}."] if signals else []),
        "- Avoid anything too close to these existing topics:",
        *[f"  - {a}" for a in avoid[-60:]],
        "# OUTPUT FORMAT",
        'Return ONLY JSON: {"ideas": [{"topic": str, "angle": str, "hook": str'
        + (', "brief": str' if briefs else "") + '}]}',
    ])


def judge_prompt(script: dict, brief: str = "") -> str:
    beats = "\n".join(f"{i + 1}. {b['say']}" for i, b in enumerate(script["beats"]))
    notes = ["", "VERIFIED RESEARCH NOTES (claims that match these, attributed as written, are documented: "
             "factual_risk 0-3; a specific claim about these people that is NOT in the notes is unsourced: 6+):", brief] if brief else []
    return "\n".join([
        "You are a ruthless short-form video editor and fact-checker for a personal finance EDUCATION channel.",
        "Score this script. Be strict on craft: most scripts are average.",
        f"TITLE: {script.get('title')}",
        f"HOOK TEXT: {script.get('hook_text')}",
        "SCRIPT:",
        beats,
        *notes,
        "",
        "Calibration for the two risk scores:",
        "factual_risk: 0-3 = documented facts, or math with its assumption stated (e.g. 'at 8% a year'); "
        "4-6 = a vague or unsourced statistic; 7-10 = a specific claim that is likely false.",
        "compliance_risk: 0-3 = general money education (saving, budgeting, habits, psychology, history, "
        "hypothetical math with a stated assumption, generic advice like 'automate your savings'); "
        "4-6 = implies a specific product or presents a likely outcome as certain; "
        "7-10 = tells the viewer to buy/sell a specific security or coin, or promises/guarantees returns.",
        "",
        'Return ONLY JSON: {"hook": 0-10, "retention": 0-10, "value": 0-10, "clarity": 0-10, '
        '"loop_ending": 0-10, "factual_risk": 0-10, "compliance_risk": 0-10, '
        '"suspect_claims": [str], "fixes": [str (max 3 concrete rewrites)]}',
    ])
