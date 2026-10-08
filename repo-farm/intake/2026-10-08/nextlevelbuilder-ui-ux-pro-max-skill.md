# Intake: nextlevelbuilder/ui-ux-pro-max-skill

- **Source:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: GITHUB_TOKEN, GOOGLE_FONTS_API_KEY, NPM_TOKEN

## Commands its docs tell you to run (read, do not run)

```
npm install -g ui-ux-pro-max-cli
python3 --version
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "beauty spa wellness" --design-system -p "Serenity Spa"
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "fintech banking" --design-system -f markdown
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "glassmorphism" --domain style
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "elegant serif" --domain typography
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "dashboard" --domain chart
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "error summary validation" --domain ux
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "decorative icon aria hidden" --domain icons
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "icon button accessible label" --domain icons
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "orphan heading line balance" --domain ux
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "badge chip label wraps to second line" --domain ux
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "rapid chip animation interrupted" --domain ux
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "form validation" --stack react
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# [UI UX Pro Max](https://uupm.cc)

<p align="center">
  <a href="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/README.id.md">🇮🇩 Bahasa Indonesia</a> |
  <a href="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/README.ko.md">🇰🇷 한국어</a> |
  <a href="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/README.vi.md">🇻🇳 Tiếng Việt</a> |
  <a href="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/README.zh.md">🇨🇳 简体中文</a> |
  <a href="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/README.md">🇺🇸 English</a>
</p>

<p align="center">
  <a href="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/releases"><img src="https://img.shields.io/github/v/release/nextlevelbuilder/ui-ux-pro-max-skill?style=for-the-badge&color=blue" alt="GitHub Release"></a>
  <img src="https://img.shields.io/badge/reasoning_rules-192-green?style=for-the-badge" alt="192 Reasoning Rules">
  <img src="https://img.shields.io/badge/UI_styles-79_searchable-purple?style=for-the-badge" alt="79 searchable UI styles">
  <img src="https://img.shields.io/badge/python-3.x-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.x">
  <a href="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/LICENSE"><img src="https://img.shields.io/github/license/nextlevelbuilder/ui-ux-pro-max-skill?style=for-the-badge&co
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: package.

MIT. A searchable data set of 79 UI styles, palettes, type pairings and UX rules behind a plain Python search script, plus a skill wrapper. Useful when the website and link-in-bio page are redesigned; the studio's own brand kit already fixes colours and fonts for video and listings.

**Worth taking:** Review the data files and, if good, vendor the UX-rule and chart tables (with the licence) for the site build; do not install its npm CLI.
