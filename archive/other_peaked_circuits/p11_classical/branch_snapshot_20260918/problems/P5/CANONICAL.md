# P5 — positive classical control

**Outcome:** `VERIFIED_CONTROL`

## Problem

P5 is the 44-qubit `u3+cz` control circuit with 902 consolidated work gates
(1,892 two-qubit gates in the source representation). Source QASM:
[`P5_granite_summit.qasm`](../../results/expert_review_p5_p6_p8_20260828/inputs/P5_granite_summit.qasm).
SHA-256: `cee80b7bcdb61c87729853adcfd80e0aa3a20da54e29127eef180cfa65e6c386`.

## Scientific objective

P5 has a known answer and therefore tests whether the classical pipeline
preserves a genuine peak. It is a control, not evidence that the blind P6
problem is solved.

## Headline result

| Configuration | Fidelity | Peak fraction | Separation |
|---|---:|---:|---:|
| cutoff `6e-4` | 44/44 | 0.012 | 7.8× |
| cutoff `1.5e-3` | 44/44 | 0.012 | 6.3× |

## Methods and interpretation

| Method | Outcome | Evidence |
|---|---|---|
| D512 MPO, faithful cutoff | passed known-answer control | [`PEAKED_FIDELITY_CALIBRATION.md`](../../docs/PEAKED_FIDELITY_CALIBRATION.md) |
| cutoff `2e-3` | 42/44 | demonstrates that loose completion can degrade fidelity |

Reproduction details and retained run paths are in [`ARTIFACTS.md`](ARTIFACTS.md).
The control is used to reject methods that look structurally plausible but
destroy a peak.

## Limitations

The answer is known for this control; it is not a blind discovery claim.
