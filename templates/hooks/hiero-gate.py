#!/usr/bin/env python3
"""HIERO Gate — PreToolUse hook for memory writes.

2026-04-25 cannon law: Memory ⇒ logic-primitive ¬ prose.

Fires on Write|Edit to memory paths. Strips frontmatter + block-quotes
(anchors ≠ prose), then runs 4-axis density check. Blocks (exit 2) when
≥2 axes fail; allows (exit 0) otherwise.

Detection axes:
  1. long-line ratio  (>120ch lines / total)
  2. logic-marker presence  (first 10 lines)
  3. multi-sentence paragraphs  (prose density)
  4. operator/glyph density  (vs token count)
"""
import sys
import json
import re

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # malformed input → don't block

tool_name = data.get("tool_name", "")
if tool_name not in ("Write", "Edit"):
    sys.exit(0)

tool_input = data.get("tool_input", {})
file_path = tool_input.get("file_path", "") or ""

# Match memory paths
MEMORY_PATTERNS = [
    r"[/\\]memory[/\\].*\.md$",
    r"GKB.*\.md$",
    r"SKB.*\.md$",
    r"JarvisxWill_.*\.md$",
]
if not any(re.search(p, file_path, re.IGNORECASE) for p in MEMORY_PATTERNS):
    sys.exit(0)

# Get content (Write uses 'content', Edit uses 'new_string')
content = tool_input.get("content") or tool_input.get("new_string", "") or ""
if len(content.strip()) < 200:
    sys.exit(0)  # too short to evaluate fairly

# Strip frontmatter (yaml between --- markers) — metadata, not memory body
body = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)

# Strip block-quote lines (Will's verbatim words = anchors, not prose)
non_quote_lines = [
    l for l in body.split("\n")
    if not l.lstrip().startswith(">")
]
analysis_text = "\n".join(non_quote_lines)
non_empty = [l for l in non_quote_lines if l.strip()]

if len(non_empty) < 5:
    sys.exit(0)

fails = []

# Axis 1: long-line ratio (prose-paragraph signal)
long_lines = [l for l in non_empty if len(l) > 120]
long_ratio = len(long_lines) / len(non_empty)
if long_ratio > 0.20 and len(long_lines) > 3:
    fails.append(
        f"long-line ratio {long_ratio:.0%} ({len(long_lines)}/{len(non_empty)} > 120ch)"
    )

# Axis 2: logic-marker presence in first 10 content lines
LOGIC_MARKER = re.compile(
    r"^\s*("
    r"#+\s|"                                  # markdown heading
    r"-\s|\*\s|\d+\.\s|"                       # list
    r"\|\s|"                                   # table row
    r"```|"                                    # code fence
    r"[A-Z][A-Z0-9_]{2,}\s|"                   # GLYPH header (CAVE, HIERO, P-001)
    r".*[⇒¬∧∨∈∉⊂→↑↓✓✗•†]"                      # contains operator
    r")"
)
first_10 = non_empty[:10]
marker_hits = sum(1 for l in first_10 if LOGIC_MARKER.match(l))
if marker_hits < 3:
    fails.append(f"logic-marker density in first 10 lines: {marker_hits}/10")

# Axis 3: multi-sentence paragraph density (prose signal)
sentence_pattern = re.compile(r"[.!?]\s+[A-Z]")
multi_sent_lines = [
    l for l in non_empty if len(sentence_pattern.findall(l)) >= 2
]
multi_sent_threshold = max(2, len(non_empty) * 0.10)
if len(multi_sent_lines) > multi_sent_threshold:
    fails.append(
        f"multi-sentence lines: {len(multi_sent_lines)} "
        f"(threshold {multi_sent_threshold:.0f})"
    )

# Axis 4: operator/glyph density vs token count
ops_pattern = re.compile(r"[⇒⇔¬∧∨∈∉⊂⊆→↦↑↓✓✗⊥⊤⊘•†×∀∃]")
op_hits = len(ops_pattern.findall(analysis_text))
total_words = len(re.findall(r"\b\w+\b", analysis_text))
op_density = op_hits / max(1, total_words)
if op_density < 0.005 and total_words > 200:
    fails.append(
        f"operator density {op_density:.4f} (target ≥ 0.0050)"
    )

# 2+ fails → BLOCK ; <2 → allow
if len(fails) >= 2:
    msg = (
        "HIERO check FAIL — memory write reads as prose.\n"
        "Cannon law (2026-04-25): Memory ⇒ logic-primitive ¬ prose.\n"
        f"Path: {file_path}\n"
        f"Fail count: {len(fails)}/4 (block threshold: ≥2)\n\n"
        "Failures:\n"
        + "\n".join(f"  • {f}" for f in fails)
        + "\n\nRecompress before write:\n"
          "  - glyph-headers, bullet/list structure\n"
          "  - operators: ⇒ ¬ ∧ ∨ ✓ ✗ × • → ↑ ↓\n"
          "  - block-quotes for Will's exact words (anchors ≠ prose, gate ignores)\n"
          "  - short lines, density-target 0.99\n"
          "  - see P·hiero-no-prose-in-memory for full rule\n"
    )
    print(msg, file=sys.stderr)
    sys.exit(2)  # block

sys.exit(0)
