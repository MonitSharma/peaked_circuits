#!/usr/bin/env python3
# ruff: noqa: E402
"""Run exact algebraic normalization and emit metrics/QASM."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit, qasm2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.normalization import normalize_exact


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasm", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    circuit = QuantumCircuit.from_qasm_file(args.qasm)
    result = normalize_exact(circuit)
    args.output.mkdir(parents=True, exist_ok=True)
    qasm_path = args.output / f"{args.qasm.stem}.normalized.qasm"
    qasm_path.write_text(qasm2.dumps(result.circuit))
    payload = {
        "schema": "exact-normalization-v1",
        "input": str(args.qasm),
        "input_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "output": str(qasm_path),
        "output_sha256": hashlib.sha256(qasm_path.read_bytes()).hexdigest(),
        "passes": result.passes,
        "before": result.before.__dict__,
        "after": result.after.__dict__,
        "two_qubit_reduction_fraction": 1.0 - result.after.two_qubit_gates / max(1, result.before.two_qubit_gates),
        "exact_mode": True,
        "approximate_synthesis": False,
    }
    (args.output / "summary.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
