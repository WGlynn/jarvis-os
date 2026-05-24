# JARVIS-OS

> *"JARVIS is a coordination layer over LLM substrates, the way an operating
> system is a coordination layer over hardware substrates. The CPU is
> interchangeable. The kernel is not. The applications run on the kernel."*
> — from [JARVIS is not a wrapper](https://github.com/WGlynn/JARVIS/blob/main/papers/jarvis-is-not-a-wrapper.md)

JARVIS-OS is the installable distribution of the JARVIS kernel for Claude
Code. It ships the navigation shell, the cognition gate, the persistence
seed, and the discipline scaffolding — enough that a fresh Claude Code
session on your machine boots into the same kernel I run on mine.

The full JARVIS substrate is the eight-layer architecture documented at
[github.com/WGlynn/JARVIS](https://github.com/WGlynn/JARVIS). This pack is
the **subset that fits in a one-line install** and provides a navigable
entry point. The MANIFEST gives byte-for-byte SHA256 hashes so you can
verify what you have matches what I ship.

## What "provably identical" means here

You install this pack. You get:

- **The same twelve hooks** that fire on my machine (Layer 1 + Layer 3)
- **The same three core primitives** that anchor my cognition stack (Layer 2: persistence)
- **The same boot screen** as the navigation surface (the OS itself)
- **The same hook-registration shape** in `settings.json`

Your **corpus** starts empty and grows from your usage. The kernel is identical
across installs; the cognition diverges from there.

The rest of my substrate is not withheld — it is **tokenized and tradeable**.
Reusable cognition primitives mint as NFTs + ERC-20 consumables on the PsiNet
context-exchange protocol (Ocean-Protocol pattern, ported to the cognition
layer). Sensitive primitives stay local; useful-but-sensitive primitives can
publish under compute-to-data (ZK / homomorphic) so the logic stays encrypted
while the projection output is queryable. NDA-locked content has no opt-in
path — it never leaves the machine.

PsiNet runs on VibeSwap's commit-reveal + canonical burn-and-mint rails — the
MEV-resistant primitive stack we built for token trading becomes the trading
rail for cognition primitives. Trading substrate inherits the same adversary
model trading tokens inherits.

That's the honest version of "provably identical." Kernel: byte-identical, free,
installed in one command. Corpus: yours by default, with optional acquisition
of others' primitives via the marketplace as the network matures.

## What the install pack contains

Mapped to the eight JARVIS layers:

| Layer | What you get |
|---|---|
| 1. Hooks | `wwwd-gate.py`, `wwwd-correction-detector.py`, `wwwd-corpus-refresh.py`, `jarvis-os-boot-screen.py` |
| 2. Persistence | seed `MEMORY.md` + 3 active primitives (WWWD, JARVIS-OS, RSAW) |
| 3. Anti-hallucination | pointer only — full HIERO/substance/framing gates live in WGlynn/JARVIS |
| 4. Discipline | scaffold in the primitives + correction-detector closing the loop |
| 5. Meta-protocols | the WWWD primitive itself is the meta-protocol for cognition |
| 6. Agent overlay | pointer — JARVIS-OS doesn't ship subagents (yet) |
| 7. Stateful applications | pointer — your applications, not ours |
| 8. Filesystem-as-substrate | everything is markdown + Python; greppable; forkable |

## What the OS does

**Boot screen.** Every Claude Code session opens with an 8-bit ASCII menu
that lists the active protocols, key files, gates, philosophy, and the
natural-language commands (`show protocols`, `show gates`, `show wwwd`)
Claude recognizes at the conversation layer. Live WWWD-corpus stats
inline.

**WWWD gate.** Before any `Write`, `Edit`, or `Agent` tool-call, the gate
pauses and projects the candidate action through the Will-emulation
corpus. Triggers detect severity calibration, partner-facing writes,
marketing tone, scope decisions, ambiguous referents, deployment-phase
severity claims, and template resolution. The gate emits a projection
note as `additionalContext`; it never blocks.

**Correction detector.** When you push back on a Claude response
(`no`, `actually`, `let me clarify`), the Stop hook logs the correction
back to the most recent gate-fire entry. Future projections in that
decision-class route through the updated corpus.

**Corpus refresh.** On session start, recompute a priority cache from
the gate-fire log. Surfaces a convergence signal: improving / stable /
drifting / insufficient-data.

The four hooks form one closed loop: fire → project → execute → correct
→ log → next projection improves.

## Install

Requires Python 3.8+, Bash, and Claude Code.

```bash
git clone https://github.com/WGlynn/jarvis-os.git ~/jarvis-os
cd ~/jarvis-os
bash install.sh
```

Or download the zip from Releases and extract; then run `bash install.sh`.

You'll be prompted for your name (used to instantiate the cognition gate)
and the installer will:

1. Copy hooks into `~/.claude/hooks/`
2. Seed `MEMORY.md` + the three core primitives into your Claude memory dir
3. Merge hook registrations into `~/.claude/settings.json` (backup made)

Dry-run first if you want to see what changes:

```bash
bash install.sh --dry-run
```

Open a new Claude Code session — the boot screen renders on SessionStart.

## Verify

After install, verify the kernel files match what shipped:

```bash
cd ~/jarvis-os
sha256sum -c MANIFEST.sha256
```

Every file in `templates/` and `examples/` should report `OK`.

## Customize

The shipped hooks contain my Will-specific projection notes inside
`wwwd-gate.py` (look at `PARTNER_FACING_PATH_PATTERNS`, the trigger
keyword lists, and the `project_will_pick` function). Read these as
documentation of one approach, then edit them to match your patterns:

- Replace `PARTNER_FACING_PATH_PATTERNS` with paths/names you use
- Edit `project_will_pick` to render your own decision-pattern reminders
- Add or remove trigger classes as you discover them

Your cognition primitive ships pre-populated with mine
(`primitive_what-would-will-do.md`). Either rename it to your own and
edit the content, or fork-and-extend — the gate's projection logic and
your primitive together define your kernel personality.

## Absorb other substrates

JARVIS-OS is amendable. If you find another Claude substrate repo — someone
else's hook stack, their primitive library, their gates — you can pull it
into your install agnostically:

```bash
bash absorb.sh <path-or-git-url> [--namespace prefix] [--dry-run] [--auto]
```

The absorber:

1. Scans the source for hook-shaped (`*.py` matching `*/hooks/*`, `*-gate.py`, etc.) and primitive-shaped (`primitive_*.md`, `feedback_*.md`, etc.) files
2. Reads `jarvis-os.yaml` if the source repo publishes one (see `MANIFEST_SPEC.md`)
3. Prompts you for each candidate
4. Copies imports into your install with namespace-prefixed filenames (so two `voice-gate.py` files from different sources can coexist)
5. Auto-registers imported hooks in `settings.json` with heuristic event-matcher assignment (or declared assignment from the manifest)
6. Backs up `settings.json` to `.bak-pre-absorb` before any write

The point: many Claude memory + hook + primitive stacks are converging on the
same shape. JARVIS-OS treats them as composable substrates rather than
competing forks. You read someone's repo, you decide what looks useful, you
absorb it. The OS handles the wiring.

If you publish your own substrate, add a `jarvis-os.yaml` manifest at the
repo root (see `MANIFEST_SPEC.md`) so absorbers get explicit event-matcher
assignments instead of having to guess from filename patterns.

## Going further

This pack is the entry layer. For the full substrate — eight layers,
395+ memory files, the full agent overlay with subagents and skills,
the meta-protocol library, the stateful applications — see
[github.com/WGlynn/JARVIS](https://github.com/WGlynn/JARVIS).

If you want to build your own overlay: clone `JARVIS`, read each
layer's README, start with the hook layer (universal coverage at
O(1) cost). Persistence is the second-highest leverage.

The Telegram bot, validator suite, sharded BFT runtime, and other
stateful applications are downstream of these two layers.

## Philosophy

The gate is augmentation, not block. It never prevents an action; it
makes the cognition explicit. The gate-fire log accumulates a record
of (decision, projection, correction) triples that you can read to see
how the system has drifted from your actual preferences — and to tune
the projection logic in response.

This is what an OS-grade overlay does. The model is amnesic. The
system is not.

## License

MIT. See `LICENSE`.

## Provenance

Built 2026-05-24 as the navigation-shell layer of the JARVIS
architecture. The cognition gate is named after my own preference
(`What Would Will Do?`) but the framework is yours to instantiate
with your name and your patterns.

**v1.0.1** (2026-05-24) — adds four primitives surfaced by today's
WWWD-arc work: the airgap-closure stack, the four-substrate
convergence theorem, proof-of-mind, and the substrate-port pattern.
See `templates/memory/primitive_*.md` and the boot screen.

Forks welcome. PRs that genericize the framework further (without
losing the substrate-as-shared-example shape) especially welcome.
