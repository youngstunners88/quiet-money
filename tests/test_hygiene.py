"""Repository hygiene and safety invariants. These do not test behaviour, they pin the promises the operation makes to the owner:
no key in git, nothing rendered or huge in git, spend caps that add up, nothing public without a yes, AI labels on, workflows with no
repository secrets. Changing one of these on purpose means editing the test in the same commit, which is the point: it cannot happen by accident."""

import json
import py_compile
import re
import subprocess
from pathlib import Path

import pytest

from faceless import config, preflight
from faceless.config import STUDIO

# The owner's go, as a switch in the open. Flip a constant only in the commit that records the owner saying yes.
OWNER_APPROVED_LIVE_POSTING = False
OWNER_APPROVED_HOOK_CLIPS = False
LIVE_PUBLISH_MODES = {"upload_post", "composio", "muapi"}

SECRET_SHAPES = {
    "OpenAI/OpenRouter style key": r"\bsk-[A-Za-z0-9_-]{32,}",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "AWS access key id": r"\bAKIA[0-9A-Z]{16}\b",
    "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "JSON web token": r"\beyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}",
    "key assigned a long literal": r"""(?i)\b(?:api[_-]?key|secret|token|password)\b["']?\s*[:=]\s*["'][A-Za-z0-9_\-+/]{24,}["']""",
}
# Lines that are examples or fixtures on purpose carry one of these words.
NOT_A_SECRET = ("not-real", "not_real", "NOT-REAL", "example", "placeholder", "YOUR_", "xxxx", "dummy")


def _git(*args) -> list[str]:
    r = subprocess.run(["git", *args], cwd=STUDIO, capture_output=True, check=False)
    if r.returncode != 0:
        pytest.skip("not a git checkout")
    return [n for n in r.stdout.decode("utf-8", "replace").split("\0") if n]


def test_no_secret_shaped_string_is_committed():
    hits = []
    for f in preflight.tracked_text_files():
        if f.name == "test_hygiene.py":
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if len(line) > 4000 or any(w in line for w in NOT_A_SECRET):
                continue
            hits += [f"{f.relative_to(STUDIO)}:{n} looks like a {what}" for what, rx in SECRET_SHAPES.items() if re.search(rx, line)]
    assert not hits, "secret-shaped strings are committed (names only, values withheld):\n" + "\n".join(hits[:10])


def test_every_module_compiles(tmp_path):
    bad = []
    for f in sorted([*(STUDIO / "faceless").rglob("*.py"), *(STUDIO / "tests").glob("*.py")]):
        try:
            py_compile.compile(str(f), cfile=str(tmp_path / (f.name + "c")), doraise=True)
        except py_compile.PyCompileError as e:
            bad.append(f"{f.relative_to(STUDIO)}: {str(e)[:100]}")
    assert not bad, bad


def test_no_rendered_media_and_nothing_huge_is_tracked():
    names = _git("ls-files", "-z")
    rendered = [n for n in names if n.startswith("production/output/") or n.startswith("production/cache/") or (n.startswith("distribution/queue/") and n.endswith((".mp4", ".wav")))]
    assert not rendered, f"rendered media is tracked (CLAUDE.md says it is gitignored): {rendered[:5]}"
    huge = [n for n in names if (STUDIO / n).is_file() and (STUDIO / n).stat().st_size > 20 * 2**20]
    assert not huge, f"files over 20 MB bloat every clone: {huge}"


def test_keys_and_local_state_are_gitignored():
    ignore = (STUDIO / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".env", "production/output/", "production/cache/"):
        assert pattern in ignore.splitlines(), f".gitignore lost {pattern}"


def test_spend_caps_add_up():
    cfg = config.load()
    ceiling = cfg["safety"]["daily_usd_ceiling"]
    assert 0 < ceiling <= 10, "the studio-wide ceiling should be small, and above zero"
    caps = {"[muapi] daily_usd": cfg["muapi"]["daily_usd"],
            "[images] muapi_daily_usd": cfg["images"]["muapi_daily_usd"],
            "[images] openrouter_daily_images x $0.04": cfg["images"]["openrouter_daily_images"] * 0.04,
            "[production.hookclip] daily_usd": cfg["production"]["hookclip"]["daily_usd"]}
    over = {k: v for k, v in caps.items() if v > ceiling}
    assert not over, f"a provider cap above the studio ceiling is a cap that can never bind: {over}"
    assert cfg["muapi"]["per_call_usd"] <= cfg["muapi"]["daily_usd"]
    images = cfg["images"]
    assert 0 <= images["cloudflare_qa_reserve"] < images["cloudflare_daily_neurons"] <= 10_000, "Cloudflare's free tier is 10,000 neurons a day"


def test_nothing_goes_public_without_the_owners_go():
    cfg = config.load()
    mode = cfg["publish"]["mode"]
    assert OWNER_APPROVED_LIVE_POSTING or mode not in LIVE_PUBLISH_MODES, f"publish mode {mode!r} posts for real; the owner has not said go"
    assert OWNER_APPROVED_LIVE_POSTING or mode == "local"
    assert OWNER_APPROVED_HOOK_CLIPS or not cfg["production"]["hookclip"]["enabled"], "hook clips cost money per video and need the owner's yes"
    assert cfg["channel"].get("has_affiliate_links") is False or "has_affiliate_links" in cfg["channel"]


def test_the_ai_labels_are_still_sent_with_every_upload():
    src = (STUDIO / "faceless" / "providers" / "publish.py").read_text(encoding="utf-8")
    assert "tiktok_is_ai_generated" in src and "containsSyntheticMedia" in src, "AI disclosure labels must stay ON for every platform that has the flag"


WORKFLOWS = sorted((STUDIO / ".github" / "workflows").glob("*.yml"))
# Keys the optional, owner-triggered runners may read if the owner ever stores them as Actions secrets (the studio itself runs with none).
OPTIONAL_RUNNER_SECRETS = {"GITHUB_TOKEN", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "CLOUDFLARE_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "COMPOSIO_API_KEY",
                           "ELEVENLABS_API_KEY", "TYPESAFE_API_KEY", "UPLOAD_POST_API_KEY", "UPLOAD_POST_USER"}


def _triggers(text: str) -> set[str]:
    block = re.search(r"^on:[ \t]*\n((?:[ \t]+\S.*\n|[ \t]*\n)+)", text, re.M)
    return set(re.findall(r"^  ([a-z_]+):", block.group(1), re.M)) if block else set()


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_workflows_use_least_privilege_and_open_triggers_see_no_secrets(wf: Path):
    text = wf.read_text(encoding="utf-8")
    used = set(re.findall(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)", text))
    if _triggers(text) & {"push", "pull_request", "pull_request_target"}:
        assert used <= {"GITHUB_TOKEN"}, f"{wf.name} runs on pushes or pull requests, so it must not see {sorted(used - {'GITHUB_TOKEN'})}"
    assert used <= OPTIONAL_RUNNER_SECRETS, f"{wf.name} reads an unexpected secret: {sorted(used - OPTIONAL_RUNNER_SECRETS)}"
    assert re.search(r"^permissions:", text, re.M), f"{wf.name} has no top-level permissions block (the default token is too wide)"
    for action in re.findall(r"uses:\s*([^\s#]+)", text):
        assert "@" in action and not action.endswith(("@main", "@master")), f"{wf.name} uses an unpinned action {action}"


def test_two_sessions_appending_to_the_journal_merge_without_a_conflict(tmp_path):
    """The routine and a manual session both push events. With the union driver in .gitattributes both sets of lines survive and nothing stops the merge."""
    def git(*a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *a], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    git("init", "-q", "-b", "main")
    (tmp_path / ".gitattributes").write_text((STUDIO / ".gitattributes").read_text(encoding="utf-8"), encoding="utf-8")
    log = tmp_path / "state" / "journal.jsonl"
    log.parent.mkdir()
    log.write_text('{"t": "2026-10-08T09:00:00", "type": "START"}\n', encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "manual")
    log.write_text(log.read_text(encoding="utf-8") + '{"t": "2026-10-08T10:00:00", "type": "MANUAL"}\n', encoding="utf-8")
    git("commit", "-qam", "manual session")
    git("checkout", "-q", "main")
    log.write_text(log.read_text(encoding="utf-8") + '{"t": "2026-10-08T10:05:00", "type": "ROUTINE"}\n', encoding="utf-8")
    git("commit", "-qam", "routine session")
    git("merge", "-q", "--no-edit", "manual")                                   # would raise on a conflict
    merged = log.read_text(encoding="utf-8")
    assert "MANUAL" in merged and "ROUTINE" in merged and "START" in merged and "<<<<" not in merged
    assert all(json.loads(line) for line in merged.splitlines())


def test_only_append_only_logs_use_the_union_driver():
    attrs = dict(line.split()[:2] for line in (STUDIO / ".gitattributes").read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))
    assert attrs.get("state/journal.jsonl") == "merge=union" and attrs.get("state/ledger.jsonl") == "merge=union"
    assert not {"channel/empire/portfolio.jsonl", "script-lab/ideas/backlog.jsonl"} & set(attrs), "rewritten files would duplicate lines under a union merge"
