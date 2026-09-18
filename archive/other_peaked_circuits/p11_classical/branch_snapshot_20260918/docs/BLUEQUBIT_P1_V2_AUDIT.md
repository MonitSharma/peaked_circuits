# BlueQubit P1 v2 Mac portfolio audit

This branch is `bluequbit-p1-mac-portfolio`, created from the verified v1
screening head `efd24d3e3d46f2f038d3bfddd7bfa09a50a52bd2`. The P1 input remains
local and uncommitted at `/Users/monitsharma/Downloads/P1_little_dimple.qasm`.
Its SHA256 is
`0a02afffbdcf6755d5ed16b3a10cddd40cde4ee072d6072dbe7013e1c42f2ff8` and its
size is 219,814 bytes.

The campaign is answer-blind. No P1 answer, verifier, cloud simulation, QPU,
P9 run, P11 run, P12 run, or HPC job was used. Historical P1 v1 artifacts are
read-only background evidence; P9/P11 conclusions are not reopened.

## Environment

The experiment environment is an Apple arm64 Mac running macOS 26.5.2 with
36,864 MiB nominal unified memory. The pinned experiment Python reports Python
3.10.16, NumPy 2.2.6, SciPy 1.15.3, Qiskit 1.4.5, Quimb 1.15.0, and MLX
0.32.2. Julia is available at `/Users/monitsharma/.juliaup/bin/julia`. The
qstvec checkout is local at `external/qstvec`, commit
`545614fa196e2a77d96d408e0cdf39520684b251`.
The public mirrored-TNO method was studied as a separate CPU probe using
`qiskit-quimb==0.0.10`; its source was not copied into `external/` or modified.
The same public repository's `CircuitPermMPS` bitstring-distillation workflow
was adapted separately, including its documented two-step permutation mapping.
The public `spd` sparse-Pauli implementation was also studied as a separate
representation; its source was not copied or modified.

## Verified input surface

The existing parser reports 36 qubits, 4,407 operations, 2,950 arbitrary
single-qubit `u` gates, 1,457 `cz` gates, depth 307, and two-qubit depth 153.
There are 564 unique interacting pairs. The simple unweighted mean degree is
31.333; the weighted interaction frequency mean is 80.944. The latter is not a
graph degree. The circuit contains no measurement events in the parsed input.

## Reuse and decision gates

The existing QASM parser and structural utilities are reused. Existing MPS is
retained only as a weak portfolio member because the v1 cross-seed evidence was
unstable. The new v2 work begins with a reusable profiler, then sparse-state
simulation and lightcone-guided PPS. BP and fixed-output amplitude contraction
remain gated until a method produces a serious blind candidate.

The single-qubit Clifford audit is now complete. Only 1.05% of `U` gates are
within `1e-6` phase-invariant Frobenius distance of a Clifford, and 1.46% are
within `1e-2`; the decision is `CLIFFORD_PERTURBATION_LOW_PRIORITY`.

The machine-readable audit is in `results/bluequbit_p1_v2/AUDIT.json`.
