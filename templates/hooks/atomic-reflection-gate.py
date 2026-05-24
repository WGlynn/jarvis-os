#!/usr/bin/env python3
"""
atomic-reflection-gate.py

Enforces primitive extraction at decision-moments BEFORE routing around.

Fire points:
  PostToolUse on tool error/timeout  -> inject reflection prompt
  PreToolUse on Agent (subagent)     -> inject delegation-introspection prompt

Source primitive: memory/feedback_atomic-self-reflection-gate.md
Origin: Will 2026-05-17 — "atomic self reflection at every decision from now on. gate it"
"""
import json
import sys


REFLECTION_PROMPT_ERROR = (
    "[ATOMIC REFLECTION GATE] Tool failed or timed out. "
    "BEFORE routing around: extract the primitive. "
    "What failure pattern just surfaced? "
    "Save it (or note explicitly 'no primitive worth saving because Z') "
    "BEFORE the workaround. Tool failure is data, not noise. "
    "Per [F·atomic-self-reflection-gate]."
)

REFLECTION_PROMPT_DELEGATION = (
    "[ATOMIC REFLECTION GATE] About to delegate to a subagent. "
    "Is the delegation routing around a reflection that should happen here? "
    "If you're delegating because your last approach failed, capture WHY "
    "before handing off — the subagent will not learn the lesson for you. "
    "Per [F·atomic-self-reflection-gate]."
)


def is_error_result(tool_response):
    """Detect error / timeout signals in a tool result payload.

    Narrow detection — structural fields only. Substring search on
    full tool_response content triggers false positives whenever the
    successful output happens to contain the word "error" or "timeout"
    (e.g., editing a hook script that mentions either word).
    """
    # Specific error-message phrases that signal an actual tool failure.
    # These are deliberately narrow: "timed out after" is the exact form
    # ripgrep / Glob / Grep emit on timeout; bare "timeout" is NOT enough.
    ERROR_PHRASES = (
        "timed out after",
        "ripgrep search timed out",
        "tool ran into an error",
        "tool_use_error",
    )

    if isinstance(tool_response, dict):
        # Structural error flag (Claude Code sets this on tool errors)
        if tool_response.get("is_error"):
            return True
        # Dedicated error fields
        for key in ("error", "tool_use_error", "error_message"):
            val = tool_response.get(key)
            if isinstance(val, str) and val.strip():
                return True
        # Top-level content as explicit error string
        content = tool_response.get("content")
        if isinstance(content, str):
            low = content.lower()
            if low.startswith("error:") or any(p in low for p in ERROR_PHRASES):
                return True
        # Content as list of blocks (Anthropic message-format shape)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    if isinstance(text, str):
                        low = text.lower()
                        if low.startswith("error:") or any(p in low for p in ERROR_PHRASES):
                            return True
        return False

    # Non-dict response: fire only on exact error-message phrases
    haystack = str(tool_response).lower()
    return any(p in haystack for p in ERROR_PHRASES)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Fail silent — never block tool flow because the gate itself broke
        print(json.dumps({}))
        return

    event = payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")

    # PostToolUse: fire on tool error / timeout
    if event == "PostToolUse":
        tool_response = payload.get("tool_response", {})
        if is_error_result(tool_response):
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": REFLECTION_PROMPT_ERROR,
                }
            }
            print(json.dumps(out))
            return

    # PreToolUse: fire on subagent delegation
    if event == "PreToolUse" and tool == "Agent":
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": REFLECTION_PROMPT_DELEGATION,
            }
        }
        print(json.dumps(out))
        return

    # No-op for all other cases
    print(json.dumps({}))


if __name__ == "__main__":
    main()
