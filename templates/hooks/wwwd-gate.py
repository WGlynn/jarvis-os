#!/usr/bin/env python3
"""
WWWD Gate Hook
==============

PreToolUse hook for Write|Edit on partner-facing paths and Agent dispatch.
Implements the V3 JARVIS cognition gate per primitive_what-would-will-do.md
and v3-wwwd-protocol.md.

The five-step gate (executed inline by this script):
  1. PAUSE — detect trigger class
  2. ENUMERATE — call deep-recall.py over corpus
  3. PROJECT — emit Will-projection prompt to additionalContext
  4. REVISE-or-ESCALATE — augmentation, not block (let assistant revise)
  5. EXECUTE — log gate-fire and return

Status: prototype. Augmentation gate (never blocks). Will refine the
trigger detection and projection logic over usage as the gate-fire log
accumulates corrections.

Companions:
  - wwwd-log-writer.py (Stop-event log appender)
  - wwwd-correction-detector.py (Stop-event correction-detector)
  - wwwd-corpus-refresh.py (SessionStart corpus-priority cache rebuild)

Gate-fire log: memory/_system/wwwd_gate_fires.jsonl
"""

import json
import re
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# ============ Configuration ============

MEMORY_DIR = Path.home() / ".claude" / "projects" / "{{PROJECT_DIR}}" / "memory"
GATE_FIRE_LOG = MEMORY_DIR / "_system" / "wwwd_gate_fires.jsonl"

# Trigger detection — 11 decision classes (7 original + 4 from Cycle 1C)
# Per v3-wwwd-protocol.md trigger set.

PARTNER_FACING_PATH_PATTERNS = [
    r"Desktop/.*-reply-",
    r"Desktop/.*-handoff-",
    r"Desktop/.*-cover-",
    r"Desktop/kim-",
    r"Desktop/bernhard-",
    r"Desktop/tom-",
    r"Desktop/rick-",
    r"Desktop/anas-",
    r"Desktop/hl-",
    r"Desktop/usd8-",
    r"Desktop/outreach_",
    r"Desktop/.*-linkedin",
    r"Desktop/newsletter-post-",
]

SEVERITY_KEYWORDS = ["critical", "high", "medium", "low", "informational", "severity", "bounty", "estimate", "$[0-9]"]
TONE_KEYWORDS = ["excited to announce", "thrilled to share", "delighted", "honored", "let's see", "fingers crossed"]
SCOPE_KEYWORDS = ["next steps", "should we", "want me to", "continue", "stop", "pivot"]
INTERPRETATION_PRECEDENCE_MARKERS = ["this", "that one", "the one we", "you mean"]
DEPLOYMENT_PHASE_MARKERS = ["deployed", "shipped", "live on", "in production", "spec-only", "to build"]

# ============ Helpers ============

def detect_triggers(tool_input: dict, tool_name: str) -> list[str]:
    """Return the list of WWWD trigger-class names that this tool-call fires."""
    triggers = []

    path = tool_input.get("file_path") or tool_input.get("path") or ""
    content = (
        tool_input.get("content")
        or tool_input.get("new_string")
        or tool_input.get("prompt")
        or ""
    )

    # Trigger 1: partner-facing or publicly visible
    for pat in PARTNER_FACING_PATH_PATTERNS:
        if re.search(pat, path, re.IGNORECASE):
            triggers.append("partner-facing-publicly-visible")
            break

    # Trigger 2: severity calibration
    if any(re.search(kw, content, re.IGNORECASE) for kw in SEVERITY_KEYWORDS):
        triggers.append("severity-calibration")

    # Trigger 3: tone / framing
    if any(kw in content.lower() for kw in TONE_KEYWORDS):
        triggers.append("tone-framing-marketing-register")

    # Trigger 4: scope decisions
    if any(kw in content.lower() for kw in SCOPE_KEYWORDS):
        triggers.append("scope-decision")

    # Trigger 5: ask / spending Will's attention — detected at chat level, not hook level (skip here)
    # Trigger 6: gate-fired ambiguity — detected by orchestrator chaining (skip here)
    # Trigger 7: multi-defensible fork — detected by orchestrator (skip here)

    # Trigger 8: interpretation precedence
    if tool_name in ("Agent",) and any(m in content.lower() for m in INTERPRETATION_PRECEDENCE_MARKERS):
        triggers.append("interpretation-precedence")

    # Trigger 9: read-order-as-framing — Agent dispatch with multiple file references
    if tool_name == "Agent" and content.count("/") > 3:
        triggers.append("read-order-as-framing")

    # Trigger 10: deployment-phase-adjusted severity
    if any(kw in content.lower() for kw in DEPLOYMENT_PHASE_MARKERS) and "severity" in content.lower():
        triggers.append("deployment-phase-adjusted-severity")

    # Trigger 11: artifact-template resolution
    if "template" in content.lower() and tool_name in ("Write", "Edit"):
        triggers.append("artifact-template-resolution")

    return triggers


def project_will_pick(triggers: list[str], tool_name: str, content_excerpt: str) -> str:
    """Emit the Will-projection note for the additionalContext stream.

    This is a prototype: the projection is rendered as a structured reminder.
    Future versions will call into a small-model WWWD-projector for genuine
    Will-emulation rather than rule-based hints.
    """
    notes = []

    if "partner-facing-publicly-visible" in triggers:
        notes.append(
            "Partner-facing write. Apply: Will-voice register (frank, builder, no AI tells), "
            "em-dash-scrub before delivery, lead with concrete object not framing, "
            "thesis lands as payoff. Cite receipts where available."
        )

    if "severity-calibration" in triggers:
        notes.append(
            "Severity calibration in flight. Apply: honest-number-over-marketing-number. "
            "Verify against deployed state, not against optimistic estimate. "
            "Downgrade if README disclaims, finding lives in archived repo, or claim is "
            "spec-only-not-deployed."
        )

    if "tone-framing-marketing-register" in triggers:
        notes.append(
            "Marketing-register language detected. Apply: drop the rhetoric, lead with "
            "the substance. No 'excited to', no 'thrilled to', no 'let's see if'. "
            "Frank-be-human register."
        )

    if "scope-decision" in triggers:
        notes.append(
            "Scope-decision moment. Apply: full-leverage-only-moves; complete-as-ready-"
            "for-critique; ask-when-unsure if the projection cannot resolve between "
            "multiple Will-defensible options."
        )

    if "interpretation-precedence" in triggers:
        notes.append(
            "Ambiguous referent detected in agent prompt. Apply: which 'this' is meant? "
            "Name the candidate referents and route the projection through the most-load-"
            "bearing one. If unclear, escalate."
        )

    if "read-order-as-framing" in triggers:
        notes.append(
            "Multi-file-read agent dispatch. The read-order shapes interpretation. "
            "Apply: order reads from most-foundational to most-derivative; flag if the "
            "agent will be biased by the order."
        )

    if "deployment-phase-adjusted-severity" in triggers:
        notes.append(
            "Severity claim made about deployed-vs-spec-only code. Apply: separate the "
            "two phases explicitly. Spec-only code earns zero bounty and produces zero "
            "user impact even if logically buggy. Deployed code is the real surface."
        )

    if "artifact-template-resolution" in triggers:
        notes.append(
            "Template/artifact reference detected. Apply: materialize the cited template "
            "exactly OR infer-and-adapt — the choice is load-bearing. Default to "
            "materialize-exactly; only adapt with explicit reason."
        )

    if not notes:
        notes.append(
            "No specific WWWD trigger pattern matched this tool-call. Continuing under "
            "general Will-emulation defaults: frank-be-human, lead-with-crux, no-hedging, "
            "advocate-with-receipts."
        )

    return "\n\n".join(notes)


def append_gate_fire_log(entry: dict) -> None:
    """Append a gate-fire entry to wwwd_gate_fires.jsonl. Best-effort: don't
    block tool execution if logging fails."""
    try:
        GATE_FIRE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with GATE_FIRE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # silent fail; gate-fire logging is supporting infrastructure, not blocking


# ============ Main ============

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Malformed payload — silent pass-through; don't block.
        print(json.dumps({}))
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    # WWWD fires on Write|Edit and Agent dispatch per the spec.
    if tool_name not in ("Write", "Edit", "Agent"):
        print(json.dumps({}))
        return 0

    triggers = detect_triggers(tool_input, tool_name)

    if not triggers:
        # No triggers fired — log a null entry for telemetry, return clean.
        append_gate_fire_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_class": "uncategorized",
            "trigger": [],
            "tool_name": tool_name,
            "candidate_excerpt": "",
            "projection": "no-trigger-fired",
            "executed": True,
            "gate_revision_occurred": False,
            "corpus_sources_used": [],
            "correction": None,
        })
        print(json.dumps({}))
        return 0

    # Build a short excerpt for the log.
    candidate_excerpt = (
        tool_input.get("content")
        or tool_input.get("new_string")
        or tool_input.get("prompt")
        or ""
    )[:200]

    projection = project_will_pick(triggers, tool_name, candidate_excerpt)

    # Log the gate-fire.
    append_gate_fire_log({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision_class": triggers[0] if triggers else "uncategorized",
        "trigger": triggers,
        "tool_name": tool_name,
        "candidate_excerpt": candidate_excerpt,
        "projection": projection,
        "executed": True,  # augmentation, not block — always execute
        "gate_revision_occurred": False,  # set True if assistant revises after seeing projection (future telemetry)
        "corpus_sources_used": [],  # populated by future deep-recall integration
        "correction": None,  # populated by wwwd-correction-detector.py on Stop
    })

    # Emit the additionalContext so the assistant sees the projection BEFORE executing.
    out = {
        "hookSpecificOutput": {
            "hookEventName": payload.get("hook_event_name", "PreToolUse"),
            "additionalContext": (
                f"[WWWD GATE] Trigger(s) fired: {', '.join(triggers)}. "
                f"Will-projection note:\n\n{projection}\n\n"
                f"Augmentation, not block. Revise the candidate if the projection identifies a mismatch; "
                f"otherwise proceed."
            ),
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
