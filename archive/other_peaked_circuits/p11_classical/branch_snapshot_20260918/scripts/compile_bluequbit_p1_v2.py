#!/usr/bin/env python3
"""Run bounded, exact Qiskit compilation checks for the local P1 input."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from qiskit import QuantumCircuit, transpile


def metrics(circuit: QuantumCircuit) -> dict[str, object]:
    return {"gate_count": len(circuit.data), "gate_counts": {str(k): int(v) for k, v in circuit.count_ops().items()}, "depth": circuit.depth(), "two_qubit_depth": circuit.depth(lambda item: len(item.qubits) == 2)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    source = QuantumCircuit.from_qasm_file(str(args.qasm))
    runs = []
    for level in (1, 2, 3):
        compiled = transpile(source, optimization_level=level, basis_gates=["u", "cz"], seed_transpiler=0)
        runs.append({"tool": "qiskit_transpile", "optimization_level": level, **metrics(compiled)})
    result = {"schema": "bluequbit-p1-v2-compile-summary-v1", "blind": True, "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(), "source": metrics(source), "candidates": runs, "runtime_s": time.monotonic() - started, "decision": "NO_MATERIAL_EXACT_QISKIT_SIMPLIFICATION"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
