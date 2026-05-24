#!/usr/bin/env python3
"""
Entity-Context Cross-Reference Hook (AA#3 / CCP enforcer)
=========================================================

PreToolUse hook on Write / Edit. When the content about to be written contains
patterns that indicate entity-listing (target lists, outreach drafts, public
artifacts mentioning multiple named entities), the hook:

  1. Extracts candidate named entities (capitalized 1-3 word phrases)
  2. Greps memory/project_*.md, memory/J·*.md, memory/R·*.md,
     memory/correspondence/*.md for each candidate
  3. If matches found, injects a system-reminder via additionalContext
     surfacing the matched snippets so the assistant can apply
     cross-reference before final delivery

Implements the load-bearing enforcement tier of:
  - [F·entity-context-cross-reference] (AA#3, audit-arsenal)
  - [P·cross-context-protocol] (CCP, meta-parent)

The hook does NOT block the tool. It surfaces context. The model decides
whether to revise based on the matched snippets. This preserves author agency
while making the cross-reference structural rather than recall-dependent.

Origin: 2026-05-13. Will: "go full autopilot, no questions asked, do whatever
you want to do" after naming the context-vulnerability class (USD8 outreach
target list missed OpenZeppelin/Rick + LayerZero/post-abandonment).

Trigger heuristics tuned conservative (under-trigger > annoy):
  - Content length >= 500 chars
  - Content contains entity-list signal patterns

Performance: greps are cached per-entity within a single invocation; total
overhead < 200ms for typical entity-list content (5-50 named entities).
"""
import json
import os
import re
import sys
import time
from pathlib import Path

MEMORY_DIR = Path.home() / ".claude" / "projects" / "{{PROJECT_DIR}}" / "memory"
ENTITY_INDEX_PATH = MEMORY_DIR / "_system" / "entity_index.json"

# Telemetry: log every hook fire to _system/protocol_telemetry.jsonl
_HOOKS_DIR = Path(__file__).parent
sys.path.insert(0, str(_HOOKS_DIR))
try:
    from _telemetry import log_event
except Exception:
    def log_event(*a, **kw): pass

# Cache the loaded index across a single invocation. Stale-check via mtime
# comparison against the memory dir's most recent .md mtime.
_index_cache: dict | None = None


def _load_index() -> dict | None:
    """Load the entity_index.json if it exists and isn't grossly stale."""
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    if not ENTITY_INDEX_PATH.exists():
        return None
    try:
        with ENTITY_INDEX_PATH.open(encoding="utf-8") as f:
            _index_cache = json.load(f)
    except Exception:
        return None
    # Staleness floor: if any .md file in memory is newer than the index by
    # >5 minutes, treat the index as stale and fall back to grep. Cheap stat
    # over ~500 files (~30ms on Will's hardware).
    try:
        idx_mtime = ENTITY_INDEX_PATH.stat().st_mtime
        for p in MEMORY_DIR.rglob("*.md"):
            if p.stat().st_mtime > idx_mtime + 300:
                _index_cache = None
                return None
    except Exception:
        pass
    return _index_cache

# Patterns that indicate this is an entity-listing or outreach-related write.
# Under-trigger > over-trigger.
ENTITY_LIST_SIGNAL_PATTERNS = [
    r"##\s*Email\s+\d",          # Email N. format
    r"\*\*To\*\*:",              # **To**: field (email header)
    r"\*\*Subject\*\*:",         # **Subject**: field
    r"target\s+list",            # explicit target-list reference
    r"outreach",                 # outreach context
    r"contacts?\s*\(",           # "contacts (" or "contact ("
    r"@[A-Z][a-z]+",             # @-mentions of capitalized names
    r"\|\s*\[?[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+\s*\]?\s*\|",  # table row w/ proper-noun pair
    r"DM\s+[A-Z]",               # "DM Name"
    r"reach\s+out",              # explicit reach-out language
    r"introduction(s)?\s+to",    # introductions to ...
]

# Conservative proper-noun extraction: 2-3 word capitalized phrases.
# Excludes single capitalized words (too noisy — would match Solidity, Git, etc.)
# Excludes 4+ word phrases (those are usually sentences, not names)
PROPER_NOUN_PATTERN = re.compile(
    r"\b[A-Z][a-z]{1,15}(?:\s+[A-Z][a-z]{1,15}){1,2}\b"
)

# Single-token entities that ARE recognized (firm names, protocols).
# Allowlist — we only flag these when they appear in entity-list signal context.
KNOWN_FIRMS = {
    "OpenZeppelin", "LayerZero", "Pendle", "Morpho", "Euler", "Silo",
    "Fluid", "Instadapp", "Sommelier", "Yearn", "Beefy", "Aerodrome",
    "Velodrome", "Balancer", "Curve", "Uniswap", "Across", "Wormhole",
    "Spectra", "Karpatkey", "Llama", "Steakhouse", "Avantgarde", "Chaos",
    "Gauntlet", "Gitcoin", "Safe", "Gnosis", "Hop", "Pashov", "Trail",
    "ChainSecurity", "Cantina", "Spearbit", "Cyfrin", "Code4rena",
    "Sherlock", "Zellic", "Runtime", "Bankless", "Defiant", "Empire",
    "Blockworks", "Bell", "Codephobic", "VibeSwap", "USD8", "Rick", "Will",
    "Aave", "Compound", "Maker", "Circle", "Tether", "Frax", "Liquity",
    "Angle", "TRION", "Anthropic", "OpenAI", "Variant", "1kx", "Delphi",
    "Brevis", "Halmos", "Certora", "OpenZep",
}

# Stopword filter — common capitalized phrases that are NOT entities.
STOPWORD_PHRASES = {
    "Et Al", "I'M", "We Re", "Smart Collateral", "Smart Debt", "Cover Pool",
    "Cover Score", "Cross Chain", "Open Zeppelin",  # we want the unified form
}


def extract_candidate_entities(content: str) -> list[str]:
    """Extract candidate named entities from content."""
    candidates = set()

    # Multi-word proper-noun phrases
    for match in PROPER_NOUN_PATTERN.findall(content):
        normalized = match.strip()
        if normalized not in STOPWORD_PHRASES:
            candidates.add(normalized)

    # Single-word firms from the allowlist
    for firm in KNOWN_FIRMS:
        if re.search(rf"\b{re.escape(firm)}\b", content):
            candidates.add(firm)

    return sorted(candidates)


def grep_memory_for_entity(entity: str) -> list[tuple[Path, str]]:
    """
    Find files mentioning the entity. Uses entity_index.json reverse-lookup
    if available (O(matches)), falls back to live grep (O(memory-size))
    if the index is missing or stale.
    """
    if not MEMORY_DIR.exists():
        return []

    # Fast path: index lookup
    index = _load_index()
    if index is not None:
        entity_to_files = index.get("entity_to_files", {})
        files = entity_to_files.get(entity, [])
        if not files:
            return []
        matches = []
        pattern = re.compile(rf"\b{re.escape(entity)}\b", re.IGNORECASE)
        for rel_path in files:
            filepath = MEMORY_DIR / rel_path
            if not filepath.exists():
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line in content.splitlines():
                if pattern.search(line):
                    snippet = line.strip()[:200]
                    matches.append((filepath, snippet))
                    break
        return matches

    # Fallback: live grep
    matches = []
    pattern = re.compile(rf"\b{re.escape(entity)}\b", re.IGNORECASE)

    search_globs = [
        "project_*.md",
        "feedback_*.md",
        "reference_*.md",
        "primitive_*.md",
        "protocol_*.md",
    ]
    if (MEMORY_DIR / "correspondence").exists():
        search_globs.append("correspondence/*.md")

    seen_files = set()
    for glob_pattern in search_globs:
        for filepath in MEMORY_DIR.glob(glob_pattern):
            if filepath in seen_files:
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if not pattern.search(content):
                continue
            for line in content.splitlines():
                if pattern.search(line):
                    snippet = line.strip()[:200]
                    matches.append((filepath, snippet))
                    seen_files.add(filepath)
                    break

    return matches


def main() -> int:
    try:
        payload = sys.stdin.read()
        data = json.loads(payload) if payload.strip() else {}
    except Exception:
        return 0

    tool_name = data.get("tool_name") or data.get("toolName") or ""
    tool_input = data.get("tool_input") or data.get("toolInput") or {}

    # Only fire on Write / Edit
    if tool_name not in ("Write", "Edit"):
        return 0

    # Extract content being written
    content = (
        tool_input.get("content")
        or tool_input.get("new_string")
        or tool_input.get("newString")
        or ""
    )
    if not isinstance(content, str) or len(content) < 500:
        return 0

    # Does the content look like entity-listing / outreach material?
    has_signal = any(re.search(pat, content, re.IGNORECASE) for pat in ENTITY_LIST_SIGNAL_PATTERNS)
    if not has_signal:
        return 0

    # Extract entities + grep memory
    entities = extract_candidate_entities(content)
    if not entities:
        return 0

    matched = {}
    for entity in entities:
        results = grep_memory_for_entity(entity)
        if results:
            matched[entity] = results

    if not matched:
        log_event("entity-context-cross-reference", "noop",
                  meta={"reason": "no_memory_matches", "entities_checked": len(entities)})
        return 0

    log_event("entity-context-cross-reference", "match",
              matches=list(matched.keys()),
              meta={"entity_count": len(matched),
                    "total_file_matches": sum(len(v) for v in matched.values())})

    # Build the system-reminder
    lines = [
        "[ENTITY-CONTEXT CROSS-REFERENCE — AA#3 / CCP enforcer]",
        "",
        "The content being written contains named entities that have memory references. "
        "Per [F·entity-context-cross-reference] (AA#3) and [P·cross-context-protocol] (CCP), "
        "cross-reference each before delivery. Stated entities ≠ valid entities until reconciled.",
        "",
        "Matches found:",
        "",
    ]

    for entity, results in matched.items():
        lines.append(f"**{entity}**:")
        for filepath, snippet in results[:3]:  # cap to top 3 per entity to avoid noise
            rel_path = filepath.name
            lines.append(f"  - `{rel_path}` — {snippet}")
        lines.append("")

    lines.extend([
        "Reconciliation checklist:",
        "- Relationship: is this entity an employer / co-founder / collaborator of someone on our team?",
        "- Abandoned: did we recently move off this entity (e.g., post-incident)?",
        "- In-flight: is another team member already in conversation with this entity?",
        "- NDA-locked: is this entity tied to a discretion-flagged engagement?",
        "",
        "If any reconciliation applies, revise the output before completing the Write/Edit.",
    ])

    additional_context = "\n".join(lines)

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": additional_context,
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
