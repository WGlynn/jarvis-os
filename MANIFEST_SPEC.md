# JARVIS-OS Substrate Manifest Spec

Optional declarative manifest that any Claude substrate repo can publish at
its root as `jarvis-os.yaml`. Repos with a manifest get cleaner absorption
into JARVIS-OS installs — the absorber reads the manifest instead of pattern-
scanning, and event-matcher assignments come from the publisher rather than
from heuristics.

Repos without a manifest still work via pattern-scan; the manifest is purely
a quality-of-life upgrade for the publisher.

## File location

```
<repo-root>/jarvis-os.yaml
```

## Schema

```yaml
# JARVIS-OS substrate manifest
name: substrate-name              # required, lowercase, used as namespace prefix
version: 1                        # manifest format version
description: |                    # optional, free-form
  One-paragraph summary of what this substrate adds.
author: name-or-handle            # optional
license: MIT                      # optional, but encouraged

# Hooks this substrate publishes.
# Each entry MUST specify: path (relative to repo root), event, matcher.
# Optional: timeout, status_message, priority (lower = earlier).
hooks:
  - path: hooks/my-hook.py
    event: PreToolUse              # SessionStart|UserPromptSubmit|PreToolUse|PostToolUse|Stop|StopFailure|PreCompact
    matcher: Write|Edit            # null for events that don't take matchers
    timeout: 8
    status_message: "My hook firing..."
    priority: 50

  - path: hooks/my-other-hook.py
    event: SessionStart
    matcher: null
    timeout: 5

# Memory primitives this substrate publishes.
# Each entry MUST specify: path. Optional: kind, tags, depends_on.
primitives:
  - path: memory/primitive_my-thing.md
    kind: primitive                # primitive|feedback|reference|project|protocol
    tags: [discipline, voice]
    depends_on: []                 # other primitive names this references

  - path: memory/feedback_my-pattern.md
    kind: feedback

# Optional: substrate-wide settings that the absorber MAY apply.
# Conservative defaults — most absorptions should NOT need these.
settings:
  permissions_allow: []            # additional permissions to add
  env: {}                          # environment vars

# Optional: compatibility hints for the absorber.
compat:
  min_jarvis_os_version: 1
  conflicts_with: []               # namespaces this substrate is known to conflict with
  requires: []                     # namespaces this substrate needs to be absorbed first
```

## Minimal valid manifest

```yaml
name: alice-substrate
version: 1
description: Alice's voice-discipline gate stack.

hooks:
  - path: hooks/voice-gate.py
    event: PreToolUse
    matcher: Write|Edit

primitives:
  - path: memory/primitive_alice-voice.md
    kind: primitive
```

## Why publish a manifest

- **Explicit event-matcher assignment.** Pattern-scan has to guess; manifest knows.
- **Dependency ordering.** If your hook depends on another being absorbed first, declare it.
- **Conflict declarations.** Flag known incompatibilities so the absorber warns.
- **Version pinning.** Future JARVIS-OS versions can degrade gracefully.

## Absorption semantics

When the absorber finds a manifest:

1. Read `name` → use as the namespace prefix
2. For each hook entry: validate path exists, copy to `~/.claude/hooks/<namespace>-<filename>`, register with declared event/matcher
3. For each primitive entry: copy to `~/.claude/projects/<project>/memory/<namespace>-<filename>`
4. Apply settings (if any) with user confirmation
5. Honor depends_on / conflicts_with constraints

A manifest takes priority over pattern-scan. Pattern-scan still runs for repos without manifests.

## Reserved namespaces

- `jarvis-os` — reserved for the canonical install pack
- `core` — reserved for future built-in substrates

## Spec status

This is v1 of the manifest format. Backwards-compatible additions go in
minor version bumps; breaking changes bump `version` to 2.

The reference implementation lives in `absorb.sh` of this repo. Future
versions will add: manifest-validation tool, programmatic registry,
conflict-resolution dialog improvements.
