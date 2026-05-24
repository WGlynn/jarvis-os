#!/usr/bin/env python3
"""
WWWD Corpus Refresh
===================

SessionStart hook. Reads the accumulated gate-fire log, extracts the
corrections from prior sessions, builds a priority-cache index that
recent corrections dominate older primitives in WWWD's enumerate step.

Output: writes a summary file at memory/_system/wwwd_corpus_priority.json
that the gate hook reads on subsequent runs to know which primitives have
recent-correction weight.

Per the recency-dominance rule in v3-wwwd-protocol.md: a Will-correction
from this session beats a memory primitive from last week; a primitive
written this month beats one from three months ago unless reaffirmed.

Companion to wwwd-gate.py + wwwd-correction-detector.py.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

MEMORY_DIR = Path.home() / ".claude" / "projects" / "{{PROJECT_DIR}}" / "memory"
GATE_FIRE_LOG = MEMORY_DIR / "_system" / "wwwd_gate_fires.jsonl"
PRIORITY_CACHE = MEMORY_DIR / "_system" / "wwwd_corpus_priority.json"

# Decay constants for corpus-priority weighting.
RECENCY_HALFLIFE_DAYS = 14  # corrections fade over time; recent dominates


def parse_log() -> list[dict]:
    """Read the gate-fire log into a list of entries. Tolerates malformed
    lines (skips them)."""
    if not GATE_FIRE_LOG.exists():
        return []
    entries = []
    try:
        for line in GATE_FIRE_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except Exception:
        return []
    return entries


def compute_priority_cache(entries: list[dict]) -> dict:
    """Build the WWWD corpus priority cache from gate-fire log entries.

    Output structure:
      {
        "computed_at": ISO timestamp,
        "total_gate_fires": int,
        "total_corrections": int,
        "correction_rate": float,
        "by_decision_class": {
          <class_name>: {
            "fires": int,
            "corrections": int,
            "correction_rate": float,
            "recent_correction_weight": float,  # half-life-decayed
            "matched_correction_patterns": [str, ...]  # top-N
          }, ...
        },
        "convergence_signal": str  # "improving" / "stable" / "drifting" / "insufficient-data"
      }
    """
    now = datetime.now(timezone.utc)

    by_class: defaultdict = defaultdict(
        lambda: {
            "fires": 0,
            "corrections": 0,
            "matched_patterns": Counter(),
            "weighted_corrections": 0.0,
        }
    )

    total_fires = 0
    total_corrections = 0

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        decision_class = entry.get("decision_class", "uncategorized")
        by_class[decision_class]["fires"] += 1
        total_fires += 1

        correction = entry.get("correction")
        if not correction or not isinstance(correction, dict):
            continue

        by_class[decision_class]["corrections"] += 1
        total_corrections += 1

        # Half-life decay for the weighted-correction metric.
        try:
            ts = datetime.fromisoformat(correction.get("timestamp", "").replace("Z", "+00:00"))
            age_days = (now - ts).total_seconds() / 86400.0
            weight = 0.5 ** (age_days / RECENCY_HALFLIFE_DAYS)
        except Exception:
            weight = 0.0

        by_class[decision_class]["weighted_corrections"] += weight
        for pat in correction.get("matched_patterns", []):
            by_class[decision_class]["matched_patterns"][pat] += 1

    # Convergence signal: are corrections-per-fire trending down?
    # Simple windowed comparison: most-recent N fires vs oldest N fires.
    convergence = "insufficient-data"
    if total_fires >= 20:
        window = max(10, total_fires // 4)
        recent = entries[-window:]
        oldest = entries[:window]
        recent_corrections = sum(1 for e in recent if e.get("correction"))
        oldest_corrections = sum(1 for e in oldest if e.get("correction"))
        if recent_corrections < oldest_corrections * 0.7:
            convergence = "improving"
        elif recent_corrections > oldest_corrections * 1.3:
            convergence = "drifting"
        else:
            convergence = "stable"

    out = {
        "computed_at": now.isoformat(),
        "total_gate_fires": total_fires,
        "total_corrections": total_corrections,
        "correction_rate": (total_corrections / total_fires) if total_fires else 0.0,
        "by_decision_class": {
            cls: {
                "fires": v["fires"],
                "corrections": v["corrections"],
                "correction_rate": (v["corrections"] / v["fires"]) if v["fires"] else 0.0,
                "recent_correction_weight": round(v["weighted_corrections"], 4),
                "top_correction_patterns": [
                    p for p, _ in v["matched_patterns"].most_common(5)
                ],
            }
            for cls, v in by_class.items()
        },
        "convergence_signal": convergence,
    }
    return out


def main() -> int:
    try:
        _payload = json.load(sys.stdin)
    except Exception:
        _payload = {}

    entries = parse_log()
    cache = compute_priority_cache(entries)

    try:
        PRIORITY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        PRIORITY_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass  # silent fail; not load-bearing on the session boot

    # Emit a brief boot-context note summarizing the convergence signal.
    if cache["total_gate_fires"] > 0:
        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"[WWWD CORPUS REFRESH] {cache['total_gate_fires']} gate-fires, "
                    f"{cache['total_corrections']} corrections "
                    f"({cache['correction_rate']:.1%} correction rate), "
                    f"convergence: {cache['convergence_signal']}. "
                    f"Priority cache at memory/_system/wwwd_corpus_priority.json."
                ),
            }
        }
        print(json.dumps(out))
    else:
        print(json.dumps({}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
