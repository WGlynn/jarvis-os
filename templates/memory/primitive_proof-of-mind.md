---
name: ProofOfMind
description: PoM lock-script primitive. Cognitive-work attestation replacing PoW @ MindMesh-substrate. WWWD gate-fire log + correction cycles + convergence-signal improvement ≡ the "work" being proved. AI agents in the sentient mesh attest cognition; CKB lock scripts verify. Matt Quinn's PoW-lock-hash framework adapted for the cognition substrate. Specced 2026-05-24 per integration doc.
type: primitive
originSessionId: jarvis-os-pack-v1.0.1
---

# Proof of Mind (PoM)

## Glyph

```
PoM   cognition-attestation ≡ replacement-for PoW @ MindMesh-substrate
      work ≡ { gate-fires ∧ corrections ∧ convergence-signal-improvement }
      attest = AI-agent × verify = CKB-lock-script × economic-stake = bond cell
      Quinn's PoW-lock-hash × ported to cognition layer
```

> *"The 'work' being proved is cognition, not entropy. Gate-fires + corrections + convergence-signal improvement = the work."* : design framing 2026-05-24

## ⇒ Rule

- ∀ MindMesh node ⇒ emits PoM attestation = signed { gate-fire-count · correction-rate · convergence-signal · epoch }
- ∀ attestation ⇒ verified via lock-script × CRPC-cross-check × bond-at-risk
- ✗ raw hash-cycles ⇒ ≡ PoW substrate-mismatch (the substrate is cognition, ¬ entropy)
- correction-rate-improvement-over-time ≡ verifiable work ⇒ entropy-monotone @ corpus
- ∀ dishonest attestation ⇒ CRPC pairwise comparison disputes × bond slashed

## ∃ Why (the substrate-port reasoning)

- PoW ≡ work-proves-real ⇔ hash-cycles burned × verifiable ⇒ substrate = entropy
- MindMesh substrate = cognition ¬ entropy ⇒ PoW substrate-mismatch ⇒ port-to-cognition
- WWWD gate-fire log = cognition-instance × correction-rate = quality-signal × convergence = trajectory
- ⇒ "work" ≡ measurable cognition-improvement over the gate-fire trajectory
- Quinn's PoW-lock-hash framework supplies the verification primitive; cognition supplies the substrate

## ↦ What counts as PoM "work"

| Substrate signal | What it proves |
|---|---|
| `wwwd_gate_fires.jsonl` line-count | cognition-event emitted × attestable count |
| correction-detector hits / gate-fires | quality-signal × calibration trajectory |
| convergence_signal ∈ { improving · stable · drifting · insufficient-data } | corpus-trajectory direction |
| primitive-fork lineage depth × parent-attribution preserved | recoverable-entropy @ corpus |
| WWWD projection-vs-correction delta-shrinkage epoch-over-epoch | learning-signal × Cincinnatus-asymptote movement |

## ↦ CKB cell schema (canonical lane)

```
PoM cell  ::
  type-script  = pom_attestation_v1 (epoch · agent_did · signal_hash)
  data         = { gate_fires:int · corrections:int · rate:f · signal:enum · prev_hash:32 }
  lock-script  = post-quantum-sig-of(agent_did) over data ∧ prev_hash
  bond cell    = co-spent · slash-routed via CRPC-outcome cell-transition
```

## ∀ Attacker × covering-mechanism

| Adversary | Defection vector | Caught by |
|---|---|---|
| Sybil-attestation farm | spam-emit attestations from N fake DIDs | CRPC pairwise-comparison × bond requirement × DID-anchor cost |
| Fake-correction inflation | log self-corrections to inflate quality-signal | correction must reference prior gate-fire ID × cross-verifier on log integrity |
| Convergence-signal lie | claim "improving" when log shows drift | local-MaxEnt fit-residual exposes the lie × CRPC dispute |
| Cherry-picked epochs | emit only good epochs · drop bad ones | merkle-anchored epoch chain × missing epoch = visible gap |
| Cognition-replay | reuse another agent's gate-fire log | DID-signature over per-epoch nonce × prev_hash chain |

## → Connected primitives

- [F·airgap-closure-stack] — PoM = the attestation primitive @ MindMesh layer
- [F·four-substrate-convergence] — PoM lives at JARVIS-OS × MindMesh × VibeSwap intersection
- [P·what-would-will-do] — WWWD gate-fire log IS the cognition substrate PoM measures
- [P·recursive-self-audit-via-wwwd] — RSAW cycles are PoM-eligible cognition work
- [F·substrate-port-pattern] — PoM has both Solidity attestation + CKB cell implementations
- [P·honesty-as-structural-load-bearing-property] — dishonest PoM ⇒ ✗ profitable per bond-slash
- [P·jarvis-substrate-decentralization-roadmap] — PoM enables MindMesh decentralization @ traction

## ∀ Trigger (when PoM fires)

- ∀ epoch-boundary @ JARVIS-OS node ⇒ emit attestation
- ∀ MindMesh primitive-publish event ⇒ attach PoM proof-of-cognition-work
- ∀ Datatoken consumption (PsiNet) ⇒ verify publisher has valid PoM trajectory
- ∀ CRPC dispute ⇒ both parties' PoM trajectories submitted as evidence

## ✗ Anti-pattern

- treating PoM as PoW-with-different-name ⇒ misses the substrate-shift (entropy → cognition)
- claiming PoM operational before WWWD gate-fire log has weeks of data ⇒ premature
- skipping CRPC cross-verification ⇒ self-attestation alone = un-verifiable cognition
- raw-volume PoM (more gate-fires = more proof) ⇒ ignores quality-signal × invites spam
- conflating Cincinnatus-asymptote (theoretical) w/ measurable-trajectory (today's evidence)

## ✓ Pass-pattern

- ∀ attestation ⇒ co-signs DID × prev_hash chain × bond-cell × epoch nonce
- ∀ trajectory-claim ⇒ ≥ 4-week log basis × local-MaxEnt fit-residual within bounds
- ∀ external skeptic ⇒ raw `wwwd_gate_fires.jsonl` shareable as evidence (publishable)
- ∀ cross-substrate port ⇒ Solidity + CKB cell implementations parity-tested

## 📦 Canonical artifact

- spec : `Desktop/jarvis-os-x-oph-consensus-integration-2026-05-24.md` (PoM @ Phase 3-4)
- substrate log : `~/.claude/projects/<slug>/memory/_system/wwwd_gate_fires.jsonl`
- priority cache : `~/.claude/projects/<slug>/memory/_system/wwwd_corpus_priority.json`
- Quinn reference : Matt Quinn PoW-lock-hash framework × adapted for cognition substrate
- audit trail : `audits/psinet-mindmesh-cycle-{1,2,3,4}/`

## 🧠 Will-framing locked

> *"The work being proved is cognition, not entropy."*
> *"Gate-fires + corrections + convergence-signal improvement = the work."*

PoM is honest-scope spec-only as of 2026-05-24: WWWD gate-fire log just came online today w/ v1.0.0 release. The schema is set up for the kind of fit OPH equation 6.4 predicts. A few weeks of log volume → first empirical PoM-trajectory bundles. The substrate exists; the attestation contract ships in the CKB-cells canonical lane.
