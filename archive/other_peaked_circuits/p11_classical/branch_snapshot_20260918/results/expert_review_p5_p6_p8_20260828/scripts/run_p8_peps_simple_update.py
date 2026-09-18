#!/usr/bin/env python3
"""Run native-graph PEPS simple-update marginals for the P8 iSWAP circuit."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn
from qiskit import QuantumCircuit


ISWAP = np.array(
    [
        [1, 0, 0, 0],
        [0, 0, 1j, 0],
        [0, 1j, 0, 0],
        [0, 0, 0, 1],
    ],
    dtype=np.complex128,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("qasm", type=Path)
    ap.add_argument("--max-bond", type=int, default=16)
    ap.add_argument("--cutoff", type=float, default=1e-2)
    ap.add_argument("--max-distance", type=int, default=1)
    ap.add_argument("--sites", help="Comma-separated logical sites to evaluate (default: all)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    qc = QuantumCircuit.from_qasm_file(str(args.qasm))
    qc.remove_final_measurements()
    edges = sorted({tuple(sorted(qc.find_bit(q).index for q in inst.qubits))
                    for inst in qc.data if len(inst.qubits) == 2})
    if any(len(edge) != 2 for edge in edges):
        raise ValueError("Only one- and two-qubit gates are supported")

    started = time.monotonic()
    circuit = qtn.CircuitPEPSSimpleUpdate(
        N=qc.num_qubits,
        edges=edges,
        max_bond=args.max_bond,
        cutoff=args.cutoff,
        dtype="complex128",
        # Repeated real-time simple updates can overflow their Vidal gauges
        # even for unitary gates. Per-bond renormalization keeps the
        # approximate state numerically representable.
        renorm=True,
    )
    for instruction in qc.data:
        operation = instruction.operation
        qubits = [qc.find_bit(q).index for q in instruction.qubits]
        if operation.name in {"u", "u3"}:
            circuit.apply_gate("U3", *map(float, operation.params), qubits[0])
        elif operation.name == "iswap":
            circuit.apply_gate(ISWAP, *qubits)
        else:
            raise ValueError(f"Unsupported operation: {operation.name}")

    projector = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.complex128)
    sites = list(range(qc.num_qubits)) if args.sites is None else [int(x) for x in args.sites.split(",")]
    if any(site < 0 or site >= qc.num_qubits for site in sites):
        raise ValueError("--sites contains an out-of-range site")
    p0 = []
    for site in sites:
        value = circuit.local_expectation(
            projector, site, max_distance=args.max_distance, normalized=True
        )
        p0.append(float(np.real(value)))
    bitstring = "".join("1" if value < 0.5 else "0" for value in p0)
    result = {
        "schema": "bluequbit-p8-peps-simple-update-v1",
        "qasm": str(args.qasm),
        "qasm_sha256": hashlib.sha256(args.qasm.read_bytes()).hexdigest(),
        "n_qubits": qc.num_qubits,
        "gate_count": qc.size(),
        "unique_edges": len(edges),
        "max_bond": args.max_bond,
        "cutoff": args.cutoff,
        "max_distance": args.max_distance,
        "sites": sites,
        "dtype": "complex128",
        "iswap_definition": "explicit_matrix_q0q1=[1, iSWAP, iSWAP, 1]",
        "p0": p0,
        "bitstring_q0_first": bitstring,
        "reversed": bitstring[::-1],
        "weakest_margin": min(abs(x - 0.5) for x in p0),
        "elapsed_s": time.monotonic() - started,
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
