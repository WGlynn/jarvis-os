#!/usr/bin/env python3
"""Partner-facing substance gate / anti-hallucination check (PreToolUse on Write/Edit).

Implements deterministic terminology fact-checking for partner-facing repos.
Distinct from the framing gate (which scans commit messages / PR descriptions
for retrospective comm patterns).

Core principle (Will, 2026-04-28):
  *"calling something that's not a clawback a clawback is a hallucination,
    somethings that deterministic anti hallucination fact checking should
    catch even if im the one pushing for it"*

Each watch-list entry has:
  - the suspect term pattern
  - validator phrases that, if present in context, justify the term
  - rationale and suggested replacement

Logic:
  - Term hit found
  - Scan ±20 lines for validator phrases
  - If validators ABSENT → high-confidence hallucination → ask (with strong msg)
  - If validators PRESENT → lower-confidence; surface anyway for explicit review

Born from 2026-04-28 COUNTERFACTUALS.md "clawback" → "forfeiture" fix. Once
a term is in a Solidity function name or contract identifier, the 4-byte
selector is permanent. Catching at write-time is the right window.

Fires regardless of who's pushing for the term. Authorship doesn't validate.
"""
import json
import os
import re
import sys

PARTNER_REPO_PATH_PATTERNS = [
    r"[/\\]usd8-cover-score[/\\]",
    r"[/\\]usd8-frontend[/\\]",
    r"[/\\]usd8-boosters-NFT[/\\]",
    r"[/\\]Eridu-internal[/\\]",
]

SKIP_PATH_PATTERNS = [
    r"[/\\]node_modules[/\\]",
    r"[/\\]\.git[/\\]",
    r"[/\\]dist[/\\]",
    r"[/\\]build[/\\]",
    r"[/\\]out-(?:full|ci|deploy)[/\\]",
    r"[/\\]coverage[/\\]",
    r"[/\\]package-lock\.json$",
    r"[/\\]yarn\.lock$",
]

# Each entry implements a handshake-math-determinism check between term and mechanism:
#   pattern    = regex matching the suspect term
#   label      = short name in messages
#   suggest    = recommended replacement
#   why        = rationale
#   required   = list of regexes; ALL must match in context for the term to validate
#                (handshake-math: mechanism must affirmatively confirm what term implies)
#   forbidden  = list of regexes; if ANY match, the context explicitly contradicts
#                the term (definite hallucination — handshake fails on contradiction)
#   strict     = if True, missing required = hallucination flag (default safe choice)
#
# Handshake protocol:
#   - All required present + no forbidden  = handshake completes (term valid)
#   - Any forbidden present                = handshake fails (definite hallucination)
#   - Required missing, no forbidden       = handshake incomplete (likely hallucination if strict)
#   - Mixed signals                        = surfaced for explicit review
WATCH_LIST = [
    {
        "pattern": r"\b(?:auto[-_]?)?clawback[s]?\b",
        "label": "clawback",
        "suggest": "forfeiture (claim-layer) OR explicit fund-recovery primitive",
        "why": "'Clawback' = recovery of already-distributed funds. If the mechanism reduces a CLAIM (score/share/weight) BEFORE payout, the term is forfeiture/score-restatement, not clawback. Term ≠ mechanism = hallucination.",
        "required": [
            r"\b(?:recover|recall|reclaim|claw\s+back)(?:s|ed|ing|y|ies)?\s+(?:of\s+)?(?:already[- ]?)?(?:distributed|paid|disbursed|sent)",
        ],
        "forbidden": [
            r"\bbefore\s+(?:payout|distribution|disbursement)",
            r"\bclaim[- ]?layer\b",
            r"\bscore[- ]?(?:reduction|reduces|decrease|decreases|shrinks)",
            r"\bweight[- ]?(?:reduction|reduces|decrease|decreases)",
            r"\bshare[- ]?(?:shrinks|reduces|decreases)",
            r"\bno\s+(?:money|funds?)\s+(?:are\s+)?(?:recalled|recovered)",
            r"\bnot\s+at\s+the\s+fund[- ]?(?:layer|recovery)",
            r"\bforfeiture\b",  # explicit declaration of what it actually is
        ],
        "strict": True,
    },
    {
        "pattern": r"\bnon[-_]extractive\b|\banti[-_]extraction\b",
        "label": "non-extractive / anti-extraction",
        "suggest": "(reword as structural/methodology claim, not USD8 runtime claim)",
        "why": "Per F·usd8-non-extractive-not-yet-earned: USD8 cannot claim runtime non-extraction yet — needs track record. Math-layer claims about Shapley axioms encoding anti-extraction are fine; USD8-runtime claims are not.",
        "required": [
            r"\b(?:Shapley\s+axiom|methodology\s+layer|math[- ]layer|axioms?\s+encode|structural(?:ly)?\s+encode)",
        ],
        "forbidden": [
            r"\bUSD8\s+is\s+(?:non[- ]?extractive|anti[- ]?extraction)",
            r"\bUSD8\'?s\s+(?:non[- ]?extractive|anti[- ]?extraction)\s+propert",
            r"\bno\s+extraction\s+in\s+USD8",
        ],
        "strict": True,
    },
    {
        "pattern": r"\bcypherpunk\b",
        "label": "cypherpunk",
        "suggest": "cooperative-capitalist / mutual-aid / voluntary-mutualization",
        "why": "In USD8 context, 'cypherpunk' implies censorship-resistance + anti-state stances USD8 has not committed to. Political over-claim.",
        "required": [
            r"\b(?:censorship[- ]?resist|Tim\s+May|cypherpunks?\s+manifesto)",
        ],
        "forbidden": [],
        "strict": True,
    },
    {
        "pattern": r"\bslash(?:ing|ed|es)?\b",
        "label": "slashing",
        "suggest": "forfeiture / weight-disqualification (if no capital destroyed)",
        "why": "'Slashing' implies destruction of staked capital (PoS). If the mechanism reduces score-weight without burning capital, slashing is the wrong term.",
        "required": [
            r"\b(?:validator|stake(?:d|r)?|proof[- ]of[- ]stake|PoS|burn(?:ed|ing)?\s+(?:capital|stake|tokens?))",
        ],
        "forbidden": [
            r"\bno\s+capital\s+(?:is\s+)?(?:destroyed|burned)",
            r"\bweight[- ]?(?:reduction|disqualification)",
            r"\bclaim[- ]?layer",
        ],
        "strict": False,  # slashing is more domain-flexible; less aggressive
    },
    {
        # Governance-authority signature. Per Augmented Governance hierarchy
        # (Physics > Constitution > Governance), governance is NOT free to
        # change math-enforced invariants. Claims like "DAO controls X" /
        # "governance can adjust Y" must specify the bounded scope (which
        # params are tunable) or cite the Physics/Constitution layer that
        # bounds them. Unbounded governance claims = governance-capture
        # marketing, which is the #1 DeFi DAO failure mode.
        "pattern": r"\b(?:DAO\s+(?:controls?|governs?|can\s+(?:change|adjust|set|modify|update)|has\s+(?:full|complete|unlimited|unrestricted|total)\s+(?:control|authority|power))|governance\s+(?:controls?|sets?|determines?|can\s+(?:change|adjust|set|modify|update)|has\s+(?:full|complete|unlimited|unrestricted|total)\s+(?:control|authority|power)))\b",
        "label": "governance-authority overclaim",
        "suggest": "scope-bound (e.g. 'DAO-tunable within Physics-bounded range') OR cite the math-layer that bounds it",
        "why": "Augmented Governance hierarchy: Physics (Shapley invariants) > Constitution (fairness floors) > Governance (free within Physics+Constitution). Unbounded 'DAO controls X' overclaims governance authority and signals governance-capture risk. Required handshake: scope must be specified OR the bounding layer (Physics/Constitution) cited nearby.",
        "required": [
            r"\b(?:within|bounded\s+by|subject\s+to|capped\s+by|constrained\s+by|physics[- ]?(?:layer|bound)|constitutional[- ]?(?:layer|floor|bound)|math[- ]?(?:layer|bound)|invariant)",
        ],
        "forbidden": [
            # Explicit unbounded claims = definite hallucination
            r"\bDAO\s+can\s+(?:change|adjust|set|modify|update)\s+(?:any|everything|all\s+params?)",
            r"\bgovernance\s+(?:has\s+full|has\s+complete|has\s+unlimited|has\s+unrestricted)\s+(?:control|authority|power)",
            r"\bfully\s+governance[- ]?(?:controlled|determined|set)",
        ],
        "strict": True,
    },
]

SCAN_EXTENSIONS = {
    ".sol", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".rs", ".go", ".java", ".kt", ".c", ".cpp", ".h", ".hpp",
    ".md", ".mdx", ".rst", ".txt",
    ".json", ".yaml", ".yml", ".toml",
    ".html", ".vue", ".svelte",
}

CONTEXT_LINES = 20  # lines above and below to scan for validators


def is_partner_path(path):
    return any(re.search(p, path) for p in PARTNER_REPO_PATH_PATTERNS)


def should_skip(path):
    return any(re.search(p, path) for p in SKIP_PATH_PATTERNS)


def has_scannable_extension(path):
    ext = os.path.splitext(path)[1].lower()
    return ext in SCAN_EXTENSIONS


def get_context_window(content_lines, line_no, k=CONTEXT_LINES):
    start = max(0, line_no - 1 - k)
    end = min(len(content_lines), line_no + k)
    return "\n".join(content_lines[start:end])


def any_match(context, patterns):
    return any(re.search(p, context, re.IGNORECASE) for p in patterns)


def handshake_state(context, required, forbidden):
    """Two-party handshake check.
    Returns one of: 'valid', 'contradicted', 'incomplete', 'mixed'.
    """
    forbidden_hit = any_match(context, forbidden) if forbidden else False
    required_all = all(re.search(p, context, re.IGNORECASE) for p in required) if required else True

    if forbidden_hit and required_all:
        return "mixed"
    if forbidden_hit:
        return "contradicted"
    if required_all:
        return "valid"
    return "incomplete"


def scan_content(content, path):
    """Each hit is a dict with: label, suggest, why, line_no, line_text,
    matched, handshake_state, hallucination_flag.
    """
    lines = content.split("\n")
    hits = []
    for entry in WATCH_LIST:
        for match in re.finditer(entry["pattern"], content, re.IGNORECASE):
            line_no = content.count("\n", 0, match.start()) + 1
            line_text = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else ""
            if len(line_text) > 100:
                line_text = line_text[:100] + "..."
            context = get_context_window(lines, line_no)
            state = handshake_state(context, entry.get("required", []), entry.get("forbidden", []))
            # Hallucination flag: definite contradiction OR (strict AND incomplete)
            hallucination = (
                state == "contradicted"
                or (entry.get("strict") and state == "incomplete")
            )
            hits.append({
                "label": entry["label"],
                "suggest": entry["suggest"],
                "why": entry["why"],
                "line_no": line_no,
                "line_text": line_text,
                "matched": match.group(),
                "handshake_state": state,
                "hallucination_flag": hallucination,
            })
    return hits


def scan_path(path):
    """Path-level checks: function names, contract names, file basenames."""
    hits = []
    basename = os.path.basename(path).lower()
    for entry in WATCH_LIST:
        if re.search(entry["pattern"], basename, re.IGNORECASE):
            hits.append({
                "label": entry["label"],
                "suggest": entry["suggest"],
                "why": entry["why"],
                "line_no": 0,
                "line_text": f"file path: {path}",
                "matched": "",
                "validated": False,
                "hallucination_flag": True,
            })
    return hits


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "NotebookEdit"):
        sys.exit(0)

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    if not is_partner_path(file_path):
        sys.exit(0)

    if should_skip(file_path):
        sys.exit(0)

    if not has_scannable_extension(file_path):
        sys.exit(0)

    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")
    else:
        content = ""

    path_hits = scan_path(file_path)
    content_hits = scan_content(content, file_path) if content else []
    all_hits = path_hits + content_hits

    if not all_hits:
        sys.exit(0)

    hallucination_count = sum(1 for h in all_hits if h["hallucination_flag"])

    lines = []
    if hallucination_count > 0:
        lines.append(f"P·anti-hallucination / substance gate: {hallucination_count} likely TERMINOLOGY HALLUCINATION(S) in")
    else:
        lines.append("P·anti-hallucination / substance gate: terminology hits in")
    lines.append(f"  {file_path}")
    lines.append("")

    seen = set()
    for h in all_hits:
        key = (h["label"], h["line_no"])
        if key in seen:
            continue
        seen.add(key)
        loc = f"L{h['line_no']}" if h['line_no'] else "path"
        state = h["handshake_state"]
        if h["hallucination_flag"]:
            if state == "contradicted":
                flag = "✗ HALLUCINATION (context CONTRADICTS term — forbidden attributes present)"
            else:
                flag = "⚠ HALLUCINATION (required validators absent)"
        else:
            if state == "valid":
                flag = "(handshake valid — flagged for explicit review)"
            elif state == "mixed":
                flag = "(mixed handshake — required + forbidden both present, explicit review)"
            else:
                flag = "(handshake state: review)"
        lines.append(f"  [{loc}] '{h['label']}'  {flag}")
        lines.append(f"        line: {h['line_text']}")
        lines.append(f"        suggest: {h['suggest']}")
        lines.append(f"        why: {h['why']}")
        lines.append("")
        if len(seen) >= 8:
            lines.append(f"  ... and {len(all_hits) - 8} more")
            break

    lines += [
        "Anti-hallucination principle: if the term doesn't match the mechanism,",
        "the term is the lie. Fix the term to match the referent before pushing.",
        "Gate fires regardless of authorship — Will's preference for a term",
        "does not validate the term. F·anti-hallucination-fires-on-will-too.",
    ]

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "\n".join(lines),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
