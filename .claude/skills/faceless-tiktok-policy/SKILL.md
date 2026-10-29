---
name: faceless-tiktok-policy
description: Keep Quiet Money TikTok posts inside the Community Guidelines. Wording and picture checklist, the commercial-disclosure and AI-label toggles, the lint (faceless/ttpolicy.py) the poster runs, and what to do when TikTok removes a video. Use before posting anything to TikTok, when writing captions, titles, on-screen text or spoken lines, when a video is removed or a warning arrives, or when asked about TikTok policy.
metadata:
  author: quiet-money
  version: 1.0.0
  source: tiktok.com/community-guidelines (fetched 2026-10-29) and the removal notice on the account, 2026-10-27
---

# TikTok policy for a faceless finance channel

## What happened (so it is not repeated)
The 2026-10-27 hero Short was removed ("This video violates our Community Guidelines", first warning, "the next violation will result in a strike"). The notice names no rule. The post said "Every month something quietly **bleeds** you" in the caption AND in the spoken line, plus "Free **money** Reset checklist". The other posts of the same day, with the same "link in bio" line, stayed up, so the differences are the prime suspects: **bleeds** (graphic-content vocabulary, caption and audio) and **free money** (a scam phrase). Neither is confirmed. A warning is on the account: treat every post as the one that could become a restriction.

## The rules that can touch us (TikTok Community Guidelines)
- **Shocking and graphic content:** extremely gory, disturbing or violent material is removed; excessive blood, graphic fights and graphic fictional violence are age-restricted and kept off the For You feed.
- **Fraud and scams:** fake investment offers and "get-rich-quick" schemes are removed. Finance education must never read like a payout promise.
- **Commercial disclosure:** promoting your own business, product or service needs the **Content disclosure and ads** setting (Your brand). Undisclosed promotion loses reach, can get posting restrictions, and repeat offenders lose the account.
- **Edited media and AIGC:** realistic AI scenes must be labelled. Our label is the **AI-generated content** toggle, always ON (never written on screen).
- **Misinformation and unoriginal content:** no claims that could cause harm; reused material with nothing added is kept off the feed.
- **Enforcement:** warning, then temporary restriction of features or posting, then a ban; severe violations skip the warning. In-app the appeal window is 80 days.
- Sources: community-guidelines `/en/integrity-authenticity`, `/en/sensitive-mature-themes`, `/en/regulated-commercial-activities`, `/en/accounts-features`, `/en/mental-behavioral-health`. The notice text in the app is generic, so the rule behind a removal is always a guess.

## Before every TikTok post
1. **Lint the caption, the spoken lines and the on-screen text:** `python -c "from faceless import ttpolicy; print(ttpolicy.report(open('caption.txt').read()))"`. `tools/tt-phone-post.py` runs it and refuses `block` and `warn` hits (override only with `--allow-wording` and a reason in the receipt note). The gauntlet shows the same hits as the advisory gate `platform_wording`.
2. **Words to avoid:** bleed, blood, kill, murder, shoot, bomb, gun, suicide, self-harm (use drains, leaks, costs, wipes out); free money, get rich, guaranteed, risk-free, double your money, easy money (use "free checklist", "can", "often"); payout promises of any kind (`faceless-offer`).
3. **Picture:** no blood, wounds, gore; no glass shattering as an explosion, crashes or fire aimed at people; nothing a classifier could read as violence. Cinematic metaphors (coins, doors, rockets) are fine.
4. **Turn on both toggles** in More options: **AI-generated content** ON, and **Content disclosure and ads -> Your brand** whenever the caption promotes our own checklist, planner, kit or gig (`ttpolicy.needs_commercial_disclosure`). Paid offers (the Money Reset Kit, the Daily Planner) always need it.
5. Keep hashtags to five and complete words (TikTok autocompletes the last one).

## When a video is removed or a warning arrives
1. Read it: TikTok -> Inbox -> System notifications -> Account updates -> the removal -> Next (reasons) -> Next (what you can do).
2. Do not appeal or send feedback without the owner: both are account actions.
3. Find the likely cause with `ttpolicy` on the caption, the voice lines and the on-screen text; fix the wording in the source (script, `tools/hero_edit.py` lines, caption) and re-render.
4. Post a **new** version, never the identical file. Record the change in `state/phone/receipts.jsonl` (`phone done ... --note`).
5. Add what was learned to `LEXICON` in `faceless/ttpolicy.py` and a test in `tests/test_ttpolicy.py`.
