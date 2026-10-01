"""Package stage: platform metadata with the disclosures every post needs."""

from __future__ import annotations

import json

from faceless import config

DISCLAIMER = "Educational content, not financial advice. Narration and visuals are AI-assisted."


def run(job, script: dict) -> dict:
    ch = config.load()["channel"]
    tags = script.get("hashtags") or ["#money", "#personalfinance"]
    link = ch.get("link_in_bio", "")
    desc = [script.get("description", "")]
    if link:
        desc += ["", f"Free 7-day Money Reset checklist + calculators: {link}"]
    if ch.get("has_affiliate_links"):
        desc += ["Some links are affiliate links: I may earn a commission at no cost to you."]
    desc += ["", DISCLAIMER, "", " ".join(tags + ["#shorts"])]
    caption = script.get("caption") or script["title"]
    for t in tags:
        if t.lower() not in caption.lower():
            caption += f" {t}"
    meta = {
        "title": script["title"][:95],
        "description": "\n".join(desc).strip(),
        "caption": caption[:2150],
        "hashtags": tags,
        "first_comment": script.get("first_comment", ""),
        "pillar": job.pillar,
        "topic": job.topic,
    }
    (job.dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta
