# Results Directory Index

This directory organizes all verified pipeline deliverables, audit reports, simulation records, and scientific benchmark studies for the P12 Helios Recovery project.

Problem-level navigation is available in [`../problems/`](../problems/). Each problem manifest points
to the canonical result directories below and records the associated methods, resources, timing, and
evidence status. Historical result paths are intentionally unchanged.

---

## 1. Core Milestone Deliverables & Verification Artifacts

These folders and reports contain deterministic outputs generated during Milestones 1–4 of the recovery protocol:

| Path | Description |
| :--- | :--- |
| [`compilation/`](./compilation/) | Exact-target compilation reports, circuit DAGs, and measurement maps. |
| [`mapping_validation/`](./mapping_validation/) | Validation of logical-to-physical qubit mappings and reversible test cases. |
| [`nexus/`](./nexus/) | Quantinuum Nexus integration artifacts: syntax check jobs, emulator mapping reports, and cost estimates. |
| [`qir/`](./qir/) | Deterministic P12 QIR (`.ll`, `.bc`), pyqir validation, and logical-to-QIR result maps. |
| [`synthetic/`](./synthetic/) | Synthetic target benchmark outputs and statistical recovery confidence metrics. |
| [`manifests/`](./manifests/) | SHA256 integrity manifests and run metadata for verified steps. |
| [`figures/`](./figures/) | Rendered circuit diagrams, interaction graphs, and layout graphs. |
| [`hardware_readiness_report.json`](./hardware_readiness_report.json) | Comprehensive hardware gate readiness report. |
| [`readiness_evidence.json`](./readiness_evidence.json) | Machine-readable evidence bundle for Quantinuum execution gates. |
| [`public_audit.md`](./public_audit.md) / [`.json`](./public_audit.json) | Full public release audit verifying no credentials or paid jobs were submitted. |

---

## 2. P9 Solver Benchmarks & Contraction Optimization

Classical MPO/MPS benchmark studies and contraction performance optimizations for the P9 peaked circuit:

| Path | Description |
| :--- | :--- |
| [`p9_optimization/`](./p9_optimization/) | Contraction dynamics, SVD method comparisons, multi-seed validation, and finalists summary. |
| [`p9_rescale1e12_regression_20260815/`](./p9_rescale1e12_regression_20260815/) | Rescaling regression check (1e-12 threshold). |
| [`p9_rescale1e6_regression_20260815/`](./p9_rescale1e6_regression_20260815/) | Rescaling regression check (1e-6 threshold). |
| [`p9_rescale1e6_drop_20260816/`](./p9_rescale1e6_drop_20260816/) | Threshold drop evaluation under rescale conditions. |

## 2a. P5/P6/P8 recovery campaign

| Path | Description |
| :--- | :--- |
| [`p5_p6_p8_recovery/P5/`](./p5_p6_p8_recovery/P5/) | P5 known-answer calibration and recovery records. |
| [`p5_p6_p8_recovery/P6/`](./p5_p6_p8_recovery/P6/) | P6 MPO, cutoff, structural, candidate, and endpoint records. |
| [`p5_p6_p8_recovery/P8/`](./p5_p6_p8_recovery/P8/) | P8 routing, tail-materialization, and candidate records. |
| [`new_p6_p8_20260831/`](./new_p6_p8_20260831/) | Later P6/P8 representation and structural investigations. |

---

## Curated classical index

[`classical_index.json`](classical_index.json) is the machine-readable index of
major classical outcomes. Validate it with:

```bash
.venv/bin/python ../scripts/validate_classical_index.py
```

It is a navigation and provenance layer; raw result bundles remain authoritative
for detailed numerical evidence.

## 3. P11 Routing & Entanglement Studies

In-depth tensor network routing diagnostics for the P11 peaked circuit:

| Path | Description |
| :--- | :--- |
| [`p11_diagnosis/`](./p11_diagnosis/) | Distilled trajectory CSVs (`routing_runs_summary.csv`, `routing_trajectories.csv`, `entanglement_growth.csv`), solver maxswap patch, and diagnosis results index. |
| [`p11_research/`](./p11_research/) | Intermediate research telemetry, stall checks, and candidate exploration logs. |

---

## 4. Local Execution & Sweeps

- Heavy, uncommitted parameter sweep run directories and raw checkpoint files are organized in [`../experiments/runs/`](../experiments/runs/) to keep this repository clean and lightweight.
