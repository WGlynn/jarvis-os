#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mesh-pull.py — Stage 1 discovery + cache
=========================================

CLI: mesh-pull.py {tag} [--since ISO8601] [--peers PATH] [--cache PATH]

Stage 1 mechanism (per Agent C §"Discovery + consumption"):
  - Read static peer list from ~/.claude/mesh/peers.yaml
  - For each peer, GET their published-primitive index over HTTP(S):
       {peer.endpoint}/published-index.json
       optional ?tag={tag}&since={iso}
  - Cache results to ~/.claude/mesh/cache/{tag}/{primitive_id}.json
  - TTL 1 hour optimistic consistency

NO IPFS dependency: peers may be either IPFS gateways or simple HTTPS hosts
that publish a flat index. Stage 2 tightens consistency via MeshIndex events
(Agent C cross-dep #3, gated on PsiNet deploy).

Stage 1 limitations (honest):
  - No signature verification of peer indices yet. Stage 2: verify each entry
    against the peer DID + ed25519 public key. (Agent A cross-dep.)
  - No revocation check. Stage 2: consult ~/.claude/mesh/cache/revoked.jsonl
    populated by mesh-status-refresh.py from on-chain `PrimitiveRevoked`
    events. (Agent E §B cross-dep.)
  - Static YAML doesn't scale past ~10 peers. Bridge: well-known DNS list.
    Permanent: PsiNet MeshIndex / DHT. (Agent C cross-dep #5.)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MESH_DIR = Path.home() / ".claude" / "mesh"
PEERS_PATH = MESH_DIR / "peers.yaml"
CACHE_DIR = MESH_DIR / "cache"
TTL_SECONDS = 3600  # 1 hour optimistic eventual consistency


def load_peers(path: Path) -> list[dict]:
    """Minimal YAML-ish parser. Expects a top-level `peers:` list of dicts
    with `did:` and `endpoint:` keys. Anything weirder -> []."""
    if not path.exists():
        return []
    peers: list[dict] = []
    current: dict | None = None
    in_peers = False
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if line.strip() == "peers:":
                in_peers = True
                continue
            if not in_peers:
                continue
            stripped = line.lstrip()
            if stripped.startswith("- "):
                if current:
                    peers.append(current)
                current = {}
                stripped = stripped[2:]
                if ":" in stripped:
                    k, _, v = stripped.partition(":")
                    current[k.strip()] = v.strip().strip('"').strip("'")
            elif ":" in stripped and current is not None:
                k, _, v = stripped.partition(":")
                current[k.strip()] = v.strip().strip('"').strip("'")
        if current:
            peers.append(current)
    except Exception:
        return []
    # filter placeholder example peers
    return [p for p in peers if p.get("endpoint") and "example" not in p.get("endpoint", "")]


def fetch_peer_index(peer: dict, tag: str, since: str | None) -> list[dict]:
    """GET {endpoint}/published-index.json[?tag=...&since=...].
    Returns a list of primitive entries. Empty on any failure (graceful)."""
    endpoint = peer.get("endpoint", "").rstrip("/")
    if not endpoint:
        return []
    qs = {"tag": tag}
    if since:
        qs["since"] = since
    url = f"{endpoint}/published-index.json?{urllib.parse.urlencode(qs)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jarvis-os-mesh-pull/1"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict):
            data = data.get("primitives") or data.get("entries") or []
        if not isinstance(data, list):
            return []
        return data
    except Exception as e:
        sys.stderr.write(f"mesh-pull: peer {peer.get('did', '?')[:40]} unreachable ({e})\n")
        return []


def cache_path(tag: str, primitive_id: str) -> Path:
    return CACHE_DIR / tag / f"{primitive_id}.json"


def is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        age = time.time() - path.stat().st_mtime
        return age < TTL_SECONDS
    except Exception:
        return False


def write_cache(tag: str, entries: list[dict], source_did: str) -> int:
    n = 0
    for entry in entries:
        pid = entry.get("primitive_id")
        if not pid:
            continue
        out = cache_path(tag, pid)
        out.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "primitive_id": pid,
            "source_did": source_did,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "tag": tag,
            "entry": entry,
            "stage": 1,
            # Stage 2: signature_verified (bool), revoked (bool)
        }
        out.write_text(json.dumps(record, indent=2), encoding="utf-8")
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 1 MindMesh discovery + cache")
    ap.add_argument("tag", help="primitive tag to pull (e.g. wwwd, hiero, airgap)")
    ap.add_argument("--since", default=None, help="ISO8601 timestamp")
    ap.add_argument("--peers", default=str(PEERS_PATH))
    ap.add_argument("--cache", default=str(CACHE_DIR))
    ap.add_argument("--force", action="store_true", help="ignore TTL")
    args = ap.parse_args()

    peers = load_peers(Path(args.peers))
    if not peers:
        print(
            f"mesh-pull: no peers configured in {args.peers}\n"
            f"  (Stage 1: copy peers.example.yaml -> peers.yaml and add a peer.)"
        )
        return 0

    # TTL check on the tag's cache dir
    tag_dir = Path(args.cache) / args.tag
    if not args.force and tag_dir.exists():
        try:
            newest = max((p.stat().st_mtime for p in tag_dir.glob("*.json")), default=0)
            if newest and (time.time() - newest) < TTL_SECONDS:
                age_min = int((time.time() - newest) / 60)
                print(f"mesh-pull: cache fresh for tag '{args.tag}' (age {age_min}m, TTL 60m). "
                      f"Use --force to refresh.")
                return 0
        except Exception:
            pass

    total = 0
    for peer in peers:
        entries = fetch_peer_index(peer, args.tag, args.since)
        n = write_cache(args.tag, entries, peer.get("did", "unknown"))
        if n:
            print(f"mesh-pull: {peer.get('did', '?')[:30]}... -> {n} entries (tag={args.tag})")
        total += n

    if total == 0:
        print(f"mesh-pull: 0 entries fetched for tag '{args.tag}' across {len(peers)} peer(s).")
        print(f"  (Stage 1 honesty: mesh is empty until peers come online. This is expected.)")
    else:
        print(f"mesh-pull: cached {total} entries for tag '{args.tag}' across {len(peers)} peer(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
