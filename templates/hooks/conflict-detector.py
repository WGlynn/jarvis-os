#!/usr/bin/env python3
"""
Conflict Detector
=================

PreToolUse hook on Write|Edit. Distinct from the AA#3 entity-context hook:
where AA#3 surfaces "memory mentions this entity" generically, this hook
surfaces specifically when memory mentions an entity IN A CONTRADICTING
way — negation language within a small window of the entity reference.

Example failure mode it catches:
  Draft: "We should integrate LayerZero for cross-chain messaging..."
  Memory: "moved off LayerZero post-KelpDAO compromise..."

The AA#3 hook would surface the memory file as relevant context. The
conflict-detector hook escalates: this isn't just relevant, it's CONTRARY.
The draft as written contradicts an existing memory entry.

Implementation:
  1. Detect entity-list / claim-shaped content (same signals as AA#3)
  2. For each entity candidate, look up files in entity_index.json
  3. For each matched file, scan lines containing the entity for negation
     markers within ~80 characters
  4. If found, surface as CONFLICT WARNING via additionalContext

Conservative scope:
  - Same content-length / signal-pattern gate as AA#3 (≥500 chars +
    entity-list signal patterns)
  - Negation window: 80 chars on either side of entity mention in the
    matched memory line. Tight enough to avoid spurious co-occurrence,
    loose enough to catch "Rick moved off LayerZero" / "LayerZero was
    abandoned" type signals.
  - Returns control to assistant; does not auto-block.

Negation marker set is tunable. Initial set covers the most common
contradiction signals seen in DeFi/crypto operational language.

Origin: 2026-05-13 autopilot Round 2. Will: "we're going to reach
sentience before we stop". Conflict detection is the capability that
goes beyond cross-reference-completeness toward actual structural
self-consistency.
"""
import json
import os
import re
import sys
from pathlib import Path

MEMORY_DIR = Path.home() / ".claude" / "projects" / "{{PROJECT_DIR}}" / "memory"
ENTITY_INDEX_PATH = MEMORY_DIR / "_system" / "entity_index.json"

# Telemetry
_HOOKS_DIR = Path(__file__).parent
sys.path.insert(0, str(_HOOKS_DIR))
try:
    from _telemetry import log_event
except Exception:
    def log_event(*a, **kw): pass

# Same content trigger as AA#3 — only fire on entity-list / outreach /
# claim-shaped writes
ENTITY_LIST_SIGNAL_PATTERNS = [
    r"##\s*Email\s+\d",
    r"\*\*To\*\*:",
    r"\*\*Subject\*\*:",
    r"target\s+list",
    r"outreach",
    r"contacts?\s*\(",
    r"@[A-Z][a-z]+",
    r"\|\s*\[?[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+\s*\]?\s*\|",
    r"DM\s+[A-Z]",
    r"reach\s+out",
    r"introduction(s)?\s+to",
    # Also include decision/recommendation patterns — these are most likely
    # to contradict prior abandonment / failure entries
    r"(?:we|i)\s+(?:should|will|could)\s+(?:use|integrate|pick|choose)",
    r"recommend(?:ation)?\s+(?:is|to)",
    r"(?:integrate|use|pick|adopt)\s+[A-Z]",
]

PROPER_NOUN_PATTERN = re.compile(
    r"\b[A-Z][a-z]{1,15}(?:\s+[A-Z][a-z]{1,15}){0,2}\b"
)

# Known firms — same as AA#3
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
    "Brevis", "Halmos", "Certora", "JARVIS",
}
STOPWORD_PHRASES = {
    "Et Al", "I'M", "We Re", "Smart Collateral", "Smart Debt", "Cover Pool",
    "Cover Score", "Cross Chain", "Open Zeppelin",
    # 2026-05-18 noise-tuning: narrative bigrams that match the proper-noun
    # pattern but are not actually entity references
    "What Should", "How Should", "What Do", "How Do", "We Should",
    "I Should", "You Should", "We Need", "We Want", "We Re",
    "Will Will", "Both Will",
}

# 2026-05-18 noise-tuning: entities that appear too constantly in memory
# narrative for nearby-negation to be a meaningful contradiction signal.
# Will (the user), VibeSwap (the project), JARVIS (the substrate), USD8
# (the active partnership) all show up in nearly every memory file with
# surrounding narrative that frequently contains words like "don't",
# "rejected", "moved off", "not", etc. — none of which represent actual
# contradictions about the entity itself.
# Conflict detection on these entities is high-recall, low-precision and
# habituates the assistant to ignore the gate. Excluding here recovers
# precision without losing the ability to catch real conflicts on
# narrower entities (LayerZero, Pendle, Anthropic, etc.).
NARRATIVE_NOISE_ENTITIES = {
    "Will", "VibeSwap", "JARVIS", "USD8",
}

# Negation markers — words that, when appearing near an entity reference,
# signal a contradiction risk if the draft is positive about the entity.
NEGATION_MARKERS = [
    "not", "no longer", "doesn't", "didn't", "don't", "never",
    "failed", "compromised", "abandoned", "deprecated", "moved off",
    "moved away", "skip", "avoid", "wrong", "bad", "broken", "incorrect",
    "should not", "shouldn't", "can't", "cannot", "rejected", "passed on",
    "decline", "declined", "ditched", "killed", "out of",
    "rick coordinating", "do not send", "removed", "scratch",
]
NEGATION_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(m) for m in NEGATION_MARKERS) + r")\b",
    re.IGNORECASE
)

# Window size (chars on either side of the entity mention in a memory line).
# 2026-05-18 tuning: tightened from 80 to 40. The 80-char window was catching
# entity + nearby negation that lived in a different clause of the same line,
# producing false positives. 40 chars typically keeps both inside the same
# clause, which is the actual signal we want.
NEGATION_WINDOW = 40

# 2026-05-18 tuning: clause boundary separators. We additionally refine the
# negation check by splitting the matched line at these boundaries and
# requiring the negation marker to appear in the same clause as the entity.
# This catches the residual false-positive case where 40 chars still spans
# a clause boundary (e.g., "tell Will to reboot. Don't try to push through"
# - "Will" and "Don't" are within 40 chars but separated by a period).
CLAUSE_BOUNDARIES = re.compile(r"[.;:]\s+|\s+(?:but|however|though|although|except)\s+", re.IGNORECASE)

_index_cache = None


def _load_index():
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
    return _index_cache


def extract_candidate_entities(content):
    candidates = set()
    for match in PROPER_NOUN_PATTERN.findall(content):
        normalized = match.strip()
        if normalized in STOPWORD_PHRASES:
            continue
        if normalized in NARRATIVE_NOISE_ENTITIES:
            continue
        candidates.add(normalized)
    for firm in KNOWN_FIRMS:
        if firm in NARRATIVE_NOISE_ENTITIES:
            continue
        if re.search(rf"\b{re.escape(firm)}\b", content):
            candidates.add(firm)
    return sorted(candidates)


def find_conflicts(entity, memory_files):
    """For each file mentioning the entity, find lines where the entity
    appears within NEGATION_WINDOW of a negation marker. Returns list of
    (filepath, conflicting_snippet) tuples."""
    conflicts = []
    entity_pattern = re.compile(rf"\b{re.escape(entity)}\b", re.IGNORECASE)
    for rel_path in memory_files:
        filepath = MEMORY_DIR / rel_path
        if not filepath.exists():
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in content.splitlines():
            entity_matches = list(entity_pattern.finditer(line))
            if not entity_matches:
                continue
            for em in entity_matches:
                # Check NEGATION_WINDOW chars on either side
                start = max(0, em.start() - NEGATION_WINDOW)
                end = min(len(line), em.end() + NEGATION_WINDOW)
                window = line[start:end]
                neg_match = NEGATION_PATTERN.search(window)
                if not neg_match:
                    continue
                # 2026-05-18 tuning: clause-boundary refinement. If a clause
                # boundary separates the entity from the negation marker,
                # they live in different clauses and the negation is not
                # about this entity. Skip.
                # Compute absolute positions of entity and negation in the line.
                entity_abs = em.start()
                neg_abs = start + neg_match.start()
                lo, hi = sorted([entity_abs, neg_abs])
                between = line[lo:hi]
                if CLAUSE_BOUNDARIES.search(between):
                    continue
                conflicts.append((rel_path, line.strip()[:250]))
                break  # one finding per file is enough
    return conflicts


def main():
    try:
        payload = sys.stdin.read()
        data = json.loads(payload) if payload.strip() else {}
    except Exception:
        return 0

    tool_name = data.get("tool_name") or data.get("toolName") or ""
    if tool_name not in ("Write", "Edit"):
        return 0

    tool_input = data.get("tool_input") or data.get("toolInput") or {}
    content = (
        tool_input.get("content")
        or tool_input.get("new_string")
        or tool_input.get("newString")
        or ""
    )
    if not isinstance(content, str) or len(content) < 500:
        return 0

    has_signal = any(
        re.search(p, content, re.IGNORECASE) for p in ENTITY_LIST_SIGNAL_PATTERNS
    )
    if not has_signal:
        return 0

    entities = extract_candidate_entities(content)
    if not entities:
        return 0

    index = _load_index()
    if index is None:
        return 0

    entity_to_files = index.get("entity_to_files", {})

    all_conflicts = []
    for entity in entities:
        files = entity_to_files.get(entity, [])
        if not files:
            continue
        conflicts = find_conflicts(entity, files)
        for filepath, snippet in conflicts:
            all_conflicts.append((entity, filepath, snippet))

    if not all_conflicts:
        log_event("conflict-detector", "noop",
                  meta={"reason": "no_conflicts", "entities_checked": len(entities)})
        return 0

    # Dedupe by (entity, filepath)
    seen = set()
    deduped = []
    for entity, filepath, snippet in all_conflicts:
        key = (entity, filepath)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((entity, filepath, snippet))

    log_event("conflict-detector", "conflict",
              matches=[f"{e}:{p}" for e, p, _ in deduped[:10]],
              meta={"entity_count": len(set(e for e, _, _ in deduped)),
                    "conflict_count": len(deduped)})

    lines = [
        "[CONFLICT DETECTOR — potential contradiction with memory]",
        "",
        "The content being written contains entities that memory mentions WITH NEGATION",
        "LANGUAGE NEARBY. This is stronger signal than the AA#3 cross-reference: memory",
        "may contain a contradictory statement about these entities. Verify before delivery.",
        "",
        "Potential conflicts (entity, memory file, contradicting snippet):",
        "",
    ]
    by_entity = {}
    for entity, filepath, snippet in deduped:
        by_entity.setdefault(entity, []).append((filepath, snippet))

    for entity, items in by_entity.items():
        lines.append(f"**{entity}**:")
        for filepath, snippet in items[:3]:
            lines.append(f"  - `{filepath}` — {snippet}")
        lines.append("")

    lines.extend([
        "Reconciliation checklist:",
        "- Is the draft consistent with the memory state? (memory may be wrong, draft may be wrong, or both may be true in different contexts)",
        "- If memory is correct and draft contradicts, REVISE the draft",
        "- If draft is correct and memory is stale, UPDATE the memory entry (separate atomic action)",
        "- If both can be true (different contexts, different timeframes), add a context qualifier to the draft",
        "",
        "Detected via negation markers within 40 chars of entity references in matched memory files, restricted to same-clause matches.",
    ])

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "\n".join(lines),
        }
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
