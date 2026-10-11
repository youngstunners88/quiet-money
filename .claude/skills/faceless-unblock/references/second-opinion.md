# Second opinion from other models

Use it when two hypotheses have failed, or before a change you cannot easily undo. It is a hint source, not an authority.

- **Command:** `python .claude/skills/faceless-unblock/scripts/consult.py "the question" --file notes.md [--model google/gemini-3.1-pro-preview] [--model microsoft/phi-4]`
- **Defaults:** `google/gemini-3.1-pro-preview` (about $0.025 for a 3,000-token brief) and `microsoft/phi-4` (about $0.0002). Check `https://openrouter.ai/api/v1/models` for current ids and prices before changing them.
- **Cap:** $0.25 per case. The script refuses a brief that would exceed it and prints the cost of every call. OpenRouter needs a positive balance (`python -m faceless keys openrouter`); never top it up.
- **Brief:** the symptom with ids, what you ruled out, the relevant code or schema, and one concrete question. Secrets are redacted before sending, but do not paste any on purpose.
- **Trust:** verify every claim against the source. In the first review, one model invented tool names (`YOUTUBE_SCOPE_VALIDATOR`) that do not exist; the other raised a real terms-of-service risk and a zombie-process risk, which are now in the skill.
- **Never** ask a model to help get around a verification, policy or authentication check.
