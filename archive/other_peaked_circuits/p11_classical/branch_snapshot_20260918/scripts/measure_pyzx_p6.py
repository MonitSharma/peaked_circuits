#!/usr/bin/env python3
"""Measure answer-blind structural proxies for original and PyZX P6 QASM.

These metrics intentionally stay independent of the readout answer.  The
``work_gate_proxy`` is a raw unitary-operation count; it is not claimed to be
the production solver's consolidated U-gate count when the input is in a
different basis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from qiskit import QuantumCircuit


def measure(path: Path) -> dict:
    circuit = QuantumCircuit.from_qasm_file(str(path))
    edges: Counter[tuple[int, int]] = Counter()
    spans: list[int] = []
    twoq = 0
    for instruction in circuit.data:
        qubits = [circuit.find_bit(q).index for q in instruction.qubits]
        if len(qubits) != 2:
            continue
        a, b = sorted(qubits)
        edges[(a, b)] += 1
        spans.append(b - a)
        twoq += 1

    n = circuit.num_qubits
    # Natural-order edge cutwidth: maximum number of distinct interaction
    # edges crossing a qubit-index cut.  This is a transparent routing proxy,
    # not an optimized minimum-cutwidth result.
    cutwidth = 0
    cut_profile = []
    for cut in range(n - 1):
        crossing = sum(a <= cut < b for a, b in edges)
        cut_profile.append(crossing)
        cutwidth = max(cutwidth, crossing)

    counts = Counter(instruction.operation.name.lower() for instruction in circuit.data)
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "qubits": n,
        "total_ops": len(circuit.data),
        "one_qubit_ops": len(circuit.data) - twoq,
        "two_qubit_ops": twoq,
        "depth": circuit.depth(),
        "interaction_edges": len(edges),
        "interaction_edge_events": twoq,
        "natural_order_cutwidth": cutwidth,
        "natural_order_cutwidth_mean": (sum(cut_profile) / len(cut_profile)) if cut_profile else 0.0,
        "interaction_span_max": max(spans, default=0),
        "interaction_span_mean": (sum(spans) / len(spans)) if spans else 0.0,
        "work_gate_proxy": len(circuit.data),
        "gate_counts": dict(sorted(counts.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--reduced", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = {"answer_blind": True, "circuits": [measure(args.original)]}
    payload["circuits"].extend(measure(path) for path in args.reduced)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
