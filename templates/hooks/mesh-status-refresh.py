#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mesh-status-refresh.py — Stage 1 SessionStart status writer
============================================================

SessionStart hook. Refreshes ~/.claude/mesh/status.json with mesh state
that the boot-screen MESH panel consumes.

Status fields (Stage 1):
  did                       8-char short DID for boot panel
  peers_known               static peer count from peers.yaml
  peers_active_24h          peers with cache writes in last 24h (proxy for sync)
  published_primitives      local primitive count with `published: true`
  subscribed_topics         tag count under ~/.claude/mesh/cache/
  last_sync                 newest cache mtime, ISO8601
  queue_depth               pending publishes in ~/.claude/mesh/queue/
  stage                     1
  generated_at              ISO8601

Stage 2 will add (per Agent E §B):
  revoked_count             from cache/revoked.jsonl
  on_chain_synced           bool, MeshIndex event subscription healthy

Hook contract: emits empty JSON to stdout — the boot-screen hook reads
status.json directly. No additionalContext payload from this script.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MESH_DIR = Path.home() / ".claude" / "mesh"
DID_PATH = MESH_DIR / "identity" / "did.json"
PEERS_PATH = MESH_DIR / "peers.yaml"
CACHE_DIR = MESH_DIR / "cache"
QUEUE_DIR = MESH_DIR / "queue"
STATUS_PATH = MESH_DIR / "status.json"

# We deliberately do NOT hardcode the primitive memory dir here — boot-screen
# resolves it via {{PROJECT_DIR}}. For published-count we scan the standard
# memory tree directly.
MEMORY_GLOB = "primitive_*.md"
PUBLISHED_RE = re.compile(r"^\s*published\s*:\s*true\s*$", re.IGNORECASE | re.MULTILINE)


def count_peers() -> int:
    """Count `- did:` or `- endpoint:` list entries under `peers:`."""
    if not PEERS_PATH.exists():
        return 0
    try:
        text = PEERS_PATH.read_text(encoding="utf-8")
    except Exception:
        return 0
    n = 0
    in_peers = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.strip() == "peers:":
            in_peers = True
            continue
        if in_peers and line.lstrip().startswith("- ") and "example" not in line.lower():
            n += 1
    return n


def count_active_peers_24h() -> int:
    """Count distinct source_dids that appear in cache entries < 24h old."""
    if not CACHE_DIR.exists():
        return 0
    cutoff = time.time() - 86400
    dids: set[str] = set()
    try:
        for f in CACHE_DIR.rglob("*.json"):
            try:
                if f.stat().st_mtime < cutoff:
                    continue
                rec = json.loads(f.read_text(encoding="utf-8"))
                did = rec.get("source_did")
                if did:
                    dids.add(did)
            except Exception:
                continue
    except Exception:
        return 0
    return len(dids)


def count_published_primitives() -> int:
    """Scan ~/.claude/projects/**/memory/primitive_*.md for `published: true`."""
    root = Path.home() / ".claude" / "projects"
    if not root.exists():
        return 0
    n = 0
    try:
        for p in root.rglob(MEMORY_GLOB):
            try:
                if PUBLISHED_RE.search(p.read_text(encoding="utf-8")):
                    n += 1
            except Exception:
                continue
    except Exception:
        return 0
    return n


def count_subscribed_topics() -> int:
    if not CACHE_DIR.exists():
        return 0
    try:
        return sum(1 for d in CACHE_DIR.iterdir() if d.is_dir())
    except Exception:
        return 0


def last_sync_iso() -> str | None:
    if not CACHE_DIR.exists():
        return None
    try:
        mtimes = [p.stat().st_mtime for p in CACHE_DIR.rglob("*.json")]
        if not mtimes:
            return None
        return datetime.fromtimestamp(max(mtimes), tz=timezone.utc).isoformat()
    except Exception:
        return None


def count_queue() -> int:
    if not QUEUE_DIR.exists():
        return 0
    try:
        return sum(1 for _ in QUEUE_DIR.glob("*.json"))
    except Exception:
        return 0


def short_did() -> str | None:
    if not DID_PATH.exists():
        return None
    try:
        doc = json.loads(DID_PATH.read_text(encoding="utf-8"))
        did = doc.get("did", "")
        # did:key:z6Mk{rest} -> z6Mk + first 4 of rest = 8 chars after did:key:
        m = re.match(r"did:key:(z6Mk[0-9A-Za-z]{4})", did)
        if m:
            return m.group(1)
        return did[-8:] if did else None
    except Exception:
        return None


def build_status() -> dict:
    return {
        "stage": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "did_short": short_did(),
        "peers_known": count_peers(),
        "peers_active_24h": count_active_peers_24h(),
        "published_primitives": count_published_primitives(),
        "subscribed_topics": count_subscribed_topics(),
        "last_sync": last_sync_iso(),
        "queue_depth": count_queue(),
    }


def main() -> int:
    try:
        _ = json.load(sys.stdin)
    except Exception:
        pass

    # If mesh dir absent entirely, do not write status — boot screen
    # interprets missing file as "MESH OFFLINE".
    if not MESH_DIR.exists():
        print(json.dumps({}))
        return 0

    try:
        status = build_status()
        MESH_DIR.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    except Exception:
        # Best-effort; never block session start.
        pass

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
