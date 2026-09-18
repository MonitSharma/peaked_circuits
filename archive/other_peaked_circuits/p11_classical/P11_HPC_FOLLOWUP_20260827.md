# P11 HPC bounded follow-up — 2026-08-27

## Result

`NO_GO_P11_ESCALATION`: the HPC environment was reproduced and the exact sparse
adapter panel passed, but the first bounded P9 MPO calibration did not make
useful progress. No full P11 run was launched, and P11 blindness was preserved.

## Environment

- Host: `LHC-104-070` (Ubuntu 24.04.4, kernel `6.8.0-134-generic`)
- Repository: `p11_classical`, commit `d7e355431e3ef975f6b9caf2f0c69cc56378af7f`
- Hardware: 4 NUMA nodes, 72 physical / 144 logical CPUs, approximately 503 GiB RAM
- Swap: 8 GiB configured, 0 bytes used throughout the run
- Python: 3.12.3 in `.venv-hpc`
- Pinned stack: NumPy 2.2.6, SciPy 1.15.3, Quimb 1.11.2, Cotengra 0.7.5,
  Numba 0.65.0, Qiskit 1.4.5, qiskit-quimb 0.0.10, plus the declared dev and
  quantum extras

Offline validation passed: 146 tests. The exact qstvec/BASS small-circuit panel
passed all 4 circuits. Ruff and mypy remain non-clean due existing repository
lint/type issues; they were not changed during this investigation.

## P9 calibration

| run | configuration | result |
|---|---|---|
| initial launch | 18 threads, NUMA node 3, max bond 512, cutoff 0.0006 | stopped before tensor work because the checked-in solver patch was applied at the wrong source locations and caused an `IndentationError` |
| `p9_18_baseline_retry_qr_fix` | 18 threads, CPUs 54–71, NUMA node 3, max bond 512, cutoff 0.0006, bond unswapping | stopped intentionally at 15/1,885 gates after 198 s; approximately 1.1 GiB RSS; swap remained 0 |

The retry used a separate solver branch, `codex/hpc-qr-guard-fix`, commit
`06e668047d2a2505cebb45cbbdd969ea6cbdea89`, retaining the QR compatibility guard
after restoring the malformed CLI/pipeline patch hunks. A Quimb QR fallback
warning was observed. The run produced a manifest and console log but no final
summary because it was stopped under the no-progress safety rule.

Artifacts are preserved under `results/hpc_followup/`. The full P11 campaign
was not started, and no P11 answer, candidate, scorer, emulator result, or hidden
target information was accessed.

## Recommendation

Keep P11 frozen. The current evidence shows HPC memory headroom, but no completed
P9 recovery gate or stable throughput baseline. Do not run 36/72-core scaling or
any P11 probe until the solver patch is repaired and a clean, reproducible P9
calibration completes with the documented safeguards.
