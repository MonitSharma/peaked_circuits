# Classical research overview

## Research question

Can peaked-circuit outputs be recovered classically, with answer-blind
tensor-network or structural methods, and can the result be distinguished from
truncation or readout artifacts?

## Circuit family

The campaign studies large circuits whose output distribution is expected to
contain a hidden sharp peak. Circuit size alone is not the relevant difficulty:
interaction geometry, routing, entanglement growth, and truncation trajectory
jointly determine whether a classical method preserves the peak.

## Validation philosophy

P5 and P9 are known-answer controls. A claimed recovery must have recorded
provenance, a frozen candidate, a separated distribution, and an independent
validation path. Gate completion without fidelity is explicitly insufficient.
Overlap feedback supplied after candidate generation is kept separate as
oracle-assisted analysis.

## Outcomes

| Problem | Qubits | Work gates | Status | Headline |
|---|---:|---:|---|---|
| P1 | 36 | 1,457 2q | `METHOD_EXHAUSTED` | diagnostic/provider evidence |
| P5 | 44 | 902 | `VERIFIED_CONTROL` | 44/44 at 6e-4 and 1.5e-3 |
| P6 | 62 | 2,593 | `UNRESOLVED` | tight cutoff stalls; loose cutoffs flatten |
| P8 | 40 | 808 | `SOLVED_CLASSICAL` | tail materialization, external 40/40 |
| P9 | 56 | 1,885 | `VERIFIED_CONTROL` | 56/56 across calibrated cutoffs |
| P11 | 98 | 1,984 | `METHOD_EXHAUSTED` | no blind candidate in local envelope |

## Methods investigated

The campaign covered ordinary and permutation MPS, midpoint MPO, routing and
absorption schedules, tail materialization, graph/ZX and CAMPS diagnostics,
Pauli propagation, SOP/rank-width screens, structural reconstruction, and
candidate-family adjudication. The [P6 matrix](../../problems/P6/METHOD_MATRIX.md)
is the detailed method-level account.

## Main lessons

P5 and P9 establish that the pipeline can preserve real peaks. P8 shows that a
near-complete MPO need not be discarded: materializing the residual four-gate
tail converted an 804/808 routing checkpoint into a validated answer. P6 is
different: its faithful route stalls much earlier, while the cutoff settings
that complete the traversal destroy the peak. P11 reaches an even stronger
entanglement/routing barrier on the available host.

## Reproducibility and limitations

Use [`REPRODUCIBILITY_CLASSICAL.md`](REPRODUCIBILITY_CLASSICAL.md) and the
machine-readable [results index](../../results/classical_index.json). This
repository reports measured method/resource outcomes, not impossibility
theorems. Long runs are preserved as evidence and are not routine smoke tests.
