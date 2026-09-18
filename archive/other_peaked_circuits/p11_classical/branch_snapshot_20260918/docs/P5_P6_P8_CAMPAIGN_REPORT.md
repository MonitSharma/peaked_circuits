# P5 / P6 / P8 recovery — campaign report

**Scope.** Classical recovery of three peaked circuits using the midpoint
MPO + unswapping solver (`p9solver`), calibrated against two circuits with
known answers. All work local to an M3 Pro / 36 GiB Mac; no QPU, emulator, or
cloud compute. Candidate generation was answer-blind throughout: every candidate
was frozen with a hash and timestamp before any external check.

## Outcome

| circuit | qubits | 2q gates | work gates | status |
|---|---:|---:|---:|---|
| **P5** Granite Summit | 44 | 1892 | 902 | **SOLVED — 44/44** |
| **P8** Grid 888 iSWAP | 40 | 888 | 808 | **SOLVED — 40/40** |
| **P6** Titan Pinnacle | 62 | 3494 | 2593 | **unresolved — no candidate** |

Two of three solved and externally confirmed. P6 produced no string better than
chance.

---

## 1. The environment bug that gated everything

`.venv-p9-isolated` (Python 3.10.16 / SciPy 1.15.3) **segfaults at D=512**. The
conda `p9-openblas` env (3.10.21 / SciPy 1.15.2) is stable. Every pre-2026-08-29
local MPO run used the segfaulting environment, which invalidates that whole
body of evidence independently of any other issue.

## 2. Fidelity calibration (the measurement the campaign lacked)

Cutoff sweeps against **known** answers, which separates *completion* from
*fidelity* for the first time:

| circuit | gates | cutoff | overlap | peak frac | decoder top-1 | top1/top2 |
|---|---:|---|---|---:|---:|---:|
| P9 | 1885 | 6e-4 | 56/56 | 0.048 | 5.3e-2 | 5.3x |
| P9 | 1885 | **1.5e-3** | **56/56** | **0.098** | 9.98e-2 | **23.1x** |
| P9 | 1885 | 2e-3 | 56/56 | 0.086 | 7.18e-2 | 4.5x |
| P9 | 1885 | 5e-3 | wrong 25/56 | 0.001 | 4.9e-9 | ~1x |
| P5 | 902 | 6e-4 | 44/44 | 0.012 | 1.09e-2 | 7.8x |
| P5 | 902 | 1.5e-3 | 44/44 | 0.012 | 1.16e-2 | 6.3x |
| P5 | 902 | 2e-3 | 42/44 | 0.004 | 3.39e-3 | 3.4x |
| **P8** | 808 | 6e-4 | **40/40** | 0.038 | 2.86e-2 | 6.44x |
| **P6** | 2593 | 2e-3 | — | **0.001** | **2.8e-07** | **1.02x** |

**Three findings that changed the campaign:**

1. **A looser cutoff is not inherently destructive and can *improve* the peak.**
   P9's best mode of the entire campaign is at 1.5e-3 (peak 0.098,
   top1/top2 23x) -- better than at its own originally calibrated 6e-4.
2. **The promotion bar was set too high.** P5 is correct at peak **0.012**. An
   earlier 3% gate would have discarded a correct answer. The usable criterion
   is a *distinct* mode, not a large one:
   `ACCEPT: top-1 >= ~1e-3 AND top1/top2 >= ~3x`.
3. **Materialized-state size is not a fidelity indicator** and was discarded:
   P9 returned 56/56 from a **174-element** state, smaller than P6's *destroyed*
   294-element one.

In all three verified circuits the **sampling mode and the beam decoder top-1
agreed exactly** -- a reliable co-indicator of correctness.

---

## 3. P5 — solved

```
11110000001110100101110011111101010001100001
```

D=512, cutoff 6e-4, `--route-score bond_profile` with 4 candidates, and the
no-progress guard relaxed from its default of 2. That guard was the blocker:
runs stalled at 888/902 and aborted; with it relaxed the run reached 902/902.

Peak 0.012, decoder top-1 1.09e-2, top1/top2 7.8x, sampling and decoder
agreeing. Independently reproduced at cutoff 1.5e-3 (44/44, Hamming 0).

---

## 4. P8 — solved

```
1000011001010101101111011100000111000111
```

### 4.1 The routing attractor is real

Nineteen configurations spanning routing scores, unswap selectors, absorb
scores, centre ratios, seeds, patience levels, balanced scheduling, cycle
detection with tabu, and a depth-4 tail beam. **All stalled at 779-804 of 808.**

The strongest single observation: **three qualitatively different controllers
converge on a bit-identical terminal state** (799/808, `L=404/404 R=395/404`) --
plain greedy, balanced `delta=0.02`, and tail beam width 8 / horizon 4. Cycle
telemetry recorded 94 routing-state hashes with only **32 unique**.

Not entanglement-limited: `selected_absorbs_hit_max_bond = 0` on all nineteen
runs, and final bond at the stall spans 64-176 while the stall point moves only
12 gates. Not threshold-limited: **0 of 1170/259/482** absorb rows had *both*
probes over `unswap_threshold`.

Absorption scheduling was the only lever that moved the terminal state
(799 -> 801 -> 804); every swap-selection change landed on 799.

### 4.2 Provenance recovery

The 804 result was documented as unreproducible. Three blocking claims were each
checked and each was wrong: the commits exist in the **solver** repo (not
`p12-helios-recovery`); the manifest **does** record
`solver_git_commit=e1a6eef`, `dirty=True`; and the `peaked-mpo-solver-p8-beam`
worktree is still on disk and clean at `7296a2a`.

`e1a6eef` hard-codes `flip_freq=None` and exposes no `--flip-freq`, so the
`dirty=True` *was* the flag exposure, committed later as `7296a2a`. Rerunning
`7296a2a` with the recorded settings reproduced the trajectory **bit-for-bit**:
804 gates, `no_progress_cycle_limit`, final bond 105, final elems 215604, peak
bond 272, peak elems 688728, leftover L=2/R=17.

### 4.3 The solution

**Escaping the attractor was never necessary.** `mpo_to_mps` applies the
residual layers *before* the compressed core (`pipeline.py:2760` loops them,
2766 applies the core), so a stall with few enough gates remaining still
materializes into a faithful full-circuit state.

At 804 only **4 work gates** remained. `--tail-materialize --tail-limit 8` fired
on the abort -- by design, since `cli.py:1076` evaluates eligibility *after* the
loop exits and the `and not tail_materialize_eligible` clause lets an aborted
run still materialize. Sampling that state gave the correct answer at peak
0.038.

**The generalisable correction:** the promotion criterion for an MPO run is not
*"did it consume all work gates"* but ***"is the residual small enough to
materialize faithfully"***.

---

## 5. P6 — unresolved

No candidate. Nothing produced for P6 beats a random 62-bit string.

### 5.1 It is not the dense one

The problem statement advertises "all-to-all" connectivity. The measured
interaction graphs say otherwise:

| circuit | density | mean degree | solved |
|---|---:|---:|:--:|
| P9 | 69.4% | 38.2 | yes |
| P5 | 61.1% | 26.3 | yes |
| **P6** | **34.8%** | **21.2** | **no** |
| P8 | 8.1% | 3.1 | yes |

P6 is the **second sparsest** of the four and both denser circuits were solved.
Connectivity is not what distinguishes P6, and any plan premised on
"P6 needs a different representation because it's dense" targets a
non-difference.

### 5.2 Five hypotheses closed by measurement

| hypothesis | test | result |
|---|---|---|
| bond dimension | D=512 runs | `selected_absorbs_hit_max_bond = 0` always |
| element threshold | probe telemetry | never binding |
| cutoff window | P5/P9 sweeps | 1.5e-3 and 2e-3 preserve *their* answers |
| depth | P9 at 1885 gates | exact at 2e-3; depth is not the mechanism |
| route/trajectory quality | same cutoff, `flip_freq=2` vs default | equally flat; top-1 an order of magnitude *worse* |
| **readout precision** | same MPO, cutoff 2e-3 vs **1e-8** | **identically flat** |

The readout test was the sharpest. Compression was byte-identical (final MPO
bond 27, 43,456 elements); only the MPO->MPS cutoff changed:

| materialize cutoff | MPS bond | MPS elems | peak | top1/top2 |
|---|---:|---:|---:|---:|
| 2e-3 | 4 | 294 | 0.001 | 1.02x |
| 2e-3 | 11 | 2290 | 0.001 | 1.06x |
| **1e-8** | **18** | **8842** | **0.001** | **1.058x** |

With bond 4096 available and essentially no truncation, the state materialized
to bond **18**. The MPO is not being crushed -- it does not contain more
structure. **The peak dies during compression, not at readout.**

### 5.3 The diagnostic the campaign was missing: cross-run convergence

Every earlier P6 conclusion measured *peak sharpness* -- a property of a single
state. Nobody measured whether **two independent runs of the same circuit
agree**. That test is decisive:

| comparison | decoder-map agreement |
|---|---|
| P9, two cutoffs, both correct | **0/56 top-1** (identical) |
| P5, three configs, all correct | **0-2/44 top-1** |
| P6, same MPO, readout 2e-3 vs 1e-8 | **3/62** (readout is deterministic) |
| **P6, different routing seed, same cutoff** | **30-33/62** |

Random 62-bit pairs sit at Hamming ~31. **Two routing paths through P6 at the
same cutoff produce statistically orthogonal states.** The approximation is not
converging to anything -- the state is a function of the route taken, not of the
circuit. That explains the flat peak without any special story about P6's peak
weight.

### 5.4 The failure is progressive, not a threshold

Prefix probes at matched depth across two routing seeds:

| depth | decoder-map agreement | reading |
|---|---|---|
| gate 100 | **17/62** | correlated (3.6 sigma below random) |
| gate 2593 | **30-33/62** | random |

The states begin genuinely related and decorrelate as the circuit proceeds.
There is no single breaking point -- error accumulates over 2593 gates until
nothing of the circuit survives.

**Consequence: no parameter setting fixes P6.** A critical-value search --
cutoff bisection, split absorb/route cutoffs, rescue pulses -- is the wrong
shape of intervention for an accumulation problem. Those remain worth one shot
as due diligence, but should be expected to move the decorrelation depth
marginally rather than solve it.

### 5.5 What would actually address it

**CAMPS (Clifford-augmented MPS)** is the one proposal that targets the failure
mode: all 3494 P6 entanglers are CZ and therefore Clifford, so a Clifford frame
carries that entanglement *exactly* and error accrues only on the residual
rotations. Run the cheap GF(2) nullity profile as a go/no-go before building a
simulator.

**Any new P6 method should be gated on convergence, not on peak.** Run it twice
with different routing seeds; if the decoder maps land near Hamming 31/62, that
configuration is generating noise and no readout, sampling, or bond increase
will rescue it. For PyZX specifically the question is not whether `full_reduce`
cuts 25% of gates -- it is whether the reduced circuit **holds seed-to-seed
agreement deeper into the circuit**.

**Closed:** the layer-207 structural lead (fixed mapping matched 0 edges at
widths 16-256; the 3-qubit motif failed neighbourhood expansion).

---

## 5.6 Three independent representations, all closed by their controls

After the state-based routes were exhausted, three structurally different
methods were screened. **Each was closed by its positive control, not by a P6
result** -- in every case the already-solved circuits failed the same test:

| route | what it measures | outcome |
|---|---|---|
| **CAMPS** | GF(2) nullity of Clifford-conjugated rotations | all four saturate at `min(left,right)`; P6 has the *highest* Clifford fraction (36.7%) and still saturates |
| **Pauli propagation** | sparsity of `U^dag Z_i U` in Pauli space | support explodes on **P5** at event 440 of 5,720 (7.7%); P6 survives *further* in relative terms |
| **SOP / rank-width** | rank-width of the Feynman path graph | cut-rank equals qubit count for all four: 44, 40, 56, 62 |

Each took under an hour because the cheap go/no-go ran before any build. Two
implementation bugs were caught by those controls before they could produce
confident wrong answers: a left-side restriction inflating CAMPS edge cuts, and a
missing sign in the Pauli CZ conjugation rule that passed depth-2 circuits and
failed at depth 3.

The joint reading is stronger than any single result. Three independent
parameters all saturate, **including on circuits we solved**. P5, P8 and P9 were
recovered despite having no exploitable structure under any of these measures --
by the MPO route's mirror cancellation, a mechanism none of these diagnostics
captures. So their saturation is not evidence that P6 is uniquely hard; it is
evidence that these parameters do not discriminate within this family at all.

## 6. Corrections made to earlier conclusions

Recorded because several were acted on before being checked:

- **P8 `CURRENT_METHODS_EXHAUSTED` was wrong.** Its mechanism was right and its
  conclusion was not; the circuit was solvable from the stall it documented.
- **The 804 run was not provenance-blocked.** Three checkable claims, all wrong.
- **The P6 "cutoff window refuted" claim** rested on P9/P5 data, not P6 data,
  and both sub-2e-3 P6 runs were stopped by scheduling decisions rather than by
  the solver.
- **The materialized-state-size diagnostic** was proposed and refuted the same
  day.
- **`--flip-freq` was unreachable.** `pipeline.py` had always supported it;
  `cli.py` hard-coded `None`. Exposing it produced P8's best pre-solution result
  (804) and P6's best faithful-cutoff result (148 vs a 138 ceiling).
- **The structural stack could not read P6 or P8 at all.** `parse_qasm` *raised*
  on `u3`/`iswap`, and `_QREG` hard-coded the register name `q`, so P5 (`q83`)
  failed too. Fixed with a regression test; 202 tests pass.

## 7. Artifacts

`results/p5_p6_p8_recovery/` -- run logs, stats, summaries, candidate freezes.
Companion documents: `P8_TAIL804_CANDIDATE.md`, `P8_804_FORENSIC_RECONSTRUCTION.md`,
`P8_MPO_DIAGNOSIS.md`, `P6_MPO_DIAGNOSIS.md`, `PEAKED_FIDELITY_CALIBRATION.md`.
