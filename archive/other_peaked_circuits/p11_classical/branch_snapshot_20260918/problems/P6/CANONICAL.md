# P6 — unresolved classical outlier

**Outcome:** `UNRESOLVED`

## Problem

P6 is the 62-qubit `u3+cz` circuit from
[`P6_titan_pinnacle.qasm`](../../results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm).
Its source hash is `206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4`;
the campaign records 3,494 CZ gates, 6,992 U3 gates, and 2,593 work gates.

## Scientific objective

Find the peaked 62-bit output with an answer-blind classical method, while
using P5/P9 as positive controls. A complete traversal is not sufficient: the
final samples must retain a separated, reproducible peak and survive fidelity
checks.

## Headline result

| Configuration | Traversal | Readout |
|---|---:|---|
| D512, cutoff `6e-4` | typically stalls around 138–150 | no promoted candidate |
| cutoff `1.875e-3`, flip 2 | 2,593/2,593 | flat; peak fraction about 0.001 |
| cutoff `2e-3` | 2,593/2,593 | flat; top1/top2 about 1.02–1.06× |

The complete loose-cutoff traversals are evidence that completion and fidelity
are separate conditions. They do not establish a P6 answer.

## Methods attempted

The complete matrix is [`METHOD_MATRIX.md`](METHOD_MATRIX.md). The concise
closure statement is [`CLASSICAL_EXHAUSTION_SUMMARY.md`](CLASSICAL_EXHAUSTION_SUMMARY.md).
The candidate ledger and raw run paths are listed in [`ARTIFACTS.md`](ARTIFACTS.md).

## Why unresolved

Tight cutoffs preserve information but couple routing to growing tensors and
stall. Relaxing the cutoff permits traversal but destroys the peak before
readout. Structural, Pauli, CAMPS, PyZX, rank-width, patch-invariant, and
candidate-ranking screens did not produce a verified blind candidate.

## Limitations

`UNRESOLVED` describes the scientific result. It is not a theorem that P6 is
classically impossible. Oracle-supplied overlap scores are retained only as
post-hoc analysis and were not used to tune candidate generation.
