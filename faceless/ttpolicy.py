"""TikTok wording and disclosure lint (skill faceless-tiktok-policy).

TikTok removed a Quiet Money video (the 2026-10-27 hero, caption "Every month something quietly bleeds you...") for a "Community Guidelines" violation and its
notice names no rule. The rules that can touch a finance-education Short are: Shocking and Graphic Content, Fraud and Scams, Commercial disclosure, Edited Media
and AIGC. This module catches the wording that tends to trip them BEFORE a post goes out. It is advisory text matching, not TikTok's classifier: a clean result
does not guarantee the post stays up, and a hit is a reason to reword, not proof of a violation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# severity: "block" = reword before posting; "warn" = reword unless the sentence needs it; "watch" = fine in context, check the picture too
LEXICON: list[tuple[str, str, str, str]] = [
    # pattern, severity, policy area, suggested replacement
    (r"\bbleed(?:s|ing)?\b", "block", "graphic content", "drains, leaks, costs you"),
    (r"\bblood(?:y|shed)?\b", "block", "graphic content", "cost, price"),
    (r"\b(?:kill|kills|killed|killing|murder\w*)\b", "block", "violent content", "ends, wipes out, stops"),
    (r"\b(?:suicide|self[- ]harm|kill yourself)\b", "block", "suicide and self-harm", "(remove)"),
    (r"\b(?:shoot|shot|shooting|bomb\w*|explod\w*|gun\w*)\b", "block", "violent content", "hit, jump, spike"),
    (r"\bfree money\b", "warn", "fraud and scams", "a free checklist, a free guide"),
    (r"\bget rich(?: quick)?\b|\brich quick\b|\bquick cash\b|\beasy money\b", "block", "fraud and scams", "build wealth slowly"),
    (r"\bguarantee[ds]?\b|\brisk[- ]free\b|\bno risk\b|\bsure thing\b", "block", "fraud and scams", "can, often, historically"),
    (r"\bdouble your (?:money|savings|income)\b|\b\d+x your (?:money|income)\b", "block", "fraud and scams", "(remove the promise)"),
    (r"\bpassive income\b|\bquit your job\b|\bmake \$?\d[\d,]* (?:a|per) (?:day|week|month)\b", "warn", "fraud and scams", "describe the mechanism, not the payout"),
    (r"\b(?:dies|died|dead|death|war)\b", "watch", "graphic content", "fine as a fact in a story; keep it off the picture"),
]

# picture and sound: no regex can see these, so the skill carries a checklist and the poster prints it
VISUAL_WATCHLIST = (
    "blood, wounds, injuries, gore, corpses",
    "shattering glass shown as an explosion, vehicle crashes, fire and explosions, weapons pointed at people",
    "real-looking minors, real public figures shown doing or saying something they did not",
    "a realistic scene with no AI label (the label must be ON for every post)",
)

DISCLOSURE_PATTERN = re.compile(
    r"link in bio|\bour (?:kit|planner|checklist|guide|course|gig)\b|money reset (?:kit|checklist)|\bdaily planner\b|\b(?:paid|buy|gumroad|fiverr)\b", re.I)


@dataclass(frozen=True)
class Finding:
    severity: str
    area: str
    text: str
    suggestion: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.area}: \"{self.text}\" -> {self.suggestion}"


def scan(text: str) -> list[Finding]:
    out: list[Finding] = []
    for pat, sev, area, fix in LEXICON:
        for m in re.finditer(pat, text or "", re.I):
            out.append(Finding(sev, area, m.group(0), fix))
    return out


def needs_commercial_disclosure(text: str) -> bool:
    """True when the caption promotes the studio's own offer (a checklist, planner, kit, gig). TikTok requires the Content disclosure toggle ("Your brand") for that."""
    return bool(DISCLOSURE_PATTERN.search(text or ""))


def blockers(text: str) -> list[Finding]:
    return [f for f in scan(text) if f.severity in ("block", "warn")]


def report(text: str) -> str:
    fs = scan(text)
    lines = [str(f) for f in fs] or ["no risky wording found"]
    if needs_commercial_disclosure(text):
        lines.append("[disclosure] promotes our own offer: turn on Content disclosure and ads -> Your brand before posting")
    return "\n".join(lines)
