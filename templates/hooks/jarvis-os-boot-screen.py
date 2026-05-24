#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS OS Boot Screen
=====================

SessionStart hook. Renders an 8-bit-style ASCII boot menu as the
welcome banner for every new Claude Code session. Surfaces the
navigation layer for the JARVIS protocol stack: protocols, files,
gates, philosophy, and natural-language commands.

Aesthetic: Unicode box-drawing (CP437-era DOS line-drawing chars),
dot leaders, no emoji. Retro loadout-screen vibe.

Emitted via additionalContext so it lands in boot context. Will sees
this at the top of every fresh session and knows the full surface
without grep-spelunking through ~/.claude/.

Companion piece to wwwd-corpus-refresh.py (loaded just before).
"""

import json
import sys
import io
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path.home() / ".claude" / "projects" / "{{PROJECT_DIR}}" / "memory"
PRIORITY_CACHE = MEMORY_DIR / "_system" / "wwwd_corpus_priority.json"

BANNER = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     ▄█ ▄▄▄   █▀▀▄ ▄   ▄ ▄█ ▄▄▄                                       ║
║      █ █  █  █▄▄▀ █   █  █ █                                         ║
║      █ █▀▀█  █  █  █ █   █ ▀▀▄    [ O S ]                            ║
║   █  █ █  █  █  █   █    █   █                                       ║
║    ▀▀  ▀  ▀  ▀  ▀   ▀    ▀ ▀▀▀                                       ║
║                                                                      ║
║                  V3  ·  Will-Emulating Autopilot                     ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""


def render_priority_status() -> str:
    """Read the WWWD corpus priority cache; return a one-line status."""
    if not PRIORITY_CACHE.exists():
        return "WWWD corpus · not yet computed (run a session to seed)"
    try:
        cache = json.loads(PRIORITY_CACHE.read_text(encoding="utf-8"))
        fires = cache.get("total_gate_fires", 0)
        corrections = cache.get("total_corrections", 0)
        rate = cache.get("correction_rate", 0.0)
        signal = cache.get("convergence_signal", "?")
        return (
            f"WWWD corpus · {fires} gate-fires · {corrections} corrections "
            f"({rate:.1%}) · convergence: {signal}"
        )
    except Exception:
        return "WWWD corpus · cache unreadable"


def render_boot_screen() -> str:
    """Compose the full 8-bit boot screen."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M ET")
    priority_status = render_priority_status()

    screen = BANNER + f"""
┌─[ PROTOCOLS ]───────────────────────────────────────────────────────┐
│ WWWD  ········ What Would Will Do?  (cognition gate · V3 capstone)  │
│ RSAW  ········ Recursive Self-Audit via WWWD  (TRP methodology)     │
│ HIERO ········ Operator-density memory format (hook-enforced)       │
│ NCI   ········ Bonded-validator meta-consensus (L0+L1 unified)      │
│ ETM   ········ Economic Theory of Mind (substrate-of-mind axis)     │
│ CCP   ········ Cross-Context Protocol (multi-context cross-ref)     │
└─────────────────────────────────────────────────────────────────────┘

┌─[ FILES ]───────────────────────────────────────────────────────────┐
│ SESSION_STATE   →  vibeswap/.claude/SESSION_STATE.md                │
│ MEMORY index    →  ~/.claude/projects/{{PROJECT_DIR}}/memory/         │
│ WAL             →  vibeswap/.claude/WAL.md                          │
│ V3 SPEC         →  ~/JARVIS/05-meta-protocols/v3-jarvis-protocol.md │
│ WWWD primitive  →  memory/primitive_what-would-will-do.md           │
│ RSAW primitive  →  memory/primitive_recursive-self-audit-via-wwwd.md│
│ META STACK      →  ~/.claude/META_STACK.md                          │
│ Global rules    →  ~/.claude/CLAUDE.md                              │
└─────────────────────────────────────────────────────────────────────┘

┌─[ GATES ]───────────────────────────────────────────────────────────┐
│ ▸ WWWD-gate          PreToolUse Write│Edit│Agent  (Will-emulation) │
│ ▸ HIERO-gate         PreToolUse Write│Edit        (density check)  │
│ ▸ NDA-Eridu-gate     PreToolUse Bash(git *)       (NDA scrub)      │
│ ▸ Em-dash-gate       PostToolUse Write│Edit       (partner-draft)  │
│ ▸ Conflict-detector  PreToolUse Write│Edit        (memory contra.) │
│ ▸ Atomic-reflection  PostToolUse + PreToolUse Agent (err/timeout)  │
│ ▸ Entity x-ref       PreToolUse Write│Edit        (AA#3 / CCP)     │
│ ▸ Substance gate     PreToolUse Write│Edit        (claim-handshake)│
└─────────────────────────────────────────────────────────────────────┘

┌─[ PHILOSOPHY ]──────────────────────────────────────────────────────┐
│ THE CAVE ········· Build with constraints. The cave selects.        │
│ STRUCTURE ········ Structure does the work, not policy.             │
│ HONESTY ·········· Honesty as structural load-bearing property.     │
│ CINCINNATUS ······ Operator-independence test (Will-AFK robustness).│
│ FULL LEVERAGE ···· Wait until leverage is total, not partial.       │
│ COMPLETE-AS-RFC ·· Complete = ready-for-critique, not validated.    │
└─────────────────────────────────────────────────────────────────────┘

┌─[ COMMANDS ]────────────────────────────────────────────────────────┐
│ "show protocols"    →  enumerate all protocol primitives            │
│ "show gates"        →  enumerate all hooks + matchers               │
│ "show state"        →  print SESSION_STATE.md tail                  │
│ "show memory"       →  print MEMORY.md index                        │
│ "show philosophy"   →  cave + ETM + structure + cincinnatus         │
│ "show files"        →  reprint this file table                      │
│ "show wal"          →  print WAL.md epoch status                    │
│ "show wwwd"         →  WWWD gate-fire stats + convergence signal    │
└─────────────────────────────────────────────────────────────────────┘

  ▸ Boot: {now}
  ▸ {priority_status}
  ▸ READY  ▶  Awaiting Will-input
"""
    return screen


def main() -> int:
    # Force UTF-8 stdout on Windows so the box-drawing chars survive.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    try:
        _payload = json.load(sys.stdin)
    except Exception:
        _payload = {}

    screen = render_boot_screen()

    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "[JARVIS OS BOOT SCREEN]\n" + screen,
        }
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
