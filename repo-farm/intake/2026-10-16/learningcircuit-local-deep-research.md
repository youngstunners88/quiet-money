# Intake: LearningCircuit/local-deep-research

- **Source:** https://github.com/LearningCircuit/local-deep-research
- **Looked at:** 2026-10-16 05:33 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: LDR_LLM_OPENAI_API_KEY

## Commands its docs tell you to run (read, do not run)

```
docker run -d -p 11434:11434 --name ollama ollama/ollama
docker exec ollama ollama pull gpt-oss:20b
docker run -d -p 8080:8080 --name searxng searxng/searxng
docker run -d --network host \
curl -O https://raw.githubusercontent.com/LearningCircuit/local-deep-research/main/docker-compose.yml && docker compose up -d
curl -O https://raw.githubusercontent.com/LearningCircuit/local-deep-research/main/docker-compose.yml && \
curl -O https://raw.githubusercontent.com/LearningCircuit/local-deep-research/main/docker-compose.gpu.override.yml && \
docker compose -f docker-compose.yml -f docker-compose.gpu.override.yml up -d
pip install local-deep-research
python -m local_deep_research.web.app   # starts the web UI on http://localhost:5000
python -m local_deep_research.benchmarks.cli.benchmark_commands simpleqa --examples 50
pip install "local-deep-research[mcp]"
curl \
python -c "from local_deep_research.database.sqlcipher_compat import get_sqlcipher_module; \
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Local Deep Research

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/LearningCircuit/local-deep-research?style=for-the-badge)](https://github.com/LearningCircuit/local-deep-research/stargazers)
[![Docker Pulls](https://img.shields.io/docker/pulls/localdeepresearch/local-deep-research?style=for-the-badge)](https://hub.docker.com/r/localdeepresearch/local-deep-research)
[![PyPI Downloads](https://img.shields.io/pypi/dm/local-deep-research?style=for-the-badge)](https://pypi.org/project/local-deep-research/)

[![Trendshift](https://trendshift.io/api/badge/repositories/14116)](https://trendshift.io/repositories/14116)

[![Commits](https://img.shields.io/github/commit-activity/m/LearningCircuit/local-deep-research?style=for-the-badge)](https://github.com/LearningCircuit/local-deep-research/commits/main)
[![Last Commit](https://img.shields.io/github/last-commit/LearningCircuit/local-deep-research?style=for-the-badge)](https://github.com/LearningCircuit/local-deep-research/commits/main)

[![SimpleQA Accuracy](https://img.shields.io/badge/SimpleQA-~95%25_Accuracy-gold?style=for-the-badge)](https://huggingface.co/datasets/local-deep-research/ldr-benchmarks)
[![SQLCipher](https://img.shields.io/badge/Database-SQLCipher_Encrypted-red?style=for-the-badge&logo=sqlite&logoColor=white)](docs/SQLCIPHER_INSTALL.md)


[![OpenSSF Scorecard](https://api.securityscorecar
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-16)

**PARK**, pipeline stage: ideate.

MIT. A research assistant that runs its own agent loop with an LLM and search engines and returns cited reports; the README says it needs Ollama (or any OpenAI-compatible endpoint) plus SearXNG, ships as Docker or pip, and makes no telemetry calls. It does not save us money: our research and fact sheets cost a few cents of Opus per video, a local model needs a GPU this container lacks, and a hosted model would cost the same tokens the engine already spends. It adds a service to run. Flags: MED unpinned-run, LOW telemetry (the README says none).

**Worth taking:** Two ideas. (1) The `search` tool returns raw results from free engines with no LLM call, which is the cheap way to fact-check or watch topics: our engine can call Wikipedia, Wikinews, The Guardian and the Wayback Machine directly for the same effect. (2) A research library that accumulates sources, which our channel/research briefs already do by hand.

**Only the owner can:** None. Revisit only if research spend becomes a real line in the ledger.
