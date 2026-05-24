#!/usr/bin/env python3
"""
em-dash-augmentation-gate.py

When a partner-facing draft is written, scan for em-dashes (U+2014, U+2013).
If present, augment Claude's context with a reminder to scrub them before delivery.

Augmentation gate, NOT a block. Em-dashes remain permitted in memory primitives,
code comments, internal analysis. The gate fires only on partner-facing draft
paths so that conversations-with-humans output gets scrubbed.

Source primitive: memory/feedback_em-dash-filter-for-conversations.md
Origin: Will 2026-05-18 - "augmentation gate, so em dashes can still be used
but just get filtered out for conversations"
"""
import json
import re
import sys


# File-path patterns indicating a partner-facing draft.
# All matched case-insensitively against forward-slashed paths.
# 2026-05-18 v0.2 audit: tightened separator handling. Date-prefixed files
# often use `_` before keywords (`_email-`, `_linkedin-`); original patterns
# only matched `-` before keywords, missing those drafts. Now: `[_-]` on
# left boundary so both separators match.
PARTNER_FACING_PATTERNS = [
    r"/desktop/[^/]*[_-]reply[-_.]",
    r"/desktop/[^/]*[_-]draft[-_.]",
    r"/desktop/outreach[_-]",
    r"/desktop/outreach_pitches/",
    r"/desktop/usd8[_-]",
    r"/desktop/kim[_-]",
    r"/desktop/bernhard[_-]",
    r"/desktop/tom[_-]",
    r"/desktop/rick[_-]",
    r"/desktop/anthropic[_-]",
    r"/desktop/justin[_-]",
    r"/desktop/jp[_-]",
    # date-prefixed files: keyword anywhere after the date underscore
    r"/desktop/[0-9]{4}-[0-9]{2}-[0-9]{2}_[^/]*linkedin",
    r"/desktop/[0-9]{4}-[0-9]{2}-[0-9]{2}_[^/]*medium",
    r"/desktop/[0-9]{4}-[0-9]{2}-[0-9]{2}_[^/]*ethresearch",
    r"/desktop/[0-9]{4}-[0-9]{2}-[0-9]{2}_[^/]*email",
    r"/desktop/[0-9]{4}-[0-9]{2}-[0-9]{2}_[^/]*letter",
    # start-of-name shortcuts
    r"/desktop/ethresearch[_-]",
    r"/desktop/medium[_-]",
    r"/desktop/linkedin[_-]",
    r"/desktop/telegram[_-]",
    # middle-of-name keyword + boundary on both sides
    r"/desktop/[^/]*[_-]pitch[-_.]",
    r"/desktop/[^/]*[_-]letter[-_.]",
    r"/desktop/[^/]*[_-]email[-_.]",
    r"/desktop/[^/]*[_-]message[-_.]",
    r"/desktop/[^/]*[_-]post[-_.]",
    r"/desktop/[^/]*[_-]thread[-_.]",
    r"/desktop/[^/]*[_-]dm[-_.]",
]


def is_partner_facing(path):
    if not path:
        return False
    norm = path.replace("\\", "/").lower()
    return any(re.search(pat, norm) for pat in PARTNER_FACING_PATTERNS)


def count_em_dashes(content):
    """Count em-dash characters in the content.

    U+2014 is the canonical em-dash. U+2013 (en-dash) is also flagged
    because it gets used as an em-dash substitute and reads the same way
    in partner-facing prose.
    """
    if not content or not isinstance(content, str):
        return 0
    return content.count("—") + content.count("–")


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        return

    event = payload.get("hook_event_name", "")
    if event != "PostToolUse":
        print(json.dumps({}))
        return

    tool = payload.get("tool_name", "")
    if tool not in ("Write", "Edit", "NotebookEdit"):
        print(json.dumps({}))
        return

    tool_input = payload.get("tool_input", {})
    path = tool_input.get("file_path", "")

    if not is_partner_facing(path):
        print(json.dumps({}))
        return

    # Pull the content that was written into the file
    content = ""
    if tool == "Write":
        content = tool_input.get("content", "")
    elif tool == "Edit":
        content = tool_input.get("new_string", "")
    elif tool == "NotebookEdit":
        content = tool_input.get("new_source", "")

    count = count_em_dashes(content)
    if count == 0:
        print(json.dumps({}))
        return

    msg = (
        f"[EM-DASH AUGMENTATION GATE] {count} em-dash(es) detected in "
        f"partner-facing draft at {path}. Per [F·em-dash-filter-for-conversations], "
        f"partner-facing drafts must filter em-dashes before delivery. "
        f"Replace with comma, period, colon, or parens depending on context: "
        f"mid-clause em-dash -> comma or sentence-split; parenthetical em-dash -> parens; "
        f"range/connection em-dash -> 'to'/'vs' or split. "
        f"Edit the file to scrub before the user paste-sends. "
        f"This gate augments awareness, it does not block the write."
    )
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
