# Intake: antiwork/gumroad-cli

- **Source:** https://github.com/antiwork/gumroad-cli
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **MED `binary-download`:** ships or downloads prebuilt binaries: unreviewed code
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: GUMROAD_ACCESS_TOKEN, GUMROAD_ADMIN_TOKEN

## Commands its docs tell you to run (read, do not run)

```
brew install antiwork/cli/gumroad
curl -fsSL https://gumroad.com/install-cli.sh | bash
go install github.com/antiwork/gumroad-cli/cmd/gumroad@latest
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# <img src="assets/gumroad-badge.svg" height="28" alt="Gumroad"> Gumroad CLI

CLI for the [Gumroad API](https://app.gumroad.com/api). Designed for humans and AI agents alike.

## Install

'''sh
brew install antiwork/cli/gumroad
'''

On Windows, download [`gumroad-cli_windows_amd64.zip`](https://github.com/antiwork/gumroad-cli/releases/latest/download/gumroad-cli_windows_amd64.zip) or [`gumroad-cli_windows_arm64.zip`](https://github.com/antiwork/gumroad-cli/releases/latest/download/gumroad-cli_windows_arm64.zip), unzip it, and put `gumroad.exe` on your PATH. In PowerShell:

'''powershell
Invoke-WebRequest https://github.com/antiwork/gumroad-cli/releases/latest/download/gumroad-cli_windows_amd64.zip -OutFile gumroad-cli.zip
Expand-Archive .\gumroad-cli.zip -DestinationPath "$env:LOCALAPPDATA\gumroad"
$env:Path = "$env:LOCALAPPDATA\gumroad;$env:Path"
[Environment]::SetEnvironmentVariable("Path", "$env:LOCALAPPDATA\gumroad;" + [Environment]::GetEnvironmentVariable("Path", "User"), "User")
gumroad auth login
'''

Use Windows Terminal or PowerShell. Quote paths that contain spaces (`& "$env:LOCALAPPDATA\gumroad\gumroad.exe"`). If SmartScreen blocks `gumroad.exe`, choose More info → Run anyway. Homebrew and the curl installer do not apply to stock PowerShell.

<details>
<summary>Other installation methods</summary>

'''sh
# Shell script (macOS, Linux, and Windows Git Bash / MSYS2)
cur
```

## Verdict (a person or the review step fills this in)

- [x] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**USE**, pipeline stage: sell.

Official Gumroad CLI (MIT), built for people and agents. faceless/shop.py already drives it to create DRAFT products only, with the owner's token. Its curl installer is a pipe-to-shell line: install by `brew` or `go install ...@<tag>` (pinned), never the script.

**Worth taking:** Command shapes for products, comps and sales are mirrored in shop.py.

**Only the owner can:** Put GUMROAD_ACCESS_TOKEN in the Claude Code environment (never in a file) when ready for drafts.
