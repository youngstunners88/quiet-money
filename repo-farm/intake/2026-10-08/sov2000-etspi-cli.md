# Intake: sov2000/etspi-cli

- **Source:** https://github.com/sov2000/etspi-cli
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | GPL-3.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `build-time-code`:** installs by running its own script (install.sh / setup.py / source-only release): read it before use
- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: ETSPI_KEY, ETSPI_REFRESH_TOKEN, ETSPI_TOKEN, YOUR_API_KEY, YOUR_AUTH_TOKEN

## Commands its docs tell you to run (read, do not run)

```
pipx install etspi
python = "^3.12"
python-dotenv = "^1.0.1"
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Etsy Shop CLI

Etspi is a command-line tool that empowers Etsy sellers to manage their shops and listings efficiently. The tool is an interface to the [API](https://developers.etsy.com/documentation) 
provided by Etsy and allows viewing and managing the shop and the listings directly with JSON.

## Prerequisites:

- Access to the Etsy API is essential. Review [Etsy Quick Start Guide](https://developers.etsy.com/documentation/tutorials/quickstart) for directions on how to get your personal API key. 
- Familiarize yourself with the Etsy OAuth 2.0 authentication process ([link to Etsy OAuth 2.0 documentation](https://developers.etsy.com/documentation/essentials/authentication))
- Familiarity with JMESPath expressions ([link to JMESPath examples](https://jmespath.org/examples.html)) is recommended to filter and transform output data.

## Features:
- **Easy Authentication and Authorization:** Etspi guides you through the process of obtaining and managing API tokens.
- **Automatic Token Management:** Etspi simplifies token maintenance by automatically refreshing access tokens as needed (if configured).
- **Listing Management:** Handle shop listings and variant inventory directly from the command line.
- **Flexible Output Filtering:** Tailor output using JMESPath expressions to retrieve only the data you need.
- **Streamlined Request Formatting:** Transform listing data effortlessly
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: sell.

GPL-3.0 command-line client for the Etsy API v3 (OAuth, listing and variant management). Needs the owner's Etsy developer app. Etsy is the one rail with no agent path today, and creating listings by API on a brand-new shop looks like automated activity; the first listings should be made by hand from the ready packs.

**Worth taking:** Its mapping of listing fields to API calls is the reference if we later write a thin draft-only client (state=draft, never publish).

**Only the owner can:** Create an Etsy developer app only after the first four listings are live and the shop has history.
