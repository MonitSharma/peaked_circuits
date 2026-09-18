# P8 method status

> **2026-08-31: FIRST P8 CANDIDATE PRODUCED.** The MPO tail-materialization
> route reached a sampled candidate that passes every fidelity gate calibrated
> on the verified P5 and P9 answers. See `docs/P8_TAIL804_CANDIDATE.md`.

## Scope

P8 is the 40-qubit circuit with 888 native `iSWAP` gates and 1816 `u3` gates,
consolidated to 808 unitary work gates. The objective is to obtain the exact
target bitstring using a classical tensor-network method.

## What was tried before the new method

The main line-MPO approach treated native `iSWAP` as a rank-4 two-qubit
operator, followed by greedy unswapping and routing. It repeatedly reached
roughly 779--799 of 808 work gates. The best recorded controller reached
804/808, but did not complete. Increasing the bond dimension, changing seeds,
cutoffs, patience, route selection, lookahead, and SWAP selection did not
remove the terminal routing attractor.

Other explored routes included permutation-MPS, PEPS/PEPO simple update,
weighted TTN, graph belief propagation, TNO feasibility probes, structural
local-unitary scans, and several routing proxies. None produced a validated
808/808 solution. Some MPS/TTN results were affected by truncation and were
not exact certificates.

## New idea: expose the iSWAP permutation

The exact identity used was

```text
iSWAP(a,b) = SWAP(a,b) · CZ(a,b) · (S(a) ⊗ S(b)).
```

The proposed representation applies the local `S` gates, applies a rank-2
`CZ`, and records the `SWAP` as a classical logical/physical permutation.
No SWAP tensor is emitted. The implementation is in
`src/p12_recovery/peak/iswap_frame.py`, with lowering in
`scripts/lower_p8_iswap_frame.py` and tests in `tests/test_iswap_frame.py`.

The transformation passed five local exactness and bookkeeping tests. It
produced a SWAP-free frame circuit containing 1816 `u3`, 1776 `s`, and 888
`cz` operations.

## Where the permutation-frame method failed

The frame circuit was run on HPC through the existing line-MPO solver. Under
the matched bounded settings (`D=512`, cutoff `6e-4`, seed `2024`), it achieved
only 4/808 work gates before no progress and reached the bond cap during
unswapping. The direct native-iSWAP control reached 101/808 in the same bounded
test and had a substantially lower peak bond.

This is a negative result for the combination:

```text
permutation-frame iSWAP representation + existing line-MPO unswap solver
```

It does not disprove the algebraic identity, and it does not test a genuine
geometry-preserving graph contraction. The line-MPO solver still pays for the
dynamic permutation through its one-dimensional ordering, so removing SWAP
tensors alone made the representation worse for that solver.

## Terminal-handoff method

The next method separates bulk compression from the final routing tail:

1. Run the native-iSWAP bulk MPO solver.
2. Stop before another unswap cycle when at most 12 work gates remain.
3. Save the live MPO, residual left/right layers, and mapping metadata.
4. Contract each residual side as one consolidated tail MPO at a temporary
   higher bond, rather than continuing the normal unswap controller.

The explicit handoff boundary was added as the tracked patch
`hpc/solver_patches/0002-p8-terminal-handoff.patch` and the tail consumer is
`scripts/solve_p8_tail_bundle.py`.

## Where this new method failed so far

The first experiment used the solver's older forced-tail-drain option. It did
not reach the terminal window: the run stalled around 784/808 and spent many
cycles in the same attractor. This shows that direct tail draining cannot fix
the problem if the controller never gets close enough to the tail.

The explicit handoff implementation was then added and synced to an isolated
HPC solver directory, leaving the user's active HPC checkout untouched. The
recorded 804/808 handoff bundle was subsequently consumed successfully by the
tail materializer. The resulting sample and beam-decoder outputs agree exactly
and pass the calibrated P8 fidelity gate; the bundle and provenance are linked
in `docs/P8_TAIL804_CANDIDATE.md`.

## Current conclusion

The evidence supports the following conclusion:

* The iSWAP permutation identity is correct but is not useful when inserted
  into the existing one-dimensional line-MPO solver.
* The P8 difficulty remains a routing/order and contraction issue, not an
  algebraic iSWAP issue.
* The explicit terminal handoff was validated from the recorded 804/808
  checkpoint: tail materialization produced the recorded 40/40 result with a
  3.8% peak and 6.44x top-1/top-2 separation.
* The most important unresolved research path is a native-grid,
  geometry-preserving contraction that keeps the iSWAP/CZ structure without
  forcing it into a line MPO. The existing result is preserved as a validated
  tail-materialization record, not as evidence that every clean replay reaches
  the same checkpoint.

Relevant commits on `p11_classical`:

* `250dbea` — exact iSWAP permutation frame
* `a80ff11` — frame smoke comparison evidence
* `f409f25` — explicit terminal handoff patch
* `6e81873` — global tail bundle contraction
