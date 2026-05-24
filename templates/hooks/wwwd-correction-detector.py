#!/usr/bin/env python3
"""
WWWD Correction Detector
========================

Stop-event hook. Scans the most recent user message for correction markers
("no", "not that", "actually", "let me clarify", explicit revision verbs)
and writes the correction back to the most recent gate-fire log entry's
`correction` field.

This closes the WWWD self-compounding loop: each Will-correction becomes
training signal for the next projection. Per v3-wwwd-protocol.md
self-compounding section.

Companion to wwwd-gate.py (the gate that writes the initial entries).

Gate-fire log: memory/_system/wwwd_gate_fires.jsonl
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

MEMORY_DIR = Path.home() / ".claude" / "projects" / "{{PROJECT_DIR}}" / "memory"
GATE_FIRE_LOG = MEMORY_DIR / "_system" / "wwwd_gate_fires.jsonl"

# Correction markers — phrases that signal Will is correcting prior output.
# Tuned over usage; conservative to start (false-positive cost is one stale
# correction-write, false-negative cost is a missed training signal).
CORRECTION_PATTERNS = [
    r"\bno,?\s+",                       # "no", "no,"
    r"\bnot that\b",
    r"\bactually,?\s+",
    r"\bwait,?\s+",                     # mid-stream correction
    r"\blet me (?:clarify|correct|rephrase)\b",
    r"\bcorrection:\s",
    r"\bI meant\b",
    r"\binstead of\b",
    r"\bswap (?:that|this)\b",
    r"\brevise\b",
    r"\bdrop the\b",
    r"\bremove (?:that|this|the)\b",
    r"\bchange (?:that|this|the) to\b",
    r"\bredo\b",
    r"\btry again\b",
    r"\bthat's wrong\b",
    r"\bnope\b",
    r"\bthat's not right\b",
]


def detect_correction(text: str) -> tuple[bool, list[str]]:
    """Return (is_correction, matched_patterns)."""
    if not text or not isinstance(text, str):
        return False, []
    matched = [p for p in CORRECTION_PATTERNS if re.search(p, text, re.IGNORECASE)]
    return (len(matched) > 0), matched


def append_correction_to_last_entry(correction_text: str, matched_patterns: list[str]) -> bool:
    """Read the gate-fire log, find the most recent entry without a correction,
    set its correction field, and write the log back. Returns True if a write
    happened, False otherwise.

    This is O(N) on the log size; for production we'd want indexed access.
    Prototype is fine for now."""
    if not GATE_FIRE_LOG.exists():
        return False

    try:
        lines = GATE_FIRE_LOG.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False

    # Find the most recent entry without a correction recorded.
    target_idx = None
    for i in range(len(lines) - 1, -1, -1):
        try:
            entry = json.loads(lines[i])
        except Exception:
            continue
        if entry.get("correction") is None and entry.get("decision_class") != "uncategorized":
            target_idx = i
            break

    if target_idx is None:
        return False

    try:
        entry = json.loads(lines[target_idx])
        entry["correction"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text_excerpt": correction_text[:500],
            "matched_patterns": matched_patterns,
        }
        # Also mark gate_revision_occurred = True since a correction implies the
        # projection didn't fully match Will-pick.
        entry["gate_revision_occurred"] = True
        lines[target_idx] = json.dumps(entry, ensure_ascii=False)
    except Exception:
        return False

    try:
        GATE_FIRE_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return 0

    # Stop event: payload contains the conversation context. We want the most
    # recent user message that just preceded this assistant response.
    # Claude Code's Stop hook payload shape varies; try a few standard fields.
    user_msg = (
        payload.get("user_message")
        or payload.get("last_user_message")
        or ""
    )

    # Fallback: look in `messages` array if present.
    if not user_msg and isinstance(payload.get("messages"), list):
        for msg in reversed(payload["messages"]):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_msg = content
                elif isinstance(content, list):
                    user_msg = " ".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )
                break

    is_correction, matched = detect_correction(user_msg)

    if not is_correction:
        print(json.dumps({}))
        return 0

    wrote = append_correction_to_last_entry(user_msg, matched)

    if wrote:
        # Optional: emit a quiet additionalContext so the assistant knows the
        # correction was logged. Useful for transparency during development.
        out = {
            "hookSpecificOutput": {
                "hookEventName": payload.get("hook_event_name", "Stop"),
                "additionalContext": (
                    f"[WWWD CORRECTION LOGGED] Will-correction detected and written back "
                    f"to most recent gate-fire entry. Matched patterns: "
                    f"{', '.join(matched[:3])}. Future projections in this decision-class "
                    f"will route through the updated corpus."
                ),
            }
        }
        print(json.dumps(out))
    else:
        print(json.dumps({}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
