# P9 — positive classical control

**Outcome:** `VERIFIED_CONTROL`

## Problem

P9 is the 56-qubit canonical peaked circuit with 1,885 work gates. Source:
[`peaked_circuit_P9_Hqap_56x1917.qasm`](../../data/canonical/peaked_circuit_P9_Hqap_56x1917.qasm),
SHA-256 `cff3496c45d9133c1f1693f1d3b0cf1fc2da338f13cd7b339db330a4762d0f35`.

## Scientific objective

P9 is the larger known-answer control used to calibrate whether traversal,
truncation, and readout preserve a real peak. It anchors comparisons with the
unresolved P6 case.

## Headline result

| Cutoff | Fidelity | Peak fraction | Top1/top2 |
|---|---:|---:|---:|
| `6e-4` | 56/56 | 0.048 | 5.3× |
| `1.5e-3` | 56/56 | 0.098 | 23.1× |
| `2e-3` | 56/56 | 0.086 | 4.5× |

## Methods and artifacts

The calibrated MPO controls and run provenance are summarized in
[`PEAKED_FIDELITY_CALIBRATION.md`](../../docs/PEAKED_FIDELITY_CALIBRATION.md)
and listed in [`ARTIFACTS.md`](ARTIFACTS.md). These results show that a looser
cutoff can sharpen a valid peak on one circuit; they do not transfer that
conclusion automatically to P6.

## Limitations

P9 is a known-answer control. Provider/HPC variants must be distinguished from
the validated reference rather than silently pooled with it.
