# Results Directory Index

This directory organizes all verified pipeline deliverables, audit reports, simulation records, and scientific benchmark studies for the P12 Helios Recovery project.

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

---

## 3. P11 Routing & Entanglement Studies

In-depth tensor network routing diagnostics for the P11 peaked circuit:

| Path | Description |
| :--- | :--- |
| [`p11_diagnosis/`](./p11_diagnosis/) | Distilled trajectory CSVs (`routing_runs_summary.csv`, `routing_trajectories.csv`, `entanglement_growth.csv`), solver maxswap patch, and diagnosis results index. |
| [`p11_research/`](./p11_research/) | Intermediate research telemetry, stall checks, and candidate exploration logs. |

---

## 4. Local Execution & Sweeps

- Heavy, uncommitted parameter sweep run directories and raw checkpoint files are organized in [`../experiments/runs/`](../experiments/runs/) to keep this repository clean and lightweight.

## 5. P11/P12 public evidence packages

The canonical human-facing problem index is [`../problems/`](../problems/).
The self-contained packages for the externally accepted P11 and P12 hardware
recoveries are in [`tracker_submissions/`](./tracker_submissions/). They contain
the source QASM, raw provider artifacts, normalized shots, plots, measured
classical runtimes, reproducibility scripts, and tracker issue drafts.

The older [`quantinuum/`](./quantinuum/) layout is retained for historical link
compatibility and is not the preferred entry point for a new reader.
