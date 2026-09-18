#!/usr/bin/env python3
"""Benchmark generic qstvec CZ evolution versus the local in-place kernel."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from p12_recovery.bluequbit.sparse_sv import SparseState
from structural.qasm_events import parse_qasm


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--support", type=int, default=65536)
    parser.add_argument("--repetitions", type=int, default=100)
    args = parser.parse_args()
    sys.path.insert(0, "external/qstvec/src")
    from qstvec import Statevector as GenericStatevector

    circuit = parse_qasm(args.qasm)
    gates = list(circuit.two_qubit)[: args.repetitions]
    rng = np.random.default_rng(20260828)
    basis = np.arange(args.support, dtype=np.int64)
    alpha = rng.normal(size=args.support) + 1j * rng.normal(size=args.support)
    alpha = alpha.astype(np.complex128)
    alpha /= np.linalg.norm(alpha)
    specialized = SparseState(circuit.n_qubits, basis=basis, alpha=alpha.copy())
    generic = GenericStatevector(circuit.n_qubits)
    generic.basis = basis.copy()
    generic.alpha = alpha.copy()
    t0 = time.perf_counter()
    for event in gates:
        specialized.evolve_cz(*event.wires)
    specialized_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    cz = np.diag([1, 1, 1, -1]).astype(np.complex128)
    for event in gates:
        generic.evolve(cz, event.wires)
    generic_s = time.perf_counter() - t0
    order = np.argsort(generic.basis)
    expected = specialized.alpha[np.argsort(specialized.basis)]
    actual = generic.alpha[order]
    result = {"schema": "bluequbit-p1-v2-sparse-kernel-benchmark-v1", "blind": True, "qasm_sha256": __import__("hashlib").sha256(args.qasm.read_bytes()).hexdigest(), "support": args.support, "cz_gates": len(gates), "specialized_seconds": specialized_s, "generic_seconds": generic_s, "speedup": generic_s / specialized_s if specialized_s else None, "max_abs_error": float(np.max(np.abs(expected - actual))), "support_preserved": specialized.support == args.support == generic.basis.size}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
