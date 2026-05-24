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
MESH_STATUS = Path.home() / ".claude" / "mesh" / "status.json"

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


def render_mesh_panel() -> str:
    """Render the MESH panel from ~/.claude/mesh/status.json.

    Stage 1: panel reflects local-only state — empty mesh is honest, not
    a bug. File absent (mesh not initialized) → MESH OFFLINE banner.
    Agent C §"Boot screen delta".
    """
    if not MESH_STATUS.exists():
        return (
            "\n"
            "┌─[ MESH ]────────────────────────────────────────────────────────────┐\n"
            "│ MESH OFFLINE — run scripts/mesh-init.py to bootstrap identity       │\n"
            "└─────────────────────────────────────────────────────────────────────┘\n"
        )
    try:
        s = json.loads(MESH_STATUS.read_text(encoding="utf-8"))
    except Exception:
        return (
            "\n"
            "┌─[ MESH ]────────────────────────────────────────────────────────────┐\n"
            "│ MESH status.json unreadable — re-run mesh-status-refresh.py         │\n"
            "└─────────────────────────────────────────────────────────────────────┘\n"
        )

    did_short = s.get("did_short") or "uninitialized"
    n_known = s.get("peers_known", 0)
    n_active = s.get("peers_active_24h", 0)
    n_pub = s.get("published_primitives", 0)
    n_topics = s.get("subscribed_topics", 0)
    last_sync = s.get("last_sync") or "never"
    if last_sync != "never" and len(last_sync) > 16:
        last_sync = last_sync[:16].replace("T", " ")
    queue = s.get("queue_depth", 0)

    did_field = f"did:key:{did_short}..." if did_short != "uninitialized" else did_short

    def pad(line_inner: str, width: int = 69) -> str:
        # account for unicode display width of pipes — keep simple, truncate
        return line_inner[:width].ljust(width)

    return (
        "\n"
        "┌─[ MESH ]────────────────────────────────────────────────────────────┐\n"
        f"│ {pad(f'DID         {did_field}')}│\n"
        f"│ {pad(f'Peers       {n_known} known · {n_active} active')}│\n"
        f"│ {pad(f'Published   {n_pub} primitives')}│\n"
        f"│ {pad(f'Subscribed  {n_topics} topics · last sync {last_sync}')}│\n"
        f"│ {pad(f'Queue       {queue} pending publish')}│\n"
        "└─────────────────────────────────────────────────────────────────────┘\n"
    )


def render_boot_screen() -> str:
    """Compose the full 8-bit boot screen."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M ET")
    priority_status = render_priority_status()
    mesh_panel = render_mesh_panel()

    screen = BANNER + f"""
┌─[ PROTOCOLS ]───────────────────────────────────────────────────────┐
│ WWWD  ········ What Would Will Do?  (cognition gate · V3 capstone)  │
│ RSAW  ········ Recursive Self-Audit via WWWD  (TRP methodology)     │
│ HIERO ········ Operator-density memory format (hook-enforced)       │
│ AIRGAP ······· 6-layer chain↔reality closure stack (OPH-anchored)   │
│ 4-SURFACE ···· VibeSwap+JARVIS-OS+Rosetta+OPH convergence theorem   │
│ PoM ·········· Proof-of-Mind (cognition attestation · PoW-port)     │
│ (extend with your own as you add primitives to memory/)             │
└─────────────────────────────────────────────────────────────────────┘

┌─[ FILES ]───────────────────────────────────────────────────────────┐
│ SESSION_STATE   →  vibeswap/.claude/SESSION_STATE.md                │
│ MEMORY index    →  ~/.claude/projects/{{PROJECT_DIR}}/memory/         │
│ WAL             →  vibeswap/.claude/WAL.md                          │
│ V3 SPEC         →  ~/JARVIS/05-meta-protocols/v3-jarvis-protocol.md │
│ WWWD primitive  →  memory/primitive_what-would-will-do.md           │
│ RSAW primitive  →  memory/primitive_recursive-self-audit-via-wwwd.md│
│ AIRGAP stack    →  memory/primitive_airgap-closure-stack.md         │
│ 4-SURFACE conv  →  memory/primitive_four-substrate-convergence.md   │
│ PoM primitive   →  memory/primitive_proof-of-mind.md                │
│ PORT pattern    →  memory/primitive_substrate-port-pattern.md       │
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
{mesh_panel}
┌─[ PHILOSOPHY ]──────────────────────────────────────────────────────┐
│ THE CAVE ········· Build with constraints. The cave selects.        │
│ STRUCTURE ········ Structure does the work, not policy.             │
│ HONESTY ·········· Honesty as structural load-bearing property.     │
│ CINCINNATUS ······ Operator-independence test (Will-AFK robustness).│
│ FULL LEVERAGE ···· Wait until leverage is total, not partial.       │
│ COMPLETE-AS-RFC ·· Complete = ready-for-critique, not validated.    │
└─────────────────────────────────────────────────────────────────────┘

┌─[ ASK CLAUDE ]──────────────────────────────────────────────────────┐
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
