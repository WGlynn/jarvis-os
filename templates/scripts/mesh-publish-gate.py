#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mesh-publish-gate.py — Stage 1 publish gate (PostToolUse)
==========================================================

PostToolUse hook on Write|Edit when the path matches memory/primitive_*.md.
Fires only when the primitive's frontmatter contains `published: true`.

Behavior (per Cycle 2 / Agent E §A — deny-list pipeline):

  1. Parse frontmatter from the just-written primitive.
  2. If `published: true`, load 3-tier deny-list:
       - NDA-Eridu KEYWORDS  (imported from ~/.claude/bin/nda-eridu-gate.py)
       - global ~/.claude/mesh/deny-list.yaml
       - per-primitive `mesh.scrub_extra: [...]`
  3. Scan canonicalized body + frontmatter VALUES (literal + word-boundary).
  4. ON HIT: ABORT publish — emit JSON additionalContext with diff-style
     preview + suggested redactions. Author resolves manually.
     (No auto-scrub: silent edits to published primitives are exactly the
     failure mode this gate exists to prevent.)
  5. ON CLEAN: sign canonicalized markdown with ed25519 key, append entry
     to ~/.claude/mesh/queue/.

HONEST FRAMING: This is a PostToolUse OBSERVATION + signing hook. It does
NOT block the Write — the file is already on disk. What it blocks is the
PUBLISH step (queue append). Author can flip `published: false`, edit the
primitive, or extend `mesh.scrub_extra` and re-save.

Stage 1 scope:
  - Queue-only. mesh-push.sh (Stage 2 fully wired) drains the queue to IPFS
    and emits on-chain `MeshIndex.publish` calls. Agent C cross-dep #3.
  - No IPFS daemon required. Queue persists locally.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ============ Paths ============

MESH_DIR = Path.home() / ".claude" / "mesh"
KEY_PATH = MESH_DIR / "identity" / "ed25519.key"
DID_PATH = MESH_DIR / "identity" / "did.json"
QUEUE_DIR = MESH_DIR / "queue"
GLOBAL_DENY = MESH_DIR / "deny-list.yaml"
NDA_GATE_PATH = Path.home() / ".claude" / "bin" / "nda-eridu-gate.py"

PRIMITIVE_PATH_RE = re.compile(r"memory[/\\]primitive_[^/\\]+\.md$", re.IGNORECASE)


# ============ Frontmatter parsing (no external dep) ============

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML-ish frontmatter parser. Handles flat keys + simple lists.
    Sufficient for primitive frontmatter; falls back to {} on anything weird."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    fm: dict = {}
    current_list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # list continuation
        if current_list_key and line.startswith("  - "):
            fm.setdefault(current_list_key, []).append(line[4:].strip().strip('"').strip("'"))
            continue
        current_list_key = None
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip()
            if not v:
                current_list_key = k  # next lines may be a list
                fm[k] = []
            elif v.lower() in ("true", "false"):
                fm[k] = v.lower() == "true"
            else:
                fm[k] = v.strip('"').strip("'")
    return fm, body


def is_published(fm: dict) -> bool:
    # supports flat `published: true` and nested `mesh.published`
    if fm.get("published") is True:
        return True
    # primitive nested form: `mesh:` followed by `  published: true`
    # (our minimal parser flattens to dotted keys when seen at top level)
    return False


def get_scrub_extra(fm: dict) -> list[str]:
    val = fm.get("mesh.scrub_extra") or fm.get("scrub_extra") or []
    if isinstance(val, list):
        return [str(x) for x in val if x]
    return []


# ============ Deny-list loading ============

def load_nda_keywords() -> list[str]:
    """Import KEYWORDS from nda-eridu-gate.py to keep tiers in sync.
    Per Agent E: adding a term to nda-eridu-gate updates both gates atomically.
    """
    if not NDA_GATE_PATH.exists():
        return []
    try:
        spec = importlib.util.spec_from_file_location("nda_eridu_gate", NDA_GATE_PATH)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return list(getattr(mod, "KEYWORDS", []))
    except Exception:
        return []


def load_global_deny() -> list[str]:
    """Read ~/.claude/mesh/deny-list.yaml. Minimal parser: one term per line
    under a `terms:` key, or top-level `- term`. Comments stripped."""
    if not GLOBAL_DENY.exists():
        return []
    terms: list[str] = []
    try:
        for line in GLOBAL_DENY.read_text(encoding="utf-8").splitlines():
            s = line.split("#", 1)[0].strip()
            if not s or s.endswith(":"):
                continue
            if s.startswith("- "):
                terms.append(s[2:].strip().strip('"').strip("'"))
        return [t for t in terms if t]
    except Exception:
        return []


# ============ Scan ============

def scan_hits(content: str, terms: list[str]) -> list[tuple[str, int]]:
    """Literal + word-boundary match per Agent E recommendation. Returns
    list of (term, line_number) tuples."""
    hits: list[tuple[str, int]] = []
    for term in terms:
        if not term:
            continue
        # word-boundary literal match; case-insensitive
        try:
            pat = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        except re.error:
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if pat.search(line):
                hits.append((term, i))
    return hits


def render_diff_preview(content: str, hits: list[tuple[str, int]]) -> str:
    """Build a diff-style preview suggesting redactions. Per Agent E:
    `Tom` -> `[partner-A]`, `Bernhard` -> `[partner-B]`. We render a generic
    suggestion; the author picks the actual redaction tag."""
    lines = content.splitlines()
    seen_lines: set[int] = set()
    out: list[str] = []
    for term, lineno in hits[:20]:  # cap preview at 20 hits
        if lineno in seen_lines:
            continue
        seen_lines.add(lineno)
        if 1 <= lineno <= len(lines):
            orig = lines[lineno - 1]
            redacted = re.sub(
                r"\b" + re.escape(term) + r"\b",
                f"[REDACTED:{term[:3].upper()}]",
                orig,
                flags=re.IGNORECASE,
            )
            out.append(f"  L{lineno}: term='{term}'")
            out.append(f"    - {orig.strip()[:140]}")
            out.append(f"    + {redacted.strip()[:140]}")
    return "\n".join(out) if out else "  (no preview available)"


# ============ Signing + queue ============

def sign_and_enqueue(primitive_path: Path, canonical: str) -> dict | None:
    """Sign canonical markdown with ed25519 key, write queue entry. Returns
    queue entry on success, None on failure (e.g. mesh not initialized)."""
    if not KEY_PATH.exists() or not DID_PATH.exists():
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError:
        return None
    try:
        sk = Ed25519PrivateKey.from_private_bytes(KEY_PATH.read_bytes())
        sig = sk.sign(canonical.encode("utf-8")).hex()
        did = json.loads(DID_PATH.read_text(encoding="utf-8")).get("did", "")
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        entry = {
            "primitive_id": primitive_path.stem,
            "primitive_path": str(primitive_path),
            "content_hash": content_hash,
            "signature_hex": sig,
            "did": did,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": 1,
            # Stage 2 fields (Agent C cross-dep #3): cid, mesh_index_tx
        }
        out_file = QUEUE_DIR / f"{content_hash[:16]}.json"
        out_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        return entry
    except Exception:
        return None


# ============ Main ============

def emit(ctx: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ctx,
        }
    }, ensure_ascii=False))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return 0

    if payload.get("tool_name") not in ("Write", "Edit"):
        print(json.dumps({}))
        return 0

    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path or not PRIMITIVE_PATH_RE.search(path):
        print(json.dumps({}))
        return 0

    try:
        content = Path(path).read_text(encoding="utf-8")
    except Exception:
        print(json.dumps({}))
        return 0

    fm, body = parse_frontmatter(content)
    if not is_published(fm):
        print(json.dumps({}))
        return 0

    # Build the 3-tier deny-list
    nda_terms = load_nda_keywords()
    global_terms = load_global_deny()
    extra_terms = get_scrub_extra(fm)
    all_terms = nda_terms + global_terms + extra_terms

    # Scan canonicalized body + frontmatter VALUES (not keys)
    scan_text = body + "\n" + "\n".join(str(v) for v in fm.values())
    hits = scan_hits(scan_text, all_terms)

    if hits:
        preview = render_diff_preview(scan_text, hits)
        unique_terms = sorted({t for t, _ in hits})
        emit(
            f"[MESH PUBLISH GATE] ABORT — deny-list hit on `published: true` primitive.\n"
            f"File: {path}\n"
            f"Hits: {len(hits)} across {len(unique_terms)} term(s): {', '.join(unique_terms)}\n\n"
            f"Diff-style preview (suggested redactions):\n{preview}\n\n"
            f"Resolution options:\n"
            f"  1. Edit primitive to remove/rephrase the flagged terms.\n"
            f"  2. Add a partner alias to mesh.scrub_extra and re-run.\n"
            f"  3. Flip `published: false` to keep this primitive local-only.\n\n"
            f"No auto-scrub by design (Agent E §A). Queue entry NOT written."
        )
        return 0

    # Clean — sign and enqueue
    entry = sign_and_enqueue(Path(path), body)
    if entry is None:
        emit(
            f"[MESH PUBLISH GATE] Deny-list clean, but mesh identity not initialized.\n"
            f"Run: python ~/.claude/scripts/mesh-init.py\n"
            f"File: {path}"
        )
        return 0

    emit(
        f"[MESH PUBLISH GATE] Clean. Queued for publish.\n"
        f"  primitive: {entry['primitive_id']}\n"
        f"  hash:      {entry['content_hash'][:16]}...\n"
        f"  did:       {entry['did'][:40]}...\n"
        f"  queue:     ~/.claude/mesh/queue/{entry['content_hash'][:16]}.json\n"
        f"(Stage 1: queue-only. Stage 2 mesh-push.sh drains to IPFS + MeshIndex.)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
