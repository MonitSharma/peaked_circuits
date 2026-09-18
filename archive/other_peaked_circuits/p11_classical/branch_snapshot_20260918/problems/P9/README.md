# P9

## Status

P9 is a positive known-answer control with multiple validated MPO settings,
including cutoff `6e-4`, `1.5e-3`, and `2e-3`.

## Methods and resources

Used midpoint MPO compression, routing/unswapping, multiple seeds, local
rescue, structural unscrambling, and fidelity calibration. Resources include
the canonical P9 QASM, the local solver, Quimb/Qiskit, MettleQ and emulator
controls, and structural-analysis scripts.

## Timing and evidence

The calibration report contains exact per-run timing and quality metrics. The
strongest recorded mode is at `1.5e-3`, with 56/56 overlap and top-1/top-2
about 23.1x.

## Canonical records

See [ARTIFACTS.md](ARTIFACTS.md).
