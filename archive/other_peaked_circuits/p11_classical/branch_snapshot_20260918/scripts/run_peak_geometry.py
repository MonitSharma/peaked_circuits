#!/usr/bin/env python3
"""Bounded native-graph PEPS probe for sparse P8-like circuits.

This is a geometry-aware approximation diagnostic. Its product-marginal
bitstring is never treated as a joint MAP candidate or exact recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn
from qiskit import QuantumCircuit

ISWAP = np.array([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]], dtype=np.complex128)


def run(args: argparse.Namespace) -> dict:
    source = Path(args.qasm)
    qc = QuantumCircuit.from_qasm_file(str(source))
    qc.remove_final_measurements()
    edges = sorted({tuple(sorted(qc.find_bit(q).index for q in instruction.qubits)) for instruction in qc.data if len(instruction.qubits) == 2})
    circuit = qtn.CircuitPEPSSimpleUpdate(N=qc.num_qubits, edges=edges, max_bond=args.max_bond, cutoff=args.cutoff, dtype="complex128", renorm=True)
    started = time.monotonic()
    for instruction in qc.data:
        operation = instruction.operation
        qubits = [qc.find_bit(q).index for q in instruction.qubits]
        if operation.name in {"u", "u3"}:
            circuit.apply_gate("U3", *map(float, operation.params), qubits[0])
        elif operation.name == "iswap":
            circuit.apply_gate(ISWAP, *qubits)
        else:
            raise ValueError(f"unsupported operation: {operation.name}")
    projector = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.complex128)
    p0 = [float(np.real(circuit.local_expectation(projector, site, max_distance=args.max_distance, normalized=True))) for site in range(qc.num_qubits)]
    bitstring = "".join("1" if value < 0.5 else "0" for value in p0)
    return {"schema": "p12-peak-geometry-peps-v1", "method_family": "geometry_peps", "status": "COMPLETE", "answer_blind": True, "joint_map_claim": False, "qasm_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "n_qubits": qc.num_qubits, "unique_edges": len(edges), "max_bond": args.max_bond, "cutoff": args.cutoff, "max_distance": args.max_distance, "p0": p0, "product_marginal_diagnostic": bitstring, "weakest_margin": min(abs(value - 0.5) for value in p0), "runtime_s": time.monotonic() - started}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qasm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-bond", type=int, default=4)
    ap.add_argument("--cutoff", type=float, default=1e-10)
    ap.add_argument("--max-distance", type=int, default=2)
    args = ap.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        result = {"schema": "p12-peak-geometry-peps-v1", "status": "ABORTED", "answer_blind": True, "reason": f"{type(exc).__name__}: {exc}"}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
        return 2
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
