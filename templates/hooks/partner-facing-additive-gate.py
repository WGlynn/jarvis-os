#!/usr/bin/env python3
"""Partner-facing additive-framing gate (PreToolUse on Bash).

Implements F·partner-facing-additive-framing under P·dont-make-will-look-dumb.

Surfaces retrospective-framing keywords ("we missed", "originally we",
"fix oversight", etc.) when pushing commits or creating/editing PRs against
partner-facing repos (Usd8-fi, Eridu-internal). Forces a review prompt via
permissionDecision=ask — does not block, but inserts a checkpoint.

Born from 2026-04-28 USD8 PR #3 expansion: rewrote dispute-only doc to cover
both dispute and clawback applications. Original framing of expansion would
have read as "we missed clawback" / "fix oversight." Will: "dont make it look
like we messed up but we are just adding context and clarifying."

Contract
--------
- stdin: JSON from Claude Code PreToolUse for Bash tool.
- tool_input.command: the bash command about to run.
- Filter: only fires for `git push` and `gh pr create|edit` commands.
- Gate scope: only when the repo's origin remote matches a partner-facing org.
- Output:
  - No hits → exit 0 silently → tool proceeds.
  - Hits → JSON with permissionDecision=ask + reason listing detected lines →
    Claude Code surfaces a confirm-prompt; user can proceed or abort.
"""
import json
import os
import re
import subprocess
import sys

PARTNER_REPO_PATTERNS = [
    r"github\.com[:/]+Usd8-fi/",
    r"github\.com[:/]+EriduLabs/",
    r"github\.com[:/]+eridulabs/",
    r"github\.com[:/]+Eridu-internal/",
]

# Each (regex, label). Hits are surfaced individually with the matched line.
# Be conservative — false positives are cheap (Will reads + proceeds).
# False negatives are the cost (Will-look-dumb leak through to partner).
RETROSPECTIVE_PATTERNS = [
    (r"\bwe\s+missed\b", "we missed"),
    (r"\bwe\s+forgot\b", "we forgot"),
    (r"\b(?:had|have)\s+missed\b", "had/have missed"),
    (r"\boversight\b", "oversight"),
    (r"\bwe\s+initially\b", "we initially"),
    (r"\bI\s+initially\b", "I initially"),
    (r"\boriginally\s+we\b", "originally we"),
    (r"\bpreviously\s+we\b", "previously we"),
    (r"\bearlier\s+(?:we|version|draft|interpretation|framing)\b", "earlier we/version/draft/interp/framing"),
    (r"\bwasn'?t\s+(?:captured|covered|included)\b", "wasn't captured/covered/included"),
    (r"\bdidn'?t\s+(?:include|cover|capture)\b", "didn't include/cover/capture"),
    (r"\bto\s+correct\b", "to correct"),
    (r"\bcorrecting\s+(?:earlier|prior|the\s+earlier)\b", "correcting earlier/prior"),
    (r"\bfix\s+oversight\b", "fix oversight"),
    (r"\bfix\s+missing\b", "fix missing"),
    (r"\bfix\s+incomplete\b", "fix incomplete"),
    (r"\bour\s+(?:error|mistake|miss|oversight)\b", "our error/mistake/miss/oversight"),
    (r"\bbased\s+on\s+(?:rick'?s|justin'?s|the)\s+feedback\b", "based on (rick/justin/the) feedback"),
    (r"\bupdated\s+based\s+on\b", "updated based on"),
    (r"\bcomplete\s+rewrite\b", "complete rewrite"),
    (r"\bshould\s+have\s+(?:been|included|covered)\b", "should have been/included/covered"),
    # 2026-04-28 expansion: catch the phrasings that slipped through on the
    # COUNTERFACTUALS forfeiture-vs-clawback fix. Will: "will gate next time".
    (r"\bhonest\s+error\b", "honest error"),
    (r"\bearlier\s+commits?\b", "earlier commits"),
    (r"\bwas\s+wrong\b", "was wrong"),
    (r"\bgot\s+(?:it|that)\s+wrong\b", "got it/that wrong"),
    (r"\bfix\s+language\b", "fix language"),
    (r"\blanguage\s+fix\b", "language fix"),
    (r"\bmis-?written\b", "miswritten"),
    (r"\bwrong\s+(?:term|terminology|word|wording)\b", "wrong term/terminology/word/wording"),
    (r"\bincorrect\s+(?:term|terminology|wording|language)\b", "incorrect term/terminology/wording/language"),
    (r"\bterm(?:inology)?\s+correction\b", "term/terminology correction"),
    # 2026-04-29 expansion: explicit retrospective markers and scope-specific
    # miss markers that slipped through earlier coverage. All unambiguously
    # retrospective — not easily confused with forward-looking language.
    (r"\brectif(?:y|ies|ied|ication|ying)\b", "rectify/rectifies/rectified/rectification"),
    (r"\bmissed\s+in\s+(?:PR|commit)\b", "missed in PR/commit (scope-specific retrospective)"),
    (r"\bshould\s+have\s+caught\b", "should have caught"),
    (r"\bin\s+(?:retrospect|hindsight)\b", "in retrospect/hindsight"),
]


def run_git(cwd, *args, timeout=3):
    try:
        result = subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def get_remote_url(cwd):
    return run_git(cwd, "remote", "get-url", "origin").strip()


def is_partner_repo(remote_url):
    return any(re.search(p, remote_url) for p in PARTNER_REPO_PATTERNS)


def get_outgoing_commits(cwd):
    """Commit messages + bodies of commits ahead of upstream."""
    text = run_git(cwd, "log", "@{u}..HEAD", "--format=%H%n%B%n---END---")
    if not text:
        # No upstream set, or no outgoing — try common fallbacks.
        text = run_git(cwd, "log", "origin/main..HEAD", "--format=%H%n%B%n---END---")
    return text


def extract_heredoc_body(command):
    """Pull the body out of a `gh pr create/edit ... --body "$(cat <<'EOF' ... EOF)"`.

    Returns the body text if found, else "".
    """
    m = re.search(r"<<\s*'?(\w+)'?\s*\n([\s\S]*?)\n\1\b", command)
    if m:
        return m.group(2)
    return ""


def extract_quoted_arg(command, flag):
    """Extract --flag "..." or --flag '...' from a command."""
    pattern = rf"{flag}\s+(?:\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)')"
    m = re.search(pattern, command)
    if m:
        return m.group(1) or m.group(2) or ""
    return ""


def scan_text(text):
    hits = []
    for pattern, label in RETROSPECTIVE_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end == -1:
                line_end = len(text)
            line = text[line_start:line_end].strip()
            if len(line) > 120:
                line = line[:120] + "..."
            hits.append((label, line))
    return hits


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    cwd = payload.get("cwd") or os.getcwd()

    is_push = bool(re.search(r"\bgit\s+push\b", command))
    is_gh_pr = bool(re.search(r"\bgh\s+pr\s+(?:create|edit)\b", command))

    if not (is_push or is_gh_pr):
        sys.exit(0)

    remote_url = get_remote_url(cwd)
    if not is_partner_repo(remote_url):
        sys.exit(0)

    hits_with_source = []

    if is_push:
        commits_text = get_outgoing_commits(cwd)
        for label, line in scan_text(commits_text):
            hits_with_source.append((label, line, "outgoing commit"))

    if is_gh_pr:
        body_text = extract_heredoc_body(command) or extract_quoted_arg(command, "--body")
        if body_text:
            for label, line in scan_text(body_text):
                hits_with_source.append((label, line, "PR body"))
        title_text = extract_quoted_arg(command, "--title")
        if title_text:
            for label, line in scan_text(title_text):
                hits_with_source.append((label, line, "PR title"))

    if not hits_with_source:
        sys.exit(0)

    lines = [
        f"P·dont-make-will-look-dumb gate: retrospective-framing keywords detected in {('push' if is_push else 'PR command')} to partner repo {remote_url}.",
        "",
    ]
    seen = set()
    for label, line, source in hits_with_source:
        key = (label, source, line)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  [{source}] '{label}' -> {line}")
        if len(seen) >= 25:
            lines.append(f"  ... and {len(hits_with_source) - 25} more")
            break
    lines += [
        "",
        "F·partner-facing-additive-framing: iterate as 'adding context / expanding scope', not 'we missed / fix'.",
        "Backstage process should not be visible to partner. Confirm framing then proceed.",
    ]

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "\n".join(lines),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
