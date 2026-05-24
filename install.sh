#!/usr/bin/env bash
#
# JARVIS-OS Installer
# ===================
# Installs the JARVIS-OS kernel into a user's ~/.claude/ configuration.
# Works on macOS, Linux, and Windows (Git Bash / WSL).
#
# What gets installed:
#
# Hooks (~/.claude/hooks/):
#   Layer 1 — WWWD cognition gate:
#     wwwd-gate.py                 — PreToolUse Write|Edit|Agent
#     wwwd-correction-detector.py  — Stop
#     wwwd-corpus-refresh.py       — SessionStart
#     jarvis-os-boot-screen.py     — SessionStart
#
#   Layer 3 — Anti-hallucination chain (deterministic gates):
#     hiero-gate.py                       — PreToolUse Write|Edit
#     partner-facing-substance-gate.py    — PreToolUse Write|Edit
#     strategic-framing-filter.py         — PreToolUse Write|Edit
#     entity-context-cross-reference.py   — PreToolUse Write|Edit
#     conflict-detector.py                — PreToolUse Write|Edit
#     partner-facing-additive-gate.py     — PreToolUse Bash
#     em-dash-augmentation-gate.py        — PostToolUse Write|Edit
#     atomic-reflection-gate.py           — PostToolUse + PreToolUse Agent
#
# Memory seed (~/.claude/projects/<project>/memory/):
#   MEMORY.md
#   primitive_what-would-will-do.md     (cognition gate primitive)
#   primitive_jarvis-os.md              (navigation shell primitive)
#   primitive_recursive-self-audit-via-wwwd.md  (audit methodology)
#
# Plus hook registrations merged into ~/.claude/settings.json.

set -e

# ============ Defaults ============

USER_NAME=""
PROJECT_DIR=""
DRY_RUN=0
CLAUDE_HOME="$HOME/.claude"
INSTALLER_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ============ Arg parsing ============

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)        USER_NAME="$2"; shift 2 ;;
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --claude-home) CLAUDE_HOME="$2"; shift 2 ;;
    -h|--help)     sed -n '2,33p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ============ Interactive prompts ============

if [[ -z "$USER_NAME" ]]; then
  echo
  echo "JARVIS-OS Installer"
  echo "==================="
  echo
  read -r -p "Your first name (used in cognition-gate projection): " USER_NAME
fi

if [[ -z "$USER_NAME" ]]; then
  echo "User name required. Aborting."
  exit 1
fi

if [[ -z "$PROJECT_DIR" ]]; then
  PROJECT_DIR=$(echo "$HOME" | sed 's|/|-|g; s|^-||; s|:||g')
fi

echo
echo "Installation plan:"
echo "  User name      : $USER_NAME"
echo "  Project slug   : $PROJECT_DIR"
echo "  Claude home    : $CLAUDE_HOME"
echo "  Dry-run        : $DRY_RUN"
echo

if [[ "$DRY_RUN" != "1" ]]; then
  read -r -p "Proceed? [y/N] " yn
  case "$yn" in [Yy]*) ;; *) echo "Aborted."; exit 0 ;; esac
fi

# ============ Helpers ============

mkdir_p() {
  if [[ "$DRY_RUN" == "1" ]]; then echo "  [dry] mkdir -p $1"
  else mkdir -p "$1"; fi
}

install_file() {
  local src="$1" dst="$2"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [dry] install $src -> $dst"
  else
    sed \
      -e "s|{{USER_NAME}}|$USER_NAME|g" \
      -e "s|{{USER_NAME_LOWER}}|$(echo "$USER_NAME" | tr '[:upper:]' '[:lower:]')|g" \
      -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
      "$src" > "$dst"
    chmod +x "$dst" 2>/dev/null || true
    echo "  installed: $(basename "$dst")"
  fi
}

# ============ Directories ============

HOOKS_DIR="$CLAUDE_HOME/hooks"
MEMORY_DIR="$CLAUDE_HOME/projects/$PROJECT_DIR/memory"
SETTINGS_FILE="$CLAUDE_HOME/settings.json"

mkdir_p "$HOOKS_DIR"
mkdir_p "$MEMORY_DIR/_system"

# ============ Hooks: Layer 1 (WWWD) ============

echo
echo "Installing Layer 1 — WWWD cognition gate..."
for f in jarvis-os-boot-screen.py wwwd-gate.py wwwd-correction-detector.py wwwd-corpus-refresh.py; do
  install_file "$INSTALLER_DIR/templates/hooks/$f" "$HOOKS_DIR/$f"
done

# ============ Hooks: Layer 3 (anti-hallucination) ============

echo
echo "Installing Layer 3 — anti-hallucination chain..."
for f in hiero-gate.py partner-facing-substance-gate.py partner-facing-additive-gate.py strategic-framing-filter.py entity-context-cross-reference.py conflict-detector.py em-dash-augmentation-gate.py atomic-reflection-gate.py; do
  install_file "$INSTALLER_DIR/templates/hooks/$f" "$HOOKS_DIR/$f"
done

# ============ Memory seed ============

echo
echo "Installing Layer 2 — memory seed..."
install_file "$INSTALLER_DIR/templates/memory/MEMORY.md"                                 "$MEMORY_DIR/MEMORY.md"
install_file "$INSTALLER_DIR/templates/memory/primitive_what-would-will-do.md"           "$MEMORY_DIR/primitive_what-would-will-do.md"
install_file "$INSTALLER_DIR/templates/memory/primitive_jarvis-os.md"                    "$MEMORY_DIR/primitive_jarvis-os.md"
install_file "$INSTALLER_DIR/templates/memory/primitive_recursive-self-audit-via-wwwd.md" "$MEMORY_DIR/primitive_recursive-self-audit-via-wwwd.md"

# ============ Settings merge ============

echo
echo "Merging hook registrations into settings.json..."

if [[ "$DRY_RUN" == "1" ]]; then
  echo "  [dry] would merge hook registrations into $SETTINGS_FILE"
else
  python3 - <<PYEOF
import json
from pathlib import Path

settings_path = Path("$SETTINGS_FILE")
hooks_dir = Path("$HOOKS_DIR")

if settings_path.exists():
    try:
        cfg = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception as e:
        backup = settings_path.with_suffix(".json.bak-malformed")
        settings_path.rename(backup)
        print(f"  WARNING: existing settings.json malformed ({e}). Backed up to {backup}.")
        cfg = {}
else:
    cfg = {}

cfg.setdefault("hooks", {})
H = cfg["hooks"]

def already_registered(blocks, substr):
    return any(substr in h.get("command", "")
               for b in blocks for h in b.get("hooks", []))

def find_or_create_block(blocks, matcher=None):
    for b in blocks:
        if b.get("matcher") == matcher:
            return b
    new = {"hooks": []}
    if matcher is not None:
        new["matcher"] = matcher
    blocks.append(new)
    return new

def add_hook(event, matcher, script, status_msg, timeout=8):
    H.setdefault(event, [])
    if already_registered(H[event], script):
        return
    block = find_or_create_block(H[event], matcher)
    block["hooks"].append({
        "type": "command",
        "command": f"python {hooks_dir}/{script}",
        "timeout": timeout,
        "statusMessage": status_msg,
    })
    print(f"  registered: {event}({matcher or '*'}) -> {script}")

# Layer 1 — WWWD
add_hook("SessionStart", None,                "wwwd-corpus-refresh.py",        "WWWD corpus refresh...")
add_hook("SessionStart", None,                "jarvis-os-boot-screen.py",      "JARVIS OS boot screen...", timeout=5)
add_hook("PreToolUse",   "Write|Edit|Agent",  "wwwd-gate.py",                  "WWWD gate: projecting...")
add_hook("Stop",         None,                "wwwd-correction-detector.py",   "WWWD correction detector...", timeout=5)

# Layer 3 — anti-hallucination
add_hook("PreToolUse",   "Write|Edit",        "hiero-gate.py",                       "HIERO gate: memory density...", timeout=5)
add_hook("PreToolUse",   "Write|Edit",        "partner-facing-substance-gate.py",    "Substance gate: claim-handshake...")
add_hook("PreToolUse",   "Write|Edit",        "strategic-framing-filter.py",         "Strategic framing filter...", timeout=5)
add_hook("PreToolUse",   "Write|Edit",        "entity-context-cross-reference.py",   "Entity cross-reference (AA#3 / CCP)...", timeout=10)
add_hook("PreToolUse",   "Write|Edit",        "conflict-detector.py",                "Conflict detector: memory contradictions...", timeout=10)
add_hook("PreToolUse",   "Bash",              "partner-facing-additive-gate.py",     "Additive-framing gate...")
add_hook("PreToolUse",   "Agent",             "atomic-reflection-gate.py",           "Atomic reflection: delegation introspection...", timeout=5)
add_hook("PostToolUse",  "Write|Edit|NotebookEdit", "em-dash-augmentation-gate.py",   "Em-dash augmentation gate...", timeout=5)
add_hook("PostToolUse",  None,                "atomic-reflection-gate.py",           "Atomic reflection: error/timeout check...", timeout=5)

# Backup + write
if settings_path.exists():
    backup = settings_path.with_suffix(".json.bak-pre-jarvis-os")
    if not backup.exists():
        backup.write_text(settings_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  backup: {backup}")

settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"  wrote: {settings_path}")
PYEOF
fi

# ============ Done ============

echo
echo "============================================================"
echo "  JARVIS-OS installed for $USER_NAME"
echo "============================================================"
echo
echo "  12 hooks registered across 4 events."
echo "  3 core primitives + seed MEMORY.md in your memory dir."
echo "  settings.json backup at ~/.claude/settings.json.bak-pre-jarvis-os"
echo
echo "  Verify the install:"
echo "    cd $INSTALLER_DIR && sha256sum -c MANIFEST.sha256"
echo
echo "  Customize your cognition gate:"
echo "    \$EDITOR $MEMORY_DIR/primitive_what-would-will-do.md"
echo
echo "  Start a new Claude Code session to see the boot screen."
echo
