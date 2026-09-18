# P6 KAK/oracle branch

This branch contains two isolated experiments:

* `scripts/p6_oracle_solver.py` converts exact Hamming-overlap observations
  into binary linear constraints and certifies per-bit min/max values with a
  MILP solver. The eight supplied post-hoc observations certify only bits 1 and
  8 (zero-based); they do not determine the answer.
* `scripts/p6_kak_analysis.py` extracts maximal contiguous pair-local blocks
  and records Qiskit's Weyl coordinates plus operator-Schmidt spectra.
  `scripts/p6_kak_midpoint.py` compares time-reflected midpoint signatures to
  shuffled controls.

On the checked-in P6 QASM, extraction produced 2,673 blocks from 3,494
two-qubit events, including 680 blocks with repeated entanglers. The bounded
midpoint test (`midpoint=5243`, `window=500`, 100 controls) produced:

* observed mean nearest Weyl distance: `0.0135606537`
* shuffled-control mean: `0.0137513160`
* z improvement: `0.28`
* exact nearest matches: `1080 / 1319`

This is not evidence of a meaningful global midpoint mirror. The exact-match
count is inflated by repeated/common canonical signatures (especially CZ-like
blocks), so it must not be interpreted as a recovery probability.

The extraction is intentionally a bounded first pass, not a claim that
contiguous textual blocks are the unique DAG-level logical decomposition.
