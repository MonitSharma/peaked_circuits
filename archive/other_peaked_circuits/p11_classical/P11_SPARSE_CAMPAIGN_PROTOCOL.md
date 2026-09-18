# P11 sparse-state campaign protocol

Status: preregistered before sparse experiments.

## Question and blindness

This campaign tests whether sparse-state representations preserve peaked-circuit
output information that the completed MPO extraction path did not preserve.
P11 remains blind: no public P11 candidate, scorer, hardware result, emulator
result, or expected bitstring may be accessed. P9 is the only known-answer
control.

The comparison is deliberately three-way:

1. qstvec top-k computational-basis simulation;
2. BASS `FixedBasisSimulator` top-k;
3. BASS adaptive-basis simulation.

P9 is the falsification filter. No P11 sparse run or 98-bit port is allowed
before exact small-circuit validation and the relevant P9 gate pass.

## Frozen implementation policy

Published upstream code is retained under `external/qstvec` and `external/bass`.
The initial adapter feeds exact matrices obtained from Qiskit `Operator` objects,
not convenience gate classes, so gate-angle conventions are tested rather than
assumed. All methods receive the same canonical parsed gate stream and QASM hash.

The upstream one-word basis-key limitation is recorded explicitly. P9 (56 bits)
is in scope; P11 (98 bits) is out of scope until a method earns a P9 GO gate.

## Exact-validation gate

Before full P9 runs, use dense Qiskit statevectors on a representative panel of
small circuits: 1q gates, 2q gates, arbitrary unitary matrices, CZ, RZZ, mixed
fragments, nonadjacent labels, and measurement permutations. qstvec, BASS fixed,
and BASS adaptive-without-effective-truncation must satisfy fidelity at least
`1 - 1e-10`, plus norm, amplitude, probability, top-1, and ordering checks.

Any failure is a blocking correctness issue and must be fixed and regression
tested before P9.

## Matched P9 budgets and escalation

Primary budgets are `k = 2^14, 2^16, 2^18, 2^20`, run sequentially. Start with
`2^14` and `2^16`; escalate only when the preceding result is informative and
resource-safe. All three methods use identical P9 QASM, complex128, initial
`|0...0>`, top-k truncation, canonical output ordering, and deterministic seeds.

For every selected run record target rank/presence/weight, top-1 Hamming
distance, rank-1/rank-2 gap when meaningful, final/max support, truncation and
retained-mass diagnostics, participation ratio, wall time, peak RSS, and exact
provenance.

The primary causal comparison is BASS adaptive versus BASS fixed at the same k.
The secondary comparison is qstvec versus BASS fixed. Fixed-time comparisons,
qstvec p-mass, and any 98-bit work are secondary and require a justified GO.

## P9 gates

`GO_QSTVEC_98` requires a feasible tested budget with P9 target top-1 (preferred)
or a documented, predeclared near-top-1 condition, stable/improving with k, and
credible scaling. Otherwise `NO_GO_QSTVEC`.

`GO_BASS_98` requires BASS P9 recovery and a material same-k improvement of
adaptive over fixed (target rank/weight, Hamming, retained mass, or PR), not a
minor rank change. Otherwise `NO_GO_BASS_ADAPTATION` or `NO_GO_BASS` as
appropriate.

If all methods fail P9 at the largest informative safe budget, stop with
`NO_GO_SPARSE_METHODS_ON_P9` and do not port to 98 bits.

## Safety and provenance

Heavy jobs run sequentially under `caffeinate`, with bounded wall time and RSS
monitoring. No run directory is overwritten. Each result records repository and
upstream SHAs, dirty states, QASM and canonical-stream hashes, environment,
command, timing, RSS, termination, and artifact hashes.
