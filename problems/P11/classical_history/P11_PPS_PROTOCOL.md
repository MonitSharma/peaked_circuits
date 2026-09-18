# P11 Classical PPS protocol

This document records the answer-blind PauliPropagation.jl campaign requested for the `p11_classical` branch.

## Scope and safeguards

- Use only the canonical local QASM files and the independent PauliPropagation.jl backend.
- Do not reopen MPS, MPO, qstvec, BASS, or prior solver paths.
- P9 is the validation control. P11 is blind: only its local QASM structure, gate counts, and generic package documentation may be inspected. No P11 answer, candidate, issue, or external scorer is consulted.
- Preserve the existing dirty HPC checkout and all artifacts. No reset, clean, or deletion.

## Environment

- HPC checkout: `/home/hclau/p12-helios-recovery`, branch `p11_classical`.
- Julia: 1.10.10, user-local at `/home/hclau/tools/julia-1.10.10/bin/julia`.
- PauliPropagation.jl: exact commit `5c7bf06b95904e7cc8b327165963e616265ecd71`.
- Backend: `VectorPauliSum`; Heisenberg Z observables; `max_weight=Inf`; no `mcpropagate`.
- Threshold ladder: `1e-2`, `3e-3`, `1e-3`, `3e-4`, `1e-4`; thresholds are run only when authorized by the preceding gate.
- Nested BLAS threads: 1. Thread-scaling points: Julia threads 1, 4, 8, and 18 on one NUMA node.

## Gates

1. Export the canonical QASM stream with Qiskit, preserving gate order and mapping Qiskit zero-based qubits to Julia one-based qubits.
2. Validate native mappings and generic transfer-map fallbacks against dense Qiskit expectations at error `<=1e-10` with no truncation.
3. Run the fixed P9 smoke panel at positions `1, 8, 16, 24, 32, 40, 48, 56`.
4. Continue P9 convergence only if the smoke result contains a nonzero, resource-safe signal. A P9 GO requires at least 7/8 correct signs and stability at the tighter threshold.
5. Only after strict P9 GO may the blind P11 panel be run at positions `1, 14, 28, 42, 56, 70, 84, 98`.

The campaign must terminate using one of the defined protocol states, including `NO_GO_PPS_P9_SMOKE`, `NO_GO_PPS_P9`, `GO_PPS_P11`, `NO_GO_P11_PPS_SCALING`, `NO_REPRODUCIBLE_P11_PPS_SIGNAL`, or `NEEDS_DEPENDENCY_STAGING`.
