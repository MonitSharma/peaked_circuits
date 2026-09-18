# P6 classical-methods review package

**Purpose:** shareable, answer-blind account of the classical approaches used
on P6 (`Titan Pinnacle`), what each method attempted, and why it did not yield
an end-to-end solution.

**Status as of 2026-09-07:** no verified P6 answer. The best externally scored
hypothesis is 40/62, which is not sufficient to identify a 62-bit answer.

The P11/P12 positive-control audit completed on 2026-09-07 confirms that the
local weighted-medoid/cluster pipeline can recover the externally accepted
answers from retained hardware data. This is useful validation of the analysis
method, but it does not change the P6 conclusion: after correcting the Nexus
result-framing issue, five P6 hardware batches produced 500 unique strings and
no reproducible frequency peak. The earlier apparent P6 repeats were first-
frame duplication from SDK result assembly and are superseded.

The positive-control report is at
`results/quantinuum/positive_control_audit_20260907/audit.md`; the corrected
P6 report is at
`results/hardware/p6_five_batch_corrected_analysis_20260907/analysis.md`.

## 1. Problem definition and provenance

Input: `P6_titan_pinnacle.qasm`

- Qubits: 62
- Operations: 10,486 (`6,992 u3` and `3,494 cz`)
- Circuit depth: 416
- Interaction edges: 658
- Source SHA-256:
  `206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4`
- Canonical output width: 62 bits

The simulations were intended to be answer-blind. External overlap scores were
used only after candidate generation, for audit and constraint analysis. They
were not fed back into the original simulator or used to tune its parameters.

The detailed classical work is distributed between the `p12_quantum` branch
and the later `p11_classical` branch in the adjacent recovery checkout. The
main audit documents are:

- `docs/P6_MPO_DIAGNOSIS.md`
- `docs/P6_P8_REASSESSMENT_20260831.md`
- `docs/P6_REPRESENTATION_INVESTIGATION_20260901.md`
- `docs/P6_CANDIDATE_LEDGER.md`
- `docs/P6_KAK_ORACLE_RESULTS.md`
- `docs/P6_CONSTRAINED_RANKING.md`
- `docs/P6_CAMPS_FEASIBILITY.md`

## 2. What counts as success

P5 and P9 were used as positive controls for the production MPO family. A
usable result should satisfy more than “the run completed” or “the approximate
state has a large MAP ratio.” The useful controls require:

1. a reproducible, non-flat sampled distribution;
2. a distinct top mode rather than an approximately 1:1 top-1/top-2 ratio;
3. agreement between sampling and the decoder;
4. agreement across independent seeds/configurations;
5. a retained-fidelity diagnostic above the uniform-floor gate;
6. exact or near-exact overlap when a known answer is available.

For reference, the calibrated positive controls included P5 at 44/44 and P9
at 56/56. P5 produced about a 1.2% peak with a roughly 7.8x top-1/top-2
separation. A loose P9 control produced a flat, wrong distribution despite
completing, demonstrating that completion alone is not evidence of fidelity.

## 3. Method family A: MPS and permutation-MPS simulation

### What was attempted

The circuit was evolved as an approximate matrix-product state, with variants
including:

- identity/natural qubit ordering;
- heavy-interaction and spectral orderings;
- permutation-aware MPS (`CircuitPermMPS`-style) evolution;
- annealed D128 ordering;
- bond dimensions from D64 through D128 in the retained P6 campaign;
- strict and loose truncation cutoffs;
- sampling, marginal majority, bootstrap, and split-half diagnostics.

The goal was to let the tensor-network approximation expose a high-probability
P6 string without routing the circuit through physical hardware connectivity.

### What happened

The apparent MPS modes were not stable fidelity signals. The key diagnostics
were:

- retained-norm proxies around `10^-25`–`10^-30` for identity/heavy-greedy/
  spectral families in the early campaign;
- the independent annealed D128 `peakfind.py` run completed the parsed circuit,
  but failed its retained-fidelity gate;
- its top-1/top-2 ratio was only about `1.020x`, with a top-32 mean Hamming
  spread of about 3.6;
- the loose D128 extraction produced 10,000 unique samples and a stable-looking
  majority, but that majority exactly matched a supplied evaluated candidate;
  this was interpreted as a truncation bias, not a recovered peak;
- independent D128/CircuitPermMPS seeds produced materially different strings.

### Failure mode

The MPS approximation generated its own low-rank bias. A candidate can have a
large ratio to the uniform probability floor while still being unrelated to
the true circuit distribution. Stability within one approximate run was not
enough: cross-method and cross-seed agreement failed.

**Conclusion:** no MPS/permutation-MPS candidate was promoted.

## 4. Method family B: midpoint MPO compression with unswapping

### What was attempted

This was the main classical recovery path: evolve a midpoint matrix-product
operator, compress by SVD, route/unswap the logical interaction layers, then
materialize an approximate MPS and sample/decode it.

The production family was run with:

- D128 and D512;
- cutoffs `6e-4`, `1e-3`, `1.5e-3`, `1.75e-3`, `1.875e-3`, `2e-3`, and `5e-3`;
- default bond-based routing;
- SABRE/bond-profile routing with multiple route candidates;
- bond-route-proxy and hybrid routing;
- `flip_freq=2`;
- pair-lookahead unswap selection;
- different no-progress guards and patience values;
- different random seeds;
- balanced absorption and related scheduling controls.

### Main run outcomes

| Configuration | Result |
|---|---|
| D128, cutoff `0.005` | Completed 2,593/2,593; effectively flat; no candidate |
| D512, cutoff `6e-4` | Preserved tighter fidelity regime but stalled around 86–148/2,593 |
| D512, cutoff `1e-3` | Stalled around 180/2,593 |
| D512, cutoff `1.5e-3` | Tested to 89–180 gates, but stopped before a natural endpoint |
| D512, cutoff `1.75e-3` | Reached 164 gates before decaying/stopping; no natural completion |
| D512, cutoff `1.875e-3`, `flip_freq=2` | Reached 94 gates, then genuine no-progress routing stall |
| D512, cutoff `2e-3`, default router | Completed; flat readout, approximately 1.02x top-1/top-2 |
| D512, cutoff `2e-3`, `flip_freq=2` | Completed; flat readout, approximately 1.06x top-1/top-2 |
| D512, cutoff `5e-3` | Completion possible, but fidelity is not retained |

The completed `2e-3` route had approximately:

- final materialized bond 4 or 27 depending on run;
- final state size 294 in the primary run;
- 1,000/1,000 unique samples;
- peak fraction about `0.001`;
- decoder top-1 probability about `2.8e-7` or lower;
- top-1/top-2 approximately `1.02x`–`1.06x`.

Those figures resemble the known failed loose-cutoff control, not the P5/P9
positive controls.

### What the telemetry ruled out

- **Bond cap as the primary blocker:** `selected_absorbs_hit_max_bond = 0`
  across the D512 runs. The bond reached its cap transiently during unswapping,
  not during a physical absorption.
- **Element threshold as the primary blocker:** probe rejection was a minority
  of absorption rows and did not account for the stall.
- **Simple no-progress guard:** relaxing the guard from 2 to 20, 60, or
  unlimited did not unlock the tight-cutoff runs.
- **One unlucky route seed:** changing the router with `flip_freq=2` produced
  another completed but flat P6 state; the result was not rescued by the route
  change.
- **Readout-only loss:** re-materializing the same compressed MPO with a much
  tighter MPS cutoff increased the materialized bond and state size but left the
  output flat. The useful information had already been lost during MPO
  compression.

### Failure mode

There is a completion/fidelity conflict. Tight cutoffs preserve a potentially
useful state but leave the routing/unswapping controller unable to finish.
Loose cutoffs keep the computation small enough to finish but discard the
structure before sampling. Independent routing paths progressively decorrelate
as the 2,593 work gates are processed.

**Conclusion:** the MPO method did not produce a validated P6 candidate. The
remaining cutoff interval was partially probed, but routine cutoff/guard/seed
retries are unlikely to repair progressive route-dependent error.

## 5. Method family C: structural graph and interaction analysis

### What was attempted

The P6 interaction graph, weighted backbone, local gate sequence, and candidate
substructures were analyzed to find a hidden ordering or a cheap decomposition.
This included:

- heavy-edge/backbone analysis;
- cutwidth and interaction-span measurements;
- short local-unitary sequence scans;
- patch-fingerprint and neighborhood scans;
- a layer-207 permutation/reconstruction hypothesis;
- bounded structural prefixes and candidate-family reconstruction.

### Findings

P6 is not simply the “dense/all-to-all” outlier. It is sparser than P5 and P9,
which were solved by classical methods, but combines 62 qubits, 3,494
two-qubit events, and 2,593 consolidated work gates.

The short-window scans found coincidences and local structure, but inferred
permutations were unstable between windows and did not form a global
unscrambling map. The layer-207 hypothesis failed to match the required edges
at tested widths, and the three-qubit motif did not expand into a valid global
construction.

**Failure mode:** local regularity was mistaken for a circuit-wide invariant.

**Conclusion:** structural scans generated useful diagnostics but no exact
reduction or global permutation.

## 6. Method family D: exact PyZX circuit rewrites

### What was attempted

PyZX was used for exact-basis graph rewriting, with `full_reduce` and
`teleport_reduce` representations. This was not approximate simulation; no
angle snapping was used.

### Results

| Representation | Operations | Two-qubit gates | Depth |
|---|---:|---:|---:|
| Original | 10,486 | 3,494 | 416 |
| `full_reduce` extraction | 26,073 | 3,631 | 1,119 |
| `teleport_reduce` extraction | 98,280 | 3,494 | 3,611 |

`full_reduce` introduced 40 extracted SWAPs and increased depth by about 2.7x.
`teleport_reduce` preserved the two-qubit count but increased total operations
by about 9.4x and depth by about 8.7x.

The graph transformations are exact as rewrites, but a full independent
62-qubit statevector equivalence check was not feasible locally. The extracted
forms did not provide a lower-cost input for the MPO solver.

**Failure mode:** exact algebraic rewriting did not produce a computationally
useful representation; it increased, rather than reduced, the relevant work.

## 7. Method family E: Clifford-augmented MPS / CAMPS feasibility screen

### Motivation

All 3,494 P6 entanglers are CZ gates, hence Clifford. A Clifford-augmented MPS
could in principle carry the Clifford frame exactly and leave only
non-Clifford rotations for the tensor network.

### Test

The `camps_nullity.py` diagnostic tracked the propagated Clifford frame and the
GF(2) rank of conjugated residual Pauli strings across cuts.

At the recorded tolerance:

- Clifford rotations: 6,661;
- residual rotations: 14,315;
- maximum support rank/nullity: 62;
- maximum theoretical bond bound: `2^62`;
- the profile saturated the full middle-cut rank.

The same screen saturated the corresponding maximum on P5, P8, and P9 as well,
so the rank diagnostic is not a proof that P6 is mathematically impossible.
It does show that the hoped-for small residual subproblem does not appear in
this representation.

**Failure mode:** the Clifford fraction is high, but the single-qubit
non-Clifford rotations generate a full-rank residual space after conjugation.

**Conclusion:** CAMPS was closed as a promising near-term rescue without
building a full simulator.

## 8. Method family F: KAK/Weyl and midpoint-mirror analysis

### What was attempted

The circuit was split into maximal contiguous pair-local blocks. For each block,
KAK/Weyl coordinates and operator-Schmidt signatures were computed. A bounded
time-reflected midpoint comparison was then tested against shuffled controls.

Recorded results:

- 2,673 extracted pair-local blocks from 3,494 two-qubit events;
- 680 blocks with repeated entanglers;
- observed mean nearest-Weyl distance: `0.0135606537`;
- shuffled-control mean: `0.0137513160`;
- z improvement: `0.28`;
- exact nearest matches: `1080/1319`.

The exact-match count was inflated by repeated/common CZ-like signatures. The
observed separation from shuffled controls was not meaningful evidence of a
global midpoint mirror or answer-recovery symmetry.

**Conclusion:** no usable global KAK/mirror invariant was found.

## 9. Method family G: constrained reconstruction and candidate ranking

### What was attempted

Previously evaluated candidate overlaps were converted into hard Hamming
constraints. D128 and loose-cutoff D512 marginal information was then used only
as soft log-likelihood priors to rank feasible 62-bit strings.

The ranking is mathematically useful for consistency checking, but it cannot
create information absent from the original circuit simulation.

### Candidate record

The externally evaluated candidates include overlaps from 30/62 through 36/62.
The best later score-constrained hypothesis reached 40/62:

`10101111111011011111110000011010110011000101000101101111111000`

It satisfies the recorded overlap constraints, but that only means it has not
been excluded by those constraints. Other constraint-consistent hypotheses
scored only 30/62, demonstrating that feasibility is not correctness.

The earlier combined-prior leader was subsequently tested and scored 30/62.
The D128-only and D512-only leaders were different, and the top two combined
leaders were separated by only about `0.0244` log-likelihood units.

**Failure mode:** external overlap scores provide aggregate Hamming information,
not bitwise correction information. Treating overlap as a way to infer which
individual bits to flip would be invalid.

**Conclusion:** constrained ranking produced hypotheses and exclusions, not an
end-to-end answer.

## 10. Runtime and implementation issues

Several engineering problems were found and corrected or isolated:

- one Python/SciPy environment could segfault at D512 with native signal
  `SIGSEGV`; validated MPO runs used the stable `p9-openblas` environment;
- Numba cache paths needed to be writable;
- `flip_freq` existed in the solver but was hard-coded unreachable in the CLI;
- the structural parser initially rejected `u3`/`iswap` and assumed a fixed
  register name;
- some long-running experiments ended by wall/user scheduling limits rather
  than natural solver conclusions;
- the P6 loose completed extraction retained a stale `running` summary marker,
  so endpoint telemetry rather than that marker was used for interpretation.

These issues matter for reproducibility, but correcting them did not produce a
verified P6 answer.

## 11. Overall assessment

The classical campaign did not fail because one obvious method was omitted. It
tested approximate state evolution, permutation-aware MPS, MPO compression and
routing, route/controller variants, structural graph analysis, exact PyZX
rewrites, Clifford-augmented feasibility, KAK/mirror diagnostics, and
constraint-based reconstruction.

The consistent negative result is:

> approximate classical states either fail to converge across independent
> routes/methods, or complete only after losing the information needed for a
> peaked readout.

P6 therefore has no submission-grade classical candidate at present. A
Helios-1 hardware run is a reasonable next experimental path because Helios
avoids IBM's severe connectivity-routing expansion. It should nevertheless be
described as a hardware test of recoverability, not as a guaranteed solution.

## 12. Questions for an external expert

An expert review would be most useful on these points:

1. Is there a tensor-network representation that avoids route-dependent MPO
   decorrelation for this exact `u3`/`cz` circuit?
2. Does the P6 interaction structure suggest a non-MPS contraction ordering or
   separator decomposition that has not been tested?
3. Is the CAMPS nullity screen sufficient to reject a Clifford-frame approach,
   or is there a more informative residual-rotation representation?
4. Can a hybrid method use hardware to estimate a small, well-defined set of
   observables without assuming that noisy hardware can preserve the full
   62-bit peak?
5. What minimum Helios shot count and acceptance diagnostics would distinguish
   a genuine P6 signal from a noisy or diffuse hardware distribution?

## 13. Reproducibility pointers

The machine-readable P6 candidate ledger, constraints, and diagnostic outputs
are retained in the classical checkout under `results/`. The corresponding
P6/P8 IBM transpilation evidence and the current P8 hybrid prototype are in
this branch. No hidden target, portal feedback, or hardware result should be
added to candidate-generation inputs after the fact.
