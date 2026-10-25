# Security

An AI agent with phone access can read what's on screen and act as you. OpenDeviceMCP is built to keep that local and bounded.

## Threat model

| Risk | Mitigation |
|---|---|
| Remote access to your phone | No network listener. The server only speaks MCP over stdio to the client that launched it. WDA traffic goes to `127.0.0.1`. |
| Agent does something destructive | `confirm-destructive` mode (default) needs `confirmed: true` for install, uninstall, push, and pull. `read-only` blocks all actions. `--dry-run` previews commands. |
| Arbitrary shell commands | `adb_shell` only runs commands that match `shellAllow` and no `shellDeny` rule. Pipes, redirects, `;`, `&`, `$`, backticks, `rm -r`, `reboot`, `su`, `fastboot`, and `dd` are always rejected. |
| Command injection through arguments | Arguments are passed to adb as an argv array, never through a host shell. Package names, activities, tags, and URLs are validated. Typed text is quoted for the device shell. |
| Reading or writing your computer's files | `install_app`, `push_file`, and `pull_file` only accept paths inside `pathAllowlist`. Device paths are limited to `/sdcard`, `/storage`, and `/data/local/tmp`, and `..` is rejected. |
| Controlling the wrong phone | `deviceAllowlist` limits which serials are usable. When several phones are connected, the agent must pick one explicitly. |
| Sensitive data in logs | The audit log stores tool, arguments, status, and a hash of the output. Typed text is replaced with its length. Screenshots and file contents are never logged. |
| Prompt injection from on-screen content | Text in the UI tree is data, not instructions. The agent prompt in `docs/AGENT_PROMPT.md` tells agents to stop and ask before purchases, messages, or deletions. |

## Recommendations

- Use a spare phone or an emulator for unattended runs.
- Keep `mode` at `confirm-destructive` unless you fully trust the workflow.
- Review `~/open-device-mcp/audit.jsonl` after long sessions.
- Turn off USB or wireless debugging when you're not using it.

Report vulnerabilities privately through the repository's security advisory feature.
