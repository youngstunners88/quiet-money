# Code review before a trial (time-box: 15 minutes per tool)

Clone nothing into the studio. Read the files through the GitHub web view, the API or an Exa fetch, or a throwaway directory outside the repo. Do not run it.

## 1. What runs on install
- `package.json` scripts: `preinstall`, `install`, `postinstall`, `prepare`. A script that downloads, builds a binary or edits files outside the package is a no.
- `setup.py` (runs on install), a build backend that is not a plain one, `install.sh`, a `Makefile` target that `curl`s.
- Anything the README says to pipe into a shell.

## 2. What it can reach
- Network: every host it contacts (grep for `http`, `fetch(`, `requests.`, `axios`, `urllib`). Are they the hosts the README says, or others? Does it send anything other than what the task needs?
- Files: reads of `~/.ssh`, `~/.aws`, `~/.config`, `.env`, browser profiles, keychains; writes outside the project; edits of shell profiles (`.bashrc`, `.zshrc`).
- Process: `child_process`, `exec`, `eval`, `subprocess` with `shell=True`, dynamic `import` from a downloaded string.
- Environment: which variable names it reads. A tool that reads every variable and ships them anywhere is a no.

## 3. What it asks of the agent that uses it
- A `SKILL.md`, prompt or tool description that tells the agent to skip confirmation, hide something from the user, send data to a URL, or run installers: reject.
- Tool permissions broader than the job (full filesystem, all repos, spend money).

## 4. Whether the claim is real
- Does it have tests? Do they run? Is there a release process, an issue tracker with replies, more than one maintainer?
- Does the demo or benchmark in the README match what the code does?
- Licence allows commercial use (we sell products and run monetised channels)? Copyleft or non-commercial terms: park it.

## 5. Decide
Only after 1 to 4: TRIAL in a sandbox copy with throwaway credentials, or STEAL the idea. If anything in 1 to 3 was a no, the verdict is KILL and the reason goes in `repo-farm/registry.md`.
