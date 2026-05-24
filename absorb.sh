#!/usr/bin/env bash
#
# JARVIS-OS Substrate Absorber
# ============================
# Agnostically pulls hooks, primitives, and settings from another Claude
# substrate repo into your local JARVIS-OS install.
#
# Scans for:
#   hooks/*.py                       (anywhere in the repo)
#   .claude/hooks/*.py
#   memory/primitive_*.md
#   memory/feedback_*.md
#   .claude/projects/*/memory/primitive_*.md
#   .claude/projects/*/memory/feedback_*.md
#   .claude/projects/*/memory/reference_*.md
#   .claude/projects/*/memory/project_*.md
#   jarvis-os.yaml                   (optional declarative manifest)
#
# Strategy:
#   1. Locate the source repo (clone if URL, otherwise treat as local path)
#   2. Scan for hook + primitive files matching the patterns above
#   3. Read jarvis-os.yaml if present (declarative manifest takes priority)
#   4. Interactive: present each candidate; user picks import / skip / rename
#   5. Copy into your install with namespace-prefix collision handling
#   6. Auto-register imported hooks into settings.json (with comment trail)
#
# Usage:
#   bash absorb.sh <path-or-git-url> [--namespace prefix] [--dry-run] [--auto]
#
# Examples:
#   bash absorb.sh ~/another-substrate
#   bash absorb.sh https://github.com/someone/their-claude-setup
#   bash absorb.sh ~/their-setup --namespace alice --auto

set -e

# ============ Defaults ============

SOURCE=""
NAMESPACE=""
DRY_RUN=0
AUTO=0
CLAUDE_HOME="$HOME/.claude"
PROJECT_DIR=""

# ============ Arg parsing ============

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace)   NAMESPACE="$2"; shift 2 ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --auto)        AUTO=1; shift ;;
    --claude-home) CLAUDE_HOME="$2"; shift 2 ;;
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    -h|--help)     sed -n '2,30p' "$0"; exit 0 ;;
    -*)            echo "Unknown arg: $1"; exit 1 ;;
    *)             SOURCE="$1"; shift ;;
  esac
done

if [[ -z "$SOURCE" ]]; then
  echo "Usage: bash absorb.sh <path-or-git-url> [--namespace prefix] [--dry-run] [--auto]"
  exit 1
fi

if [[ -z "$PROJECT_DIR" ]]; then
  # Try to detect the active project from existing claude config.
  if [[ -d "$CLAUDE_HOME/projects" ]]; then
    PROJECT_DIR=$(ls -t "$CLAUDE_HOME/projects" 2>/dev/null | head -1)
  fi
  if [[ -z "$PROJECT_DIR" ]]; then
    PROJECT_DIR=$(echo "$HOME" | sed 's|/|-|g; s|^-||; s|:||g')
  fi
fi

HOOKS_DIR="$CLAUDE_HOME/hooks"
MEMORY_DIR="$CLAUDE_HOME/projects/$PROJECT_DIR/memory"
SETTINGS_FILE="$CLAUDE_HOME/settings.json"

# ============ Locate source ============

if [[ "$SOURCE" =~ ^(https?|git):// ]] || [[ "$SOURCE" =~ ^git@ ]]; then
  TMPDIR=$(mktemp -d -t jarvis-os-absorb-XXXXXX)
  trap "rm -rf '$TMPDIR'" EXIT
  echo "Cloning $SOURCE into $TMPDIR..."
  git clone --depth 1 "$SOURCE" "$TMPDIR/src" >/dev/null 2>&1
  SRC_ROOT="$TMPDIR/src"
else
  SRC_ROOT="$(cd "$SOURCE" 2>/dev/null && pwd)" || { echo "Source not found: $SOURCE"; exit 1; }
fi

if [[ -z "$NAMESPACE" ]]; then
  NAMESPACE=$(basename "$SRC_ROOT" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')
fi

echo
echo "Absorption plan:"
echo "  Source         : $SRC_ROOT"
echo "  Namespace      : $NAMESPACE"
echo "  Target hooks   : $HOOKS_DIR/"
echo "  Target memory  : $MEMORY_DIR/"
echo "  Dry-run        : $DRY_RUN"
echo "  Auto-import    : $AUTO (skip prompts; absorb everything)"
echo

# ============ Manifest read (optional) ============

MANIFEST="$SRC_ROOT/jarvis-os.yaml"
if [[ -f "$MANIFEST" ]]; then
  echo "Found declarative manifest: $MANIFEST"
  echo "  (declarative absorption not yet implemented — falling back to pattern scan)"
  echo
fi

# ============ Scan ============

scan_files() {
  local pattern="$1" search_root="$2"
  find "$search_root" -type f -name "$pattern" 2>/dev/null \
    | grep -v "/node_modules/" \
    | grep -v "/\.git/" \
    | grep -v "/\.venv/" \
    | grep -v "/__pycache__/"
}

declare -a HOOKS_FOUND
declare -a PRIMS_FOUND

while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  HOOKS_FOUND+=("$f")
done < <(scan_files "*.py" "$SRC_ROOT" | grep -E '(/hooks/|/session-chain/|gate\.py$|-gate\.py$|hook\.py$|-hook\.py$)' | head -200)

while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  PRIMS_FOUND+=("$f")
done < <( { scan_files "primitive_*.md" "$SRC_ROOT"; scan_files "feedback_*.md" "$SRC_ROOT"; scan_files "reference_*.md" "$SRC_ROOT"; scan_files "project_*.md" "$SRC_ROOT"; } | head -500)

echo "Scan results:"
echo "  Hook-shaped files  : ${#HOOKS_FOUND[@]}"
echo "  Primitive-shaped   : ${#PRIMS_FOUND[@]}"
echo

# ============ Interactive import ============

prompt_yn() {
  if [[ "$AUTO" == "1" ]]; then echo "y"; return; fi
  local msg="$1"
  read -r -p "$msg [y/N/s=skip-all] " yn </dev/tty
  echo "$yn"
}

SKIP_ALL=0
IMPORTED_HOOKS=()
IMPORTED_PRIMS=()

import_file() {
  local src="$1" dst="$2"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  [dry] cp $src -> $dst"
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  if [[ -f "$dst" ]]; then
    echo "  [skip] target exists: $dst (would overwrite — pass --auto to force)"
    return 1
  fi
  cp "$src" "$dst"
  echo "  imported: $dst"
  return 0
}

echo "=== HOOKS ==="
for h in "${HOOKS_FOUND[@]}"; do
  [[ "$SKIP_ALL" == "1" ]] && break
  rel=$(basename "$h")
  ns_name="${NAMESPACE}-${rel}"
  dst="$HOOKS_DIR/$ns_name"

  echo
  echo "  Source : $h"
  echo "  Would import as : $dst"
  yn=$(prompt_yn "Absorb this hook?")
  case "$yn" in
    [Yy]*) import_file "$h" "$dst" && IMPORTED_HOOKS+=("$ns_name") ;;
    [Ss]*) SKIP_ALL=1; echo "  Skipping all remaining hooks." ;;
    *)     echo "  Skipped." ;;
  esac
done

SKIP_ALL=0
echo
echo "=== PRIMITIVES ==="
for p in "${PRIMS_FOUND[@]}"; do
  [[ "$SKIP_ALL" == "1" ]] && break
  rel=$(basename "$p")
  ns_name="${NAMESPACE}-${rel}"
  dst="$MEMORY_DIR/$ns_name"

  echo
  echo "  Source : $p"
  echo "  Would import as : $dst"
  yn=$(prompt_yn "Absorb this primitive?")
  case "$yn" in
    [Yy]*) import_file "$p" "$dst" && IMPORTED_PRIMS+=("$ns_name") ;;
    [Ss]*) SKIP_ALL=1; echo "  Skipping all remaining primitives." ;;
    *)     echo "  Skipped." ;;
  esac
done

# ============ Register imported hooks ============

if [[ ${#IMPORTED_HOOKS[@]} -gt 0 ]] && [[ "$DRY_RUN" != "1" ]]; then
  echo
  echo "Registering ${#IMPORTED_HOOKS[@]} imported hook(s) into settings.json..."
  python3 - <<PYEOF
import json
from pathlib import Path

settings_path = Path("$SETTINGS_FILE")
hooks_dir = Path("$HOOKS_DIR")
imported = """${IMPORTED_HOOKS[@]}""".split()
namespace = "$NAMESPACE"

if not settings_path.exists():
    print("  WARNING: settings.json not found; skipping registration.")
    raise SystemExit(0)

cfg = json.loads(settings_path.read_text(encoding="utf-8"))
cfg.setdefault("hooks", {})
H = cfg["hooks"]

# Heuristic matcher inference from filename
def infer_event_and_matcher(name):
    n = name.lower()
    if "session" in n or "boot" in n or "loader" in n or "preprocessor" in n:
        return ("SessionStart", None)
    if "stop" in n or "post-generation" in n or "decision-capture" in n:
        return ("Stop", None)
    if "compact" in n:
        return ("PreCompact", None)
    if "post-tool" in n or "checkpoint" in n or "em-dash" in n:
        return ("PostToolUse", "Write|Edit|NotebookEdit")
    if "agent" in n or "reflection" in n:
        return ("PreToolUse", "Agent")
    if "bash" in n or "git" in n or "nda" in n:
        return ("PreToolUse", "Bash")
    # Default for hook/gate
    return ("PreToolUse", "Write|Edit")

backup = settings_path.with_suffix(".json.bak-pre-absorb")
backup.write_text(settings_path.read_text(encoding="utf-8"), encoding="utf-8")
print(f"  backup: {backup}")

for script in imported:
    event, matcher = infer_event_and_matcher(script)
    H.setdefault(event, [])
    # Find or create matcher block
    target_block = None
    for b in H[event]:
        if b.get("matcher") == matcher:
            target_block = b
            break
    if target_block is None:
        target_block = {"hooks": []}
        if matcher is not None:
            target_block["matcher"] = matcher
        H[event].append(target_block)
    # Skip if already registered
    if any(script in h.get("command", "") for h in target_block["hooks"]):
        continue
    target_block["hooks"].append({
        "type": "command",
        "command": f"python {hooks_dir}/{script}",
        "timeout": 8,
        "statusMessage": f"[absorbed:{namespace}] {script}",
    })
    print(f"  registered: {event}({matcher or '*'}) -> {script}")

settings_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"  wrote: {settings_path}")
PYEOF
fi

# ============ Summary ============

echo
echo "============================================================"
echo "  Absorption complete: $NAMESPACE"
echo "============================================================"
echo "  Hooks imported     : ${#IMPORTED_HOOKS[@]}"
echo "  Primitives imported: ${#IMPORTED_PRIMS[@]}"
echo
if [[ ${#IMPORTED_HOOKS[@]} -gt 0 ]]; then
  echo "  Imported hook event-matcher assignments are heuristic. Audit:"
  echo "    \$EDITOR $SETTINGS_FILE"
  echo
fi
echo "  Roll back at any time with the backup at:"
echo "    $SETTINGS_FILE.bak-pre-absorb"
echo
