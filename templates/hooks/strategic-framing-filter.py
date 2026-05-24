#!/usr/bin/env python3
"""Strategic-framing filter gate (PreToolUse on Write/Edit).

Blocks writes to external-audience artifacts (Justin_Reports, EriduLabs_RnD, any
Desktop .md naming justin/eridu) when the content contains strategic-framing
language that was intended strictly between Will and Jarvis.

Prevents the 2026-04-21 near-miss where today's Justin daily report almost
shipped with a quote of the private strategic framing ("Justin is 99%
Eridu-focused ... cleverly make everything useful to him"). Will caught it
manually during Gmail paste; this gate catches it at write time.

Contract
--------
- stdin: JSON from Claude Code PreToolUse. Key fields: tool_name, tool_input.
- tool_input for Write: { file_path, content }
- tool_input for Edit:  { file_path, old_string, new_string, replace_all }
- exit 0 + stdout JSON with permissionDecision=allow (or silent exit 0) → proceed
- exit 0 + stdout JSON with permissionDecision=deny + reason → block
- Hook runs on matcher `Write|Edit` configured in settings.json

Escape hatch
------------
Content containing the literal marker `<!-- strategic-filter: reviewed -->`
is allowed through. Use sparingly, only when the match is a false positive
that's been human-reviewed.
"""
import json
import os
import re
import sys

# ----- External-audience paths. Any write to these is filtered.

EXTERNAL_PATH_PATTERNS = [
    r"[/\\]Desktop[/\\]Justin_Reports[/\\]",
    r"[/\\]Desktop[/\\]EriduLabs_RnD[/\\]",
    # Any .md/.txt/.html/.pdf on Desktop whose filename mentions justin/eridu
    r"[/\\]Desktop[/\\][^/\\]*(?:justin|eridu|puffpaff)[^/\\]*\.(md|txt|html|pdf)$",
    # Drafts folder (emails, etc.)
    r"[/\\]Desktop[/\\][^/\\]*drafts?[^/\\]*[/\\].*(?:justin|eridu)",
]

# ----- Leak patterns. Each is a (regex, description) pair.
# Be conservative - false positives are cheap (quick fix), false negatives are "feelings hurt."

LEAK_PATTERNS = [
    # Attention-budget framings - strategic assessments of external parties' bandwidth
    (
        r"\b\d{1,3}\s*%\s*(?:focused|eridu-focused|attention|attention-focused|focus)",
        "attention-budget framing (e.g. '99% focused') - strategic assessment of external party's bandwidth",
    ),
    (
        r"(?:1|2|3|4|5)\s*%\s*attention",
        "attention-budget framing - quantifying external party's bandwidth",
    ),
    # Direct quotes of private strategic framings
    (
        r"cleverly\s+make\s+(?:everything|it|things)\s+useful",
        "Will's private strategic quote about making work useful to external party",
    ),
    (
        r"(?:hasn(?:'|')?t\s+had\s+time|doesn(?:'|')?t\s+have\s+(?:the\s+)?time)\s+to\s+(?:actually\s+)?understand",
        "Framing that external party lacks understanding - condescension signal",
    ),
    # Strategy vocabulary
    (
        r"main[- ]character\s+(?:accommodat|status|lifestyle|narrative)",
        "main-character-accommodation strategy vocabulary",
    ),
    (
        r"ego[- ]flatter(?:y|ing)|flatter(?:ing)?\s+(?:people(?:'|')?s?\s+)?egos",
        "ego-flattery tactic vocabulary",
    ),
    (
        r"(?:give|giving|gave|giveaway|giving\s+away)\s+(?:the\s+)?credit\s+(?:away|to|for)",
        "credit-away sacrifice framing",
    ),
    (
        r"adoption\s+strategy|strategic\s+patience",
        "adoption-strategy vocabulary",
    ),
    (
        r"(?:selection|conversion)\s+filter(?:\s+.{0,40}movement)?",
        "selection-filter meta-strategic framing",
    ),
    # Privacy markers that leaked through
    (
        r"(?:strictly\s+)?between\s+us\b",
        "'between us' private-tier marker - should never appear in external artifact",
    ),
    (
        r"strictly\s+private",
        "'strictly private' marker - should never appear in external artifact",
    ),
    (
        r"between\s+(?:Will|will)\s+and\s+(?:Jarvis|jarvis)",
        "explicit Will-to-Jarvis scope marker",
    ),
    # Directory / structural leaks
    (
        r"nda[_\- ]locked[/\\]",
        "nda-locked directory reference - external artifacts should not name this directory",
    ),
    # Attribution-failure thesis vocabulary (specific to VibeSwap thesis memory)
    (
        r"broken\s+attribution\s+game|attribution[_\- ]failure|attribution\s+is\s+structurally\s+broken",
        "attribution-failure thesis vocabulary - private framing of why VibeSwap exists",
    ),
    # Underestimation framings
    (
        r"(?:even\s+)?(?:the\s+)?people\s+(?:giving\s+us\s+a\s+chance\s+are\s+)?underestimat(?:e|ing)",
        "underestimation framing - strategic assessment of collaborators",
    ),
    (
        r"they(?:'|')?ll\s+never\s+(?:just\s+)?accept",
        "pessimistic framing about adopter acceptance",
    ),
    # Direct first-person strategy narration
    (
        r"we\s+(?:have|need|gotta|got\s+to)\s+(?:be\s+strategic|cleverly|strategically)",
        "first-person strategy narration that shouldn't appear in external artifact",
    ),
]

ESCAPE_MARKER = "<!-- strategic-filter: reviewed -->"


def path_is_external(file_path: str) -> bool:
    """Does the write target an external-audience artifact path?"""
    normalized = file_path.replace("\\", "/")
    for pat in EXTERNAL_PATH_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return True
    return False


def scan_content(content: str) -> list[tuple[str, str, int]]:
    """Return [(pattern_description, matched_text, line_number)] for any hits."""
    hits = []
    for regex, description in LEAK_PATTERNS:
        for m in re.finditer(regex, content, re.IGNORECASE | re.MULTILINE):
            # Find line number by counting newlines before the match
            line_num = content[: m.start()].count("\n") + 1
            matched = m.group(0)
            if len(matched) > 120:
                matched = matched[:120] + "..."
            hits.append((description, matched, line_num))
    return hits


def deny(reason: str) -> None:
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(out))
    # stderr log
    print(f"[strategic-framing-filter] BLOCKED: {reason[:200]}", file=sys.stderr)
    sys.exit(0)


def allow_silent() -> None:
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        print(f"[strategic-framing-filter] stdin parse error: {e}", file=sys.stderr)
        allow_silent()

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    if tool_name not in ("Write", "Edit"):
        allow_silent()

    file_path = tool_input.get("file_path", "")
    if not file_path or not path_is_external(file_path):
        allow_silent()

    # Collect content to scan based on tool
    if tool_name == "Write":
        content = tool_input.get("content", "") or ""
    else:  # Edit
        content = tool_input.get("new_string", "") or ""

    if ESCAPE_MARKER in content:
        print(
            f"[strategic-framing-filter] escape marker present - allowing write to {file_path}",
            file=sys.stderr,
        )
        allow_silent()

    hits = scan_content(content)
    if not hits:
        print(
            f"[strategic-framing-filter] clean - allowing write to {file_path}",
            file=sys.stderr,
        )
        allow_silent()

    # Block. Build an actionable message listing specific matches.
    lines = [
        f"STRATEGIC-FRAMING FILTER: external-audience write BLOCKED.",
        f"",
        f"File: {file_path}",
        f"This path writes to an external-audience artifact (Justin_Reports / EriduLabs_RnD / Desktop artifact matching justin/eridu).",
        f"",
        f"Strategic-framing leak(s) detected in content:",
    ]
    for description, matched, line_num in hits[:10]:
        lines.append(f"  • line {line_num}: {description}")
        lines.append(f"      matched text: {matched!r}")
    if len(hits) > 10:
        lines.append(f"  … and {len(hits) - 10} more")
    lines.append("")
    lines.append(
        "These patterns are strategic framings intended as private context between Will and Jarvis. "
        "They must not appear in artifacts sent to external audiences (Justin / EriduLabs collaborators / public)."
    )
    lines.append("")
    lines.append(
        "Fix: revise the content to remove the flagged language, then retry the write. "
        "If a match is genuinely a false positive after human review, add the literal marker "
        f"`{ESCAPE_MARKER}` to the file to bypass this filter."
    )

    deny("\n".join(lines))


if __name__ == "__main__":
    main()
