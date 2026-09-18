# P5 — granite summit

## Status

P5 is a positive known-answer control: the calibrated MPO route recovered the
known 44-bit answer at cutoff `6e-4` and independently at `1.5e-3`. It is a
validation control for methods, not a new unknown-answer submission.

## Methods and resources

The main route used midpoint MPO compression, SVD truncation, greedy unswapping,
SABRE routing, sampling, and beam decoding. Additional local-rescue and
calibration runs are retained. Resources include the P5 QASM input, the local
MPO solver checkout, Quimb, Qiskit, and the P9-openblas conda environment.

## Timing and evidence

Exact runtimes and peak statistics are in the per-run summaries. The key
calibration is 902/902 gates, peak fraction about 0.012, and top-1/top-2 about
7.8x at `6e-4`.

## Canonical records

See [ARTIFACTS.md](ARTIFACTS.md).
