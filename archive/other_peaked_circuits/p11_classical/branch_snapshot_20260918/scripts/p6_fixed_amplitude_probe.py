#!/usr/bin/env python3
"""Fixed-candidate amplitude adjudication for a P6 QASM circuit.

This tool deliberately treats candidates as fixed hypotheses.  It does not
consume or emit oracle-supplied overlap labels; those belong in post-hoc
analysis only.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn
from qiskit import QuantumCircuit
from qiskit.qasm2 import loads as qasm2_loads


def build_circuit(qasm_path: Path) -> QuantumCircuit:
    return qasm2_loads(qasm_path.read_text())


def amplitude_rehearse(circuit: qtn.Circuit, bitstring: str, optimizer: str) -> dict:
    """Estimate contraction cost without contracting the amplitude."""
    bits = [int(ch) for ch in bitstring]
    if len(bits) != circuit.N:
        raise ValueError(f"candidate has {len(bits)} bits; circuit has {circuit.N} qubits")
    target = circuit.amplitude(bits, rehearse=True, optimize=optimizer)
    if isinstance(target, dict):
        # quimb includes the complete tensor network in ``tn``.  It is useful
        # interactively, but enormous and not a reproducible report field.
        compact = {}
        for key, value in target.items():
            if key in {"tn", "tree"}:
                continue
            if isinstance(value, (int, float, str, bool)) or value is None:
                compact[key] = value
        if "tree" in target:
            compact["tree_summary"] = str(target["tree"])
        return compact
    return {"rehearsal": str(target)}


def parse_candidates(items: list[str]) -> list[tuple[str, str]]:
    candidates = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"candidate must be NAME=BITSTRING: {item}")
        name, bits = item.split("=", 1)
        if not name or not bits or any(ch not in "01" for ch in bits):
            raise ValueError(f"invalid candidate: {item}")
        candidates.append((name, bits))
    return candidates


def parse_reference_doc(path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text().splitlines():
        match = re.search(r"P6-(A\d+)\s*\|\s*`([01]+)`", line)
        if match:
            rows.append((f"P6-{match.group(1)}", match.group(2)))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qasm", type=Path)
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument("--candidate-doc", type=Path, action="append", default=[])
    parser.add_argument("--optimizer", choices=("greedy", "random-greedy"), default="greedy")
    parser.add_argument("--rehearse", action="store_true", help="estimate cost; do not contract amplitudes")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    candidates = parse_candidates(args.candidate)
    for doc in args.candidate_doc:
        candidates.extend(parse_reference_doc(doc))
    if not candidates:
        parser.error("provide --candidate and/or --candidate-doc")
    qc = build_circuit(args.qasm)
    circuit = qtn.Circuit(qc.num_qubits, dtype=np.complex128)
    # qiskit preserves QASM order; this mirrors the gate conversion used by
    # the existing P8 probe and supports the gates present in P6.
    for instruction in qc.data:
        op = instruction.operation
        qargs = instruction.qubits
        qubits = [qc.find_bit(q).index for q in qargs]
        if op.name == "u3":
            circuit.u3(*op.params, *qubits)
        elif op.name == "u":
            circuit.u(*op.params, *qubits)
        elif op.name == "cz":
            circuit.cz(*qubits)
        elif op.name == "iswap":
            circuit.iswap(*qubits)
        else:
            raise ValueError(f"unsupported gate in P6 QASM: {op.name}")

    rng = random.Random(args.seed)
    results = []
    for name, bits in candidates:
        for repeat in range(args.repeats):
            started = time.time()
            if args.rehearse:
                details = amplitude_rehearse(circuit, bits, args.optimizer)
            else:
                value = circuit.amplitude([int(ch) for ch in bits], optimize=args.optimizer)
                details = {"real": float(np.real(value)), "imag": float(np.imag(value)),
                           "probability": float(abs(value) ** 2)}
            row = {"name": name, "bitstring": bits, "repeat": repeat,
                   "optimizer": args.optimizer, "elapsed_s": time.time() - started,
                   **details}
            results.append(row)
            # Keep random-greedy runs independently seeded without affecting
            # the candidate data or any external oracle labels.
            if args.optimizer == "random-greedy":
                circuit.rng = rng

    report = {"schema": "p6-fixed-amplitude-probe-v1", "qasm": str(args.qasm),
              "n_qubits": qc.num_qubits, "n_operations": len(qc.data),
              "mode": "rehearsal" if args.rehearse else "amplitude", "results": results}
    rendered = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
