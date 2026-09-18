#!/usr/bin/env python3
"""Validate the sparse U3+iSWAP kernels against Qiskit Statevector."""
from __future__ import annotations

import argparse
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from p12_recovery.bluequbit.profile import _u_matrix
from p12_recovery.bluequbit.sparse_sv import SparseState


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qubits", type=int, default=5)
    parser.add_argument("--gates", type=int, default=40)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    qc = QuantumCircuit(args.qubits)
    sparse = SparseState(args.qubits)
    for _ in range(args.gates):
        if rng.random() < 0.55:
            q = int(rng.integers(args.qubits))
            theta, phi, lam = rng.uniform(-np.pi, np.pi, 3)
            qc.u(theta, phi, lam, q)
            sparse.evolve_u(_u_matrix(theta, phi, lam), q)
        else:
            q0, q1 = rng.choice(args.qubits, 2, replace=False)
            q0, q1 = int(q0), int(q1)
            qc.iswap(q0, q1)
            before = sparse.support
            sparse.evolve_iswap(q0, q1)
            assert sparse.support == before
    expected = Statevector.from_instruction(qc).data
    actual = np.zeros(1 << args.qubits, dtype=np.complex128)
    actual[sparse.basis] = sparse.alpha
    error = float(np.max(np.abs(actual - expected)))
    if error > 1e-12:
        raise SystemExit(f"Qiskit control failed: max_abs_error={error:.3e}")
    print(f"qiskit-control-ok qubits={args.qubits} gates={args.gates} max_abs_error={error:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
