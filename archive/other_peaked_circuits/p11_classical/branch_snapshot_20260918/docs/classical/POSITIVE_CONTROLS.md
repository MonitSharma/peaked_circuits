# Positive controls in the classical campaign

P5 and P9 are known-answer controls. They are part of the scientific method,
not merely convenient solved examples: a candidate-producing method is useful
only if it preserves a known peak under comparable conditions.

P5 returns 44/44 at cutoff `6e-4` and `1.5e-3`, with peak fraction about 0.012.
P9 returns 56/56 at `6e-4`, `1.5e-3`, and `2e-3`; the `1.5e-3` control has peak
fraction about 0.098 and top1/top2 about 23.1×. In contrast, P6 can complete at
`1.875e-3` or `2e-3` while producing a flat distribution.

These controls reject the tempting inference that completion, low tensor size,
or a plausible structural statistic implies fidelity. They also close several
apparently promising shortcuts—CAMPS-like diagnostics, Pauli propagation,
patch invariants, and sparse approximations—when those shortcuts fail to
preserve the controls or do not produce a complete candidate.

See [`PEAKED_FIDELITY_CALIBRATION.md`](../PEAKED_FIDELITY_CALIBRATION.md),
[`problems/P5/CANONICAL.md`](../../problems/P5/CANONICAL.md), and
[`problems/P9/CANONICAL.md`](../../problems/P9/CANONICAL.md).
