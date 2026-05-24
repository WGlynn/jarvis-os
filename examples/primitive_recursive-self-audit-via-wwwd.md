---
name: RecursiveSelfAuditViaWWWD
description: RSAW meta-process. Apply TRP/RSI audit methodology to JARVIS's own protocol stack using WWWD as the orchestration gate. 3-agent parallel cycles × N-lens coverage × honest-finding rubric × immediate-fix loop. Dogfooded 2026-05-24 on V3 spec; produced 15 real findings in 12 minutes, all → fixes, zero theater. Formalized when the dogfooding test passed.
type: primitive
originSessionId: a56046e0-1348-478f-9334-ecd5877892aa
---

# RSAW : Recursive Self-Audit via WWWD

## Glyph

```
RSAW   WWWD-orchestrated TRP/RSI × applied to JARVIS-own-stack.
       3 parallel sonnet agents × N-lens × honest-rubric × immediate-fix.
       methodology survives ⇔ it produces real findings against itself.
```

> *"OK now we start full autopilot run L3 to RSI TRP audit cycle the entire protocol stack. if succesful, formalize it as a meta procress"* : Will, 2026-05-24

## ⇒ Rule

- ∀ JARVIS substrate-layer doc ⇒ RSAW eligible
- WWWD orchestrates ⇒ each agent's lens-set is Will-projection-aware (severity-calibration, no-theater, claim-needs-structural-enforcer applied recursively)
- 3 parallel sonnet agents × non-overlapping scopes ⇒ baseline coverage
- finding ⇒ immediate-fix-if-concrete ∨ queued-design-pass-if-architectural
- methodology survives ⇔ dogfooding finds real things AGAINST the spec that defines it

## ∃ Why (the dogfooding test)

- 2026-05-24 V3 spec shipped to three repos at 10:40 ET
- RSAW dispatched at 10:50 ET against the just-shipped spec
- 12 minutes later: 15 findings (2 High × 2, 4 Medium × 4, 2 Low × 2, 1 Info × 1)
- Findings included AA#1 violations (NCI mainnet overclaim), AA#2 violations (convergence asymptote claimed measurable while log unbuilt), file-count drift (12 vs claimed 14; 134 vs claimed 297), and underspecified components (corpus enumeration, log schema, correction write-back)
- All 15 findings produced fixes. Spec strengthened against its own anti-overclaim standard.
- Cincinnatus-property test: the methodology that audits other people's contracts works on our own protocol. If it had not, V3 would have been claimed-but-not-true.

## ↦ How to apply (5-phase RSAW cycle)

### Phase 1: Brief
- Write `audits/<target>/AUDIT_BRIEF.md` with:
  - In-scope artifacts (canonical + mirrors + supporting specs + implementations + memory)
  - Lens set (drawn from SEVEN_AUDIT_PASSES + target-specific + WWWD-recursion checks)
  - Severity rubric (Critical / High / Medium / Low / Informational)
  - Finding format (Vulnerability, Failure Vector, Impact, Evidence, Suggested Fix, Cross-reference)
  - Meta-process question (did the methodology produce real findings?)

### Phase 2: Parallel dispatch
- 3 concurrent sonnet agents, non-overlapping lens-scopes
- Each agent reads AUDIT_BRIEF.md first
- Each agent has SEPARATE finding-file prefix (`c<N>a-`, `c<N>b-`, `c<N>c-`)
- WWWD orchestration: each agent's prompt encodes Will-projection-aware lenses (no-theater, claim-needs-structural-enforcer, severity-honesty)

### Phase 2.5: Active orchestration during dispatch (NEVER IDLE)
- Per `feedback_autonomous-production-default` — continue-producing is default, idle is failure
- While agents run async in background, the orchestrator does NON-OVERLAPPING productive work:
  - Build/refine artifacts the spec-under-audit describes but doesn't ship (e.g., for V3 self-audit Cycle 2, the orchestrator built wwwd-gate.py + wwwd-correction-detector.py + wwwd-corpus-refresh.py prototypes from the spec, converting 3 of the 5 spec-only items to spec-and-prototype)
  - Pre-stage the next cycle's brief
  - Update SESSION_STATE.md with current arc summary
  - Prep commit messages for the imminent fix-pass
  - Watch for in-flight issues that need human-in-loop (without polling the agent transcripts — the gate forbids that, but the findings-dir is fine to observe)
- The orchestrator MUST NOT:
  - Read the same files the dispatched agents are reading (creates work-duplication signal noise)
  - Modify the artifacts under audit (would invalidate the agents' findings against a moving target)
  - Idle by saying "awaiting completion" — that's the failure mode this phase exists to prevent
- This phase ends when ALL dispatched agents complete. Output from this phase IS substrate progress, not waste.

### Phase 3: Finding ingestion
- As each agent returns, ingest findings
- Categorize: concrete-fix (apply now) vs architectural-fix (queue for design pass) vs already-known
- DON'T batch all fixes to end — ship concrete fixes during the cycle so cycle 2 audits the corrected spec

### Phase 4: Fix + mirror + commit
- Apply fixes to canonical doc
- Mirror per `feedback_substrate-mirror-into-project-repos` (identical text, same loop turn, dual-push)
- Commit each repo with the audit's specific finding-IDs in the commit message
- This is the loop-closure: audit → fix → ship → audit-next

**Mirror paths by target-class (Cycle 2B fix):**

| Target class | Canonical | Mirror 1 | Mirror 2 |
|---|---|---|---|
| V3 stack doc | `~/JARVIS/05-meta-protocols/<name>.md` | `vibeswap/docs/jarvis-substrate/papers/<name>.md` | `jarvis-network/` (selectively, for runtime-relevant docs) |
| WWWD spec | `vibeswap/docs/jarvis-substrate/papers/v3-wwwd-protocol.md` | (no further mirrors; lives in vibeswap) | — |
| Memory primitive | `memory/primitive_<slug>.md` | (memory repo only; not cross-mirrored) | — |
| Hook source | `~/.claude/hooks/<name>.py` | `memory/_system/session_chain_mirror/<name>.py` (versioned mirror) | — |
| HIERO format | `memory/reference_hiero-dictionary.md` + `memory/primitive_hiero-no-prose-in-memory.md` | `Desktop/usd8-rick-hiero-compression-share-*.md` (external share) | — |
| MEMORY.md index | `memory/MEMORY.md` | (memory repo only) | — |

**Fix-bucket criterion (concrete vs architectural) (Cycle 2B fix):**

A finding is CONCRETE if its fix is a string-substitution, a number correction, a missing-citation addition, or a file-existence verification. Apply concrete fixes IN THE SAME CYCLE.

A finding is ARCHITECTURAL if its fix requires a design decision, a new component, or a structural choice that has multiple Will-defensible answers. Queue architectural fixes for an explicit design pass; do NOT silently choose one of the answers.

Default rule when uncertain: if the finding's "Suggested Fix" section in the finding-doc fits in 1-3 sentences and references no design alternatives, it's concrete. Otherwise architectural.

### Phase 5: Methodology survival check
- Did the cycle produce real findings (¬ theater)?
- Did the fixes strengthen the spec against its own anti-overclaim standard?
- yes ⇒ methodology holds; RSAW = the meta-process; update this primitive w/ cycle's evidence
- no ⇒ methodology failed dogfooding; surface to Will; RSAW gets revised before next use

### Phase 5.1: ¬theater operationalization (Cycle 2B fix)

A cycle's findings ¬ theater ⇔ ALL:
- ≥ 1 finding ⇒ CONCRETE factual error (count / path / cite) verifiable on disk
- ≥ 1 finding ⇒ INTERNAL CONTRADICTION (claim X ∧ claim Y ⊥)
- ≥ 1 finding ⇒ ACTUAL FIX shipped (commit hash exists ∧ mirror updated)
- findings span > 1 severity level (uniform severity ⇒ soft signal of lens-rigidity)

Theater ⇔ ANY:
- findings paraphrase each other (lens produced 1 thought × N)
- ¬ fix shipped same-session (findings → backlog ¬ closed)
- findings all flatter the spec (¬ AA#1/AA#2 catch against own standards)

Cycle 1 ⇒ 4/4 ¬theater. Cycle 2 ⇒ 4/4 ¬theater on this primitive itself.

### Phase 5.2: Falsifiable success framing (Cycle 2B fix)

Earlier criteria ("≥ 5 findings, ≥ 3 severity, ≥ 1 AA#1/AA#2") = absolute counts ⇒ wrong:
- substrate converges ⇒ fewer findings = EXPECTED
- AA#1/AA#2 catches ⇒ decline as spec hardens ⇒ ABSENCE = convergence evidence ¬ failure

Falsifiable framing:
- cycle sufficient ⇔ ≥ 1 fix-class novel relative to all prior cycles
- ¬ absolute count; relative-to-history
- 3 consecutive cycles × 0 novel fix-classes ⇒ substrate hit current lens-set ceiling
- → either (a) spec honest-and-converged ∨ (b) lens-set homogenized
- (b) handled by anti-pattern below

## → Connected primitives

- [P·what-would-will-do] WWWD orchestration — RSAW's cognition layer
- [feedback_substrate-mirror-into-project-repos] mirror discipline applied in Phase 4
- [feedback_trp-round-summaries] round summary file convention applied per-cycle
- [P·complete-as-ready-for-critique] RSAW is the critique surface; the audited spec is the artifact
- [feedback_anti-stale-feed-protocol] verify against current state before asserting (Phase 2 grounds findings in disk evidence)
- [P·audit-fork-loses-hardness] AA#1 lens applied recursively
- [F·claim-needs-structural-enforcer] AA#2 lens applied recursively
- [primitive_self-theater-audit-gate] sibling 8-pass audit, lens-set contributor
- [F·parallel-agents-plus-revision] parallel dispatch pattern this composes with

## ∀ Trigger

- ∀ JARVIS substrate-layer doc shipped ⇒ RSAW within 24 hours of shipping (catches drift before it compounds)
- ∀ major protocol revision ⇒ RSAW pre-ship and post-ship
- ∀ Will-named protocol ⇒ RSAW as part of the formalization-loop closure
- ∀ V3-stack version bump ⇒ RSAW across all four layers (L0+L1, L2, L3, ...)

## ✗ Anti-pattern

- RSAW that produces zero findings → likely theater, lens-set too soft (unless three-cycle convergence pattern, see Success criteria)
- RSAW that batches all fixes to end → cycle 2 audits stale spec, wastes the second cycle's signal
- RSAW skipped because "the spec is fresh, it must be correct" → exactly the failure mode RSAW exists to prevent (15 findings in 12 minutes on a 30-minute-old spec)
- WWWD orchestration replaced by Claude-default agent dispatch → loses the Will-projection-aware lens calibration
- **Recurrence-class blindness** (C2B): same fix-class × 3+ cycles × ¬ structural fix ⇒ RSAW × same insight × N ¬ substrate change ⇒ fix-class itself = new RSAW failure. Fix: track fix-class identity across cycles ⇒ escalate recurrent → Will-decision ¬ re-audit
- **Lens-set homogenization** (C2B): multi-cycle agent findings overlap > 30% across lens-scopes ⇒ lens narrowed ⇒ missing other things. Fix: rotate 1 lens out / cycle + introduce 1 cycle-specific lens ⇒ prevent ossification
- **Agent-finding convergence** (C2B): 3+ agents same-cycle × functionally identical findings ⇒ parallel capacity wasted. Fix: tighten non-overlapping-scope contract Phase 2 ⇒ each agent's prompt disclaims others' scope

## ✓ Success criteria

- Cycle 1 produces ≥ 5 findings across ≥ 3 severity levels
- ≥ 1 finding is AA#1 or AA#2 class (forces the spec to honor its own anti-overclaim standards)
- All concrete-fix findings get applied + mirrored + committed within the same session
- Round summary file written to `audits/<target>/CYCLE_<N>_SUMMARY.md` per TRP convention
- Methodology-survival check passes; this primitive's evidence section grows by one cycle

## 📦 Canonical reference cycle

- 2026-05-24 V3 self-audit: `audits/v3-self-audit/`
- AUDIT_BRIEF: `audits/v3-self-audit/AUDIT_BRIEF.md`
- 15 findings across 3 agents: `audits/v3-self-audit/findings/c1*-*.md`
- Fixes shipped: JARVIS commit 27f618d + 2b9fa08, vibeswap commits 517bde8 + fe93fd90, jarvis-network 0e4d958 + e98ca14
- Methodology-survival check: passed (15 real findings, zero theater, all → fixes)

## 🧠 Will-framing locked

> *"if succesful, formalize it as a meta procress"*

The success condition was the dogfooding test. The test passed. RSAW is the meta-process.
