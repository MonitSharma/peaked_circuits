# IBM P6/P8 30-seed transpilation sweep

This was a local, transpilation-only study against the authenticated
`ibm_fez` backend. No IBM job was submitted and no QPU time was consumed.
Each circuit used optimization level 3 and `approximation_degree=1.0`.

## Summary

| Circuit | Logical 2q gates | Best transpiled 2q gates | Best 2q depth | Transpiled depth range | Duration range |
|---|---:|---:|---:|---:|---:|
| P6 | 3,494 | 24,076 (seed 9) | 3,930 (seed 6) | 9,466–11,119 | 0.372–0.436 ms |
| P8 | 888 | 3,956 (seed 23) | 690 (seed 7) | 1,987–2,529 | 0.0677–0.0853 ms |

Routing added 20,582 two-qubit gates for the best-count P6 mapping and 3,068
for the best-count P8 mapping. P6 used 64–74 physical qubits across the
sweep; P8 used 40 physical qubits.

## Calibration diagnostics

The calibration-weighted quantity is a diagnostic proxy, not a rigorous
fidelity estimate. Every P6 seed touched at least one CZ edge whose live
backend calibration record reported gate error `1.0`, so its independent
survival product is zero and should not be interpreted literally. This is an
additional warning that P6’s current mappings are unsuitable for a clean
hardware test. The best P6 two-qubit-count mapping was seed 9; the best depth
mapping was seed 6.

P8’s best-count and lowest weighted-error mapping was seed 23:

- 3,956 two-qubit gates
- 741 two-qubit depth
- 2,130 total depth
- 40 physical qubits
- 72.76 microseconds scheduled duration proxy
- mean calibrated CZ error 0.00308
- weighted-error survival proxy `4.86e-6`

The proxy is dominated by thousands of two-qubit operations and does not
predict the hidden-target score exactly, but it supports the observed IBM
P8 result: increasing from 1,000 to 8,000 shots produced only diffuse,
all-unique outputs.

Every seed’s initial/final layout and final measurement-to-classical map is
stored in `results/ibm_backend_sweep_20260830/p6_sweep.json` and
`p8_sweep.json`; aggregate metrics are in `sweep_metrics.csv`.

## Decision

Do not spend IBM QPU time on P6 with the current backend-aware compilation.
P8 is the only plausible exploratory candidate of the two, but this sweep
does not justify another large P8 run on the same compilation family. A
different layout strategy, noise-aware routing objective, or a circuit-level
reduction is needed before expecting a recoverable peak.
