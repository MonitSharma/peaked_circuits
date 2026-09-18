# P6 repository audit — 2026-09-01

## Repository state

- Repository: `C:\Users\monitsharma\Downloads\SMU-Quantum\p12-helios-recovery`
- Branch: `p11_classical`
- HEAD at audit: `b55e69e`
- Existing user changes and generated artifacts were preserved; no destructive
  git operation was used.

## Relevant inputs and code

- P6 source: `results/expert_review_p5_p6_p8_20260828/inputs/P6_titan_pinnacle.qasm`
- P6 solver diagnosis: `docs/P6_MPO_DIAGNOSIS.md`
- MPO/routing implementation: `_upstream_peaked_mpo_solver/src/p9solver/`
- Existing PyZX reference: `scripts/run_pyzx_p9.py`
- P6 PyZX launcher: `scripts/run_pyzx_p6.py`
- P6 Clifford diagnostic: `scripts/p6_clifford_diagnostic.py`
- P6 structural metrics: `scripts/measure_pyzx_p6.py`

## Verified P6 statistics

The source hash is
`206b3c04173975143083e41152ca0d7612045cc43a44cc5f2a964340712f4ee4`.
Qiskit parsing reports 62 qubits, 6,992 `u3` operations, 3,494 `cz`
operations, 10,486 total operations, and depth 416.

## Controls and success criteria

The existing calibration record is
`docs/PEAKED_FIDELITY_CALIBRATION.md`. It establishes P5 and P9 as positive
controls, with P5 requiring 44/44 and P9 requiring 56/56, plus a non-flat
peaked readout rather than completion alone. The same record documents loose
cutoff behavior as a negative control.

The solver's routing and unswap paths are in `pipeline.py`; SVD truncation and
retention instrumentation are in `retention.py` and the corresponding pipeline
logging. The CLI writes progress, timing, truncation, and sampling summaries
under each run directory.

## Closed prior hypothesis

The layer-207 permutation/reconstruction hypothesis is already rejected by the
broader evidence in `docs/P6_MPO_DIAGNOSIS.md`. No contradictory artifact was
found during this audit, so it was not extended or given additional compute.

## Reproduction pointers

The exact commands and output paths for the Phase-A through Phase-D work are
recorded in `docs/P6_REPRESENTATION_INVESTIGATION_20260901.md`. The report
also records which Phase-E screens were unavailable or unsafe to run locally.

The handoff prompt for the next machine-level structural experiment is
`docs/P6_NEXT_EXPERIMENT_CODEX_PROMPT.md`.
