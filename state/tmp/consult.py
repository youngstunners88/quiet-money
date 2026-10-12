import os, sys, json, requests
key = os.environ["OPENROUTER_API_KEY"]
skill = open(".claude/skills/faceless-unblock/SKILL.md").read()
incident = open(".claude/skills/faceless-unblock/references/incident-youtube-2026-10.md").read()
PROMPT = f"""You are reviewing an operating skill for an autonomous AI agent that runs a faceless short-video business (YouTube Shorts, TikTok, Instagram). The owner wants the agent to fix small integration problems itself (APIs, accounts, uploads, quotas, OAuth) instead of asking them. The agent can run shell commands, read SDK source, call vendor APIs through a proxy, and open draft pull requests. It cannot sign in to accounts or pass identity/phone verification, and it must not delete or move accounts.

Here is the skill (v1):
<skill>
{skill}
</skill>

Here is the incident it was derived from:
<incident>
{incident}
</incident>

Review it as a senior engineer. Reply in this exact structure, under 350 words total, no preamble:
1. MISSING FAILURE PATTERNS: up to 4 common integration failure patterns this loop does not cover (one line each, with the first probe to run).
2. WRONG OR RISKY RULES: any rule that could cause harm or wasted work (one line each, with the fix).
3. TOP 3 CONCRETE EDITS: exact sentences to add or change.
"""
def ask(model, max_tokens):
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", timeout=240,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": PROMPT}]})
    d = r.json()
    if "choices" not in d:
        return {"model": model, "error": str(d)[:300]}
    u = d.get("usage", {})
    return {"model": model, "text": d["choices"][0]["message"]["content"], "usage": u}
out = [ask("google/gemini-3.1-pro-preview", 1800), ask("microsoft/phi-4", 900)]
json.dump(out, open("state/tmp/consult_v1.json", "w"), indent=1)
for o in out:
    print("=" * 70); print(o["model"], o.get("usage", {}).get("cost", ""), o.get("error", ""))
    print(o.get("text", ""))
