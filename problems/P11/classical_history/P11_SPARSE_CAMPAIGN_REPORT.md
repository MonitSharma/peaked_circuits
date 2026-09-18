# P11 sparse campaign report

## 1. Executive conclusion

The sparse-state route was falsified at the P9 control before any 98-bit port or
P11 sparse computation. The terminal state is
`NO_GO_SPARSE_METHODS_ON_P9`.

## 2. Terminal state

`NO_GO_SPARSE_METHODS_ON_P9`: qstvec and BASS fixed both failed to preserve the
known P9 peak at matched `k=2^14` and `k=2^16`; BASS adaptive did not complete
the first matched budget within a 10-minute bounded observation. No P11 sparse
probe was run.

## 3. P11 blindness

P11 blindness remained intact. No P11 answer, public candidate, scorer,
hardware/emulator result, or expected bitstring was accessed. The only target
used in supervised metrics was the known P9 calibration target.

## 4–6. Implementations and provenance

- qstvec: MIT, commit `545614fa196e2a77d96d408e0cdf39520684b251`, clean clone.
- BASS: MIT, commit `e591cf97316026da0cb681f787406361d1e5106e`, clean clone.
- Clones: `external/qstvec`, `external/bass`.
- Both published implementations use one 64-bit basis word; P9 is supported,
  while P11's 98 bits are not. No upstream source was silently rewritten.

The detailed distinction between published behavior, repository source, adapter
logic, and future modifications is in
`docs/P11_SPARSE_IMPLEMENTATION_AUDIT.md`.

## 7. Gate-convention audit and canonical adapter

Qiskit `Operator` matrices are the source of truth. The canonical adapter feeds
the same parsed QASM instruction stream to every method and records its hash:
`fcbf07c0c107dacd7807699cde0976248e37d96d53fa880e06ef2b02baf7d3bb` for P9.
Qiskit/qstvec use the first local qarg as the low bit; BASS's kernel indexes it
as the high bit, so only the BASS adapter applies the explicit `[0,2,1,3]`
row/column permutation. Measurement ordering is tracked separately.

## 8. Exact small-circuit validation

Four circuits passed: one-qubit gates, nonadjacent two-qubit gates, arbitrary
unitary/RZZ/SWAP content, and a measurement permutation case. All three paths
matched dense Qiskit statevectors at the preregistered `1e-10` fidelity gate.
Artifact: `results/p11_sparse_campaign/exact_validation.json`.

## 9. P9 protocol

The fixed-k protocol was preregistered in
`docs/P11_SPARSE_P9_PROTOCOL.md`: sequential top-k runs starting at 2^14 then
2^16, exact common gate stream, complex128, same initial state and output order.

## 10–12. qstvec and BASS P9 results

| method | k | runtime | target support | top-1 Hamming to P9 | final nnz |
|---|---:|---:|---:|---:|---:|
| qstvec | 16,384 | 29.4 s | no | 29 | 16,384 |
| BASS fixed | 16,384 | 75.3 s | no | 30 | 16,384 |
| qstvec | 65,536 | 132.2 s | no | 30 | 65,536 |
| BASS fixed | 65,536 | 778.5 s | no | 30 | 65,536 |
| BASS adaptive | 16,384 | >630 s | incomplete | not available | incomplete |

BASS fixed gamma-squared was approximately `2.23e-183` at 2^14 and
`8.59e-165` at 2^16, showing severe cumulative retained-mass collapse. The
fixed methods saturated their support early and showed no meaningful recovery
improvement at 2^16. BASS adaptive used only about 280–295 MB RSS during the
bounded observation but remained in repeated RDM optimization.

## 13–15. Matched comparisons and limitations

At equal k, BASS fixed did not outperform qstvec; both missed the target by
about 30 bits. BASS adaptive versus fixed cannot be a recovery comparison
because adaptive did not complete the first budget. Full P9 fidelity was not
fabricated; only sparse target/rank/weight, support, gamma, PR, runtime, and
RSS diagnostics were used.

## 16–18. Resource and escalation decision

All completed runs were sequential and under `caffeinate`. Peak observed RSS
was far below the 36 GiB host capacity. The 2^16 escalation was informative:
neither fixed method recovered the target or improved top-1 Hamming distance.
Further 2^18/2^20 runs, p-mass tests, and adaptive reruns were not justified by
the preregistered information-gain rule.

## 19–22. Gates and 98-bit work

- qstvec: `NO_GO_QSTVEC`.
- BASS fixed: `NO_GO_BASS_FIXED`.
- BASS adaptive: `NO_GO_BASS_ADAPTIVE_FEASIBILITY`; no material recovery result.
- Overall: `NO_GO_SPARSE_METHODS_ON_P9`.

No 98-bit key design, 98-bit validation, BASS Z-basis endpoint, or bounded P11
probe was attempted because no method earned a P9 GO.

## 23–25. Code changes and failed hypotheses

Added the canonical QASM adapter, exact-matrix convention conversions, common
metrics/provenance, sequential runner with wall guard, exact validation panel,
protocols, state/decision logs, and regression tests. The failed hypothesis was
that published top-k sparse methods would preserve the P9 peak at feasible
matched budgets; the adaptive-basis hypothesis was additionally infeasible at
the first budget under the bounded observation.

## 26–27. Supported and unsupported claims

Supported: the adapters are convention-correct on the tested exact panel;
qstvec and BASS fixed lose the P9 target at the tested budgets; BASS adaptive
has substantial computational overhead in this configuration; sparse P11 work
is not justified by these P9 results.

Unsupported: any claim about the P11 answer, P11 correctness, 98-bit sparse
scaling, or the ultimate capability of a separately optimized implementation.

## 28. Recommended next action

Stop this sparse campaign at the P9 falsification gate. Preserve the artifacts
and do not port either published implementation to 98 bits or run P11 without a
new, separately reviewed hypothesis and protocol.
