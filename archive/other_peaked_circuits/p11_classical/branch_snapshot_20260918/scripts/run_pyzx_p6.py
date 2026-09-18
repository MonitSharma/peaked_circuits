#!/usr/bin/env python3
"""Run bounded exact PyZX reductions on the P6 circuit.

Both reductions operate on a Qiskit-transpiled ``rz/sx/x/cx`` circuit.  The
rewrites are exact; this script does not snap arbitrary rotations to Clifford
values or use the target answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps


def _count_2q(circuit) -> int:
    return sum(getattr(gate, "name", "").lower() in {"cx", "cz", "cnot", "crz"}
               for gate in circuit.gates)


def _run_mode(zx, qasm: str, mode: str):
    circuit = zx.Circuit.from_qasm(qasm)
    graph = circuit.to_graph()
    before_vertices = graph.num_vertices()
    if mode == "full_reduce":
        zx.simplify.full_reduce(graph)
        extracted = zx.extract_circuit(graph)
    elif mode == "teleport_reduce":
        zx.simplify.teleport_reduce(graph)
        # teleport_reduce deliberately preserves the graph topology and may
        # leave a phase-master graph that is not graph-like.  Use PyZX's
        # topology-preserving conversion path rather than extract_circuit,
        # which requires a graph-like diagram.
        extracted = zx.Circuit.from_graph(graph).split_phase_gates()
    else:
        raise ValueError(mode)
    return extracted, before_vertices, graph.num_vertices()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--modes", nargs="+", choices=["full_reduce", "teleport_reduce"],
                    default=["full_reduce", "teleport_reduce"])
    args = ap.parse_args()
    import pyzx as zx

    args.outdir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    source = args.source.resolve()
    circuit = QuantumCircuit.from_qasm_file(str(source))
    basis = transpile(circuit, basis_gates=["rz", "sx", "x", "cx"], optimization_level=0)
    qasm = dumps(basis)
    qasm = re.sub(
        r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?[eE][-+]?\d+",
        lambda m: f"{float(m.group()):.17f}",
        qasm,
    )
    input_payload = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "n_qubits": circuit.num_qubits,
        "source_ops": len(circuit.data),
        "basis_ops": len(basis.data),
        "basis_2q": sum(len(qargs) == 2 for inst, qargs, _ in basis.data),
        "basis": ["rz", "sx", "x", "cx"],
        "answer_blind": True,
        "equivalence": "exact_graph_rewrite",
    }
    (args.outdir / "input.json").write_text(json.dumps(input_payload, indent=2) + "\n")

    results = {}
    for mode in args.modes:
        t0 = time.monotonic()
        extracted, before_vertices, after_vertices = _run_mode(zx, qasm, mode)
        out_qasm = args.outdir / f"p6_pyzx_{mode}.qasm"
        out_qasm.write_text(extracted.to_qasm())
        results[mode] = {
            "before_2q": _count_2q(zx.Circuit.from_qasm(qasm)),
            "after_2q": _count_2q(extracted),
            "before_vertices": before_vertices,
            "after_vertices": after_vertices,
            "after_gates": len(extracted.gates),
            "reduced_qasm": str(out_qasm),
            "runtime_s": time.monotonic() - t0,
            "verdict": "MATERIAL_REDUCTION" if _count_2q(extracted) < _count_2q(zx.Circuit.from_qasm(qasm)) else "NO_MATERIAL_REDUCTION",
        }
    payload = {**input_payload, "modes": results, "runtime_total_s": time.monotonic() - start}
    (args.outdir / "pyzx_p6_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
