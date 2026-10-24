"""Prompt templates in the five-part structure (Identity, Task, Context, Constraints, Output format).

The folder files carry the persistent identity; these prompts carry the per-task direction.
"""

from __future__ import annotations

from faceless import config, moneymath

BANNED = ["in today's world", "let's dive in", "delve", "game-changer", "game changer", "unlock",
          "buckle up", "smash that", "hey guys", "welcome back", "did you know", "in this video",
          "testament", "tapestry", "navigate the", "realm",
          "part nobody mentions", "part nobody talks about"]      # the old stock re-hook: in 78 of 129 scripts by 2026-10-20

COMPLIANCE_BANNED = ["guaranteed return", "guaranteed returns", "risk-free", "risk free", "get rich quick",
                     "you should buy", "buy this stock", "100% safe", "can't lose", "cannot lose"]


def identity() -> str:
    ch = config.load()["channel"]
    return (f"You are the head writer of \"{ch['name']}\", a faceless short-form channel about "
            f"{ch['niche']}. Tagline: \"{ch['tagline']}\". You write like a calm, sharp documentary "
            f"narrator: short punchy sentences, concrete numbers, zero fluff, quietly confident. "
            f"Audience: {ch['audience']}.")


def aim_words() -> int:
    """The first draft's word target: above the middle of the range (64% of first drafts ran short), never past the top."""
    prod = config.load()["production"]
    lo, hi = prod["words_range"]
    return min(hi, (lo + hi) // 2 + int(prod.get("draft_word_bias", 0)))


def script_prompt(pillar, topic: str, angle: str = "", feedback: list[str] | None = None,
                  recent_titles: list[str] | None = None, brief: str = "") -> str:
    cfg = config.load()
    lo, hi = cfg["production"]["words_range"]
    aim = aim_words()
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
        "Retention structure: the addiction loop (stakes, big question, head fake, re-hook), repeated as cascading loops. "
        "Every step must be TRUE: the twist comes from a documented fact or a fact-sheet number, never from invented drama, "
        "and every question you raise gets answered in this video.",
        "1. STAKES (beat 1, under 15 words): open on something the viewer owns, pays, believes or recognizes (a paycheck, a card, "
        "a car payment, a degree, savings, a company everyone knows) and what it costs them or someone they can root for. "
        "Put one concrete thing in it: an object, a name, a year, or a dollar amount. No greeting, no setup, no question that "
        "can be answered with 'no'. On our own Shorts (small sample) the best openers flipped a belief about the viewer's own "
        "money or put an odd true detail on a familiar thing; abstract bias names, chores and strings of numbers did worst. "
        "A flip must rest on a fact-sheet number or a research brief; never use absolutes such as 'any', 'always', 'designed to' "
        "or 'harder than any' unless the fact sheet says so.",
        "2. BIG QUESTION (beat 2 or 3): give just enough context that ONE specific question forms in the viewer's head (how did "
        "..., why does ..., where does the money go ...). Say it out loud or make it unmistakable. Hold the full answer back "
        "for the payoff.",
        "3. HEAD FAKE (by beat 4): say what most people would assume (A), then snap to what is actually true (B). B must be "
        "documented or computed. If the honest answer is the obvious one, choose a different angle; never fake a twist.",
        "4. RE-HOOK, CASCADING (every 3-4 beats, about every 15-20 seconds): the moment one answer lands, open the next, "
        "narrower question, or move the stakes onto the viewer (their paycheck, their card, this year). Each re-hook names "
        "something specific that is still unanswered and is worded fresh for this topic; never a generic teaser. Plan at least 2.",
        "5. PAYOFF (one of the last 3 beats): answer the big question in plain words, with the viewer in it. Close every loop "
        "you opened.",
        "6. Specific numbers, names, and years beat vague claims.",
        "7. COMPLETE ENDING: the final beat is a complete sentence that finishes its thought and lands the follow CTA. "
        "NEVER trail off, never end on '...' or mid-sentence (the owner hears a cut-off video as a broken one). "
        "Its closing words may echo the opening line so a replay feels continuous.",
        f"8. One follow CTA woven into the last 2 beats, after the payoff, in this spirit: \"{ch['cta_follow']}\"",
        "",
        moneymath.fact_sheet() if pillar.id in ("math", "playbook", "myth", "psychology", "escape", "ledger") else "",
        *(["", "# RESEARCH BRIEF (verified background. Teach the frameworks in your own words and use one item from "
            "'The honest catch'. Do NOT quote anyone and do not make the video about a person; if you name someone at "
            "all, state only facts from this brief, with 'he says' on self-reported numbers)",
            brief] if brief else []),
        "",
        "# CONSTRAINTS",
        f"- LENGTH IS CRITICAL: {lo}-{hi} words in total across all 'say' fields (aim for {aim}); the "
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
        "never on beat 1. When a beat contrasts two amounts or two ideas, write its callout as 'A VS B' (e.g. '$698,000 VS "
        "$298,000', 'ASSET VS LIABILITY'); when a beat is one step of a how-to, write 'STEP ONE', 'STEP TWO' (max 3 steps).",
        "- 'visual' is an image-generation prompt for that beat: a concrete cinematic scene (subject, setting, "
        "lighting, camera angle). Real people must NOT be depicted by face: use hands, silhouettes, backs, objects, "
        "places. No text, numbers, logos, or screens with writing in the image: prefer objects without writing; if a "
        "card, phone, receipt, or document is essential, show it from behind, at a steep angle, or blurred.",
        "- 'hook_text' is the on-screen headline for the first 3 seconds: max 7 words, ALL CAPS energy.",
        "- 'title': max 60 characters, curiosity + specificity, no clickbait lies.",
        "- 'caption': 1-2 punchy lines + 4-5 hashtags (mix broad #money #personalfinance with niche tags).",
        "- 'description': 2-3 sentences summarizing the lesson.",
        "- 'first_comment': a question that invites replies (comments boost reach).",
        "- 'loop_map': the plan the beats follow (beat numbers start at 1): 'stakes' (who or what is at risk, one line), "
        "'big_question' (the one question, ending in '?'), 'assume' (what most people think) and 'reveal' (what is true), "
        "'rehook_beats' (the beat numbers that open the next question, at least 2, between beat 3 and the payoff), "
        "'payoff_beat' (the beat that answers the big question, one of the last 3).",
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
        '"facts": [{"claim": str, "basis": str}], "loop_map": {"stakes": str, "big_question": str, "assume": str, '
        '"reveal": str, "rehook_beats": [int], "payoff_beat": int}}',
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
        "On our own Shorts (small sample) the strongest topics flipped a belief about the viewer's own money (a paycheck, a "
        "degree, a car payment, a savings account) or put an odd true detail on something familiar (a household-name company, "
        "a 1930s habit that still works); bank-fee chores and abstract bias explainers did worst. Each 'hook' carries a stake "
        "the viewer cares about and leaves one question open. Never name a real person or company unless a research brief "
        "for them exists (CLAUDE.md rule 8).",
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
        '"complete_ending": 0-10 (10 = the last line is a complete sentence that finishes its thought; 0 = trails off or ends mid-sentence), "factual_risk": 0-10, "compliance_risk": 0-10, '
        '"suspect_claims": [str], "fixes": [str (max 3 concrete rewrites)]}',
    ])
