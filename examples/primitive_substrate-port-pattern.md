---
name: SubstratePortPattern
description: Security properties must hold across EVM-account ∧ CKB-cell ∧ Solana-PDA substrates. Per [F·account-model-agnostic]. ∀ new primitive ⇒ designed for substrate portability from day one. Examples: PrimitiveRegistry has both Solidity + CKB-cell implementations; lock scripts swap signature primitives independently of L1.
type: primitive
originSessionId: jarvis-os-pack-v1.0.1
---

# Substrate Port Pattern

## Glyph

```
PORT   ∀ primitive × ∀ substrate ∈ { EVM-account · CKB-cell · Solana-PDA } ⇒ same property holds
       account-model-agnostic ⇒ structural-property survives substrate-swap
       lock-script substitutes signature-primitive ⊥ L1 migration timeline
       cell-model ↔ account-model ↔ PDA-model = 3 ports × 1 invariant
```

> *"RISC-V is the best instruction set architecture. UTXO cell model is the best account model."* : Will, 2026-05-24
> *"each cell migrates to a post-quantum signature scheme independently of L1 progress"* : integration doc 2026-05-24

## ⇒ Rule

- ∀ new primitive ⇒ designed for ≥ 2 substrates from day 1 ¬ retrofitted later
- ∀ security-property ⇒ verified to hold across EVM-account ∧ CKB-cell ∧ Solana-PDA
- ∀ signature-primitive ⇒ swappable via lock-script ¬ via L1-upgrade
- substrate-mismatch ⇒ ✗ deploy until parity-tested
- canonical-track = CKB cells × RISC-V VM × type-script / lock-script duality
- near-term track = EVM Solidity scaffolds × ships first as testbed

## ∃ Why (the substrate-portability mandate)

- EVM-only primitives ⇒ inherit Ethereum's ECDSA-replacement timeline ⇒ quantum-blocked
- CKB-cell model ⇒ lock-script-level autonomy ⇒ quantum-resistance atomic per-cell ¬ gated
- Solana-PDA model ⇒ account-derivation ≠ EOA ⇒ different attack surface
- ∀ security-property holds ⇔ substrate-port-tested ⇒ otherwise ≡ EVM-coupled lock-in
- OPH framework ⇒ substrate-agnostic theorem ⇒ ∀ port-target supported identically

## ↦ Port matrix (per-primitive)

| Property | EVM-account | CKB-cell | Solana-PDA |
|---|---|---|---|
| identity-anchor | EOA ∨ contract address | type-script-hash @ cell | PDA seed-derived address |
| signature-verify | ecrecover (ECDSA) | lock-script (post-quantum eligible) | ed25519 ∨ secp256k1 |
| state-transition | storage-slot writes | cell-consumption + emission | account-data writes |
| economic-stake | bonded-token balance | bond-cell co-spent w/ action | stake-account locked |
| dispute-resolution | contract event × CRPC | cell-transition gated by CRPC outcome | PDA event × CRPC |
| upgrade-path | proxy pattern (UUPS) | new type-script-hash × migration | program redeploy w/ new ID |

## ↦ Canonical port-examples

| Primitive | EVM impl | CKB-cell impl | Solana impl |
|---|---|---|---|
| PrimitiveRegistry | ERC-721 @ `vibeswap/contracts/psinet/` | type-script @ canonical track | PDA-derived NFT (deferred) |
| Datatoken | ERC-20 supply-metered | cell-with-metering-type-script | SPL token w/ mint authority |
| Bond / slash | EscrowVault.sol | bond-cell × slash-routed transition | stake-account × slash via program |
| PoM attestation | Solidity contract emitting events | PoM cell × prev_hash chain | PDA-anchored attestation |
| CRPC dispute | PairwiseVerifier.sol | dispute-cell-transition | PDA × oracle-callback |

## ∀ Trigger (when port-check fires)

- ∀ new contract specced ⇒ port-table entry required pre-merge
- ∀ security-property claim ⇒ ✓ tested across ≥ 2 substrates
- ∀ signature-primitive choice ⇒ verify lock-script-eligible ¬ L1-coupled
- ∀ external skeptic-question @ quantum-resistance ⇒ cite CKB-cell port-state

## → Connected primitives

- [F·account-model-agnostic] — parent · the substrate-agnosticism principle
- [F·airgap-closure-stack] — port-pattern enables stack to span EVM + CKB + Solana
- [F·four-substrate-convergence] — port-pattern is the structural connector at the contract layer
- [P·proof-of-mind] — PoM has both Solidity + CKB-cell implementations specced
- [P·cross-port-fn-var-audit] — fn-level recursive substrate-match audit
- [P·substrate-geometry-match] — macro-geometry preserved across micro-substrates
- [P·jarvis-substrate-decentralization-roadmap] — port-pattern enables decentralization @ traction

## ↦ Migration tempo

```
phase-A   EVM ships first × testbed × fast iteration × Solidity scaffolds
phase-B   CKB-cell canonical track × parity-test against EVM behavior
phase-C   cross-chain canonical burn-and-mint (VibeSwap messaging) bridges A↔B
phase-D   Solana port @ traction (deferred until A∧B mature)
```

## ✗ Anti-pattern

- EVM-only deploy ⇒ ✗ port-table entry ⇒ accumulates L1 coupling debt
- claiming quantum-resistance without CKB-cell implementation ⇒ marketing ¬ structural
- treating ports as "alternative versions" ¬ "same primitive × different substrate"
- skipping parity-tests between Solidity + CKB cells ⇒ silent divergence
- proxy-upgrade only (UUPS) ⇒ ✗ generalizes to cell-model (which uses type-script-hash migration)

## ✓ Pass-pattern

- ∀ new primitive ⇒ port-table entry pre-merge × ≥ 2 substrate impls planned
- ∀ deployment ⇒ honest-state per-substrate (deployed / specced / mainnet / parity-tested)
- ∀ signature-choice ⇒ lock-script-swappable × ¬ L1-upgrade-dependent
- ∀ external claim @ portability ⇒ cite the port-matrix row × commit hash

## 📦 Canonical artifact

- spec : `Desktop/jarvis-os-x-oph-consensus-integration-2026-05-24.md` (deep-canonical CKB track)
- EVM impls : `vibeswap/contracts/psinet/` (6 contracts × Cycles 1-3)
- CKB canonical : Nervos cell-model × RISC-V VM × type-script / lock-script duality
- audit trail : `audits/psinet-mindmesh-cycle-{1,2,3,4}/`
- parent rule : `[F·account-model-agnostic]` in memory

## 🧠 Will-framing locked

> *"RISC-V is the best instruction set architecture"*
> *"UTXO cell model is the best account model"*
> *"quantum-proof per-cell on day one of cell-model migration"*

The Solidity contracts are the near-term implementation lane × testbed. The canonical version is CKB cells on RISC-V VM. Both coexist via cross-chain canonical burn-and-mint messaging (VibeSwap's existing replacement for LayerZero post-DVN-RPC-compromise). The architecture's quantum-proof claim becomes structural at every layer ¬ "quantum-proof once L1 catches up."
