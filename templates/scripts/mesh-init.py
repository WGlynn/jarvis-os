#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mesh-init.py — Stage 1 MindMesh identity bootstrap
===================================================

Generates an ed25519 keypair, writes the private key (chmod 600) and a
W3C-compliant did:key document to ~/.claude/mesh/identity/.

Idempotent: if identity already exists, prints the current DID and exits 0
without overwriting. Re-keying is handled by mesh-rotate.py (Cycle 2 spec,
Agent E §C) — NOT this script.

Stage 1 scope:
  - Local-only DID generation. No registry binding.
  - No on-chain operations. Agent A's ERC-8004 IdentityRegistry binding is
    deferred to Stage 2 (Agent C cross-dep #1).

Output paths:
  ~/.claude/mesh/identity/ed25519.key      private key, raw 32-byte, mode 600
  ~/.claude/mesh/identity/did.json         {did, public_key_multibase, created}

Reference: did:key spec (https://w3c-ccg.github.io/did-method-key/).
We use the ed25519-pub multicodec prefix (0xed 0x01) + base58btc 'z' multibase.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from cryptography.hazmat.primitives import serialization
except ImportError:
    sys.stderr.write(
        "mesh-init: missing dependency 'cryptography'. Install with:\n"
        "  pip install cryptography\n"
    )
    sys.exit(1)


MESH_DIR = Path.home() / ".claude" / "mesh"
ID_DIR = MESH_DIR / "identity"
KEY_PATH = ID_DIR / "ed25519.key"
DID_PATH = ID_DIR / "did.json"

# multicodec prefix for ed25519-pub: 0xed 0x01
ED25519_PUB_MULTICODEC = b"\xed\x01"

# base58btc alphabet (Bitcoin/IPFS variant)
B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(data: bytes) -> str:
    """Minimal base58btc encoder — no external dep."""
    n = int.from_bytes(data, "big")
    out = bytearray()
    while n > 0:
        n, r = divmod(n, 58)
        out.append(B58_ALPHABET[r])
    # preserve leading zero bytes as '1'
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return (b"1" * pad + bytes(reversed(out))).decode("ascii")


def public_key_to_did_key(pub_bytes: bytes) -> tuple[str, str]:
    """Convert raw ed25519 public key to (did:key:..., multibase encoding)."""
    payload = ED25519_PUB_MULTICODEC + pub_bytes
    multibase = "z" + b58encode(payload)
    return f"did:key:{multibase}", multibase


def load_existing() -> dict | None:
    if not DID_PATH.exists():
        return None
    try:
        return json.loads(DID_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def init_identity() -> dict:
    ID_DIR.mkdir(parents=True, exist_ok=True)

    sk = Ed25519PrivateKey.generate()
    sk_bytes = sk.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pk_bytes = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    did, multibase = public_key_to_did_key(pk_bytes)

    KEY_PATH.write_bytes(sk_bytes)
    # chmod 600 — best effort on Windows (NTFS will partially honor)
    try:
        os.chmod(KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass

    did_doc = {
        "did": did,
        "public_key_multibase": multibase,
        "key_type": "Ed25519VerificationKey2020",
        "created": datetime.now(timezone.utc).isoformat(),
        "stage": 1,
        "registry_binding": None,  # Stage 2: ERC-8004 tokenId here
    }
    DID_PATH.write_text(json.dumps(did_doc, indent=2), encoding="utf-8")
    return did_doc


def main() -> int:
    existing = load_existing()
    if existing and KEY_PATH.exists():
        print(f"mesh-init: identity already present — {existing.get('did')}")
        print(f"  key:  {KEY_PATH}")
        print(f"  doc:  {DID_PATH}")
        print("  (re-key via mesh-rotate.py, do NOT delete the key file)")
        return 0

    doc = init_identity()
    print("mesh-init: generated Stage-1 identity")
    print(f"  did:  {doc['did']}")
    print(f"  key:  {KEY_PATH}  (mode 600)")
    print(f"  doc:  {DID_PATH}")
    print()
    print("Next: copy peers.example.yaml -> peers.yaml and add at least one peer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
