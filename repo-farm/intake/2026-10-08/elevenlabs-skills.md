# Intake: elevenlabs/skills

- **Source:** https://github.com/elevenlabs/skills
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: CURSOR_API_KEY, ELEVENLABS_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npx skills add elevenlabs/skills
python3 evals/run_all.py -v
python3 evals/run_all.py --trigger-only -v
python3 evals/run_all.py --functional-only -v
python3 evals/run_all.py --skills text-to-speech agents -v
python3 evals/run_all.py --model gpt-5.4-high -v
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
![LOGO](/logo.png)

# ElevenLabs Skills

Agent skills for [ElevenLabs](https://elevenlabs.io) developer products. These skills follow the [Agent Skills specification](https://agentskills.io/specification) and can be used with any compatible AI coding assistant.

## Installation

'''bash
npx skills add elevenlabs/skills
'''

## Available Skills

| Skill | Description |
|-------|-------------|
| [text-to-speech](./text-to-speech) | Convert text to lifelike speech using ElevenLabs' AI voices |
| [speech-to-text](./speech-to-text) | Transcribe audio files to text with timestamps |
| [speech-engine](./speech-engine) | Add real-time voice conversations to a custom LLM or chat agent |
| [agents](./agents) | Build conversational voice AI agents |
| [sound-effects](./sound-effects) | Generate sound effects from text descriptions |
| [music](./music) | Generate music tracks using AI composition |
| [voice-changer](./voice-changer) | Transform the voice in an audio recording into a different target voice (speech-to-speech) |
| [voice-isolator](./voice-isolator) | Remove background noise and isolate vocals/speech from audio |
| [dubbing](./dubbing) | Dub audio/video into other languages while preserving the original speakers' voices |
| [setup-api-key](./setup-api-key) | Guide through obtaining and configuring an ElevenLabs API key |

## Configuration

All skills require an ElevenLabs API 
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: voice.

MIT agent skills for text-to-speech, speech-to-text, sound effects, music, voice changing, noise isolation and dubbing. Two ideas are worth a build later; installing the skills is not.

**Worth taking:** (1) Sound effects: a one-time library of short whooshes and hits mixed quietly under hooks and transitions. (2) Dubbing: the same finished video in Spanish or Portuguese, using free Edge neural voices and an LLM translation, which multiplies output without new visuals. Both are proposals in channel/empire/PLAN.md.

**Only the owner can:** Whether to open a second-language channel (a separate account per language).
