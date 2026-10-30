"""Content mix: the daily balance of offense and defense videos (rules in channel/CONTENT-MIX.md).

A video puts the viewer on offense (someone makes a bold move that creates upside), on defense (avoid, cancel, escape a
trap) or neither. On our numbers offense does about twice as well, yet most of the backlog is defense, so the topic picker
asks this module before it takes a topic. The rules never stop the engine: when no admissible topic exists the picker falls
back to the old order and logs MIX_RELAXED (owner: the engine is autonomous).

Posture is a hand label when the backlog item carries `"posture"`; otherwise a keyword read of the topic, which is crude.
`python -m faceless mix` prints the split so the heuristic can be checked against a person's reading.
"""

from __future__ import annotations

import re

from faceless import config

OFFENSE, DEFENSE, NEUTRAL = "offense", "defense", "neutral"
OFFENSE_RE = re.compile(r"\b(bet|bets|bought|buy|buys|build|builds|built|negotiat\w*|royalt\w*|equity|stake|stakes|own|owns|owned|"
                        r"ownership|invest|invests|investing|invested|launch\w*|turned|earn\w*|scale|scaled|deal|deals|acquire\w*|took|gamble\w*|"
                        r"win|wins|won|empire|millionaire|billionaire|monopoly|masters?|move|moves|raise|offer|offers|replace)\b", re.I)
DEFENSE_RE = re.compile(r"\b(trap|traps|cancel|avoid\w*|hidden|leak|leaks|fee|fees|stop|mistake|mistakes|bias|myth|lie|drain\w*|"
                        r"waste|overpay\w*|subscriptions?|ruin\w*|broke|danger\w*|scam\w*|regret|costs?|costing|kill|wipe|lower|"
                        r"bankrupt\w*|blew|froze|shock)\b", re.I)
DEFAULTS = {"enabled": True, "defense_max": 2, "offense_min": 2, "lead_word_max": 1,
            "lead_words": ["trap", "hidden", "cost", "costs", "leak", "quiet", "silent", "why your"]}


def settings() -> dict:
    return {**DEFAULTS, **(config.load().get("mix") or {})}


def posture(item: dict | str) -> str:
    """offense, defense or neutral. An explicit `posture` on the item wins; otherwise the topic's words are counted."""
    if isinstance(item, dict) and item.get("posture") in (OFFENSE, DEFENSE, NEUTRAL):
        return item["posture"]
    text = item.get("topic", "") if isinstance(item, dict) else str(item)
    off, de = len(OFFENSE_RE.findall(text)), len(DEFENSE_RE.findall(text))
    return OFFENSE if off > de else DEFENSE if de > off else NEUTRAL


def lead_words(text: str, words: list[str]) -> set[str]:
    low = text.lower()
    return {w for w in words if re.search(rf"\b{re.escape(w)}\b", low)}


def offense_needed(taken: list[dict], cfg: dict | None = None) -> int:
    cfg = cfg or settings()
    return max(0, int(cfg["offense_min"]) - sum(posture(t) == OFFENSE for t in taken))


def admissible(item: dict, taken: list[dict], remaining: int, cfg: dict | None = None) -> str | None:
    """None when the item may take the next slot of the day, else the reason it may not.
    `taken` are the day's items so far; `remaining` counts the slots left including this one (0 turns the offense floor off)."""
    cfg = cfg or settings()
    p = posture(item)
    if p == DEFENSE and sum(posture(t) == DEFENSE for t in taken) >= int(cfg["defense_max"]):
        return f"defense cap ({cfg['defense_max']} a day)"
    need = offense_needed(taken, cfg)
    if remaining and need >= remaining and p != OFFENSE:
        return f"offense floor: {need} offense still needed in {remaining} slots"
    for w in lead_words(item.get("topic", ""), cfg["lead_words"]):
        if sum(w in lead_words(t.get("topic", ""), [w]) for t in taken) >= int(cfg["lead_word_max"]):
            return f"lead word {w!r} already used today"
    return None


def split(items: list[dict]) -> dict[str, int]:
    out = {OFFENSE: 0, DEFENSE: 0, NEUTRAL: 0}
    for i in items:
        out[posture(i)] += 1
    return out
