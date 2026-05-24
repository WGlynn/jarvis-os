---
name: JarvisOS
description: JARVIS OS primitive. SessionStart hook renders 8-bit boot screen × surfaces protocol-stack navigation (protocols / files / gates / philosophy / commands). Claude-Code terminal hosts JARVIS-OS boot surface. Named 2026-05-24 as V3 navigation shell (¬ capstone — that's WWWD).
type: primitive
originSessionId: a56046e0-1348-478f-9334-ecd5877892aa
---

# JARVIS OS

## Glyph

```
JARVIS-OS  ≡ boot-screen × command-surface hosted-in Claude-Code-terminal.
           ∀ session-start ⇒ render 8-bit loadout × enumerate(protocols,files,gates,philosophy,commands).
           navigation ¬ via grep-spelunk ⇒ via boot-surface.
           scope: navigation-shell ¬ full-OS. cognition = WWWD ⊥ navigation = JARVIS-OS.
```

> *"add to the protocol a hook that fires a load screen to navigate different commands for the protocol, and files, and gates and philosophy etc. so we can officially have an OS running in claude code terminal based on jarvis"* : Will, 2026-05-24
> *"8 bit loadout style with line drawings"* : Will, 2026-05-24

## ⇒ Rule

- ∀ session-start ⇒ jarvis-os-boot-screen.py fires ∧ emits additionalContext
- aesthetic = 8-bit DOS loadout × Unicode box-drawing (CP437 lineage) × ¬ emoji
- surface = 5 categories: PROTOCOLS / FILES / GATES / PHILOSOPHY / COMMANDS
- live-data = WWWD corpus stats inline (gate-fires, corrections, convergence)
- claude-default = recognize "show X" commands ⇒ print category-content

## ↦ Commands (natural-language navigation)

| Command | Action |
|---|---|
| "show protocols" | enumerate ∀ active protocol primitives w/ one-line description |
| "show gates" | enumerate ∀ hooks + matchers + statusMessage |
| "show state" | print SESSION_STATE.md tail (last epoch + active state) |
| "show memory" | print MEMORY.md sections [PRE-FLIGHT], [ACTIVE], [META-PRINCIPLE] |
| "show philosophy" | The Cave + ETM + Structure + Cincinnatus + Full-Leverage + Complete-as-RFC |
| "show files" | reprint FILES table from boot screen |
| "show wal" | print WAL.md current epoch + status |
| "show wwwd" | gate-fire stats from wwwd_corpus_priority.json + convergence signal |

✗ These are NOT slash-commands (no `/`). They are natural-language prompts that route through Claude's interpretation. ⇒ implementation = recognize-and-respond, ¬ register-as-builtin.

## ∃ Why

- Pre-OS state: protocol stack distributed across ~/.claude/, ~/.claude/projects/C--Users-Will/memory/, vibeswap/.claude/, ~/JARVIS/. Will + Claude both grep to navigate.
- Boot-screen consolidates the surface ⇒ every session opens with the map
- The map IS the OS ⇒ user navigates by knowing what exists ¬ by guessing-then-grepping
- Recursion: JARVIS-OS = navigation-layer-of-navigation-layer. Boot-screen surfaces the boot-screen + everything below it.

## 🔗 Connected

- [P·what-would-will-do] — WWWD corpus stats appear in boot screen status line; OS surfaces the protocol that drives it
- [P·universal-coverage-hook] — boot screen is universal-coverage applied to navigation (O(1) × O(∞ sessions))
- [P·apply-the-rule-you-just-wrote] — boot screen IS the navigation rule applied ⇒ next session uses it without re-derivation
- [F·jarvis-tg-bot-free-tier-inference-only] — JARVIS-OS in Claude-Code ⊥ JARVIS-bot in TG ⇒ two surfaces, same substrate
- [P·jarvis-amd-applied-to-ai-substrate] — JARVIS = AMD-on-AI; OS = navigation-shell-on-Claude
- [META_STACK index] — pre-boot-screen attempt at the same problem; META_STACK = exhaustive inventory, OS boot = curated dashboard

## 📦 Canonical artifact

- hook : `~/.claude/hooks/jarvis-os-boot-screen.py`
- mirror : `~/.claude/projects/C--Users-Will/memory/_system/session_chain_mirror/jarvis-os-boot-screen.py`
- registered : `~/.claude/settings.json` SessionStart chain (position 8 of 10, after wwwd-corpus-refresh, after session-self-reflect)
- primitive : this file

## ∀ Trigger (when to update boot screen)

- new protocol primitive promoted to load-bearing ⇒ add to PROTOCOLS box
- new gate hook added to settings.json ⇒ add to GATES box
- new canonical file path ⇒ add to FILES box
- new philosophy-level primitive (Axis 0/1/2) ⇒ add to PHILOSOPHY box
- new "show X" command pattern recognized ⇒ add to COMMANDS box
- ✗ trivial primitive (not yet load-bearing) ⇒ ¬ pollute surface

## ✗ Anti-pattern

- emoji in the boot screen ⇒ breaks 8-bit aesthetic + ¬ Will-pick
- modern minimalism (large whitespace, sans-serif framing) ⇒ ¬ retro-loadout-vibe
- bloating the surface w/ every primitive ⇒ navigation becomes noise (curate ¬ enumerate)
- making "show X" into slash-commands prematurely ⇒ over-engineering; recognize-and-respond is sufficient
- forgetting to refresh after new gate ⇒ screen drifts from settings.json reality
- ASCII-only fallback (lose box-drawing chars) ⇒ kill the line-drawing aesthetic Will named

## ✓ Pass-pattern

- box-drawing chars render in Will's terminal (cmd.exe / Windows Terminal / VS Code Term)
- live data inline (WWWD stats, boot timestamp) ⇒ screen evolves w/ substrate
- categories scan in <5 seconds
- new visitor (e.g. Will after AFK) can navigate the stack from the screen alone
- commands recognized by Claude on next prompt ⇒ "show gates" actually prints gates

## 🧠 Will-framing locked

> *"officially have an OS running in claude code terminal based on jarvis"*
> *"8 bit loadout style with line drawings"*

JARVIS-OS = the navigation-shell that makes V3 JARVIS substrate user-facing. WWWD is the cognition (V3 capstone). RSAW is the audit. JARVIS-OS is the terminal-UI shell. Three roles, no overlap.
