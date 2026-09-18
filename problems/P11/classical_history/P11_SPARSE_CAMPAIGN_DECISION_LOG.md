# Sparse campaign decision log

## 2026-08-27 — Start sparse falsification campaign

- Hypothesis: a sparse representation may preserve P9 peak information despite
  the MPO extraction no-go.
- Evidence: P11 MPO extraction is already closed at `NO_GO_MAP_DECODER`; sparse
  methods are materially different and both published implementations support
  P9's 56-bit width.
- Selected action: audit and exact-validate qstvec, BASS fixed, and BASS
  adaptive before any P9 budget escalation.
- Expected information gain: distinguish adapter/circuit-convention bugs from
  genuine sparse-method failure at low cost.
- Expected cost: small-circuit tests plus bounded sequential P9 smoke runs.
- Gate: no P9 full run until exact validation passes; no P11 until P9 GO.

## 2026-08-27 — Exact gate passes; matched P9 sparse gate fails

- Hypothesis: a published sparse representation may retain the P9 peak at a
  feasible matched top-k budget.
- Evidence: all four exact small circuits passed; qstvec at 2^14 and 2^16 and
  BASS fixed at 2^14 and 2^16 completed but had no target support and top-1
  Hamming distances 29–30. BASS adaptive at 2^14 exceeded a 10-minute bounded
  observation in RDM optimization without completing, at low RSS.
- Selected action: terminate before 98-bit changes, further k escalation, or
  P11 probes.
- Why: neither fixed method showed improvement from 2^14 to 2^16, and adaptive
  BASS was not feasible at the first matched budget. Further runs would not
  change the preregistered P9 decision efficiently.
- Gate result: `NO_GO_SPARSE_METHODS_ON_P9`.
