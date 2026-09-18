# BlueQubit P1 audit

**Branch:** `bluequbit-p1-classical` (created from `p11_classical` at `1151be3`)

## Scope and controls

This branch is a separate P1 testbed. Historical P9 positive-control and P11
stress-control conclusions are unchanged. No BlueQubit, Quantinuum, QPU, or HPC
job is launched by this audit. The P1 answer remains blind; no expected output,
oracle, or verifier target is read.

The local challenge input is `/Users/monitsharma/Downloads/P1_little_dimple.qasm`.
It remains outside version control. Its SHA256 is
`0a02afffbdcf6755d5ed16b3a10cddd40cde4ee072d6072dbe7013e1c42f2ff8` and its
size is 219,814 bytes.

## Existing capability inventory

The repository already provides QASM event parsing, interaction graphs, temporal
fingerprints, sequence matching, unitary matching, dynamic permutation analysis,
MPO/MPS utilities, trajectory parsing, distillation tooling, and P9/P11 HPC
manifests. The existing `analyze_hqap_structure.py` and
`analyze_sequence_structure.py` are reusable for P9, P11, and P1; their default
search is midpoint-oriented, so this branch adds only a thin P1 input-only
forensics wrapper and explicit ratio cut scan.

The P9/P11 solver launcher and HPC scripts are not modified. The pinned external
solver remains external and ignored by Git; any future patch must be stored as an
explicit hashable patch before use.

## Audit result

The first P1 run of the existing structural tool completed successfully with
windows 64, 128, and 256 and 24 shuffled controls per point. It found a strong
raw mirror/graph signal around several cuts, but this is not yet evidence of a
recoverable inverse or permutation: the tool itself records that its optimized
matching null is not a fair optimized null. The next step is fairer sequence
controls, cut ranking, and bounded routing/ordering probes.

The “average degree 80.9” claim must not be used for P1. A simple unweighted
degree on 36 vertices is at most 35. The new audit reports separately: unique
partners and simple degree, weighted degree/interaction frequency, unique pair
count, and total two-qubit gate count.

## Reuse versus new work

| Area | Decision |
|---|---|
| QASM parsing and event representation | Reuse `structural.qasm_events` |
| Mirror and sequence fingerprints | Reuse existing structural scripts |
| Routing telemetry | Reuse `scripts/parse_routing_trajectories.py` |
| Distillation | Reuse `tools/run_mps_distillation.py` and artifact builder |
| P1 statistics, weighted/unweighted distinction, ratio cuts | New `scripts/analyze_bluequbit_p1.py` |
| P1-specific campaign state/HPC shortlist | Add only after Mac evidence |

## Initial test status

The project `.venv` contains NumPy, Matplotlib, and pytest. The system Python
does not contain those dependencies. Full non-hardware pytest and focused P1
analysis are part of the next audit step; no hardware/API tests are permitted.
